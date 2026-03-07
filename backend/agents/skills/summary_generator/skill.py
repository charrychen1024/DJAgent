"""
总结生成Skill
根据核查结果和上传材料，生成反馈总结
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
from datetime import datetime
from agents.skills.skill_base import Skill

logger = logging.getLogger(__name__)


class SummaryGeneratorSkill(Skill):
    """总结生成Skill"""
    
    name = "summary_generator"
    description = "根据核查结果和上传材料，生成反馈总结"
    tools = [
        "get_task_detail",
        "parse_pdf",
        "parse_word",
        "update_task_status",
        "save_chat_message"
    ]
    role = "报告生成专家"
    responsibilities = [
        "汇总核查结果",
        "整理上传的材料",
        "生成反馈总结",
        "更新任务状态"
    ]
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行总结生成
        
        Args:
            input_data: 输入数据，包含:
                - task_id: 任务ID
                - user_feedback: 用户反馈内容（可选）
                - auto_complete: 是否自动完成（可选）
            context: 上下文信息
            
        Returns:
            总结结果
        """
        logger.info(f"[SummaryGeneratorSkill] 执行: {input_data}")
        
        task_id = input_data.get("task_id")
        
        if not task_id:
            return {
                "success": False,
                "error": "需要提供任务ID"
            }
        
        try:
            from agents.tools import get_task_detail, update_task_status
            
            # 获取任务详情
            task_result = get_task_detail(task_id)
            
            if "error" in task_result:
                return task_result
            
            task = task_result.get("task", {})
            feedback = task_result.get("feedback", {})
            
            # 提取关键信息
            risk_summary = task.get("risk_summary", "")
            uploaded_files = feedback.get("uploaded_files", [])
            chat_history = feedback.get("chat_history", [])
            
            # 用户反馈内容
            user_feedback = input_data.get("user_feedback", "")
            
            # 生成总结
            summary = self._generate_summary(
                task_id=task_id,
                risk_summary=risk_summary,
                uploaded_files=uploaded_files,
                chat_history=chat_history,
                user_feedback=user_feedback
            )
            
            # 如果需要自动完成
            if input_data.get("auto_complete", False):
                update_result = update_task_status(task_id, "反馈完成", summary)
                
                return {
                    "success": True,
                    "action": "task_completed",
                    "task_id": task_id,
                    "feedback_summary": summary,
                    "message": "任务已完成，反馈总结已生成"
                }
            
            return {
                "success": True,
                "task_id": task_id,
                "feedback_summary": summary,
                "uploaded_files_count": len(uploaded_files),
                "message": "反馈总结已生成，请确认是否完成"
            }
            
        except Exception as e:
            logger.error(f"[SummaryGeneratorSkill] 生成总结失败: {str(e)}")
            return {"error": f"生成总结失败: {str(e)}"}
    
    def _generate_summary(
        self,
        task_id: str,
        risk_summary: str,
        uploaded_files: List[Dict],
        chat_history: List[Dict],
        user_feedback: str
    ) -> str:
        """生成反馈总结"""
        
        summary_parts = []
        
        # 任务信息
        summary_parts.append(f"## 任务 {task_id} 反馈总结\n")
        summary_parts.append(f"**风险简述**：{risk_summary}\n")
        
        # 上传材料
        if uploaded_files:
            summary_parts.append(f"**上传材料**：共{len(uploaded_files)}份")
            for f in uploaded_files:
                summary_parts.append(f"- {f.get('filename', '未知文件')}")
            summary_parts.append("")
        
        # 用户反馈
        if user_feedback:
            summary_parts.append(f"**核查结果**：{user_feedback}\n")
        
        # 总结
        summary_parts.append("**总结**：")
        
        if uploaded_files and user_feedback:
            summary_parts.append("已上传证明材料，核查工作已完成。")
        elif uploaded_files:
            summary_parts.append("已上传证明材料，待核查确认。")
        elif user_feedback:
            summary_parts.append("已完成核查，待上传证明材料。")
        else:
            summary_parts.append("任务正在处理中。")
        
        return "\n".join(summary_parts)


__all__ = ['SummaryGeneratorSkill']
