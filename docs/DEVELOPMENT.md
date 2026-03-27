# DJAgent 开发指南

**版本**: v1.0.0
**创建日期**: 2026-03-23
**用途**: 帮助开发者扩展和维护 DJAgent 系统

---

## 一、项目设置和环境配置

### 1.1 前置要求

- Python 3.10+
- Node.js 18+ (前端开发)
- ANTHROPIC_API_KEY (Claude API 密钥)
- Windows 用户：特别注意事项见下文

### 1.2 后端环境设置

#### Step 1: 创建虚拟环境
```bash
cd backend

# Windows
python -m venv .venv
.venv\Scripts\activate

# Mac/Linux
python -m venv .venv
source .venv/bin/activate
```

#### Step 2: 安装依赖
```bash
pip install -r requirements.txt
```

#### Step 3: 配置环境变量
```bash
# .env 文件（在 backend/ 目录下）
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1
ANTHROPIC_AUTH_TOKEN=your_api_key_here

# 重要：取消设置 CLAUDE 环境变量（如果之前设置过）
unset CLAUDE  # Mac/Linux
set CLAUDE=   # Windows（留空）
```

#### Step 4: 运行后端

**Windows（使用 run.py，自动处理事件循环）**：
```bash
python run.py
# 或
python -m uvicorn app_fastapi:app --loop auto --reload --host 0.0.0.0 --port 5005
```

**Mac/Linux**：
```bash
python -m uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 5005
```

验证后端运行：
```bash
curl http://localhost:5005/api/users
# 应返回用户列表
```

### 1.3 前端环境设置

#### Step 1: 安装依赖
```bash
cd frontend
npm install
```

#### Step 2: 开发模式运行
```bash
npm run dev
# 访问 http://localhost:5173
```

#### Step 3: 生产构建
```bash
npm run build
# 输出到 dist/ 目录
```

### 1.4 常见环境问题

#### 问题1: Windows 上 "NotImplementedError: asyncio ProactorEventLoop"

**原因**：Windows 默认 SelectorEventLoop 不支持子进程

**解决**：使用 `--loop auto` 参数或 run.py 脚本

#### 问题2: "CLAUDECODE: command not found"

**原因**：环境变量设置问题

**解决**：检查 CLAUDE 变量（不是 CLAUDECODE）
```bash
# 查看当前值
echo $CLAUDE

# 如果设置了，取消设置
unset CLAUDE
```

#### 问题3: 前端 API 404

**原因**：API_BASE 配置不正确

**解决**：检查 frontend/src/App.jsx
```javascript
// 应该是 5005，不是其他端口
const API_BASE = "http://localhost:5005";
```

---

## 二、如何添加新 Tool（MCP 工具）

### 2.1 工具的五个层次

```
Tool 定义层（tool_definition）
    ├─ 工具原型：@tool 装饰器
    └─ 输入/输出：JSON Schema
         │
         ▼
    MCP 服务器层（mcp_server）
    ├─ 服务器注册
    └─ 工具暴露
         │
         ▼
    Agent 配置层（config）
    ├─ 权限授权：mcp__server__tool 格式
    └─ 工具黑名单/白名单
         │
         ▼
    SessionManager 层
    ├─ 根据角色初始化不同工具集
    └─ Manager vs Staff 权限差异
         │
         ▼
    业务逻辑层（tools/*.py）
    ├─ 实际的数据操作
    └─ 数据访问和转换
```

### 2.2 添加新工具的步骤

#### Step 1: 在 tools/ 中实现业务逻辑

```python
# backend/agents/tools/data_analysis.py

async def analyze_risk_distribution(
    filename: str,
    group_by: str = "risk_level"
) -> Dict[str, Any]:
    """
    分析风险分布

    Args:
        filename: 风险数据文件名
        group_by: 分组维度（risk_level, region, type）

    Returns:
        {"distribution": {...}, "summary": {...}}
    """
    try:
        df = load_risk_data(filename)

        if group_by == "risk_level":
            distribution = df.groupby("风险等级").size().to_dict()
        elif group_by == "region":
            distribution = df.groupby("region").size().to_dict()
        else:
            distribution = df.groupby("异常类型").size().to_dict()

        return {
            "distribution": distribution,
            "summary": f"共发现 {len(df)} 条风险数据",
            "error": None
        }
    except Exception as e:
        return {
            "distribution": {},
            "summary": "",
            "error": str(e)
        }
```

#### Step 2: 在 mcp_server.py 中注册工具

