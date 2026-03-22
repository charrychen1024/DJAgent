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


def read_csv_file(filename: str, data_dir: Path = None) -> List[Dict]:
    """读取CSV文件

    Args:
        filename: 文件名
        data_dir: 数据目录，默认使用 DATA_DIR
    """
    if data_dir is None:
        data_dir = DATA_DIR
    filepath = data_dir / filename
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
    """获取用户列表（不返回user_id字段）"""
    users = read_csv_file("users.csv")
    # 移除user_id字段
    return [{k: v for k, v in u.items() if k != "user_id"} for u in users]


@app.get("/api/users/{employee_id}")
async def get_user(employee_id: str):
    """
    获取用户信息，支持 user_id 或 employee_id 查询
    注意：不返回 user_id 字段，避免与 employee_id 混淆
    """
    users = read_csv_file("users.csv")
    # 支持 user_id 或 employee_id 匹配
    user = next((u for u in users if u["employee_id"] == employee_id or u.get("employee_id") == employee_id), None)
    if user:
        # 移除 user_id 字段，只返回其他信息
        user_info = {k: v for k, v in user.items() if k != "user_id"}
        return user_info
    raise HTTPException(status_code=404, detail="User not found")


# ============ 任务接口 ============


@app.get("/api/tasks")
async def get_tasks(employee_id: Optional[str] = None, task_type: Optional[str] = None):
    tasks = read_csv_file("tasks.csv")

    # 按任务类型过滤（日度/月度）
    if task_type:
        tasks = [t for t in tasks if t.get("task_type") == task_type]

    # 超期判断：检查"反馈中"状态的任务是否已超时
    from datetime import datetime
    now = datetime.now()
    for task in tasks:
        if task.get("status") == "反馈中":
            deadline_str = task.get("feedback_deadline", "")
            if deadline_str:
                try:
                    deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
                    if now > deadline:
                        task["status"] = "已超时"
                        # 更新CSV中的状态
                        _update_task_status(task["task_id"], "已超时")
                except ValueError:
                    pass

    if employee_id:
        users = read_csv_file("users.csv")

        # 支持 user_id 或 employee_id 匹配
        user = next((u for u in users if u["employee_id"] == employee_id or u.get("employee_id") == employee_id), None)

        if user:
            role = user.get("role", "")
            user_employee_id = user.get("employee_id", "")  # 如 EMP_001

            # 总部管理员(EMP_000)：查看所有任务
            if user_employee_id == "EMP_000" or user.get("user_id") == "000":
                pass  # 不做任何过滤，返回所有任务
            # 业务负责人/分析人员：查看自己创建的任务（用 employee_id 匹配）
            elif role in ["业务负责人", "普通分析人员"]:
                tasks = [t for t in tasks if t["creator_id"] == user_employee_id]
            else:
                # 一线人员：查看分配给自己的任务（用 employee_id 匹配）
                tasks = [t for t in tasks if t["assigned_to_id"] == user_employee_id]

    # 按创建时间倒序排序，最新创建的任务排在前面
    tasks = sorted(tasks, key=lambda t: t.get("created_time", ""), reverse=True)

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
    users = read_csv_file("users.csv")

    # 解析 creator_id：支持 user_id、employee_id、姓名
    creator_input = data.get("creator_id", "000")
    creator_name_input = data.get("creator_name", "总部管理员")
    
    # 尝试从 users.csv 匹配正确的 user_id
    creator_user = None
    if creator_input.startswith("EMP_"):
        # 员工编号格式，如 EMP_001
        creator_user = next((u for u in users if u.get("employee_id") == creator_input), None)
    elif creator_input.startswith("EMP"):
        # 去掉 EMP 前缀
        creator_user = next((u for u in users if u.get("employee_id") == f"EMP_{creator_input.replace('EMP', '')}"), None)
    else:
        # 尝试匹配 user_id 或 username
        creator_user = next((u for u in users if u["employee_id"] == creator_input or u["username"] == creator_name_input), None)
    
    # 确定最终的 creator_id（存储 employee_id，如 EMP_001）
    if creator_user:
        creator_id = creator_user["employee_id"]  # 改为存储 employee_id
        creator_name = creator_user["username"]
    else:
        # 标准化处理，确保返回 EMP_xxx 格式
        if creator_input.startswith("EMP_"):
            creator_id = creator_input
        elif creator_input.startswith("EMP"):
            creator_id = f"EMP_{creator_input.replace('EMP', '')}"
        else:
            creator_id = creator_input if not creator_input.startswith("EMP") else "EMP_000"
        creator_name = creator_name_input
    
    # 解析 assigned_to_id：支持 user_id、employee_id、姓名
    assigned_input = data.get("assigned_to_id", "")
    assigned_name_input = data.get("assigned_to_name", "")
    
    assigned_user = None
    if assigned_input:
        if assigned_input.startswith("EMP_"):
            assigned_user = next((u for u in users if u.get("employee_id") == assigned_input), None)
        elif assigned_input.startswith("EMP"):
            assigned_user = next((u for u in users if u.get("employee_id") == f"EMP_{assigned_input.replace('EMP', '')}"), None)
        else:
            # 尝试匹配 user_id 或 username（优先匹配姓名）
            assigned_user = next((u for u in users if u["employee_id"] == assigned_input or u["username"] == assigned_name_input), None)
    
    # 确定最终的 assigned_to_id（存储 employee_id，如 EMP_001）
    if assigned_user:
        assigned_to_id = assigned_user["employee_id"]  # 改为存储 employee_id
        assigned_to_name = assigned_user["username"]
    else:
        # 标准化处理，确保返回 EMP_xxx 格式
        if assigned_input.startswith("EMP_"):
            assigned_to_id = assigned_input
        elif assigned_input.startswith("EMP"):
            assigned_to_id = f"EMP_{assigned_input.replace('EMP', '')}"
        else:
            assigned_to_id = assigned_input
        assigned_to_name = assigned_name_input
    
    # 使用员工编号 + 时间戳（精确到毫秒）+ 序号作为任务ID
    employee_no = creator_id.replace("EMP_", "").replace("EMP", "")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    base_task_id = f"{employee_no}-{timestamp}"

    existing_count = sum(1 for t in tasks if t["task_id"].startswith(base_task_id))
    new_task_id = f"{base_task_id}-{existing_count + 1:03d}"

    task_type = data.get("task_type", "日度")
    if task_type not in ["日度", "月度"]:
        task_type = "日度"

    new_task = {
        "task_id": new_task_id,
        "creator_id": creator_id,
        "creator_name": creator_name,
        "assigned_to_id": assigned_to_id,
        "assigned_to_name": assigned_to_name,
        "status": "已创建",
        "created_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "risk_summary": data.get("risk_summary"),
        "risk_data_url": data.get("risk_data_url"),
        "suggested_receiver_id": assigned_to_id,
        "confirmed_receiver_id": assigned_to_id,
        "completed_time": "",
        "region": data.get("region", "") or creator_user.get("region", "") if creator_user else "",
        "task_type": task_type,
        "sent_time": "",
        "feedback_deadline": data.get("feedback_deadline", ""),
        "feedback_summary": "",
    }

    tasks.append(new_task)
    fieldnames = list(new_task.keys())

    if write_csv_file("tasks.csv", tasks, fieldnames):
        logger.info(f"[API] 创建任务: {new_task_id}, 创建人: {creator_id}({creator_name}), 接收人: {assigned_to_id}({assigned_to_name})")
        
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
        employee_id = form.get("employee_id", "manager_default")
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
            employee_id = data.get("employee_id", "manager_default")
            username = data.get("username", "业务负责人")
            task_id = data.get("task_id")
            saved_files = []
        except Exception:
            message = ""
            employee_id = "manager_default"
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
            agent = await get_or_create_manager_agent(employee_id, username)
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
async def get_all_risk_data(
    employee_id: Optional[str] = None,
    region_filter: Optional[str] = None
):
    """获取所有风险数据文件列表和内容
    - 总部管理员(EMP_000)：返回所有地区数据
    - 其他用户：只返回自己所属地区的数据
    """
    # 获取用户信息，确定地区
    user_region = None
    is_admin = False
    
    if employee_id:
        users = read_csv_file("users.csv")
        user = next((u for u in users if u.get("employee_id") == employee_id or u["employee_id"] == employee_id), None)
        if user:
            user_region = user.get("region", "")
            is_admin = (user.get("employee_id") == "EMP_000" or user.get("user_id") == "000")
    
    # 如果指定了region_filter参数，优先使用
    if region_filter:
        user_region = region_filter

    risk_files = []
    risk_data_dir = DATA_DIR / "risk_data"

    for file_path in risk_data_dir.glob("risk_data_*.csv"):
        if "monthly" in file_path.name:
            continue
        try:
            data = read_csv_file(file_path.name, risk_data_dir)
            
            # 根据用户地区过滤数据
            if not is_admin and user_region:
                data = [row for row in data if row.get("region") == user_region]
            
            risk_files.append(
                {"filename": file_path.name, "data": data, "count": len(data)}
            )
        except Exception as e:
            logger.error(f"读取风险数据文件失败 {file_path}: {e}")

    return risk_files


