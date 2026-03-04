"""
风控智能体模块
包含主智能体(Manager Agent)和子智能体(Staff Agent)
"""

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
