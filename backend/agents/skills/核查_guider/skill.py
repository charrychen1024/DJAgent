"""
核查指导Skill
指导一线人员完成风险核查工作
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


class CheckGuiderSkill(Skill):
    """核查指导Skill"""
    
    name = "核查_guider"
    description = "指导一线人员完成风险核查工作"
    tools = [
        "get_task_detail",
        "parse_pdf",
        "parse_word",
        "list_uploaded_files"
    ]
    role = "核查指导专家"
    responsibilities = [
        "提供任务详细要求",
        "指导核查步骤",
        "说明需要准备的材料",
        "提醒注意事项"
    ]
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行核查指导
        
        Args:
            input_data: 输入数据，包含:
                - task_id: 任务ID
                - user_question: 用户问题（可选）
            context: 上下文信息
            
        Returns:
            指导内容
        """
        logger.info(f"[CheckGuiderSkill] 执行: {input_data}")
        
        task_id = input_data.get("task_id")
        
        if not task_id:
            return {
                "success": False,
                "error": "需要提供任务ID"
            }
        
        try:
            from agents.tools import get_task_detail, list_uploaded_files
            
            # 获取任务详情
            task_result = get_task_detail(task_id)
            
            if "error" in task_result:
                return task_result
            
            task = task_result.get("task", {})
            feedback = task_result.get("feedback", {})
            
            # 构建指导内容
            guidance = self._build_guidance(task, feedback, input_data)
            
            return {
                "success": True,
                "task_id": task_id,
                "guidance": guidance,
                "task_status": task.get("status", ""),
                "uploaded_files": feedback.get("uploaded_files", [])
            }
            
        except Exception as e:
            logger.error(f"[CheckGuiderSkill] 指导失败: {str(e)}")
            return {"error": f"获取指导失败: {str(e)}"}
    
    def _build_guidance(
        self, 
        task: Dict, 
        feedback: Dict,
        input_data: Dict
    ) -> Dict:
        """构建指导内容"""
        
        # 任务基本信息
        risk_summary = task.get("risk_summary", "风险核查")
        status = task.get("status", "")
        
        # 已上传文件
        uploaded_files = feedback.get("uploaded_files", [])
        
        # 构建指导
        guidance = {
            "task_intro": f"""📋 任务：{risk_summary}

状态：{status}

请按照以下步骤完成核查：""",
            
            "steps": [
                "1. 核实运单信息是否与风险描述一致",
                "2. 检查相关单据和凭证",
                "3. 如实记录核查结果",
                "4. 上传相关证明材料",
                "5. 提交核查反馈"
            ],
            
            "materials_needed": [
                "运单凭证",
                "签收记录（如有）",
                "照片或视频证据（如有）"
            ],
            
            "reminders": [
                "请确保上传的材料清晰可读",
                "如发现问题，请详细描述",
                "提交后可在任务详情查看反馈"
            ]
        }
        
        # 如果用户有具体问题
        user_question = input_data.get("user_question", "")
        if user_question:
            guidance["user_question"] = user_question
            # 根据问题类型添加针对性指导
            if "怎么" in user_question or "如何" in user_question:
                guidance["specific_help"] = "请按上述步骤进行核查，如有疑问可随时询问"
        
        return guidance


__all__ = ['CheckGuiderSkill']
