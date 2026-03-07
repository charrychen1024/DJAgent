"""
Skill注册中心 - 管理所有可用Skill
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Skill注册表
_skill_registry: Dict[str, Any] = {}


def register_skill(skill_instance: Any):
    """注册Skill实例"""
    name = skill_instance.name
    _skill_registry[name] = skill_instance
    logger.info(f"[SkillRegistry] 注册Skill: {name}")


def get_skill(name: str) -> Optional[Any]:
    """获取Skill实例"""
    return _skill_registry.get(name)


def get_all_skills() -> Dict[str, Any]:
    """获取所有注册的Skill"""
    return _skill_registry.copy()


def get_all_skill_names() -> List[str]:
    """获取所有Skill名称"""
    return list(_skill_registry.keys())


def get_skill_descriptions() -> Dict[str, str]:
    """获取所有Skill描述"""
    return {name: skill.description for name, skill in _skill_registry.items()}


def initialize_skills():
    """初始化所有Skill"""
    # 延迟导入，避免循环依赖
    import sys
    from pathlib import Path
    
    # 添加backend到路径
    backend_path = Path(__file__).parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    try:
        from agents.skills.risk_analyzer.skill import RiskAnalyzerSkill
        from agents.skills.task_creator.skill import TaskCreatorSkill
        from agents.skills.receiver_recommender.skill import ReceiverRecommenderSkill
        from agents.skills.核查_guider.skill import CheckGuiderSkill
        from agents.skills.summary_generator.skill import SummaryGeneratorSkill
        
        # 注册所有Skill
        register_skill(RiskAnalyzerSkill())
        register_skill(TaskCreatorSkill())
        register_skill(ReceiverRecommenderSkill())
        register_skill(CheckGuiderSkill())
        register_skill(SummaryGeneratorSkill())
        
        logger.info(f"[SkillRegistry] 已注册 {len(_skill_registry)} 个Skill")
    except ImportError as e:
        logger.warning(f"[SkillRegistry] 部分Skill导入失败: {e}")


# 初始化时自动注册
initialize_skills()


__all__ = [
    'register_skill',
    'get_skill',
    'get_all_skills',
    'get_all_skill_names',
    'get_skill_descriptions',
    'initialize_skills'
]
