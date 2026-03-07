"""
Skill层 - 业务能力封装
导出所有Skill
"""

from .skill_base import Skill, ChainSkill
from .skill_registry import (
    register_skill,
    get_skill,
    get_all_skills,
    get_all_skill_names,
    get_skill_descriptions,
    initialize_skills
)

# 导入所有Skill
from .risk_analyzer.skill import RiskAnalyzerSkill
from .task_creator.skill import TaskCreatorSkill
from .receiver_recommender.skill import ReceiverRecommenderSkill
from .核查_guider.skill import CheckGuiderSkill
from .summary_generator.skill import SummaryGeneratorSkill

# 导出
__all__ = [
    'Skill',
    'ChainSkill',
    'RiskAnalyzerSkill',
    'TaskCreatorSkill',
    'ReceiverRecommenderSkill',
    'CheckGuiderSkill',
    'SummaryGeneratorSkill',
    'register_skill',
    'get_skill',
    'get_all_skills',
    'get_all_skill_names',
    'get_skill_descriptions',
    'initialize_skills'
]
