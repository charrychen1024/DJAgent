# DJAgent 项目修复计划

**创建日期**: 2026-03-06  
**基于测试报告**: TEST_REPORT.md

---

## 一、修复优先级说明

| 优先级 | 说明 | 预计时间 |
|--------|------|----------|
| **P0** | 严重问题，必须修复才能正常运行 | 立即处理 |
| **P1** | 重要问题，强烈建议修复 | 1-2天内 |
| **P2** | 优化改进，可暂缓 | 1周内 |

---

## 二、P0 严重问题修复（必须修复）

### 🔴 修复 #1: 补充缺失的API接口

**问题描述**: 5个后端API接口缺失，导致前端功能阻塞

**需要添加的接口**:

#### 1.1 GET /api/risk-data
**功能**: 获取所有风险数据文件列表

**实现代码**:
```python
@app.get("/api/risk-data")
async def get_all_risk_data():
    """获取所有风险数据文件列表和内容"""
    risk_files = []
    
    for file_path in DATA_DIR.glob("risk_data_*.csv"):
        try:
            data = read_csv_file(file_path.name)
            risk_files.append({
                "filename": file_path.name,
                "data": data,
                "count": len(data)
            })
        except Exception as e:
            logger.error(f"读取风险数据文件失败 {file_path}: {e}")
    
    return risk_files
```

**文件**: `backend/app_fastapi.py`

---

#### 1.2 GET /api/risk-data/{identifier}
**功能**: 获取单个风险数据文件内容

**实现代码**:
```python
@app.get("/api/risk-data/{identifier}")
async def get_risk_data_file(identifier: str):
    """获取单个风险数据文件内容
    
    支持格式：
    - /api/risk-data/001  -> risk_data_001.csv
    - /api/risk-data/risk_data_001.csv -> 直接使用
    """
    try:
        import re
        if identifier.isdigit():
            num = int(identifier)
            filename = f"risk_data_{num:03d}.csv"
        elif identifier.startswith("risk_data_") and identifier.endswith(".csv"):
            filename = identifier
        else:
            match = re.search(r'\d+', identifier)
            if match:
                num = int(match.group())
                filename = f"risk_data_{num:03d}.csv"
            else:
                filename = f"risk_data_{identifier}.csv"
        
        data = read_csv_file(filename)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"风险数据文件不存在: {filename}")
        
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
```

**文件**: `backend/app_fastapi.py`

---

#### 1.3 GET /api/tasks/{task_id}/creation-history
**功能**: 获取任务创建聊天历史

**实现代码**:
```python
@app.get("/api/tasks/{task_id}/creation-history")
async def get_task_creation_history(task_id: str):
    """获取任务创建时的聊天历史"""
    feedback_path = DATA_DIR / "feedback" / f"{task_id}_creation.json"
    
    if feedback_path.exists():
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('chat_history'):
                return data['chat_history']
    
    return []
```

**文件**: `backend/app_fastapi.py`

---

#### 1.4 GET /api/feedback/{task_id}
**功能**: 获取任务反馈信息

**实现代码**:
```python
@app.get("/api/feedback/{task_id}")
async def get_task_feedback(task_id: str):
    """获取任务反馈信息"""
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
    
    if feedback_path.exists():
        with open(feedback_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {
        "task_id": task_id,
        "chat_history": [],
        "uploaded_files": [],
        "status": "未开始"
    }
```

**文件**: `backend/app_fastapi.py`

---

#### 1.5 POST /api/tasks/{task_id}/upload-file
**功能**: 上传任务相关文件

**实现代码**:
```python
@app.post("/api/tasks/{task_id}/upload-file")
async def upload_task_file(task_id: str, request: Request):
    """上传任务相关文件"""
    from fastapi import UploadFile, File
    from fastapi import Form
    
    try:
        form = await request.form()
        file = form.get('file')
        user_id = form.get('user_id')
        filename = form.get('filename', file.filename if file else '')
        
        if not file:
            raise HTTPException(status_code=400, detail="未上传文件")
        
        # 保存文件
        upload_dir = DATA_DIR / "uploads" / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / filename
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 更新反馈数据
        feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
        feedback_data = {}
        if feedback_path.exists():
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        
        if 'uploaded_files' not in feedback_data:
            feedback_data['uploaded_files'] = []
        
        feedback_data['uploaded_files'].append({
            "filename": filename,
            "file_path": str(file_path),
            "upload_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "user_id": user_id
        })
        
        with open(feedback_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": f"文件 {filename} 上传成功",
            "file_path": str(file_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] 文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
```

