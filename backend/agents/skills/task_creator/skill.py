"""
任务创建Skill
根据风险分析结果创建核查任务，下发给执行人
"""

# 动态添加路径
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 动态添加路径
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from agents.skills.skill_base import Skill

logger = logging.getLogger(__name__)


class TaskCreatorSkill(Skill):
    """任务创建Skill"""
    
    name = "task_creator"
    description = "根据风险分析结果创建核查任务，下发给执行人"
    tools = [
        "list_users",
        "create_task",
        "update_task_status",
        "assign_task",
        "get_task"
    ]
    role = "任务管理助手"
    responsibilities = [
        "确认任务信息（风险描述、执行人）",
        "调用工具创建任务",
        "分配任务给执行人",
        "返回创建结果"
    ]
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行任务创建
        
        Args:
            input_data: 输入数据，包含:
                - risk_summary: 风险简述
                - assigned_to_id: 执行人ID（可选）
                - assigned_to_name: 执行人名称（可选）
                - creator_id: 创建人ID
                - creator_name: 创建人名称
                - risk_data_url: 风险数据路径（可选）
            context: 上下文信息
            
        Returns:
            创建结果
        """
        logger.info(f"[TaskCreatorSkill] 执行: {input_data}")
        
        # 验证必需字段
        required = ["creator_id", "creator_name"]
        validation = self.validate_input(input_data, required)
        if not validation.get("success"):
            return validation
        
        try:
            from agents.tools import create_task, assign_task, list_users
            
            # 提取任务信息
            risk_summary = input_data.get("risk_summary", "风险核查任务")
            creator_id = input_data.get("creator_id")
            creator_name = input_data.get("creator_name")
            assigned_to_id = input_data.get("assigned_to_id")
            assigned_to_name = input_data.get("assigned_to_name")
            risk_data_url = input_data.get("risk_data_url", "")
            feedback_deadline = input_data.get("feedback_deadline", "")
            task_type = input_data.get("task_type", "日度")

            logger.info(f"[TaskCreatorSkill] feedback_deadline={feedback_deadline}, task_type={task_type}")

            # 如果没有指定执行人，需要获取可选执行人列表
            if not assigned_to_id or not assigned_to_name:
                users_result = list_users(role="一线操作人员")
                if users_result.get("success"):
                    return {
                        "success": True,
                        "action": "need_receiver",
                        "message": "请指定执行人",
                        "available_users": users_result.get("users", [])
                    }
            
            # 创建任务
            task_info = {
                "creator_id": creator_id,
                "creator_name": creator_name,
                "assigned_to_id": assigned_to_id or "",
                "assigned_to_name": assigned_to_name or "",
                "risk_summary": risk_summary,
                "risk_data_url": risk_data_url,
                "feedback_deadline": feedback_deadline,
                "task_type": task_type
            }

            result = create_task(task_info)

            if "error" in result:
                return result

            task_id = result.get("task_id")

            # 如果指定了执行人，直接分配任务
            if assigned_to_id and assigned_to_name:
                assign_result = assign_task(
                    task_id=task_id,
                    assigned_to_id=assigned_to_id,
                    assigned_to_name=assigned_to_name,
                    status="已下发",
                    feedback_deadline=feedback_deadline
                )
                
                if "error" not in assign_result:
                    return {
                        "success": True,
                        "action": "task_created_and_assigned",
                        "task_id": task_id,
                        "message": f"任务 {task_id} 已创建并分配给 {assigned_to_name}"
                    }
            
            return {
                "success": True,
                "action": "task_created",
                "task_id": task_id,
                "message": f"任务 {task_id} 创建成功，请指定执行人"
            }
            
        except Exception as e:
            logger.error(f"[TaskCreatorSkill] 创建任务失败: {str(e)}")
            return {"error": f"创建任务失败: {str(e)}"}
    
    async def quick_create(
        self,
        creator_id: str,
        creator_name: str,
        assigned_to_id: str,
        assigned_to_name: str,
        risk_summary: str,
        risk_data_url: str = ""
    ) -> Dict:
        """
        快速创建并分配任务
        
        Args:
            creator_id: 创建人ID
            creator_name: 创建人名称
            assigned_to_id: 执行人ID
            assigned_to_name: 执行人名称
            risk_summary: 风险简述
            risk_data_url: 风险数据URL
            
        Returns:
            创建结果
        """
        input_data = {
            "creator_id": creator_id,
            "creator_name": creator_name,
            "assigned_to_id": assigned_to_id,
            "assigned_to_name": assigned_to_name,
            "risk_summary": risk_summary,
            "risk_data_url": risk_data_url
        }
        
        return await self.execute(input_data, {})


__all__ = ['TaskCreatorSkill']