@app.get("/api/risk-data/monthly")
async def get_monthly_risk_data(
    employee_id: Optional[str] = None,
    region_filter: Optional[str] = None
):
    """获取所有月度风险数据文件列表
    - 总部管理员(EMP_000)：返回所有地区数据
    - 其他用户：只返回自己所属地区的数据
    """
    # 获取用户信息，确定地区
    user_region = None
    is_admin = False
    
    if employee_id:
        users = read_csv_file("users.csv")
        user = next((u for u in users if u.get("employee_id") == employee_id or u["employee_id"] == employee_id), None)
        if user:
            user_region = user.get("region", "")
            is_admin = (user.get("employee_id") == "EMP_000" or user.get("user_id") == "000")
    
    # 如果指定了region_filter参数，优先使用
    if region_filter:
        user_region = region_filter

    risk_files = []
    risk_data_dir = DATA_DIR / "risk_data"

    for file_path in sorted(risk_data_dir.glob("risk_data_monthly_*.csv")):
        try:
            data = read_csv_file(file_path.name, risk_data_dir)
            
            # 根据用户地区过滤数据
            if not is_admin and user_region:
                data = [row for row in data if row.get("region") == user_region]
            
            month = file_path.stem.replace("risk_data_monthly_", "")
            risk_files.append(
                {"filename": file_path.name, "month": month, "data": data, "count": len(data)}
            )
        except Exception as e:
            logger.error(f"读取月度风险数据文件失败 {file_path}: {e}")

    return risk_files