**文件**: `backend/app_fastapi.py`

**需要添加的导入**:
```python
from fastapi import UploadFile, File
```

---

### 🔴 修复 #2: 修复聊天消息保存逻辑

**问题描述**: POST /api/tasks/{task_id}/message 未保存消息到文件

**修改位置**: `backend/app_fastapi.py:206-241`

**修改后的代码**:
```python
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
    
    # ✅ 保存到文件
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
    feedback_data = {}
    
    if feedback_path.exists():
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        except Exception as e:
            logger.error(f"[ERROR] 读取反馈文件失败: {e}")
    
    if 'chat_history' not in feedback_data:
        feedback_data['chat_history'] = []
    
    feedback_data['chat_history'].append(user_message)
    feedback_data['chat_history'].append(agent_reply)
    feedback_data['task_id'] = task_id
    feedback_data['last_updated'] = timestamp
    
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    with open(feedback_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_data, f, ensure_ascii=False, indent=2)
    
    return {
        'user_message': user_message,
        'agent_reply': agent_reply
    }
```

---

### 🔴 修复 #3: 修复聊天历史接口参数

**问题描述**: GET /api/tasks/{task_id}/chat-history 参数不匹配

**修改位置**: `backend/app_fastapi.py:168`

**修改后的代码**:
```python
@app.get("/api/tasks/{task_id}/chat-history")
async def get_chat_history(task_id: str, user_id: str = None, username: str = None):
    """获取任务聊天历史
    
    使用 Query 参数传递 user_id 和 username
    """
    feedback_path = DATA_DIR / "feedback" / f"{task_id}.json"
    
    if feedback_path.exists():
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('chat_history'):
                return data['chat_history']
    
    # 调用Agent初始化任务
    try:
        agent = StaffAgent(user_id or 'staff_default', username or '一线人员')
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
```

---

### 🔴 修复 #4: 修复会话管理器异步问题

**问题描述**: session_manager.py 中 asyncio.run() 在已有事件循环中调用会报错

**修改位置**: `backend/agents/session_manager.py:45, 75, 100`

**修改1 - 第45行**:
```python
# 修改前
asyncio.run(agent.__aenter__())

# 修改后
await agent.__aenter__()
```

**修改2 - 第75行**:
```python
# 修改前
asyncio.run(agent.__aenter__())

# 修改后
await agent.__aenter__()
```

**修改3 - 第100行**:
```python
# 修改前
asyncio.run(agent.__aexit__(None, None, None))

# 修改后
await agent.__aexit__(None, None, None)
```

**注意**: 这些函数需要改为 async 函数才能使用 await

**完整修改后的函数**:
```python
async def get_or_create_staff_agent(user_id: str, user_name: str) -> StaffAgent:
    if user_id in _sessions:
        agent = _sessions[user_id]
        if isinstance(agent, StaffAgent):
            logger.info(f"[SessionManager] 复用已有 StaffAgent: {user_id}")
            return agent
        else:
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)
    
    logger.info(f"[SessionManager] 创建新的 StaffAgent: {user_id}")
    agent = StaffAgent(user_id, user_name)
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


async def get_or_create_manager_agent(user_id: str, user_name: str) -> ManagerAgent:
    if user_id in _sessions:
        agent = _sessions[user_id]
        if isinstance(agent, ManagerAgent):
            logger.info(f"[SessionManager] 复用已有 ManagerAgent: {user_id}")
            return agent
        else:
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)
    
    logger.info(f"[SessionManager] 创建新的 ManagerAgent: {user_id}")
    agent = ManagerAgent(user_id, user_name)
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


async def _close_agent(user_id: str):
    if user_id in _sessions:
        agent = _sessions[user_id]
        try:
            await agent.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"[SessionManager] 关闭会话失败: {user_id}, {e}")
        finally:
            del _sessions[user_id]


async def close_agent(user_id: str):
    logger.info(f"[SessionManager] 关闭会话: {user_id}")
    await _close_agent(user_id)


async def close_all_agents():
    logger.info(f"[SessionManager] 关闭所有会话，共 {len(_sessions)} 个")
    for user_id in list(_sessions.keys()):
        await _close_agent(user_id)
```

