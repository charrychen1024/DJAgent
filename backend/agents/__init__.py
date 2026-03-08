"""
风控智能体模块
包含主智能体(Manager Agent)和子智能体(Staff Agent)
"""

try:
    from .manager_agent import ManagerAgent
    from .staff_agent import StaffAgent
    from .session_manager import (
        get_or_create_staff_agent,
        get_or_create_manager_agent,
        get_agent,
        close_agent,
        close_all_agents,
        get_session_count,
    )

    __all__ = [
        'ManagerAgent', 
        'StaffAgent',
        'get_or_create_staff_agent',
        'get_or_create_manager_agent',
        'get_agent',
        'close_agent',
        'close_all_agents',
        'get_session_count',
    ]
except ImportError:
    # 如果缺少依赖（如 claude_agent_sdk），允许导入 agents 包但不导出具体 Agent
    pass