@app.get("/api/risk-data/{identifier}")
async def get_risk_data_file(
    identifier: str,
    employee_id: Optional[str] = None,
    region_filter: Optional[str] = None
):
    """获取单个风险数据文件内容
    - 总部管理员(EMP_000)：返回所有地区数据
    - 其他用户：只返回自己所属地区的数据

    支持格式：
    - /api/risk-data/001  -> risk_data_001.csv
    - /api/risk-data/risk_data_001.csv -> 直接使用
    - /api/risk-data/monthly_01 -> risk_data_monthly_01.csv (月度数据)
    - /api/risk-data/monthly_1 -> risk_data_monthly_01.csv
    """
    try:
        import re

        # 获取用户信息，确定地区
        user_region = None
        is_admin = False
        
        if employee_id:
            users = read_csv_file("users.csv")
            user = next((u for u in users if u.get("employee_id") == employee_id or u["employee_id"] == employee_id), None)
            if user:
                user_region = user.get("region", "")
                is_admin = (user.get("employee_id") == "EMP_000" or user.get("user_id") == "000")
        
        # 如果指定了region_filter参数，优先使用
        if region_filter:
            user_region = region_filter

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

        # 风险数据在 risk_data 子目录
        risk_data_dir = DATA_DIR / "risk_data"
        data = read_csv_file(filename, risk_data_dir)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"风险数据文件不存在: {filename}"
            )

        # 根据用户地区过滤数据
        if not is_admin and user_region:
            data = [row for row in data if row.get("region") == user_region]

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
        employee_id = form.get("employee_id")

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
                "employee_id": employee_id,
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
async def get_chat_history(task_id: str, employee_id: str = None, username: str = None):
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"

    if feedback_path.exists():
        with open(feedback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("chat_history"):
                return data["chat_history"]

    if not HAS_AGENT_SDK:
        return [{"message": "Agent SDK未安装，无法加载任务", "sender": "Agent"}]

    try:
        agent = StaffAgent(employee_id, username)
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
        employee_id = form.get("employee_id")
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
            employee_id = data.get("employee_id")
            username = data.get("username", "")
        except Exception:
            message = ""
            employee_id = None
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

    # 首次调用时初始化任务（设置sent_time和feedback_deadline）- 无论Agent SDK是否安装都需要设置
    from agents.tools import get_task_detail, update_task_status
    from datetime import timedelta
    
    task_info = get_task_detail(task_id)
    task_data = task_info.get("task", {}) if task_info else {}
    if task_data and not task_data.get("sent_time"):
        current_time = datetime.now()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        task_type = task_data.get("task_type", "日度")
        deadline_hours = 72 if task_type == "月度" else 24
        deadline_time = current_time + timedelta(hours=deadline_hours)
        deadline_str = deadline_time.strftime("%Y-%m-%d %H:%M:%S")
        
        update_task_status(task_id, "反馈中", "", sent_time=current_time_str, feedback_deadline=deadline_str)
        logger.info(f"[API] 首次消息，已设置 sent_time={current_time_str}, feedback_deadline={deadline_str}")
    
    if not HAS_AGENT_SDK:
        ai_response = "Agent SDK未安装，暂时无法处理消息"
    else:
        try:
            agent = await get_or_create_staff_agent(employee_id, username)
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
        agent = StaffAgent(employee_id, username)
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
        employee_id = data.get("employee_id")

        if employee_id:
            await close_agent(employee_id)
            logger.info(f"[API] 用户 {employee_id} 登出，会话已关闭")

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
        employee_ids = data.get("employee_ids", [])

        closed_count = 0
        for employee_id in employee_ids:
            await close_agent(employee_id)
            closed_count += 1

        logger.info(f"[API] 清理了 {closed_count} 个会话")

        return {"status": "success", "closed_count": closed_count}
    except Exception as e:
        logger.error(f"[ERROR] 清理会话失败: {str(e)}")
        return {"status": "error", "message": str(e)}


# ============ Manager 对话管理接口 ============

CHATS_DIR = DATA_DIR / "chats"


def get_user_chats_dir(employee_id: str) -> Path:
    """获取用户对话存储目录"""
    user_dir = CHATS_DIR / employee_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def list_chats(employee_id: str) -> List[Dict]:
    """获取用户的所有对话列表"""
    user_dir = get_user_chats_dir(employee_id)
    chats = []
    for f in user_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                chat_data = json.load(fp)
                # 返回简化信息
                messages = chat_data.get("messages", [])
                first_msg_time = messages[0].get("timestamp") if messages else chat_data.get("created_at")
                chats.append({
                    "chat_id": chat_data.get("chat_id"),
                    "title": chat_data.get("title"),
                    "created_at": first_msg_time,
                    "messages": messages,  # 包含消息列表，用于前端判断是否有消息
                })
        except Exception as e:
            logger.error(f"[ERROR] 读取对话失败: {f}, {e}")
    # 按创建时间倒序
    chats.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return chats


def create_chat(employee_id: str, username: str) -> Dict:
    """创建新对话"""
    import uuid
    chat_id = f"CHAT_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    chat_data = {
        "chat_id": chat_id,
        "employee_id": employee_id,
        "username": username,
        "title": "新对话",
        "created_at": timestamp,
        "updated_at": timestamp,
        "messages": []
    }
    
    chat_path = get_user_chats_dir(employee_id) / f"{chat_id}.json"
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)
    
    return chat_data


