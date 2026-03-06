# 聊天上下文保持改进方案

**目标**: Demo阶段，保证刷新网页、用户切换等简单场景下聊天不中断

**范围**: Web端（业务负责人）+ IM端（一线人员）

---

## 一、当前问题确认

### 问题根源
1. ❌ 每次请求都创建新 Agent 实例
2. ❌ 每次都启动新 Claude 客户端会话
3. ❌ 会话结束后关闭，上下文丢失
4. ❌ SessionManager 已实现但未使用

### 影响场景
| 场景 | 现状 | 期望 |
|------|------|------|
| 刷新网页 | ❌ 聊天中断 | ✅ 保持上下文 |
| 用户切换 | ❌ 聊天中断 | ✅ 切换后可以恢复 |
| 多标签页 | ⚠️ 可能冲突 | ✅ 正常处理 |

---

## 二、开发计划

### 阶段1：后端改造（1-2小时）

#### 任务1.1：修改 Web 端 chat 接口

**文件**: `backend/app_fastapi.py`

**当前代码**:
```python
@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    # ...
    agent = ManagerAgent(user_id, username)  # ❌ 每次新建
    async with agent:  # ❌ 每次启动新会话
        response_text = await agent.chat(message)
    # ...
```

**修改为**:
```python
@app.post("/api/chat")
async def chat(request: Request):
    from agents.session_manager import get_or_create_manager_agent
    
    data = await request.json()
    message = data.get("message", "")
    user_id = data.get("user_id", "manager_default")
    username = data.get("username", "业务负责人")
    
    logger.info(f"[API] 用户消息: {message}")
    
    if not HAS_AGENT_SDK:
        response_text = (
            f"收到您的消息：{message}\n\n（当前为简化模式，未连接 Agent SDK）"
        )
    else:
        try:
            # ✅ 使用 SessionManager 获取或创建 Agent
            agent = await get_or_create_manager_agent(user_id, username)
            
            # ✅ 直接 chat，不使用 async with（避免关闭会话）
            response_text = await agent.chat(message)
            
            logger.info(f"[API] ManagerAgent 回复成功")
        except Exception as e:
            logger.error(f"[ERROR] ManagerAgent 调用失败: {str(e)}")
            response_text = "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    return {
        "message": response_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
```

#### 任务1.2：修改 IM 端 send_message 接口

**文件**: `backend/app_fastapi.py`

**当前代码**:
```python
@app.post("/api/tasks/{task_id}/message")
async def send_message(task_id: str, request: Request):
    # ...
    agent = StaffAgent(user_id, username)  # ❌ 每次新建
    async with agent:  # ❌ 每次启动新会话
        agent.current_task_id = task_id
        ai_response = await agent.chat(message)
    # ...
```

**修改为**:
```python
@app.post("/api/tasks/{task_id}/message")
async def send_message(task_id: str, request: Request):
    from agents.session_manager import get_or_create_staff_agent
    
    data = await request.json()
    message = data.get("message", "")
    user_id = data.get("user_id")
    username = data.get("username", "")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    user_message = {
        "timestamp": timestamp,
        "sender": username,
        "message": message,
        "message_type": "text",
    }
    
    if not HAS_AGENT_SDK:
        ai_response = "Agent SDK未安装，暂时无法处理消息"
    else:
        try:
            # ✅ 使用 SessionManager 获取或创建 Agent
            agent = await get_or_create_staff_agent(user_id, username)
            
            # ✅ 设置当前任务ID
            agent.current_task_id = task_id
            
            # ✅ 直接 chat，不使用 async with
            ai_response = await agent.chat(message)
            
        except Exception as e:
            logger.error(f"[ERROR] Agent调用失败: {str(e)}")
            ai_response = "好的，请继续。"
    
    # 保存到文件（保持现有逻辑）
    # ...
```

#### 任务1.3：添加会话清理接口

**文件**: `backend/app_fastapi.py`

**新增接口**:
```python
@app.post("/api/logout")
async def logout(request: Request):
    """用户退出时清理会话"""
    from agents.session_manager import close_agent
    
    data = await request.json()
    user_id = data.get("user_id")
    
    if user_id:
        await close_agent(user_id)
        logger.info(f"[API] 用户 {user_id} 登出，会话已关闭")
    
    return {"status": "success", "message": "登出成功"}


@app.post("/api/session/cleanup")
async def cleanup_sessions(request: Request):
    """清理指定用户的会话"""
    from agents.session_manager import close_agent
    
    data = await request.json()
    user_ids = data.get("user_ids", [])
    
    closed_count = 0
    for user_id in user_ids:
        await close_agent(user_id)
        closed_count += 1
    
    logger.info(f"[API] 清理了 {closed_count} 个会话")
    
    return {"status": "success", "closed_count": closed_count}
```

