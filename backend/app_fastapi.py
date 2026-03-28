"""
FastAPI 后端服务 - DJAgent 风控智能助手
"""

import os
import asyncio
import csv
import json
import tempfile
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

# ============ 常量定义 ============

# 文件限制
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_FILE_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc', '.xlsx', '.xls'}

# 导入 SSE 事件管理器
from agents.sse_events import sse_manager

# 导入 Skills API 路由
try:
    from api.skills_api import router as skills_router
    app.include_router(skills_router)
    logger.info("[API] ✅ Skill 管理 API 已注册")
except ImportError as e:
    logger.warning(f"[API] Skills API 导入失败，某些功能不可用: {e}")


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
    now = datetime.now()
    for task in tasks:
        if task.get("status") == "反馈中":
            deadline_str = task.get("feedback_deadline", "")
            if deadline_str:
                deadline = None
                # 尝试多种日期格式
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                    try:
                        deadline = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue

                if deadline:
                    if now > deadline:
                        task["status"] = "已超时"
                        # 异步更新CSV中的状态
                        try:
                            _update_task_status(task["task_id"], "已超时")
                            logger.info(f"[TASK] 任务 {task['task_id']} 已更新为超时")
                        except Exception as e:
                            logger.error(f"[TASK] 更新任务状态失败: {e}")
                else:
                    logger.warning(f"[TASK] 任务 {task['task_id']} deadline 格式无法识别: {deadline_str}")
            else:
                logger.debug(f"[TASK] 任务 {task['task_id']} 无 feedback_deadline 设置")

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
            response = await agent.chat(message, files=saved_files if saved_files else None)

            # 处理两种响应格式：
            # 1. 简单字符串响应（旧格式）
            # 2. 包含消息类型的结构化响应（新格式）
            if isinstance(response, dict):
                response_data = response
            else:
                # 兼容旧格式：直接返回文本
                response_data = {
                    "type": "text",
                    "message": response,
                    "sender": "agent"
                }

            logger.info(f"[API] ManagerAgent 回复成功")
            return response_data
        except Exception as e:
            logger.error(f"[ERROR] ManagerAgent 调用失败: {str(e)}")
            return {
                "type": "text",
                "message": "抱歉，我现在无法回答您的问题，请稍后再试。",
                "sender": "agent",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    return {
        "type": "text",
        "message": response_text,
        "sender": "agent",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """
    Anthropic 标准流式聊天端点
    
    返回完整的事件流，包括：
    - thinking: 思考过程
    - tool_use: 工具调用
    - text: 正文内容
    - tool_result: 工具结果
    
    SSE 事件格式完全符合 Anthropic Messages API Streaming 规范
    """
    from fastapi.responses import StreamingResponse
    from agents.session_manager import get_or_create_manager_agent
    
    # 解析请求
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    message = data.get("message", "")
    employee_id = data.get("employee_id", "manager_default")
    username = data.get("username", "业务负责人")
    
    if not message:
        raise HTTPException(status_code=400, detail="缺少 message 参数")
    
    if not HAS_AGENT_SDK:
        # 返回简化响应
        async def simple_event_generator():
            yield "event: message_start\ndata: {'type': 'message_start'}\n\n"
            yield "event: content_block_start\ndata: {'type': 'content_block_start', 'content_block': {'type': 'text'}}\n\n"
            yield f"event: content_block_delta\ndata: {{'type': 'content_block_delta', 'delta': {{'type': 'text_delta', 'text': '当前为简化模式，未连接 Agent SDK'}}}}\n\n"
            yield "event: message_stop\ndata: {'type': 'message_stop'}\n\n"
        
        return StreamingResponse(
            simple_event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    # 获取 Agent
    try:
        agent = await get_or_create_manager_agent(employee_id, username)
        
        async def event_stream():
            """事件流生成器"""
            try:
                async for sse_event in agent.chat_stream_with_events(message=message):
                    yield sse_event
            except Exception as e:
                logger.error(f"[API] 流式事件生成失败: {e}")
                yield f"event: error\ndata: {{'error': '{str(e)}'}}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"[API] 获取 Agent 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 表单处理接口 ============


@app.post("/api/form/submit")
async def submit_form(request: Request):
    """处理表单提交

    现在支持FormData格式（包含文件上传）

    前端发送：
    FormData {
        "form_id": "form_xxx",
        "data_field1": "value1",
        "data_field2": File,
        "employee_id": "EMP_010",
        "username": "周芳",
        "task_id": "004-xxx"
    }
    """
    try:
        # Fix 17: 支持FormData格式（包含文件）
        content_type = request.headers.get("content-type", "")

        form_id = ""
        form_data = {}
        employee_id = "manager_default"
        username = "业务负责人"
        task_id = ""
        upload_dir = None

        if "multipart/form-data" in content_type:
            # 处理FormData格式
            form = await request.form()
            form_id = form.get("form_id", "")
            employee_id = form.get("employee_id", employee_id)
            username = form.get("username", username)
            task_id = form.get("task_id", "")

            # 提取表单字段 (data_xxx 格式)
            from fastapi import UploadFile
            import tempfile
            import os

            for key, value in form.items():
                if key.startswith("data_"):
                    field_name = key[5:]  # 移除 "data_" 前缀

                    try:
                        # Fix 18: 严格检查UploadFile类型，安全处理二进制数据
                        if isinstance(value, UploadFile):
                            # 保存文件
                            temp_dir = tempfile.mkdtemp()
                            file_path = os.path.join(temp_dir, value.filename or f"file_{field_name}")
                            content = await value.read()
                            with open(file_path, 'wb') as f:
                                f.write(content)
                            form_data[field_name] = {
                                "type": "file",
                                "filename": value.filename,
                                "path": file_path,
                                "size": len(content)
                            }
                            logger.info(f"[API] 收到文件: {field_name} = {value.filename} ({len(content)} bytes)")
                        else:
                            # 处理普通文本字段（不试图转换其他类型对象）
                            if isinstance(value, str):
                                form_data[field_name] = value
                            else:
                                # 其他类型忽略或转为空
                                form_data[field_name] = ""
                                logger.warning(f"[API] 跳过非字符串字段: {field_name} (type={type(value).__name__})")
                    except Exception as e:
                        logger.error(f"[API] 处理字段 {field_name} 失败: {e}")
                        form_data[field_name] = ""
        else:
            # 处理JSON格式（向后兼容）
            body = await request.json()
            form_id = body.get("form_id", "")
            form_data = body.get("data", {})
            employee_id = body.get("employee_id", "manager_default")
            username = body.get("username", "业务负责人")
            task_id = body.get("task_id", "")

        logger.info(f"[API] 表单提交: {form_id} by {username}, task_id={task_id}, 字段数={len(form_data)}")

        if not form_id:
            return {
                "success": False,
                "error": "缺少form_id"
            }

        # Fix 16: 保存表单数据到任务反馈文件
        from pathlib import Path
        import json as json_module
        from datetime import datetime as dt_now

        if task_id:
            try:
                data_dir = Path(__file__).parent.parent / "data" / "feedback"
                feedback_file = data_dir / f"{task_id}.json"

                feedback_data = {}
                if feedback_file.exists():
                    with open(feedback_file, "r", encoding="utf-8") as f:
                        feedback_data = json_module.load(f)

                if "chat_history" not in feedback_data:
                    feedback_data["chat_history"] = []

                # 添加表单提交记录（文件信息只保存元数据，不保存路径）
                form_submission = {
                    "timestamp": dt_now.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sender": username,
                    "sender_type": "user",
                    "message": f"提交表单: {form_id}",
                    "message_type": "form_submission",
                    "form_id": form_id,
                    "form_data": {
                        k: v.get("filename") if isinstance(v, dict) and v.get("type") == "file" else v
                        for k, v in form_data.items()
                    }
                }
                feedback_data["chat_history"].append(form_submission)
                feedback_data["last_updated"] = dt_now.now().strftime("%Y-%m-%d %H:%M:%S")

                # 保存回文件
                with open(feedback_file, "w", encoding="utf-8") as f:
                    json_module.dump(feedback_data, f, ensure_ascii=False, indent=2)

                logger.info(f"[API] 表单数据已保存到 {task_id}")
            except Exception as e:
                logger.error(f"[API] 保存表单数据失败: {e}")

        # Fix 16: 调用StaffAgent处理表单数据并生成回复
        try:
            from agents.session_manager import get_or_create_staff_agent

            agent = await get_or_create_staff_agent(employee_id, username)
            agent.current_task_id = task_id

            # 构建表单提交的AI处理提示
            form_data_str = "\n".join([
                f"- {k}: {v.get('filename') if isinstance(v, dict) and v.get('type') == 'file' else v}"
                for k, v in form_data.items()
            ])

            ai_prompt = f"""用户已提交表单反馈，请确认收到并简要总结提交的内容。

表单ID: {form_id}
提交的数据:
{form_data_str}

请用友好、简洁的语气确认收到这些信息，并根据需要给出下一步建议。"""

            # 调用Agent生成回复
            ai_response = await agent.chat(
                ai_prompt,
                context={"task_id": task_id, "form_id": form_id}
            )

            logger.info(f"[API] Agent已处理表单数据: {form_id}")

            # 保存Agent回复到反馈文件
            if task_id:
                try:
                    data_dir = Path(__file__).parent.parent / "data" / "feedback"
                    feedback_file = data_dir / f"{task_id}.json"
                    feedback_data = {}
                    if feedback_file.exists():
                        with open(feedback_file, "r", encoding="utf-8") as f:
                            feedback_data = json_module.load(f)

                    if "chat_history" not in feedback_data:
                        feedback_data["chat_history"] = []

                    agent_reply = {
                        "timestamp": dt_now.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sender": "Agent",
                        "sender_type": "agent",
                        "message": ai_response,
                        "message_type": "text",
                        "form_id": form_id
                    }
                    feedback_data["chat_history"].append(agent_reply)

                    with open(feedback_file, "w", encoding="utf-8") as f:
                        json_module.dump(feedback_data, f, ensure_ascii=False, indent=2)

                    logger.info(f"[API] Agent回复已保存到 {task_id}")
                except Exception as e:
                    logger.error(f"[API] 保存Agent回复失败: {e}")

            return {
                "success": True,
                "message": f"表单已收到并处理",
                "agent_reply": ai_response,
                "form_id": form_id
            }

        except Exception as e:
            logger.error(f"[API] Agent处理表单失败: {e}")
            return {
                "success": True,
                "message": f"表单已保存",
                "error": f"处理失败: {str(e)}",
                "form_id": form_id
            }

    except Exception as e:
        logger.error(f"[ERROR] 表单提交失败: {str(e)}")
        return {
            "success": False,
            "error": f"表单提交失败: {str(e)}"
        }


@app.post("/api/form/validate")
async def validate_form(request: Request):
    """验证表单数据

    请求体：
    {
        "form_id": "form_xxx",
        "schema": {...},
        "data": {...}
    }
    """
    try:
        body = await request.json()
        form_id = body.get("form_id", "")
        form_data = body.get("data", {})
        schema = body.get("schema", {})

        logger.info(f"[API] 验证表单: {form_id}")

        if not form_id:
            return {
                "success": False,
                "error": "缺少form_id"
            }

        # 从 Agent 获取 form_generator Skill
        from agents.skills.form_generator.skill import FormGeneratorSkill

        form_skill = FormGeneratorSkill()

        # 执行表单验证
        result = await form_skill.execute(
            {
                "action": "validate",
                "form_id": form_id,
                "data": form_data,
                "schema": schema
            },
            {}
        )

        return result

    except Exception as e:
        logger.error(f"[ERROR] 表单验证失败: {str(e)}")
        return {
            "success": False,
            "error": f"表单验证失败: {str(e)}"
        }



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
            filename = getattr(file, "filename", f"file_{datetime.now().timestamp()}")

        # 验证文件扩展名
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_FILE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")

        # 验证文件大小 (在读取前检查)
        upload_dir = DATA_DIR / "uploads" / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大（{len(file_content)/1024/1024:.1f}MB > {MAX_FILE_SIZE/1024/1024:.0f}MB）"
            )

        # 验证文件名安全性（防路径穿越）
        filename = os.path.basename(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="文件名非法")

        file_path = upload_dir / filename

        # 最终安全检查：确认路径在安全区域内
        try:
            file_path.resolve().relative_to(upload_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="文件保存路径非法")

        with open(file_path, "wb") as f:
            f.write(file_content)

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

        logger.info(f"[API] 文件上传成功: {filename} ({len(file_content)/1024:.1f}KB)")
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
        from agents.session_manager import get_or_create_staff_agent

        agent = await get_or_create_staff_agent(employee_id, username)
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

    # 注意：不再在这里强制设置 sent_time 和 feedback_deadline
    # 这些时间应该在 notify_new_task 和 assign_task 时设置
    # 状态流转：已创建 -> 已下发 -> 反馈中 -> 已完成

    if not HAS_AGENT_SDK:
        ai_response = "Agent SDK未安装，暂时无法处理消息"
    else:
        try:
            agent = await get_or_create_staff_agent(employee_id, username)
            agent.current_task_id = task_id
            
            ai_response = await agent.chat(
                message,
                context={"task_id": task_id},
                files=saved_files if saved_files else None
            )
        except Exception as e:
            logger.error(f"[ERROR] Agent调用失败: {str(e)}")
            ai_response = "好的，请继续。"

    agent_reply = {
        "timestamp": timestamp,
        "sender": "Agent",
        "message": ai_response,
        "message_type": "text",
    }

    # Fix 4: Extract form JSON from ai_response (if present)
    import re
    agent_reply_type = "text"
    agent_reply_schema = None
    agent_reply_form_id = None
    agent_reply_text = ai_response

    # 尝试从markdown代码块中提取JSON表单定义
    pattern = r'```json\s*([\s\S]*?)\s*```'
    match = re.search(pattern, ai_response)

    if match:
        json_text = match.group(1).strip()
        try:
            schema = json.loads(json_text)
            # 验证必需字段
            if all(key in schema for key in ['form_id', 'title', 'state', 'sections']):
                agent_reply_schema = schema
                agent_reply_form_id = schema.get('form_id')
                agent_reply_type = "form_card"
                # 移除JSON代码块，仅保留文本消息
                agent_reply_text = re.sub(pattern, '', ai_response).strip()
                logger.info(f"[API] 消息端点提取表单: form_id={agent_reply_form_id}")
        except json.JSONDecodeError as e:
            logger.debug(f"[API] JSON解析失败: {e}")

    # 更新agent_reply结构
    agent_reply["message"] = agent_reply_text
    agent_reply["type"] = agent_reply_type
    agent_reply["message_type"] = agent_reply_type  # Fix 13: 同时更新 message_type，确保持久化时一致
    if agent_reply_type == "form_card":
        agent_reply["schema"] = agent_reply_schema
        agent_reply["form_id"] = agent_reply_form_id

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

    # 更新任务状态为"反馈中"（一线人员开始反馈）
    current_status = feedback_data.get("status", "已下发")
    if current_status == "已下发":
        # 仅当状态为"已下发"时才转换为"反馈中"
        feedback_data["status"] = "反馈中"
        try:
            from agents.tools.task_manager import update_task_status
            result = update_task_status(
                task_id=task_id,
                status="反馈中"
            )
            if "error" not in result:
                logger.info(f"[API] 任务 {task_id} 状态已更新为：反馈中")
            else:
                logger.error(f"[API] 更新任务状态失败: {result.get('error')}")
        except Exception as e:
            logger.error(f"[API] 更新任务状态异常: {str(e)}")

    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    with open(feedback_path, "w", encoding="utf-8") as f:
        json.dump(feedback_data, f, ensure_ascii=False, indent=2)

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
            # Fix 3: Forward complete structure with type, schema, form_id
            response_data = {
                "success": True,
                "type": result.get("type", "text"),
                "message": result.get("message"),
                "task_id": task_id,
                "timestamp": result.get("timestamp")
            }
            # 如果是表单类型，添加schema和form_id
            if result.get("type") == "form_card":
                response_data["schema"] = result.get("schema")
                response_data["form_id"] = result.get("form_id")
                logger.info(f"[API] 返回表单卡片: form_id={response_data.get('form_id')}")
            return response_data
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