def get_chat(chat_id: str, employee_id: str) -> Optional[Dict]:
    """获取对话详情"""
    chat_path = get_user_chats_dir(employee_id) / f"{chat_id}.json"
    if not chat_path.exists():
        return None
    with open(chat_path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_chat(chat_id: str, employee_id: str, messages: List[Dict], title: str = None) -> bool:
    """更新对话"""
    chat_path = get_user_chats_dir(employee_id) / f"{chat_id}.json"
    if not chat_path.exists():
        return False
    
    with open(chat_path, "r", encoding="utf-8") as f:
        chat_data = json.load(f)
    
    chat_data["messages"] = messages
    chat_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 如果传入了新标题且消息列表不为空，更新标题为第一条消息
    if title is None and messages:
        # 使用第一条消息作为标题（截取前50字符）
        first_msg = messages[0].get("message", "")
        if first_msg:
            chat_data["title"] = first_msg[:50] + ("..." if len(first_msg) > 50 else "")
    elif title:
        chat_data["title"] = title
    
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)
    
    return True


def delete_chat(chat_id: str, employee_id: str) -> bool:
    """删除对话"""
    chat_path = get_user_chats_dir(employee_id) / f"{chat_id}.json"
    if chat_path.exists():
        chat_path.unlink()
        return True
    return False


