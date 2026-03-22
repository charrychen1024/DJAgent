"""
会话管理器 - 管理用户与 Agent 的会话
实现用户间隔离、同用户会话复用
支持统一的 Agent 创建，使用 AgentConfig 实例驱动
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from .config import AgentConfig, create_manager_config, create_staff_config

logger = logging.getLogger(__name__)

# 延迟导入 UnifiedAgent（因为依赖 claude_agent_sdk）
UnifiedAgent = None


def _get_unified_agent_class():
    """获取 UnifiedAgent 类（延迟导入）"""
    global UnifiedAgent
    if UnifiedAgent is None:
        from .unified_agent import UnifiedAgent as UA

        UnifiedAgent = UA
    return UnifiedAgent


# 用户会话缓存
# key: user_id, value: agent实例
_sessions: Dict[str, UnifiedAgent] = {}  # 使用 UnifiedAgent 类型


async def get_or_create_staff_agent(
    user_id: str, user_name: str, skills: Optional[list] = None
) -> UnifiedAgent:
    """
    获取或创建 Staff Agent（一线人员 Agent）
    同一用户复用同一实例

    Args:
        user_id: 用户ID
        user_name: 用户名称
        skills: 要加载的 Skill 列表（None 表示加载全部）

    Returns:
        UnifiedAgent 实例（Staff 模式）
    """
    if user_id in _sessions:
        agent = _sessions[user_id]
        if agent.config.mode == "staff":
            logger.info(f"[SessionManager] 复用已有 StaffAgent: {user_id}")
            return agent
        else:
            # 类型不匹配，关闭旧的
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)

    # 创建新 Agent
    logger.info(f"[SessionManager] 创建新的 StaffAgent: {user_id}")

    # Staff Agent 也需要加载 MCP 服务器
    try:
        from .mcp_server import create_djagent_mcp_server
        mcp_servers = {"djagent_tools": create_djagent_mcp_server()}
        logger.info(f"[SessionManager] StaffAgent 加载 MCP 服务器")
    except Exception as e:
        logger.error(f"[SessionManager] 加载 MCP 服务器失败: {e}")
        mcp_servers = {}

    config = create_staff_config(user_id, user_name, mcp_servers=mcp_servers, skills=skills)
    UnifiedAgentClass = _get_unified_agent_class()
    agent = UnifiedAgentClass(config)
    # 启动异步会话
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


async def get_or_create_manager_agent(
    user_id: str, user_name: str, mcp_servers: Optional[Dict[str, Any]] = None
) -> UnifiedAgent:
    """
    获取或创建 Manager Agent（业务负责人 Agent）
    同一用户复用同一实例

    Args:
        user_id: 用户ID
        user_name: 用户名称
        mcp_servers: MCP 服务器配置

    Returns:
        UnifiedAgent 实例（Manager 模式）
    """
    if user_id in _sessions:
        agent = _sessions[user_id]
        if agent.config.mode == "manager":
            logger.info(f"[SessionManager] 复用已有 ManagerAgent: {user_id}")
            return agent
        else:
            # 类型不匹配，关闭旧的
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)

    # 创建新 Agent
    logger.info(f"[SessionManager] 创建新的 ManagerAgent: {user_id}")

    # 如果没有提供 MCP 服务器，加载默认的
    if mcp_servers is None:
        try:
            from .mcp_server import create_djagent_mcp_server

            mcp_servers = {"djagent_tools": create_djagent_mcp_server()}
            logger.info(f"[SessionManager] 加载默认 MCP 服务器")
        except Exception as e:
            logger.error(f"[SessionManager] 加载 MCP 服务器失败: {e}")
            mcp_servers = {}

    config = create_manager_config(user_id, user_name, mcp_servers=mcp_servers)
    UnifiedAgentClass = _get_unified_agent_class()
    agent = UnifiedAgentClass(config)
    # 启动异步会话
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


async def get_or_create_agent(
    user_id: str, user_name: str, config: AgentConfig
) -> UnifiedAgent:
    """
    获取或创建 Agent（使用自定义配置）
    同一用户复用同一实例

    Args:
        user_id: 用户ID
        user_name: 用户名称
        config: Agent 配置

    Returns:
        UnifiedAgent 实例
    """
    if user_id in _sessions:
        agent = _sessions[user_id]
        if agent.config.mode == config.mode:
            logger.info(f"[SessionManager] 复用已有 Agent ({config.mode}): {user_id}")
            return agent
        else:
            # 类型不匹配，关闭旧的
            logger.warning(f"[SessionManager] 用户类型变化，关闭旧会话: {user_id}")
            await _close_agent(user_id)

    # 创建新 Agent
    logger.info(f"[SessionManager] 创建新的 Agent ({config.mode}): {user_id}")
    UnifiedAgentClass = _get_unified_agent_class()
    agent = UnifiedAgentClass(config)
    # 启动异步会话
    await agent.__aenter__()
    _sessions[user_id] = agent
    return agent


def get_agent(user_id: str) -> Optional[UnifiedAgent]:
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