```python
# backend/agents/mcp_server.py

from claude_agent_sdk import tool

@tool(
    name="analyze_risk_distribution",
    description="分析风险数据的分布情况（按风险等级、地区或异常类型统计）",
    input_schema={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "风险数据文件名（如 risk_data_001.csv）"
            },
            "group_by": {
                "type": "string",
                "enum": ["risk_level", "region", "type"],
                "description": "分组维度"
            }
        },
        "required": ["filename"]
    }
)
async def analyze_risk_distribution_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """处理 analyze_risk_distribution 工具调用"""
    from tools.data_analysis import analyze_risk_distribution

    result = await analyze_risk_distribution(
        args.get("filename"),
        args.get("group_by", "risk_level")
    )

    return {
        "Content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
        "is_error": result.get("error") is not None
    }

# 在 MCP 服务器中注册
server = create_sdk_mcp_server(
    name="djagent_tools",
    version="1.0.0",
    tools=[
        # ... 现有工具
        analyze_risk_distribution_tool  # ← 新工具
    ]
)
```

#### Step 3: 在 config.py 中授权工具

```python
# backend/agents/config.py

class ManagerAgentConfig(AgentConfig):
    allowed_tools = [
        # ... 现有工具
        "mcp__djagent_tools__analyze_risk_distribution"  # ← 新工具（mcp__ 前缀必须有）
    ]

# 如果是 Staff 工具，添加到 StaffAgentConfig
class StaffAgentConfig(AgentConfig):
    allowed_tools = [
        # ... 现有工具
    ]
```

#### Step 4: 测试工具

```bash
# 1. 启动后端
python run.py

# 2. 在另一个终端测试
curl -X POST http://localhost:5005/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "分析风险等级分布",
    "user_id": "EMP_001"
  }'

# 应该看到工具被调用并返回结果
```

### 2.3 工具命名规范（关键！）

| 位置 | 格式 | 示例 | 说明 |
|------|------|------|------|
| Python 函数名 | `snake_case` | `analyze_risk_distribution` | 描述性名称 |
| @tool 的 name 参数 | `snake_case` | `analyze_risk_distribution` | 与函数名一致 |
| config.py allowed_tools | `mcp__server__tool` | `mcp__djagent_tools__analyze_risk_distribution` | **必须带 mcp__ 前缀** |

### 2.4 工具最佳实践

```python
@tool(
    name="best_practice_tool",
    description="清晰、简洁、动词开头的描述",
    input_schema={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "详细说明这个参数的用途"
            },
            "param2": {
                "type": "integer",
                "description": "数值参数的范围和含义"
            }
        },
        "required": ["param1"]  # 必需的参数
    }
)
async def best_practice_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    工具实现的最佳实践：

    1. 参数验证
    2. 错误处理
    3. 结果返回
    """
    try:
        # 参数验证
        param1 = args.get("param1")
        if not param1:
            return {
                "Content": [{"type": "text", "text": "参数 param1 为空"}],
                "is_error": True
            }

        # 业务逻辑
        result = do_something(param1, args.get("param2"))

        # 返回结果
        return {
            "Content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "is_error": False
        }
    except Exception as e:
        # 错误处理
        return {
            "Content": [{"type": "text", "text": f"错误：{str(e)}"}],
            "is_error": True
        }
```

---

## 三、如何添加新 Skill（业务技能）

### 3.1 Skill 的职责

Skill 是对一个特定业务流程的封装，包括：
- **意图理解**：检测用户是否想要使用此 Skill
- **信息收集**：与用户多轮对话收集必要信息
- **处理执行**：调用工具完成业务逻辑
- **结果返回**：返回清晰的结果和建议

### 3.2 添加新 Skill 的步骤

#### Step 1: 创建 Skill 目录和文件

```bash
mkdir -p backend/agents/skills/my_skill
touch backend/agents/skills/my_skill/__init__.py
touch backend/agents/skills/my_skill/skill.py
touch backend/agents/skills/my_skill/SKILL.md
```

#### Step 2: 编写 SKILL.md（文档）

```markdown
# MySkill - 我的技能

## 职责
- 完成某项业务流程
- 给出建议

## 输入
- 参数1：说明
- 参数2：说明

## 工作流程
1. 收集信息
2. 分析
3. 给出结果

## 使用示例
"请帮我做X"

## 相关工具
- tool1
- tool2
```

#### Step 3: 编写 skill.py（实现）