@app.get("/api/chats")
async def get_user_chats(employee_id: str):
    """获取用户的所有对话列表"""
    if not employee_id:
        return []
    return list_chats(employee_id)


@app.post("/api/chats")
async def create_new_chat(request: Request):
    """创建新对话"""
    try:
        data = await request.json()
        employee_id = data.get("employee_id")
        username = data.get("username", "用户")
        
        if not employee_id:
            return {"status": "error", "message": "缺少 employee_id"}
        
        chat_data = create_chat(employee_id, username)
        return {"status": "success", "chat": chat_data}
    except Exception as e:
        logger.error(f"[ERROR] 创建对话失败: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/chats/{chat_id}")
async def get_chat_detail(chat_id: str, employee_id: str):
    """获取对话详情"""
    if not employee_id:
        return {"status": "error", "message": "缺少 employee_id"}
    
    chat = get_chat(chat_id, employee_id)
    if not chat:
        return {"status": "error", "message": "对话不存在"}
    
    return {"status": "success", "chat": chat}


@app.delete("/api/chats/{chat_id}")
async def delete_chat_by_id(chat_id: str, employee_id: str):
    """删除对话"""
    if not employee_id:
        return {"status": "error", "message": "缺少 employee_id"}
    
    success = delete_chat(chat_id, employee_id)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "对话不存在"}


