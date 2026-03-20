"""
简化版 FastAPI 后端服务 - DJAgent 风控智能助手
移除 claude_agent_sdk 依赖，直接使用 HTTP 请求调用 Claude API
"""
import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入智能体核心
try:
    from simple_agent import SimpleAgent
    AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入 SimpleAgent: {e}")
    AGENT_AVAILABLE = False

# FastAPI 应用
app = FastAPI(title="DJAgent API (Simplified)", version="1.0.0")

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

# Claude API 配置
CLAUDE_API_KEY = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
CLAUDE_API_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages")
CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")


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
    
    if AGENT_AVAILABLE:
        try:
            # 实例化智能体
            agent = SimpleAgent(user_id, username)
            # 调用智能体进行对话
            response_text = await agent.chat(message)
            logger.info(f"[API] 智能体回复: {response_text[:50]}...")
        except Exception as e:
            logger.error(f"[API] 智能体调用失败: {e}")
            response_text = f"抱歉，智能体遇到了一些问题: {str(e)}"
    else:
        # 降级模式
        response_text = f"收到您的消息：{message}\n\n（当前为简化模式，智能体核心未加载）"
    
    return {
        'message': response_text,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


# ============ 风险数据接口 ============

@app.get("/api/risk-data")
async def get_risk_data():
    """获取所有风险数据文件列表和内容"""
    risk_files = []

    # 风险数据在 risk_data 子目录
    risk_data_dir = DATA_DIR / "risk_data"

    # 查找所有风险数据文件
    for file_path in risk_data_dir.glob("risk_data_*.csv"):
        try:
            data = read_csv_file(file_path.name, risk_data_dir)
            risk_files.append({
                "filename": file_path.name,
                "data": data,
                "count": len(data)
            })
        except Exception as e:
            logger.error(f"读取风险数据文件失败 {file_path}: {e}")

    return risk_files


@app.get("/api/risk-data/{identifier}")
async def get_risk_data_file(identifier: str):
    """获取单个风险数据文件内容
    
    支持两种格式：
    - /api/risk-data/001  -> 自动映射到 risk_data_001.csv
    - /api/risk-data/risk_data_001.csv -> 直接使用
    """
    try:
        # 处理简化的 ID 格式 (如 "001", "0010" 等)
        # 统一映射到 3 位数字格式: risk_data_XXX.csv
        if identifier.isdigit():
            # 将数字转为整数再格式化为 3 位数字
            num = int(identifier)
            filename = f"risk_data_{num:03d}.csv"
        elif identifier.startswith("risk_data_") and identifier.endswith(".csv"):
            filename = identifier
        else:
            # 尝试提取数字部分
            import re
            match = re.search(r'\d+', identifier)
            if match:
                num = int(match.group())
                filename = f"risk_data_{num:03d}.csv"
            else:
                filename = f"risk_data_{identifier}.csv"

        # 风险数据在 risk_data 子目录
        risk_data_dir = DATA_DIR / "risk_data"
        data = read_csv_file(filename, risk_data_dir)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"风险数据文件不存在或为空: {filename}")
        
        return {
            "filename": filename,
            "identifier": identifier,
            "data": data,
            "count": len(data)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取风险数据文件失败 {identifier}: {e}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


# ============ 健康检查 ============

@app.get("/api/health")
async def health_check():
    return {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'data_dir': str(DATA_DIR),
        'mode': 'simplified'
    }


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    logger.info("启动 DJAgent 简化版后端服务...")
    uvicorn.run(app, host="0.0.0.0", port=5005)
