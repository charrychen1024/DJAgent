"""
推荐执行人Skill
根据风险特征和执行人情况，推荐最合适的核查人员
"""

# 动态添加路径
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
import json
import logging
from typing import Dict, Any, List, Optional
from agents.skills.skill_base import Skill

logger = logging.getLogger(__name__)


class ReceiverRecommenderSkill(Skill):
    """推荐执行人Skill"""
    
    name = "receiver_recommender"
    description = "根据风险特征和执行人情况，推荐最合适的核查人员"
    tools = [
        "list_users",
        "get_task_detail",
        "get_task"
    ]
    role = "人员推荐专家"
    responsibilities = [
        "分析风险特征（地点、类型、紧急程度等）",
        "评估可选执行人",
        "推荐最合适的执行人",
        "说明推荐理由"
    ]
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行推荐
        
        Args:
            input_data: 输入数据，包含:
                - task_id: 任务ID（可选）
                - risk_data: 风险数据（可选）
                - location: 地点信息（可选）
            context: 上下文信息
            
        Returns:
            推荐结果
        """
        logger.info(f"[ReceiverRecommenderSkill] 执行推荐: {input_data}")
        
        try:
            from agents.tools import list_users, get_task_detail, get_task
            
            # 获取可选执行人
            users_result = list_users(role="一线操作人员")
            
            if "error" in users_result:
                return users_result
            
            users = users_result.get("users", [])
            
            if not users:
                return {
                    "success": False,
                    "error": "没有可用的执行人员"
                }
            
            # 获取任务/风险信息
            task_id = input_data.get("task_id")
            risk_data = input_data.get("risk_data", {})
            location = input_data.get("location", "")
            
            task_info = {}
            if task_id:
                task_result = get_task_detail(task_id)
                if task_result.get("success"):
                    task_info = task_result.get("task", {})
                    # 尝试从任务中提取地点
                    if not location:
                        location = task_info.get("收货地", "") or task_info.get("发货地", "")
            
            # 推荐执行人
            recommendation = self._recommend(users, task_info, risk_data, location)
            
            return {
                "success": True,
                "recommendation": recommendation,
                "available_users": users
            }
            
        except Exception as e:
            logger.error(f"[ReceiverRecommenderSkill] 推荐失败: {str(e)}")
            return {"error": f"推荐失败: {str(e)}"}
    
    def _recommend(
        self, 
        users: List[Dict], 
        task_info: Dict, 
        risk_data: Dict,
        location: str
    ) -> Dict:
        """
        执行推荐逻辑
        
        Args:
            users: 可用用户列表
            task_info: 任务信息
            risk_data: 风险数据
            location: 地点
            
        Returns:
            推荐结果
        """
        # 简单的推荐逻辑
        # 实际可以更复杂，比如考虑历史任务、评分等
        
        if not users:
            return {
                "recommended": None,
                "reason": "没有可用执行人"
            }
        
        # 默认推荐第一个用户
        # 实际可以加入更多逻辑：
        # - 根据地点匹配
        # - 根据历史任务完成情况
        # - 根据负载均衡
        
        recommended_user = users[0]
        
        # 构建推荐理由
        reasons = []
        reasons.append("系统中可用的执行人员")
        
        if location:
            reasons.append(f"任务地点：{location}")
        
        # 风险等级
        risk_level = task_info.get("风险等级", "")
        if risk_level:
            reasons.append(f"风险等级：{risk_level}")
        
        return {
            "recommended_user": {
                "user_id": recommended_user.get("user_id"),
                "username": recommended_user.get("username"),
                "department": recommended_user.get("department", "")
            },
            "reasons": reasons,
            "alternatives": [
                {"user_id": u.get("user_id"), "username": u.get("username")}
                for u in users[1:3]  # 提供1-2个备选
            ]
        }


__all__ = ['ReceiverRecommenderSkill']
