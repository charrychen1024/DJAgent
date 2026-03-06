"""
会话管理器 - 管理用户与 Agent 的会话
实现用户间隔离、同用户会话复用
"""

import asyncio
import logging
from typing import Dict, Optional
from .staff_agent import StaffAgent
from .manager_agent import ManagerAgent

logger = logging.getLogger(__name__)

# 用户会话缓存
# key: user_id, value: agent实例
_sessions: Dict[str, object] = {}


async def get_or_create_staff_agent(user_id: str, user_name: str) -> StaffAgent:
    """
    获取或创建子智能体（StaffAgent）
    同一用户复用同一实例

    Args:
        user_id: 用户ID
        user_name: 用户名称

    Returns:
        StaffAgent 实例
    """
    if user_id in _sessions:
        agent = _sessions[user_id]
        if isinstance(agent, StaffAgent):
            logger.info(f"[SessionManager] 复用已有 StaffAgent: {user_id}")
            return agent
        else:
            # 类型不匹配，关闭旧的
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)

    # 创建新 Agent
    logger.info(f"[SessionManager] 创建新的 StaffAgent: {user_id}")
    agent = StaffAgent(user_id, user_name)
    # 启动异步会话
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


async def get_or_create_manager_agent(user_id: str, user_name: str) -> ManagerAgent:
    """
    获取或创建主智能体（ManagerAgent）
    同一用户复用同一实例

    Args:
        user_id: 用户ID
        user_name: 用户名称

    Returns:
        ManagerAgent 实例
    """
    if user_id in _sessions:
        agent = _sessions[user_id]
        if isinstance(agent, ManagerAgent):
            logger.info(f"[SessionManager] 复用已有 ManagerAgent: {user_id}")
            return agent
        else:
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)

    # 创建新 Agent
    logger.info(f"[SessionManager] 创建新的 ManagerAgent: {user_id}")
    agent = ManagerAgent(user_id, user_name)
    # 启动异步会话
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


def get_agent(user_id: str) -> Optional[object]:
    """
    获取已存在的 Agent

    Args:
        user_id: 用户ID

    Returns:
        Agent 实例，如果不存在返回 None
    """
    return _sessions.get(user_id)


async def _close_agent(user_id: str):
    """
    关闭用户会话（内部使用）
    """
    if user_id in _sessions:
        agent = _sessions[user_id]
        try:
            await agent.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"[SessionManager] 关闭会话失败: {user_id}, {e}")
        finally:
            del _sessions[user_id]


async def close_agent(user_id: str):
    """
    关闭用户会话

    Args:
        user_id: 用户ID
    """
    logger.info(f"[SessionManager] 关闭会话: {user_id}")
    await _close_agent(user_id)


async def close_all_agents():
    """
    关闭所有会话（服务停止时调用）
    """
    logger.info(f"[SessionManager] 关闭所有会话，共 {len(_sessions)} 个")
    for user_id in list(_sessions.keys()):
        await _close_agent(user_id)


def get_session_count() -> int:
    """获取当前会话数量"""
    return len(_sessions)
