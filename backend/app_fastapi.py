"""
FastAPI 后端服务 - DJAgent 风控智能助手
"""

import os
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入Agent模块（尝试导入，失败则降级到简化模式）
HAS_AGENT_SDK = False
UnifiedAgent = None

try:
    from agents.unified_agent import UnifiedAgent
    from agents.session_manager import get_or_create_manager_agent

    HAS_AGENT_SDK = True
    logger.info("[INFO] UnifiedAgent 导入成功")
except ImportError as e:
    logger.warning(f"[WARNING] UnifiedAgent导入失败 {e}，将使用简化模式")
    UnifiedAgent = None

# 导入认证模块
try:
    from auth import validate_user

    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False

# FastAPI 应用
app = FastAPI(title="DJAgent API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据目录
DATA_DIR = Path(__file__).parent.parent / "data"

# 导入 SSE 事件管理器
from agents.sse_events import sse_manager


def read_csv_file(filename: str) -> List[Dict]:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.error(f"[ERROR] 读取文件失败: {e}")
        return []


def write_csv_file(filename: str, data: List[Dict], fieldnames: List[str]) -> bool:
    filepath = DATA_DIR / filename
    try:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        return True
    except Exception as e:
        logger.error(f"[ERROR] 写入文件失败: {e}")
        return False


# ============ 用户接口 ============


@app.get("/api/users")
async def get_users():
    return read_csv_file("users.csv")


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    users = read_csv_file("users.csv")
    user = next((u for u in users if u["user_id"] == user_id), None)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")


# ============ 任务接口 ============


@app.get("/api/tasks")
async def get_tasks(user_id: Optional[str] = None, task_type: Optional[str] = None):
    tasks = read_csv_file("tasks.csv")

    # 按任务类型过滤（日度/月度）
    if task_type:
        tasks = [t for t in tasks if t.get("task_type") == task_type]

    if user_id:
        users = read_csv_file("users.csv")
        user = next((u for u in users if u["user_id"] == user_id), None)
        if user:
            role = user.get("role", "")
            if role in ["业务负责人", "普通分析人员"]:
                tasks = [t for t in tasks if t["creator_id"] == user_id]
            else:
                tasks = [t for t in tasks if t["assigned_to_id"] == user_id]

    return tasks


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = read_csv_file("tasks.csv")
    task = next((t for t in tasks if t["task_id"] == task_id), None)
    if task:
        return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/api/tasks")
async def create_task(request: Request):
    data = await request.json()
    tasks = read_csv_file("tasks.csv")

    # 使用员工编号 + 时间戳（精确到毫秒）+ 序号作为任务ID
    # 格式: 001-20260312112289456-001 (首个任务)
    #       001-20260312112289456-002 (同时间第2个任务)
    # 员工编号：去掉了 "EMP_" 或 "EMP" 前缀
    creator_id_raw = data.get("creator_id", "000")
    employee_no = creator_id_raw.replace("EMP_", "").replace("EMP", "")
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]  # 精确到毫秒
    base_task_id = f"{employee_no}-{timestamp}"

    # 检查是否有相同 base_task_id 的任务，序号从1开始递增（3位数）
    existing_count = sum(1 for t in tasks if t["task_id"].startswith(base_task_id))
    new_task_id = f"{base_task_id}-{existing_count + 1:03d}"

    # Task Type：用户没指定就默认"日度"
    task_type = data.get("task_type", "日度")
    if task_type not in ["日度", "月度"]:
        task_type = "日度"

    new_task = {
        "task_id": new_task_id,
        "creator_id": data.get("creator_id"),
        "creator_name": data.get("creator_name"),
        "assigned_to_id": data.get("assigned_to_id"),
        "assigned_to_name": data.get("assigned_to_name"),
        "status": "已创建",
        "created_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "risk_summary": data.get("risk_summary"),
        "risk_data_url": data.get("risk_data_url"),
        "suggested_receiver_id": data.get("assigned_to_id"),
        "confirmed_receiver_id": data.get("assigned_to_id"),
        "completed_time": "",
        "region": data.get("region", ""),
        "task_type": task_type,
    }

    tasks.append(new_task)
    fieldnames = list(new_task.keys())

    if write_csv_file("tasks.csv", tasks, fieldnames):
        # 发送 SSE 通知
        try:
            from agents.sse_events import notify_task_created
            await notify_task_created(
                new_task["creator_id"],
                new_task_id,
                new_task
            )
            logger.info(f"[API] 任务 {new_task_id} 创建成功，已发送 SSE 通知")
        except Exception as e:
            logger.error(f"[API] SSE 通知发送失败: {e}")

        return new_task
    raise HTTPException(status_code=500, detail="Failed to create task")