@app.post("/api/chats/{chat_id}/messages")
async def send_chat_message(chat_id: str, request: Request):
    """发送消息到对话"""
    from agents.session_manager import get_or_create_manager_agent

    content_type = request.headers.get("content-type", "")
    
    # 解析请求数据
    if "multipart/form-data" in content_type:
        form = await request.form()
        message = form.get("message", "")
        employee_id = form.get("employee_id")
        username = form.get("username", "业务负责人")
        
        files = form.getlist("files")
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
    else:
        try:
            data = await request.json()
            message = data.get("message", "")
            employee_id = data.get("employee_id")
            username = data.get("username", "业务负责人")
        except Exception:
            return {"status": "error", "message": "请求解析失败"}
        saved_files = []

    if not employee_id or not message:
        return {"status": "error", "message": "缺少必要参数"}

    # 获取或创建对话
    chat = get_chat(chat_id, employee_id)
    if not chat:
        return {"status": "error", "message": "对话不存在"}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构建用户消息
    user_message = {
        "timestamp": timestamp,
        "sender": username,
        "message": message,
        "message_type": "text",
        "sender_type": "user"
    }
    if saved_files:
        user_message["files"] = [{"name": os.path.basename(f)} for f in saved_files]

    # 调用 Agent 获取回复
    response_text = ""
    if HAS_AGENT_SDK:
        try:
            agent = await get_or_create_manager_agent(employee_id, username)
            response_text = await agent.chat(message, files=saved_files if saved_files else None)
        except Exception as e:
            logger.error(f"[ERROR] ManagerAgent 调用失败: {str(e)}")
            response_text = "抱歉，我现在无法回答您的问题，请稍后再试。"
    else:
        response_text = f"收到您的消息：{message}\n\n（当前为简化模式，未连接 Agent SDK）"

    # 构建 Agent 回复
    agent_message = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sender": "Agent",
        "message": response_text,
        "message_type": "text",
        "sender_type": "agent"
    }

    # 更新对话
    messages = chat.get("messages", [])
    messages.append(user_message)
    messages.append(agent_message)
    update_chat(chat_id, employee_id, messages)

    return {
        "status": "success",
        "user_message": user_message,
        "agent_reply": agent_message
    }


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

@app.get("/api/events/{employee_id}")
async def sse_events(employee_id: str):
    """
    SSE 事件流端点，用于实时推送任务通知

    推送的事件类型：
    - task_created: Manager 创建了新任务
    - new_task: 有新任务分配给当前用户（Staff）
    - task_completed: 任务被标记为反馈完成
    """
    async def event_generator():
        queue = asyncio.Queue()
        sse_manager.subscribe(employee_id, queue)

        try:
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            logger.info(f"[SSE] 用户 {employee_id} 连接断开")
        finally:
            sse_manager.unsubscribe(employee_id, queue)
            logger.info(f"[SSE] 用户 {employee_id} 取消订阅")

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
        employee_id = body.get("employee_id")
        username = body.get("username")

        logger.info(f"[API] 请求用户: employee_id={employee_id}, username={username}")

        if not employee_id or not username:
            raise HTTPException(status_code=400, detail="缺少employee_id或username")

        # 2. 获取任务信息
        tasks = read_csv_file("tasks.csv")
        task_info = next((t for t in tasks if t.get("task_id") == task_id), None)

        if not task_info:
            logger.error(f"[API] 任务不存在: {task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")

        logger.info(f"[API] 任务信息: {task_info}")

        # 3. 验证用户是否是任务的执行人
        assigned_to_id = task_info.get("assigned_to_id")
        if assigned_to_id != employee_id:
            logger.warning(f"[API] ⚠️ 用户不匹配: 请求employee_id={employee_id}, 任务assigned_to_id={assigned_to_id}")
            # 仍然允许发送，但记录警告

        # 4. 获取或创建Staff Agent
        logger.info(f"[API] 获取Staff Agent: employee_id={employee_id}")
        agent = await get_or_create_staff_agent(employee_id, username)

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


# ============ 辅助函数 ============

def _update_task_status(task_id: str, new_status: str):
    """更新任务状态"""
    import csv
    from pathlib import Path
    
    tasks_file = Path(__file__).parent.parent / "data" / "tasks.csv"
    if not tasks_file.exists():
        return False
    
    try:
        # 读取所有任务
        with open(tasks_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
        
        # 更新状态
        updated = False
        for row in rows:
            if row.get("task_id") == task_id:
                row["status"] = new_status
                updated = True
                break
        
        if updated:
            # 写回
            with open(tasks_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        return updated
    except Exception as e:
        logger.error(f"[ERROR] 更新任务状态失败: {e}")
        return False
