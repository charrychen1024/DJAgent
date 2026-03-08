"""
Skill注册中心 - 管理所有可用Skill
支持动态发现和加载Skill
"""

import logging
import sys
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any

# 确保 backend 路径在 sys.path 中
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from agents.skills.skill_base import Skill

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


def load_skill_from_file(file_path: Path):
    """从文件加载Skill"""
    try:
        # 模块名称
        module_name = f"agents.skills.{file_path.parent.name}.skill"
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找Skill子类
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Skill) and obj != Skill:
                    # 实例化并注册
                    try:
                        skill_instance = obj()
                        register_skill(skill_instance)
                        logger.info(f"[SkillRegistry] 成功加载并注册Skill: {skill_instance.name} 来自 {file_path}")
                        return True
                    except Exception as e:
                        logger.error(f"[SkillRegistry] 实例化Skill失败 {name}: {e}")
    except Exception as e:
        logger.error(f"[SkillRegistry] 加载Skill文件失败 {file_path}: {e}")
    return False


def initialize_skills():
    """初始化所有Skill - 动态扫描目录"""
    logger.info("[SkillRegistry] 开始初始化Skills...")
    
    # 获取skills目录
    skills_dir = Path(__file__).parent
    
    # 扫描子目录
    count = 0
    for item in skills_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            # 检查是否有 skill.py
            skill_file = item / "skill.py"
            if skill_file.exists():
                if load_skill_from_file(skill_file):
                    count += 1
            else:
                # 尝试直接加载 item (如果是 .py 文件)
                pass
                
    logger.info(f"[SkillRegistry] 初始化完成，共加载 {count} 个Skill")


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
