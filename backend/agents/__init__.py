"""
风控智能体模块

重构后：
1. 统一 Agent 核心 (UnifiedAgent)
2. Agent 配置 (AgentConfig)
3. SessionManager 支持统一的 Agent 创建
4. 保持向后兼容
"""

# AgentConfig 不依赖 claude_agent_sdk，可以始终导入
from .config import AgentConfig, create_manager_config, create_staff_config

__all__ = [
    "AgentConfig",
    "create_manager_config",
    "create_staff_config",
]

# 导出 SessionManager
try:
    from .session_manager import (
        get_or_create_staff_agent,
        get_or_create_manager_agent,
        get_or_create_agent,
        get_agent,
        close_agent,
        close_all_agents,
        get_session_count,
    )

    __all__ += [
        "get_or_create_staff_agent",
        "get_or_create_manager_agent",
        "get_or_create_agent",
        "get_agent",
        "close_agent",
        "close_all_agents",
        "get_session_count",
    ]
except ImportError as e:
    pass

# 导出新架构（依赖 claude_agent_sdk）
try:
    from .unified_agent import UnifiedAgent

    __all__ += ["UnifiedAgent"]
except ImportError:
    pass

# 导出 Skill 编排器
try:
    from .skill_orchestrator import (
        SkillOrchestrator,
        get_orchestrator,
        detect_intent,
        execute_skill,
        execute_by_intent,
    )

    __all__ += [
        "SkillOrchestrator",
        "get_orchestrator",
        "detect_intent",
        "execute_skill",
        "execute_by_intent",
    ]
except ImportError:
    pass

# 导出旧架构（向后兼容）
try:
    from .manager_agent import ManagerAgent
    from .staff_agent import StaffAgent

    __all__ += ["ManagerAgent", "StaffAgent"]
except ImportError:
    pass
