"""
Skill编排器 - 智能选择和组合Skill执行

功能：
1. 根据用户意图自动选择合适的Skill
2. 管理Skill执行顺序和依赖关系
3. 提供Skill组合能力（链式、并行）
4. 统一的Skill执行接口
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Skill执行模式"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"    # 并行执行
    CONDITIONAL = "conditional"  # 条件执行


@dataclass
class SkillExecution:
    """Skill执行配置"""
    skill_name: str
    input_mapping: Dict[str, str] = None  # 输入映射：{"param_name": "context_key"}
    output_key: str = None  # 输出存储到context的key
    condition: Callable[[Dict], bool] = None  # 执行条件


class SkillOrchestrator:
    """
    Skill编排器

    根据用户意图和上下文，自动选择和组合Skill执行。
    """

    def __init__(self):
        """初始化编排器"""
        self._skill_registry = {}
        self._intent_mappings = self._build_intent_mappings()
        logger.info("[SkillOrchestrator] 编排器初始化完成")

    def _build_intent_mappings(self) -> Dict[str, List[str]]:
        """
        构建意图到Skill的映射

        Returns:
            意图到Skill名称列表的映射
        """
        return {
            # 风险分析相关
            "分析风险": ["risk_analyzer"],
            "查看风险数据": ["risk_analyzer"],
            "风险排查": ["risk_analyzer"],
            "统计风险": ["risk_analyzer"],

            # 任务创建相关
            "创建任务": ["task_creator"],
            "下发任务": ["task_creator"],
            "分配任务": ["task_creator"],

            # 推荐执行人相关
            "推荐执行人": ["receiver_recommender"],
            "谁来做": ["receiver_recommender"],
            "分派给谁": ["receiver_recommender"],

            # 核查指导相关
            "如何核查": ["核查_guider"],
            "核查要点": ["核查_guider"],
            "核查步骤": ["核查_guider"],

            # 汇总生成相关
            "生成汇总": ["summary_generator"],
            "汇总": ["summary_generator"],
            "总结": ["summary_generator"],
        }

    def register_skill(self, name: str, skill_instance: Any):
        """注册Skill"""
        self._skill_registry[name] = skill_instance
        logger.info(f"[SkillOrchestrator] 注册Skill: {name}")

    def detect_intent(self, user_message: str) -> List[str]:
        """
        检测用户意图，返回需要的Skill列表

        Args:
            user_message: 用户消息

        Returns:
            需要的Skill名称列表
        """
        user_message_lower = user_message.lower()

        detected_skills = []
        for intent, skill_names in self._intent_mappings.items():
            if intent in user_message_lower:
                detected_skills.extend(skill_names)

        # 去重
        detected_skills = list(set(detected_skills))

        logger.info(
            f"[SkillOrchestrator] 意图检测: '{user_message}' -> {detected_skills}"
        )
        return detected_skills

    async def execute_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行单个Skill

        Args:
            skill_name: Skill名称
            input_data: 输入数据
            context: 上下文信息

        Returns:
            执行结果
        """
        if skill_name not in self._skill_registry:
            logger.warning(f"[SkillOrchestrator] Skill不存在: {skill_name}")
            return {
                "success": False,
                "error": f"Skill '{skill_name}' 不存在"
            }

        skill = self._skill_registry[skill_name]
        context = context or {}

        try:
            logger.info(f"[SkillOrchestrator] 执行Skill: {skill_name}")
            result = await skill.execute(input_data, context)
            return result
        except Exception as e:
            logger.error(f"[SkillOrchestrator] Skill执行失败: {skill_name}, {e}")
            return {
                "success": False,
                "error": f"Skill执行失败: {str(e)}"
            }

    async def execute_chain(
        self,
        skill_configs: List[SkillExecution],
        initial_input: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        链式执行多个Skill

        Args:
            skill_configs: Skill执行配置列表
            initial_input: 初始输入
            context: 上下文信息

        Returns:
            最终执行结果
        """
        context = context or {}
        current_input = initial_input
        results = []

        for config in skill_configs:
            # 检查执行条件
            if config.condition and not config.condition(context):
                logger.info(
                    f"[SkillOrchestrator] 跳过Skill (条件不满足): {config.skill_name}"
                )
                continue

            # 执行Skill
            result = await self.execute_skill(
                config.skill_name,
                current_input,
                context
            )
            results.append({
                "skill": config.skill_name,
                "result": result
            })

            # 处理输入映射
            if config.input_mapping and result.get("success"):
                for target_key, source_path in config.input_mapping.items():
                    # 支持嵌套路径，如 "result.data"
                    parts = source_path.split(".")
                    value = result
                    for part in parts:
                        value = value.get(part, {}) if isinstance(value, dict) else None
                        if value is None:
                            break
                    if value is not None:
                        current_input[target_key] = value

            # 存储输出到context
            if config.output_key and result.get("success"):
                context[config.output_key] = result

            # 如果执行失败，可以选择停止或继续
            if not result.get("success"):
                logger.warning(
                    f"[SkillOrchestrator] Skill执行失败: {config.skill_name}, 继续执行下一个"
                )

        return {
            "success": True,
            "chain_results": results,
            "final_context": context
        }

    async def execute_by_intent(
        self,
        user_message: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        根据用户意图自动执行Skill

        Args:
            user_message: 用户消息
            input_data: 输入数据
            context: 上下文信息

        Returns:
            执行结果
        """
        # 检测意图
        skill_names = self.detect_intent(user_message)

        if not skill_names:
            logger.info("[SkillOrchestrator] 未检测到需要执行的Skill")
            return {
                "success": False,
                "message": "未识别到需要执行的技能"
            }

        # 单一Skill直接执行
        if len(skill_names) == 1:
            return await self.execute_skill(skill_names[0], input_data, context)

        # 多个Skill链式执行
        skill_configs = [
            SkillExecution(
                skill_name=name,
                output_key=f"result_{name}"
            )
            for name in skill_names
        ]

        return await self.execute_chain(skill_configs, input_data, context)

    def get_available_skills(self) -> List[str]:
        """获取所有可用的Skill"""
        return list(self._skill_registry.keys())

    def get_skill_description(self, skill_name: str) -> Optional[str]:
        """获取Skill描述"""
        if skill_name in self._skill_registry:
            return self._skill_registry[skill_name].description
        return None

    def get_skills_for_prompt(self) -> str:
        """
        生成用于System Prompt的Skill描述

        Returns:
            格式化的Skill列表
        """
        lines = []
        for name, skill in self._skill_registry.items():
            lines.append(f"- **{name}**: {skill.description}")
        return "\n".join(lines) if lines else "（暂无配置的Skill）"


# 全局编排器实例
_orchestrator: Optional[SkillOrchestrator] = None


def get_orchestrator() -> SkillOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SkillOrchestrator()
        _load_skills()
    return _orchestrator


def _load_skills():
    """加载Skills到编排器"""
    global _orchestrator
    try:
        from .skill_registry import get_all_skills

        skills = get_all_skills()
        for name, skill in skills.items():
            _orchestrator.register_skill(name, skill)
        logger.info(f"[SkillOrchestrator] 加载了 {len(skills)} 个Skill")
    except Exception as e:
        logger.error(f"[SkillOrchestrator] 加载Skill失败: {e}")


def detect_intent(user_message: str) -> List[str]:
    """检测用户意图"""
    return get_orchestrator().detect_intent(user_message)


async def execute_skill(
    skill_name: str,
    input_data: Dict[str, Any],
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """执行Skill"""
    return await get_orchestrator().execute_skill(skill_name, input_data, context)


async def execute_by_intent(
    user_message: str,
    input_data: Dict[str, Any],
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """根据意图执行Skill"""
    return await get_orchestrator().execute_by_intent(user_message, input_data, context)


__all__ = [
    'SkillOrchestrator',
    'SkillExecution',
    'ExecutionMode',
    'get_orchestrator',
    'detect_intent',
    'execute_skill',
    'execute_by_intent'
]