```python
# backend/agents/skills/my_skill/skill.py

from agents.skills.skill_base import Skill
from typing import Dict, Any

class MySkill(Skill):
    """我的技能实现"""

    # 元数据
    name = "my_skill"
    description = "完成某项业务流程"
    role = "业务顾问"
    tools = [
        "mcp__djagent_tools__tool1",
        "mcp__djagent_tools__tool2"
    ]
    responsibilities = [
        "收集用户需求",
        "分析数据",
        "给出专业建议"
    ]

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Skill

        Args:
            input_data: 用户输入 {"question": "..."}
            context: 上下文 {"user_id": "...", "task_id": "..."}

        Returns:
            {"success": True, "data": {...}, "error": None}
        """
        try:
            # Step 1: 参数验证
            question = input_data.get("question")
            if not question:
                return {
                    "success": False,
                    "data": None,
                    "error": "请提供具体问题"
                }

            # Step 2: 业务逻辑（可能需要调用工具）
            # 注：工具调用通常由 SDK 在对话中自动完成
            # Skill 主要负责协调和返回结果

            # Step 3: 返回结果
            return {
                "success": True,
                "data": {
                    "answer": "...",
                    "recommendation": "..."
                },
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def get_system_prompt(self) -> str:
        """返回此 Skill 的系统提示词"""
        return f"""你是一个{self.role}。

你的职责：
- {chr(10).join(f"- {r}" for r in self.responsibilities)}

你有以下工具可用：
{chr(10).join(f"- {t}" for t in self.tools)}

工作原则：
1. 清晰理解用户需求
2. 步步为营，逐步分析
3. 提供专业的建议
4. 给出清晰的行动方案
"""
```

#### Step 4: 更新 Skill 意图映射（可选）

```python
# backend/agents/skill_orchestrator.py

_intent_mappings = {
    # ... 现有映射

    # 添加新 Skill 的关键词
    "我的关键词1": ["my_skill"],
    "我的关键词2": ["my_skill"],
    "我的关键词3": ["my_skill"],
}
```

#### Step 5: 测试 Skill

```bash
# Skill 会自动被加载（无需手动配置）
# 启动后端并测试
python run.py

# 在对话中使用
curl -X POST http://localhost:5005/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的关键词1",
    "user_id": "EMP_001"
  }'
```

### 3.3 Skill 最佳实践

#### 1. 清晰的职责边界
```python
class MySkill(Skill):
    # ✅ 好：明确定义职责
    responsibilities = [
        "收集用户需求信息",
        "分析业务影响",
        "制定推荐方案"
    ]

    # ❌ 差：职责太宽泛
    # responsibilities = ["做所有事情"]
```

#### 2. 完整的错误处理
```python
async def execute(self, input_data, context):
    # ✅ 好：详细的错误信息
    if not input_data.get("param"):
        return {
            "success": False,
            "data": None,
            "error": "缺少必需参数：param"
        }

    # ❌ 差：没有验证
    # result = process(input_data.get("param"))
```

#### 3. 有意义的 Tool 声明
```python
class MySkill(Skill):
    # ✅ 好：声明此 Skill 需要的工具
    tools = [
        "mcp__djagent_tools__read_risk_data",
        "mcp__djagent_tools__create_task"
    ]

    # ❌ 差：声明不需要的工具
    # tools = ["mcp__djagent_tools__everything"]
```

---

## 四、如何扩展 Agent

### 4.1 创建新的 Agent 模式

当默认的 Manager/Staff 两种模式不满足需求时，可以创建新模式。

#### Step 1: 创建 Agent 类

```python
# backend/agents/custom_agent.py

from agents.unified_agent import UnifiedAgent
from agents.config import AgentConfig

class CustomAgent(UnifiedAgent):
    """自定义 Agent"""

    def __init__(self, config: AgentConfig, mcp_server, sdk_client):
        super().__init__(config, mcp_server, sdk_client)

        # 自定义初始化逻辑
        self.custom_context = {}

    async def chat(self, message: str, files: List = None) -> str:
        """重写 chat 方法以添加自定义逻辑"""
        # 前处理
        message = self._preprocess_message(message)

        # 调用父类方法
        response = await super().chat(message, files)

        # 后处理
        response = self._postprocess_response(response)

        return response

    def _preprocess_message(self, message: str) -> str:
        """消息预处理"""
        # 可以添加日志、特殊格式转换等
        return message

    def _postprocess_response(self, response: str) -> str:
        """响应后处理"""
        # 可以添加日志、结果转换等
        return response
```