#### 任务1.4：服务启动时清理会话

**文件**: `backend/app_fastapi.py`

**新增**:
```python
# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("[API] 服务启动")
    # 清理可能存在的旧会话
    from agents.session_manager import close_all_agents
    await close_all_agents()
    logger.info("[API] 已清理所有旧会话")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[API] 服务关闭")
    # 关闭所有会话
    from agents.session_manager import close_all_agents
    await close_all_agents()
    logger.info("[API] 已关闭所有会话")
```

---

### 阶段2：Agent 类改造（30分钟）

#### 任务2.1：ManagerAgent 改造

**文件**: `backend/agents/manager_agent.py`

**修改 chat 方法，支持持续对话**:
```python
async def chat(self, message: str, context: Optional[Dict] = None) -> str:
    logger.info(f"[ManagerAgent] 收到消息: {message[:100]}...")
    
    # 构建prompt，包含上下文
    prompt = f"""当前用户：{self.user_name} (ID: {self.user_id})

"""
    
    if context:
        if context.get('task_id'):
            prompt += f"当前任务ID：{context.get('task_id')}\n"
        if context.get('risk_data'):
            prompt += f"风险数据：{context.get('risk_data')}\n"
    
    prompt += f"\n用户消息：{message}"
    
    logger.info(f"[ManagerAgent] 发送prompt给AI...")
    
    # 发送消息（client 已在 __aenter__ 中启动）
    await self.client.query(prompt)
    
    # 收集回复
    responses = []
    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    responses.append(block.text)
        elif isinstance(msg, ResultMessage):
            logger.info(f"[ManagerAgent] 请求完成: {msg.subtype}")
    
    reply = "\n".join(responses) if responses else "抱歉，我未能理解您的意思，请重试。"
    
    logger.info(f"[ManagerAgent] 回复: {reply[:100]}...")
    return reply
```

**注意**: 保持 `__aenter__` 和 `__aexit__` 方法不变，确保首次使用时启动会话。

#### 任务2.2：StaffAgent 改造

**文件**: `backend/agents/staff_agent.py`

**修改 chat 方法**:
```python
async def chat(self, message: str) -> str:
    logger.info(f"[StaffAgent] 收到消息: {message[:100]}...")
    
    # 构建prompt
    prompt = f"""当前用户：{self.user_name} (ID: {self.user_id})
当前任务ID：{self.current_task_id or '无'}

一线人员消息：{message}

请根据任务要求回复用户，指导其完成核查工作。"""
    
    # 发送消息
    await self.client.query(prompt)
    
    # 收集回复
    responses = []
    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    responses.append(block.text)
        elif isinstance(msg, ResultMessage):
            logger.info(f"[StaffAgent] 请求完成: {msg.subtype}")
    
    reply = "\n".join(responses) if responses else "好的，请继续。"
    
    logger.info(f"[StaffAgent] 回复: {reply[:100]}...")
    return reply
```

---

### 阶段3：前端改造（1小时）

#### 任务3.1：添加退出登录接口调用

**文件**: `frontend/src/App.jsx`