---

## 三、P1 重要问题修复（强烈建议）

### 🟡 修复 #5: 处理 claude-agent-sdk 依赖

**选项A - 安装SDK（如果可用）**:
```bash
pip install claude-agent-sdk
```

然后取消 `requirements.txt` 中的注释

**选项B - 使用简化版（推荐）**:
- 使用 `app_simple.py` 作为启动入口
- 或修改 `app_fastapi.py` 使用直接HTTP调用API

---

### 🟡 修复 #6: 注册Agent工具

**修改位置**: `backend/agents/manager_agent.py:71-83`

**修改后的代码**:
```python
def build_manager_options() -> ClaudeAgentOptions:
    """构建主智能体配置"""
    return ClaudeAgentOptions(
        env={
            "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
        },
        system_prompt=MANAGER_SYSTEM_PROMPT,
        permission_mode="acceptEdits",
        max_turns=15,
        thinking={"type": "disabled"},
        tools=AGENT_TOOLS  # ✅ 添加工具注册
    )
```

---

### 🟡 修复 #7: 添加用户身份验证

**创建新文件**: `backend/auth.py`

```python
"""用户认证工具"""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def validate_user(user_id: str) -> bool:
    """验证用户ID是否有效"""
    try:
        users_file = DATA_DIR / "users.csv"
        if not users_file.exists():
            return False
        
        with open(users_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('user_id') == user_id:
                    return True
        return False
    except Exception:
        return False


def get_user(user_id: str):
    """获取用户信息"""
    try:
        users_file = DATA_DIR / "users.csv"
        if not users_file.exists():
            return None
        
        with open(users_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('user_id') == user_id:
                    return row
        return None
    except Exception:
        return None
```

**在需要验证的接口中添加**:
```python
from auth import validate_user, get_user

@app.get("/api/tasks")
async def get_tasks(user_id: Optional[str] = None):
    if user_id and not validate_user(user_id):
        raise HTTPException(status_code=401, detail="无效的用户ID")
    # ...
```

---

### 🟡 修复 #8: 修正数据不一致

**修改文件**: `data/tasks.csv`

将所有创建人从"李经理"改为"王经理"（与 users.csv 一致）

或根据实际情况修改 users.csv 中的用户名

---

## 四、P2 优化改进（可暂缓）

### 🟢 修复 #9: 优化前端全选逻辑

**修改位置**: `frontend/src/App.jsx:105-111`

**建议**: 添加全局全选功能

---

### 🟢 修复 #10-14: 其他优化

- 移除未使用的导入
- 完善错误处理
- 扩展CORS配置
- 确保目录存在
- 统一Agent模型配置

---

## 五、修复执行步骤

### 第一步：修复P0问题（1-2小时）
1. ✅ 添加5个缺失的API接口
2. ✅ 修复聊天消息保存逻辑
3. ✅ 修复聊天历史接口参数
4. ✅ 修复会话管理器异步问题

### 第二步：修复P1问题（2-3小时）
5. ✅ 处理 claude-agent-sdk 依赖
6. ✅ 注册Agent工具
7. ✅ 添加用户身份验证
8. ✅ 修正数据不一致

### 第三步：测试验证（1小时）
9. ✅ 启动后端服务
10. ✅ 启动前端服务
11. ✅ 测试用户登录
12. ✅ 测试风险数据加载
13. ✅ 测试任务创建和查看
14. ✅ 测试聊天功能

### 第四步：P2优化（可选）
15. 代码清理和优化

---

## 六、修复检查清单

修复完成后，请确认以下项目：

- [ ] 后端服务正常启动（无报错）
- [ ] 前端服务正常启动
- [ ] 用户可以登录
- [ ] 风险数据可以正常加载
- [ ] 任务列表正常显示
- [ ] 任务可以正常创建
- [ ] 聊天功能正常工作
- [ ] 聊天历史可以保存和恢复
- [ ] 文件上传功能正常
- [ ] 无控制台错误信息

---

## 七、备注

- 修复P0问题后，项目应该可以基本运行
- P1问题修复后，功能和安全性会有显著提升
- P2问题不影响核心功能，可逐步优化

**修复完成后，请运行完整功能测试并更新测试报告。**