#### Step 2: 在 SessionManager 中使用

```python
# backend/agents/session_manager.py

class SessionManager:
    async def get_or_create_custom_agent(self, user_id, user_info) -> CustomAgent:
        """创建自定义 Agent"""
        if user_id not in self.sessions:
            config = self._build_custom_config(user_info)
            agent = CustomAgent(config, self.mcp_server, self.sdk_client)
            self.sessions[user_id] = agent
        return self.sessions[user_id]

    def _build_custom_config(self, user_info) -> AgentConfig:
        """构建自定义配置"""
        return AgentConfig(
            mode="custom",
            user_id=user_info["user_id"],
            username=user_info["username"],
            employee_id=user_info["employee_id"],
            # ... 其他配置
        )
```

### 4.2 添加 Agent 钩子（Hook）

Agent 的关键点上添加自定义逻辑：

```python
class ExtendedAgent(UnifiedAgent):

    # 钩子1：工具调用前
    async def before_tool_call(self, tool_name: str, args: Dict):
        """工具调用前的钩子"""
        logger.info(f"即将调用工具: {tool_name} with args: {args}")

    # 钩子2：工具调用后
    async def after_tool_call(self, tool_name: str, result: Dict):
        """工具调用后的钩子"""
        logger.info(f"工具调用结果: {result}")

    # 钩子3：Skill 执行前
    async def before_skill_execute(self, skill_name: str, input_data: Dict):
        """Skill 执行前的钩子"""
        logger.info(f"即将执行 Skill: {skill_name}")

    # 钩子4：Skill 执行后
    async def after_skill_execute(self, skill_name: str, result: Dict):
        """Skill 执行后的钩子"""
        logger.info(f"Skill 执行结果: {result}")
```

---

## 五、测试策略

### 5.1 单元测试

```python
# backend/tests/test_tools.py

import pytest
from agents.tools.data_analysis import analyze_risk_distribution

@pytest.mark.asyncio
async def test_analyze_risk_distribution():
    """测试风险分布分析工具"""
    result = await analyze_risk_distribution(
        filename="risk_data_001.csv",
        group_by="risk_level"
    )

    assert result["error"] is None
    assert "distribution" in result
    assert "高" in result["distribution"] or "中" in result["distribution"]

@pytest.mark.asyncio
async def test_analyze_risk_distribution_with_invalid_file():
    """测试工具处理无效文件"""
    result = await analyze_risk_distribution(
        filename="nonexistent.csv",
        group_by="risk_level"
    )

    assert result["error"] is not None
```

### 5.2 集成测试

```python
# backend/tests/test_agent_integration.py

import pytest
from agents.session_manager import SessionManager

@pytest.mark.asyncio
async def test_manager_agent_risk_analysis():
    """测试 Manager Agent 的风险分析流程"""
    session_manager = SessionManager()

    agent = await session_manager.get_or_create_manager_agent(
        user_id="EMP_001",
        user_info={"username": "王经理", "employee_id": "EMP_001"}
    )

    response = await agent.chat("分析今日风险数据")

    assert response is not None
    assert len(response) > 0
    # 应该包含分析结果
```

### 5.3 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行所有测试
pytest

# 运行特定测试文件
pytest backend/tests/test_tools.py

# 运行特定测试函数
pytest backend/tests/test_tools.py::test_analyze_risk_distribution

# 显示详细输出
pytest -v
```

---

## 六、部署指南

### 6.1 本地部署

```bash
# 1. 克隆项目
git clone <repo-url>
cd DJAgent

# 2. 后端设置
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 配置环境变量
echo "ANTHROPIC_AUTH_TOKEN=xxx" > .env

# 4. 启动后端
python run.py

# 5. 前端设置（新终端）
cd frontend
npm install
npm run dev

# 6. 访问
# 后端: http://localhost:5005
# 前端: http://localhost:5173
```

### 6.2 Docker 部署

```dockerfile
# Dockerfile.backend
FROM python:3.10-slim

WORKDIR /app/backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 5005