**修改 logout 逻辑**:
```javascript
const handleLogout = async () => {
  const currentUserId = currentUser?.user_id
  
  // 调用后端登出接口
  if (currentUserId) {
    try {
      await fetch(`${API_BASE}/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: currentUserId })
      })
      console.log('[INFO] 已通知后端关闭会话')
    } catch (err) {
      console.error('[ERROR] 登出失败:', err)
    }
  }
  
  setCurrentUser(null)
}
```

#### 任务3.2：用户切换时保持前一个会话（可选）

**实现思路**: 
- 简单方案：用户切换时立即调用登出接口（推荐）
- 高级方案：允许用户快速切换，保持多个会话

**推荐使用简单方案**:
```javascript
const handleUserChange = async (e) => {
  const newUserId = e.target.value
  const currentUserId = currentUser?.user_id
  
  // 如果有当前用户，先关闭会话
  if (currentUserId && newUserId !== currentUserId) {
    try {
      await fetch(`${API_BASE}/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: currentUserId })
      })
    } catch (err) {
      console.error('[ERROR] 关闭前用户会话失败:', err)
    }
  }
  
  // 切换到新用户
  if (newUserId) {
    const user = users.find(u => u.user_id === newUserId)
    if (user) setCurrentUser(user)
  } else {
    setCurrentUser(null)
  }
}
```

#### 任务3.3：刷新页面时保持用户状态

**实现思路**: 使用 localStorage 保存当前用户

**新增逻辑**:
```javascript
// 从 URL 或 localStorage 恢复用户状态
useEffect(() => {
  const params = new URLSearchParams(window.location.search)
  const presetUserId = params.get('user_id')
  
  // 尝试从 localStorage 恢复
  const savedUserId = localStorage.getItem('djagent_current_user_id')
  
  fetch(`${API_BASE}/users`).then(r => r.json()).then(usersData => {
    setUsers(usersData)
    
    // 优先级：URL参数 > localStorage > 首次用户
    const targetUserId = presetUserId || savedUserId
    
    if (targetUserId) {
      const user = usersData.find(u => u.user_id === targetUserId)
      if (user) {
        setCurrentUser(user)
        return
      }
    }
  }).catch(console.error).finally(() => setLoading(false))
}, [])

// 保存当前用户到 localStorage
useEffect(() => {
  if (currentUser) {
    localStorage.setItem('djagent_current_user_id', currentUser.user_id)
  } else {
    localStorage.removeItem('djagent_current_user_id')
  }
}, [currentUser])
```

---

### 阶段4：测试验证（30分钟）

#### 测试用例

**测试4.1：Web端连续对话**
1. 登录业务负责人账号
2. 发送消息1："你好"
3. 发送消息2："请介绍一下自己"
4. 发送消息3："你能做什么？"
5. **验证**: AI 应该能够记住之前的对话

**测试4.2：Web端刷新页面**
1. 登录业务负责人账号
2. 发送几条消息
3. 刷新页面（F5）
4. 继续发送消息
5. **验证**: AI 应该记得刷新前的对话

**测试4.3：Web端用户切换**
1. 登录业务负责人账号A，发送消息
2. 切换到业务负责人账号B，发送消息
3. 切换回业务负责人账号A
4. 继续对话
5. **验证**: 账号A 的会话应该保持，账号B 的会话应该是独立的

**测试4.4：IM端连续对话**
1. 登录一线人员账号
2. 自动进入任务对话
3. 发送多条消息
4. **验证**: AI 应该保持上下文

**测试4.5：IM端刷新页面**
1. 登录一线人员账号
2. 发送消息
3. 刷新页面
4. 继续发送消息
5. **验证**: AI 应该记得刷新前的对话

**测试4.6：多标签页**
1. 打开两个浏览器标签页
2. 登录同一个用户
3. 在标签页1发送消息
4. 在标签页2发送消息
5. **验证**: 两个标签页应该能正常工作（可能有竞态，但不应崩溃）

---

## 三、产品需求修改

### 3.1 新增 API 接口

#### POST /api/logout
**功能**: 用户登出时关闭会话

**请求**:
```json
{
  "user_id": "001"
}
```

**响应**:
```json
{
  "status": "success",
  "message": "登出成功"
}
```

#### POST /api/session/cleanup
**功能**: 批量清理会话（管理员功能）

**请求**:
```json
{
  "user_ids": ["001", "002", "003"]
}
```

**响应**:
```json
{
  "status": "success",
  "closed_count": 3
}
```

### 3.2 前端行为调整

#### 用户登录
- 支持 localStorage 自动恢复上次登录用户
- URL 参数 user_id 优先级最高

#### 用户登出
- 点击"切换用户"按钮时，先调用 `/api/logout` 关闭会话
- 清除 localStorage 中的用户信息

#### 页面刷新
- 自动恢复上次登录用户
- 自动恢复聊天历史（从文件读取）
- 保持与后端的会话连接

### 3.3 用户体验改进

#### 连接状态提示
- 首次连接时显示"正在连接..."
- 会话保持时显示"已连接"
- 会话断开时显示"连接断开，正在重连..."

#### 错误处理
- 会话创建失败时显示友好提示
- 自动重连机制（可选）

---

## 四、技术方案说明

### 4.1 会话生命周期

```
用户登录 → 创建 Agent 实例 → 启动 Claude 客户端 → 缓存到 SessionManager
    ↓
用户发送消息1 → 复用 Agent 实例 → client.query() → AI 回复（记得上下文）
    ↓
用户发送消息2 → 复用 Agent 实例 → client.query() → AI 回复（记得上下文1和2）
    ↓
用户刷新页面 → localStorage 恢复 user_id → SessionManager 复用实例 → 保持上下文
    ↓
用户切换 → 调用 /api/logout → 关闭 Agent 实例 → 清理 SessionManager
    ↓
用户重新登录 → 创建新实例 → 新会话
```

### 4.2 并发处理

**问题**: 用户打开多个标签页

**解决方案**: 
- SessionManager 已经处理了同用户复用逻辑
- 多标签页会复用同一个 Agent 实例
- 可能存在竞态条件，但在 demo 阶段可接受

**未来改进**: 使用锁机制或会话 ID 隔离

### 4.3 内存管理

**当前方案**: 全局字典缓存

```python
_sessions: Dict[str, object] = {}
```

**特点**:
- ✅ 简单直接
- ✅ 访问快速
- ❌ 进程重启后丢失
- ⚠️ 长期运行可能内存泄漏

**改进建议** (demo 阶段暂不需要):
- 添加会话超时清理（如 30 分钟无活动）
- 添加最大会话数限制（如最多 100 个活跃会话）

---

## 五、实施步骤

### Step 1: 后端改造（优先级 P0）
1. ✅ 修改 `/api/chat` 使用 SessionManager
2. ✅ 修改 `/api/tasks/{task_id}/message` 使用 SessionManager
3. ✅ 添加 `/api/logout` 接口
4. ✅ 添加服务启动/关闭事件处理
5. ✅ 测试后端接口

### Step 2: 前端改造（优先级 P0）
1. ✅ 添加 localStorage 用户恢复逻辑
2. ✅ 修改 logout 调用后端接口
3. ✅ 修改用户切换逻辑
4. ✅ 测试前端功能

### Step 3: 集成测试（优先级 P0）
1. ✅ 测试 Web 端连续对话
2. ✅ 测试 Web 端刷新页面
3. ✅ 测试 Web 端用户切换
4. ✅ 测试 IM 端连续对话
5. ✅ 测试 IM 端刷新页面

### Step 4: 文档更新（优先级 P1）
1. ✅ 更新 API 文档
2. ✅ 更新 README
3. ✅ 更新开发文档

---

## 六、风险和限制

### 6.1 当前方案的局限性

| 限制 | 说明 | 影响 | 缓解措施 |
|------|------|------|----------|
| 进程重启 | 会话全部丢失 | 服务重启后需重新登录 | Demo 阶段可接受 |
| 内存缓存 | 长期运行可能泄漏 | 建议定期重启 | Demo 阶段可接受 |
| 多标签页 | 可能竞态 | 可能导致会话混乱 | Demo 阶段可接受 |
| 无持久化 | 无法恢复历史对话 | 刷新页面后需重连 | Demo 阶段可接受 |

### 6.2 已知问题（demo 阶段暂不处理）

1. ❌ 会话持久化到数据库（需要额外依赖）
2. ❌ 会话超时自动清理
3. ❌ 多标签页会话隔离
4. ❌ 离线重连机制
5. ❌ WebSocket 实时推送

### 6.3 未来改进方向

1. 添加 Redis 作为会话存储
2. 实现会话持久化到数据库
3. 添加会话超时和清理机制
4. 实现真正的多会话支持（每个标签页独立会话）
5. 添加心跳检测和自动重连

---

## 七、验收标准

### 功能验收
- [ ] Web 端连续对话能够保持上下文
- [ ] Web 端刷新页面后上下文不丢失
- [ ] Web 端用户切换后新用户独立会话
- [ ] Web 端切换回旧用户上下文保持
- [ ] IM 端连续对话能够保持上下文
- [ ] IM 端刷新页面后上下文不丢失
- [ ] 用户登出后后端会话正确关闭
- [ ] 服务重启后正确清理旧会话

### 性能验收
- [ ] Agent 实例复用不重复创建
- [ ] 会话切换响应时间 < 1s
- [ ] 内存占用合理（不持续增长）

### 稳定性验收
- [ ] 多标签页不会导致服务崩溃
- [ ] 异常情况有友好的错误提示
- [ ] 后端日志完整，便于调试

---

## 八、时间估算

| 任务 | 预计时间 | 负责人 |
|------|---------|--------|
| 后端改造 | 1.5 小时 | - |
| Agent 类改造 | 0.5 小时 | - |
| 前端改造 | 1 小时 | - |
| 集成测试 | 0.5 小时 | - |
| 文档更新 | 0.5 小时 | - |
| **总计** | **4 小时** | - |

---

**创建日期**: 2026-03-06  
**计划状态**: 待实施  
**下一步**: 按照步骤开始改造