# ============ Agent对话接口 ============


@app.post("/api/chat")
async def chat(request: Request):
    from agents.session_manager import get_or_create_manager_agent

    # 支持 JSON 和 FormData 两种格式
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # FormData 格式（包含文件上传）
        form = await request.form()
        message = form.get("message", "")
        user_id = form.get("user_id", "manager_default")
        username = form.get("username", "业务负责人")
        task_id = form.get("task_id")

        # 处理文件上传 - 使用 getlist 获取所有同名文件
        files = form.getlist("files")
        if files:
            for f in files:
                logger.info(f"[API] 收到文件: {f.filename}")
            logger.info(f"[API] 共收到 {len(files)} 个文件")

        # 保存文件到临时目录
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp()
        saved_files = []
        for f in files:
            file_path = os.path.join(temp_dir, f.filename)
            content = await f.read()
            with open(file_path, 'wb') as pf:
                pf.write(content)
            saved_files.append(file_path)
            logger.info(f"[API] 文件已保存: {file_path}")
    else:
        # JSON 格式
        try:
            data = await request.json()
            message = data.get("message", "")
            user_id = data.get("user_id", "manager_default")
            username = data.get("username", "业务负责人")
            task_id = data.get("task_id")
            saved_files = []
        except Exception:
            message = ""
            user_id = "manager_default"
            username = "业务负责人"
            task_id = None
            saved_files = []

    logger.info(f"[API] 用户消息: {message}")
    logger.info(f"[API] 上传文件数: {len(saved_files) if saved_files else 0}")

    if not HAS_AGENT_SDK:
        response_text = (
            f"收到您的消息：{message}\n\n（当前为简化模式，未连接 Agent SDK）"
        )
    else:
        try:
            agent = await get_or_create_manager_agent(user_id, username)
            response_text = await agent.chat(message, files=saved_files if saved_files else None)
            logger.info(f"[API] ManagerAgent 回复成功")
        except Exception as e:
            logger.error(f"[ERROR] ManagerAgent 调用失败: {str(e)}")
            response_text = "抱歉，我现在无法回答您的问题，请稍后再试。"

    return {
        "message": response_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============ 风险数据接口 ============


@app.get("/api/risk-data")
async def get_all_risk_data():
    """获取所有风险数据文件列表和内容"""
    risk_files = []

    for file_path in DATA_DIR.glob("risk_data_*.csv"):
        # 排除月度数据文件
        if "monthly" in file_path.name:
            continue
        try:
            data = read_csv_file(file_path.name)
            risk_files.append(
                {"filename": file_path.name, "data": data, "count": len(data)}
            )
        except Exception as e:
            logger.error(f"读取风险数据文件失败 {file_path}: {e}")

    return risk_files


@app.get("/api/risk-data/monthly")
async def get_monthly_risk_data():
    """获取所有月度风险数据文件列表"""
    risk_files = []

    for file_path in sorted(DATA_DIR.glob("risk_data_monthly_*.csv")):
        try:
            data = read_csv_file(file_path.name)
            # 从文件名提取月份
            month = file_path.stem.replace("risk_data_monthly_", "")
            risk_files.append(
                {"filename": file_path.name, "month": month, "data": data, "count": len(data)}
            )
        except Exception as e:
            logger.error(f"读取月度风险数据文件失败 {file_path}: {e}")

    return risk_files


@app.get("/api/risk-data/{identifier}")
async def get_risk_data_file(identifier: str):
    """获取单个风险数据文件内容

    支持格式：
    - /api/risk-data/001  -> risk_data_001.csv
    - /api/risk-data/risk_data_001.csv -> 直接使用
    - /api/risk-data/monthly_01 -> risk_data_monthly_01.csv (月度数据)
    - /api/risk-data/monthly_1 -> risk_data_monthly_01.csv
    """
    try:
        import re

        # 处理月度数据标识
        if identifier.startswith('monthly_'):
            # monthly_01 或 monthly_1 -> risk_data_monthly_01.csv
            month_part = identifier.replace('monthly_', '')
            if month_part.isdigit():
                month_num = int(month_part)
                filename = f"risk_data_monthly_{month_num:02d}.csv"
            else:
                filename = f"risk_data_{identifier}.csv"
        elif identifier.isdigit():
            num = int(identifier)
            filename = f"risk_data_{num:03d}.csv"
        elif identifier.startswith("risk_data_") and identifier.endswith(".csv"):
            filename = identifier
        else:
            match = re.search(r"\d+", identifier)
            if match:
                num = int(match.group())
                filename = f"risk_data_{num:03d}.csv"
            else:
                filename = f"risk_data_{identifier}.csv"

        data = read_csv_file(filename)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"风险数据文件不存在: {filename}"
            )

        return {
            "filename": filename,
            "identifier": identifier,
            "data": data,
            "count": len(data),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取风险数据文件失败 {identifier}: {e}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


# ============ 任务反馈接口 ============


@app.get("/api/tasks/{task_id}/creation-history")
async def get_task_creation_history(task_id: str):
    """获取任务创建时的聊天历史"""
    feedback_path = DATA_DIR / "feedback" / f"{task_id}_creation.json"

    if feedback_path.exists():
        with open(feedback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("chat_history"):
                return data["chat_history"]

    return []


@app.get("/api/feedback/{task_id}")
async def get_task_feedback(task_id: str):
    """获取任务反馈信息"""
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"

    if feedback_path.exists():
        with open(feedback_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "task_id": task_id,
        "chat_history": [],
        "uploaded_files": [],
        "status": "未开始",
    }


@app.post("/api/tasks/{task_id}/upload-file")
async def upload_task_file(task_id: str, request: Request):
    """上传任务相关文件"""
    try:
        form = await request.form()
        file = form.get("file")
        user_id = form.get("user_id")

        if not file:
            raise HTTPException(status_code=400, detail="未上传文件")

        filename = form.get("filename")
        if not filename:
            filename = getattr(file, "filename", "uploaded_file")

        upload_dir = DATA_DIR / "uploads" / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
        feedback_data = {}
        if feedback_path.exists():
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedback_data = json.load(f)

        if "uploaded_files" not in feedback_data:
            feedback_data["uploaded_files"] = []

        feedback_data["uploaded_files"].append(
            {
                "filename": filename,
                "file_path": str(file_path),
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": user_id,
            }
        )

        with open(feedback_path, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": f"文件 {filename} 上传成功",
            "file_path": str(file_path),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


# ============ 子Agent对话接口 ============


@app.get("/api/tasks/{task_id}/chat-history")
async def get_chat_history(task_id: str, user_id: str = None, username: str = None):
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"

    if feedback_path.exists():
        with open(feedback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("chat_history"):
                return data["chat_history"]

    if not HAS_AGENT_SDK:
        return [{"message": "Agent SDK未安装，无法加载任务", "sender": "Agent"}]

    try:
        agent = StaffAgent(user_id, username)
        async with agent:
            initial_message = await agent.init_task(task_id)

        feedback_data = {
            "task_id": task_id,
            "chat_history": [
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sender": "Agent",
                    "message": initial_message,
                    "message_type": "text",
                }
            ],
            "uploaded_files": [],
            "status": "进行中",
        }

        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        with open(feedback_path, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        return feedback_data["chat_history"]
    except Exception as e:
        logger.error(f"[ERROR] Agent初始化失败: {str(e)}")
        return [{"message": "任务加载失败", "sender": "Agent"}]


@app.post("/api/tasks/{task_id}/message")
async def send_message(task_id: str, request: Request):
    from agents.session_manager import get_or_create_staff_agent

    # 支持 JSON 和 FormData 两种格式
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        message = form.get("message", "")
        user_id = form.get("user_id")
        username = form.get("username", "")

        # 处理文件上传
        files = form.getlist("files")
        if files:
            import tempfile
            import os
            temp_dir = tempfile.mkdtemp()
            saved_files = []
            file_info_list = []  # 保存文件名和类型信息
            for f in files:
                file_path = os.path.join(temp_dir, f.filename)
                content = await f.read()
                with open(file_path, 'wb') as pf:
                    pf.write(content)
                saved_files.append(file_path)
                # 保存文件信息
                file_info_list.append({
                    "name": f.filename,
                    "type": f.content_type or "application/octet-stream"
                })
                logger.info(f"[API] Staff 文件已保存: {file_path}")
        else:
            saved_files = []
            file_info_list = []
    else:
        try:
            data = await request.json()
            message = data.get("message", "")
            user_id = data.get("user_id")
            username = data.get("username", "")
        except Exception:
            message = ""
            user_id = None
            username = ""
        saved_files = []
        file_info_list = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user_message = {
        "timestamp": timestamp,
        "sender": username,
        "message": message,
        "message_type": "text",
        "files": file_info_list if file_info_list else None,
    }

    if not HAS_AGENT_SDK:
        ai_response = "Agent SDK未安装，暂时无法处理消息"
    else:
        try:
            agent = await get_or_create_staff_agent(user_id, username)
            agent.current_task_id = task_id
            ai_response = await agent.chat(message, files=saved_files if saved_files else None)
        except Exception as e:
            logger.error(f"[ERROR] Agent调用失败: {str(e)}")
            ai_response = "好的，请继续。"

    agent_reply = {
        "timestamp": timestamp,
        "sender": "Agent",
        "message": ai_response,
        "message_type": "text",
    }

    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
    feedback_data = {}

    if feedback_path.exists():
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedback_data = json.load(f)
        except Exception as e:
            logger.error(f"[ERROR] 读取反馈文件失败: {e}")

    if "chat_history" not in feedback_data:
        feedback_data["chat_history"] = []

    feedback_data["chat_history"].append(user_message)
    feedback_data["chat_history"].append(agent_reply)
    feedback_data["task_id"] = task_id
    feedback_data["last_updated"] = timestamp

    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    with open(feedback_path, "w", encoding="utf-8") as f:
        json.dump(feedback_data, f, ensure_ascii=False, indent=2)

    return {"user_message": user_message, "agent_reply": agent_reply}

    try:
        agent = StaffAgent(user_id, username)
        async with agent:
            agent.current_task_id = task_id
            ai_response = await agent.chat(message)
    except Exception as e:
        logger.error(f"[ERROR] Agent调用失败: {str(e)}")
        ai_response = "好的，请继续。"

    agent_reply = {
        "timestamp": timestamp,
        "sender": "Agent",
        "message": ai_response,
        "message_type": "text",
    }

    return {"user_message": user_message, "agent_reply": agent_reply}


# ============ 会话管理接口 ============


@app.post("/api/logout")
async def logout(request: Request):
    """用户登出时清理会话"""
    from agents.session_manager import close_agent

    try:
        data = await request.json()
        user_id = data.get("user_id")

        if user_id:
            await close_agent(user_id)
            logger.info(f"[API] 用户 {user_id} 登出，会话已关闭")

        return {"status": "success", "message": "登出成功"}
    except Exception as e:
        logger.error(f"[ERROR] 登出失败: {str(e)}")
        return {"status": "error", "message": "登出失败"}


@app.post("/api/session/cleanup")
async def cleanup_sessions(request: Request):
    """清理指定用户的会话"""
    from agents.session_manager import close_agent

    try:
        data = await request.json()
        user_ids = data.get("user_ids", [])

        closed_count = 0
        for user_id in user_ids:
            await close_agent(user_id)
            closed_count += 1

        logger.info(f"[API] 清理了 {closed_count} 个会话")

        return {"status": "success", "closed_count": closed_count}
    except Exception as e:
        logger.error(f"[ERROR] 清理会话失败: {str(e)}")
        return {"status": "error", "message": str(e)}


# ============ 健康检查 ============


@app.on_event("startup")
async def startup_event():
    logger.info("[API] 服务启动")
    from agents.session_manager import close_all_agents

    await close_all_agents()
    logger.info("[API] 已清理所有旧会话")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[API] 服务关闭")
    from agents.session_manager import close_all_agents

    await close_all_agents()
    logger.info("[API] 已关闭所有会话")


# ============ SSE 事件流端点 ============

@app.get("/api/events/{user_id}")
async def sse_events(user_id: str):
    """
    SSE 事件流端点，用于实时推送任务通知

    推送的事件类型：
    - task_created: Manager 创建了新任务
    - new_task: 有新任务分配给当前用户（Staff）
    - task_completed: 任务被标记为反馈完成
    """
    async def event_generator():
        queue = asyncio.Queue()
        sse_manager.subscribe(user_id, queue)

        try:
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            logger.info(f"[SSE] 用户 {user_id} 连接断开")
        finally:
            sse_manager.unsubscribe(user_id, queue)
            logger.info(f"[SSE] 用户 {user_id} 取消订阅")

    from fastapi.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "data_dir": str(DATA_DIR),
    }



# ============ Staff任务通知API ============

@app.post("/api/tasks/{task_id}/notify-staff")
async def notify_staff_task(task_id: str, request: Request):
    """
    触发Staff端任务通知 - 方案A核心API

    当Staff端收到SSE新任务事件后，前端调用此API
    后端会调用Staff Agent发送引导消息给用户

    Args:
        task_id: 任务ID

    Returns:
        Agent发送的消息
    """
    from agents.session_manager import get_or_create_staff_agent

    logger.info(f"[API] >>> notify-staff 开始: task_id={task_id}")

    try:
        # 1. 获取请求体中的用户信息
        body = await request.json()
        user_id = body.get("user_id")
        username = body.get("username")

        logger.info(f"[API] 请求用户: user_id={user_id}, username={username}")

        if not user_id or not username:
            raise HTTPException(status_code=400, detail="缺少user_id或username")

        # 2. 获取任务信息
        tasks = read_csv_file("tasks.csv")
        task_info = next((t for t in tasks if t.get("task_id") == task_id), None)

        if not task_info:
            logger.error(f"[API] 任务不存在: {task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")

        logger.info(f"[API] 任务信息: {task_info}")

        # 3. 验证用户是否是任务的执行人
        assigned_to_id = task_info.get("assigned_to_id")
        if assigned_to_id != user_id:
            logger.warning(f"[API] ⚠️ 用户不匹配: 请求user_id={user_id}, 任务assigned_to_id={assigned_to_id}")
            # 仍然允许发送，但记录警告

        # 4. 获取或创建Staff Agent
        logger.info(f"[API] 获取Staff Agent: user_id={user_id}")
        agent = await get_or_create_staff_agent(user_id, username)

        # 5. 调用Agent发送通知
        logger.info(f"[API] 调用Agent发送通知...")
        result = await agent.notify_new_task(task_id, task_info)

        if result.get("success"):
            logger.info(f"[API] >>> notify-staff 成功: {result.get('message')[:100]}...")
            return {
                "success": True,
                "message": result.get("message"),
                "task_id": task_id
            }
        else:
            logger.error(f"[API] >>> notify-staff 失败: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "发送失败"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] >>> notify-staff 异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5005)
