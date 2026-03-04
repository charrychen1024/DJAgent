"""
FastAPI 后端服务 - DJAgent 风控智能助手
"""
import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# 导入Agent模块
from agents.manager_agent import ManagerAgent
from agents.staff_agent import StaffAgent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(title="DJAgent API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据目录
DATA_DIR = Path(__file__).parent.parent / "data"


def read_csv_file(filename: str) -> List[Dict]:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.error(f"[ERROR] 读取文件失败: {e}")
        return []


def write_csv_file(filename: str, data: List[Dict], fieldnames: List[str]) -> bool:
    filepath = DATA_DIR / filename
    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
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
    return read_csv_file('users.csv')


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    users = read_csv_file('users.csv')
    user = next((u for u in users if u['user_id'] == user_id), None)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")


# ============ 任务接口 ============

@app.get("/api/tasks")
async def get_tasks(user_id: Optional[str] = None):
    tasks = read_csv_file('tasks.csv')
    
    if user_id:
        users = read_csv_file('users.csv')
        user = next((u for u in users if u['user_id'] == user_id), None)
        if user:
            role = user.get('role', '')
            if role in ['业务负责人', '普通分析人员']:
                tasks = [t for t in tasks if t['creator_id'] == user_id]
            else:
                tasks = [t for t in tasks if t['assigned_to_id'] == user_id]
    
    return tasks


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = read_csv_file('tasks.csv')
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if task:
        return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/api/tasks")
async def create_task(request: Request):
    data = await request.json()
    tasks = read_csv_file('tasks.csv')
    
    max_id = max([int(t['task_id'].replace('TASK_', '')) for t in tasks], default=0)
    new_task_id = f"TASK_{max_id + 1:03d}"
    
    new_task = {
        'task_id': new_task_id,
        'creator_id': data.get('creator_id'),
        'creator_name': data.get('creator_name'),
        'assigned_to_id': data.get('assigned_to_id'),
        'assigned_to_name': data.get('assigned_to_name'),
        'status': '已创建',
        'created_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'risk_summary': data.get('risk_summary'),
        'risk_data_url': data.get('risk_data_url'),
        'suggested_receiver_id': data.get('assigned_to_id'),
        'confirmed_receiver_id': data.get('assigned_to_id'),
        'completed_time': ''
    }
    
    tasks.append(new_task)
    fieldnames = list(new_task.keys())
    
    if write_csv_file('tasks.csv', tasks, fieldnames):
        return new_task
    raise HTTPException(status_code=500, detail="Failed to create task")


# ============ Agent对话接口 ============

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get('message', '')
    user_id = data.get('user_id', 'manager_default')
    username = data.get('username', '业务负责人')
    
    logger.info(f"[API] 用户消息: {message}")
    
    try:
        # 直接创建Agent实例
        agent = ManagerAgent(user_id, username)
        async with agent:
            response_text = await agent.chat(message)
        logger.info(f"[API] ManagerAgent 回复成功")
    except Exception as e:
        logger.error(f"[ERROR] ManagerAgent 调用失败: {str(e)}")
        response_text = "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    return {
        'message': response_text,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


# ============ 子Agent对话接口 ============

@app.get("/api/tasks/{task_id}/chat-history")
async def get_chat_history(task_id: str, user_id: str, username: str):
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
    
    if feedback_path.exists():
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('chat_history'):
                return data['chat_history']
    
    # 调用Agent初始化任务
    try:
        agent = StaffAgent(user_id, username)
        async with agent:
            initial_message = await agent.init_task(task_id)
        
        feedback_data = {
            'task_id': task_id,
            'chat_history': [{
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sender': 'Agent',
                'message': initial_message,
                'message_type': 'text'
            }],
            'uploaded_files': [],
            'status': '进行中'
        }
        
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        with open(feedback_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        
        return feedback_data['chat_history']
    except Exception as e:
        logger.error(f"[ERROR] Agent初始化失败: {str(e)}")
        return [{"message": "任务加载失败", "sender": "Agent"}]


@app.post("/api/tasks/{task_id}/message")
async def send_message(task_id: str, request: Request):
    data = await request.json()
    message = data.get('message', '')
    user_id = data.get('user_id')
    username = data.get('username', '')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    user_message = {
        'timestamp': timestamp,
        'sender': username,
        'message': message,
        'message_type': 'text'
    }
    
    try:
        agent = StaffAgent(user_id, username)
        async with agent:
            agent.current_task_id = task_id
            ai_response = await agent.chat(message)
    except Exception as e:
        logger.error(f"[ERROR] Agent调用失败: {str(e)}")
        ai_response = "好的，请继续。"
    
    agent_reply = {
        'timestamp': timestamp,
        'sender': 'Agent',
        'message': ai_response,
        'message_type': 'text'
    }
    
    return {
        'user_message': user_message,
        'agent_reply': agent_reply
    }


# ============ 健康检查 ============

@app.get("/api/health")
async def health_check():
    return {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'data_dir': str(DATA_DIR)
    }


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5005)
