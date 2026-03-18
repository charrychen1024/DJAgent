"""
动态工具注册中心 - 支持装饰器注册和热加载
参考文档: docs/AGENT_PROMPT_DESIGN.md
"""

import logging
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """工具元数据"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    category: str = "general"


class ToolRegistry:
    """动态工具注册表"""

    _tools: Dict[str, Tool] = {}
    _initialized: bool = False

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        category: str = "general"
    ):
        """装饰器：注册工具

        用法：
        @ToolRegistry.register(
            name="create_task",
            description="创建新的风控任务",
            parameters={"task_type": "str", "risk_level": "str"},
            category="task"
        )
        async def create_task(...):
            ...
        """
        def decorator(func: Callable) -> Callable:
            if name in cls._tools:
                logger.warning(f"[ToolRegistry] 工具 {name} 已存在，将被覆盖")

            cls._tools[name] = Tool(
                name=name,
                description=description,
                parameters=parameters or {},
                handler=func,
                category=category
            )
            logger.info(f"[ToolRegistry] 注册工具: {name} (category: {category})")
            return func
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[Tool]:
        """获取工具"""
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> Dict[str, Tool]:
        """获取所有工具"""
        return cls._tools.copy()

    @classmethod
    def get_tools_by_category(cls, category: str) -> List[Tool]:
        """按类别获取工具"""
        return [t for t in cls._tools.values() if t.category == category]

    @classmethod
    def get_tools_prompt(cls) -> str:
        """动态生成工具描述（用于System Prompt）"""
        if not cls._tools:
            return "（暂无配置的工具）"

        # 按类别分组
        categories: Dict[str, List[Tool]] = {}
        for tool in cls._tools.values():
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool)

        lines = []
        for category, tools in categories.items():
            lines.append(f"\n### {category}")
            for tool in tools:
                params = ", ".join(tool.parameters.keys()) if tool.parameters else "无"
                lines.append(f"- **{tool.name}**({params}): {tool.description}")

        return "\n".join(lines)

    @classmethod
    def get_tools_for_mcp(cls) -> List[str]:
        """获取MCP格式的工具名列表"""
        return list(cls._tools.keys())

    @classmethod
    def get_tools_description_simple(cls) -> str:
        """简化版工具描述（名称+描述）"""
        if not cls._tools:
            return "（暂无配置的工具）"

        lines = []
        for tool in cls._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    @classmethod
    def clear(cls):
        """清空注册表（测试用）"""
        cls._tools.clear()
        cls._initialized = False
        logger.info("[ToolRegistry] 注册表已清空")


class SkillRegistry:
    """Skill注册表（与Tool类似）"""

    _skills: Dict[str, dict] = {}

    @classmethod
    def register_skill(
        cls,
        name: str,
        description: str,
        category: str = "general",
        tools: Optional[List[str]] = None,
        sub_skills: Optional[List[str]] = None
    ):
        """注册Skill"""
        def decorator(func):
            cls._skills[name] = {
                "name": name,
                "description": description,
                "category": category,
                "tools": tools or [],
                "sub_skills": sub_skills or [],
                "handler": func
            }
            logger.info(f"[SkillRegistry] 注册Skill: {name} (category: {category})")
            return func
        return decorator

    @classmethod
    def get_skill(cls, name: str) -> Optional[dict]:
        """获取Skill"""
        return cls._skills.get(name)

    @classmethod
    def get_all_skills(cls) -> Dict[str, dict]:
        """获取所有Skills"""
        return cls._skills.copy()

    @classmethod
    def get_skills_prompt(cls) -> str:
        """生成Skill描述"""
        if not cls._skills:
            return "（暂无配置的Skill）"

        # 按类别分组
        categories: Dict[str, List[dict]] = {}
        for skill in cls._skills.values():
            category = skill.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(skill)

        lines = []
        for category, skills in categories.items():
            lines.append(f"\n### {category}")
            for skill in skills:
                lines.append(f"- **{skill['name']}**: {skill['description']}")

        return "\n".join(lines)

    @classmethod
    def clear(cls):
        """清空注册表"""
        cls._skills.clear()
        logger.info("[SkillRegistry] 注册表已清空")


__all__ = ['ToolRegistry', 'SkillRegistry', 'Tool']