CMD ["python", "-m", "uvicorn", "app_fastapi:app", "--host", "0.0.0.0", "--port", "5005"]
```

```bash
# 构建和运行
docker build -t djagent-backend -f Dockerfile.backend .
docker run -e ANTHROPIC_AUTH_TOKEN=xxx -p 5005:5005 djagent-backend
```

### 6.3 生产环境建议

- 使用 Gunicorn 作为 WSGI 服务器
- 使用 Nginx 作为反向代理
- 配置 CORS 和安全头
- 使用数据库代替 CSV 文件
- 实现速率限制
- 配置日志和监控

---

## 七、性能优化

### 7.1 缓存优化

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedDataManager:
    """带 TTL 的数据缓存管理"""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str):
        """获取缓存数据"""
        if key not in self.cache:
            return None

        data, timestamp = self.cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            del self.cache[key]
            return None

        return data

    def set(self, key: str, value):
        """设置缓存数据"""
        self.cache[key] = (value, datetime.now())

# 使用示例
cache_manager = CachedDataManager(ttl_seconds=3600)

async def get_users():
    cached = cache_manager.get("all_users")
    if cached:
        return cached

    users = load_users_from_csv()
    cache_manager.set("all_users", users)
    return users
```

### 7.2 数据库优化

如果迁移到数据库，建议：
- 为常用查询字段添加索引（creator_id, assigned_to_id, status, region）
- 使用分页查询大数据集
- 定期清理过期数据
- 使用连接池管理数据库连接

### 7.3 API 响应优化

```python
# 使用异步 I/O 处理并发请求
@app.post("/api/batch-tasks")
async def batch_tasks(requests: List[Dict]):
    """并发处理多个请求"""
    tasks = [process_task(req) for req in requests]
    results = await asyncio.gather(*tasks)
    return results

# 使用分页减少单次响应体积
@app.get("/api/tasks")
async def get_tasks(page: int = 1, per_page: int = 20):
    """分页返回任务列表"""
    start = (page - 1) * per_page
    end = start + per_page
    return tasks[start:end]
```

---

## 八、常见开发任务

### 8.1 调试技巧

```python
# 1. 使用日志
import logging

logger = logging.getLogger(__name__)
logger.debug(f"调试信息: {variable}")
logger.info(f"信息: {event}")
logger.error(f"错误: {exception}")

# 2. SDK 响应检查
async def debug_agent_response(message: str):
    await client.query(message, system=system_prompt)
    async for response in client.receive_response():
        print(f"响应类型: {type(response)}")
        print(f"响应内容: {response}")

# 3. 工具参数验证
@tool(...)
async def my_tool(args: Dict) -> Dict:
    print(f"收到的参数: {args}")  # ← 调试参数
    # ... 处理逻辑
```

### 8.2 添加日志

```python
# 配置日志
import logging
import logging.handlers

# 创建日志记录器
logger = logging.getLogger("djagent")
logger.setLevel(logging.DEBUG)

# 文件处理器
handler = logging.handlers.RotatingFileHandler(
    "logs/djagent.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

# 格式
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# 使用
logger.info(f"用户 {user_id} 创建了任务 {task_id}")
```

### 8.3 性能分析

```python
import time
import asyncio

# 测量函数执行时间
def measure_time(func):
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} 耗时: {elapsed:.2f}s")
        return result
    return wrapper

@measure_time
async def slow_function():
    await asyncio.sleep(1)
    return "done"
```

---

## 九、故障诊断

### 问题1: Agent 响应很慢

**诊断**：
```python
# 添加日志检查每一步的耗时
logger.info(f"工具调用前: {time.time()}")
await client.query(message)
logger.info(f"工具调用后: {time.time()}")
```

**解决**：
- 检查工具实现是否有重操作
- 添加缓存减少重复查询
- 异步处理 I/O 操作

### 问题2: 权限错误

**诊断**：
```python
# 检查用户信息
user = get_user_by_employee_id(employee_id)
logger.info(f"用户信息: {user}")
logger.info(f"角色: {user.role}, 区域: {user.region}")
```

**解决**：
- 确保 employee_id 正确
- 检查用户是否存在于 users.csv
- 验证角色和权限配置

### 问题3: 工具调用失败

**诊断**：
```python
# 检查工具是否在 allowed_tools 中
logger.info(f"允许的工具: {config.allowed_tools}")

# 检查工具名称格式
# 应该是 mcp__server__tool，不是 server__tool 或 tool
```

**解决**：
- 确保工具名称带有 `mcp__` 前缀
- 检查工具是否在 MCP 服务器中注册
- 验证服务器名称（djagent_tools）

---

## 十、更新历史

**最后更新**: 2026-03-23
**文档版本**: v1.0.0

### v1.0.0 (2026-03-23)
- 初始版本
- 完整的环境设置指南
- 工具、Skill、Agent 扩展指南
- 测试、部署、性能优化、故障诊断
