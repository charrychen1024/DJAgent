"""
Skill基类 - 所有Skill的父类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class Skill(ABC):
    """Skill基类"""
    
    # Skill名称
    name: str = ""
    
    # Skill描述
    description: str = ""
    
    # 使用的工具列表
    tools: List[str] = []
    
    # 角色描述
    role: str = ""
    
    # 职责列表
    responsibilities: List[str] = []
    
    def __init__(self):
        """初始化Skill"""
        logger.info(f"[Skill] 初始化: {self.name}")
    
    @abstractmethod
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行Skill
        
        Args:
            input_data: 输入数据
            context: 上下文信息
            
        Returns:
            执行结果
        """
        pass
    
    def get_system_prompt(self) -> str:
        """获取System Prompt"""
        prompt = f"""你是一个{self.role}。
        
你的职责：
"""
        for i, resp in enumerate(self.responsibilities, 1):
            prompt += f"{i}. {resp}\n"
        
        prompt += f"""
你可以使用的工具：{', '.join(self.tools)}

请根据用户需求，自主调用合适的工具完成任务。
"""
        return prompt
    
    def get_tools(self) -> List[str]:
        """获取工具列表"""
        return self.tools
    
    def validate_input(self, input_data: Dict, required_fields: List[str]) -> Dict:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            required_fields: 必需字段
            
        Returns:
            验证结果
        """
        missing = [f for f in required_fields if f not in input_data]
        if missing:
            return {
                "success": False,
                "error": f"缺少必需字段: {', '.join(missing)}"
            }
        return {"success": True}


class ChainSkill(Skill):
    """链式Skill - 组合多个子Skill"""
    
    def __init__(self):
        super().__init__()
        self.sub_skills: List[Skill] = []
    
    def add_skill(self, skill: Skill):
        """添加子Skill"""
        self.sub_skills.append(skill)
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """顺序执行子Skill"""
        results = []
        current_data = input_data
        
        for skill in self.sub_skills:
            result = await skill.execute(current_data, context)
            results.append({
                "skill": skill.name,
                "result": result
            })
            # 将结果传递给下一个Skill
            current_data = result
        
        return {
            "success": True,
            "chain_results": results
        }


__all__ = ['Skill', 'ChainSkill']
