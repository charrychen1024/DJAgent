"""
自定义Skill处理器 - 拦截并执行AI调用的Skill
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List

# 动态添加路径
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


class SkillHandler:
    """Skill处理器 - 解析并执行AI调用的Skill"""

    def __init__(self):
        # 导入所有Skill
        self.skills = {}
        try:
            from agents.skills import get_all_skills

            self.skills = get_all_skills()
            logger.info(f"[SkillHandler] 加载了 {len(self.skills)} 个Skill")
        except Exception as e:
            logger.error(f"[SkillHandler] 加载Skill失败: {e}")

    def detect_skill_calls(self, message: str) -> List[Dict[str, Any]]:
        """
        检测消息中的Skill调用

        Args:
            message: AI返回的消息

        Returns:
            Skill调用列表
        """
        calls = []

        # 检测 <function_calls> 格式
        if "<function_calls>" in message or "<invoke " in message:
            # 解析 invoke 调用
            pattern = r'<invoke name="([^"]+)">.*?(?:<parameter name="([^"]+)">(.*?)</parameter>)*.*?</invoke>'
            matches = re.findall(pattern, message, re.DOTALL)

            for match in matches:
                skill_name = match[0]
                params = {}

                # 提取参数
                param_pattern = r'<parameter name="([^"]+)">(.*?)</parameter>'
                param_matches = re.findall(param_pattern, match[2], re.DOTALL)
                for param_name, param_value in param_matches:
                    # 尝试解析JSON
                    try:
                        params[param_name] = json.loads(param_value)
                    except:
                        params[param_name] = param_value.strip()

                calls.append(
                    {"skill_name": skill_name, "params": params, "raw": match[0]}
                )

        return calls

    async def execute_skill(
        self, skill_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行Skill

        Args:
            skill_name: Skill名称
            params: 参数

        Returns:
            执行结果
        """
        if skill_name not in self.skills:
            return {
                "success": False,
                "error": f"Skill '{skill_name}' 未找到",
                "available_skills": list(self.skills.keys()),
            }

        skill = self.skills[skill_name]

        try:
            logger.info(f"[SkillHandler] 执行Skill: {skill_name}, 参数: {params}")
            result = await skill.execute(params, {})
            return result
        except Exception as e:
            logger.error(f"[SkillHandler] Skill执行失败: {skill_name}, {str(e)}")
            return {"success": False, "error": f"Skill执行失败: {str(e)}"}

    async def handle_skill_calls(self, message: str) -> str:
        """
        处理消息中的Skill调用，替换为真实结果

        Args:
            message: 原始消息

        Returns:
            处理后的消息
        """
        calls = self.detect_skill_calls(message)

        if not calls:
            return message

        logger.info(f"[SkillHandler] 检测到 {len(calls)} 个Skill调用")

        # 执行Skill并收集结果
        results = {}
        for call in calls:
            skill_name = call["skill_name"]
            params = call["params"]

            result = await self.execute_skill(skill_name, params)
            results[skill_name] = result

        # 替换消息中的function_calls为真实结果
        processed_message = self._replace_with_real_results(message, results)

        return processed_message

    def _replace_with_real_results(self, message: str, results: Dict[str, Dict]) -> str:
        """
        将消息中的function_calls替换为真实结果

        Args:
            message: 原始消息
            results: Skill执行结果

        Returns:
            处理后的消息
        """
        # 检查是否所有调用都成功
        all_success = all(r.get("success", False) for r in results.values())

        if not all_success:
            # 如果有失败，返回错误信息
            error_msg = "⚠️ 抱歉，执行以下Skill时出错：\n\n"
            for skill_name, result in results.items():
                if not result.get("success", False):
                    error_msg += (
                        f"- **{skill_name}**: {result.get('error', '未知错误')}\n"
                    )

            # 保留原始消息的上下文，但添加错误信息
            parts = message.split("---", 1)
            if len(parts) > 1:
                return parts[0] + error_msg + "---" + parts[1]
            return error_msg

        # 构建真实的回复内容
        real_responses = []

        for skill_name, result in results.items():
            if result.get("success"):
                # 根据不同Skill类型生成不同的回复
                if skill_name == "list_users":
                    users = result.get("users", [])
                    real_responses.append(self._format_users_list(users))

                elif skill_name == "receiver_recommender":
                    recommendation = result.get("recommendation", {})
                    real_responses.append(self._format_recommendation(recommendation))

                elif skill_name == "create_task" or skill_name == "task_creator":
                    real_responses.append(f"✅ {result.get('message', '任务创建成功')}")

                elif skill_name == "risk_analyzer":
                    analysis = result.get("analysis", {})
                    real_responses.append(self._format_analysis(analysis))

                else:
                    # 通用格式化
                    real_responses.append(f"✅ {skill_name} 执行成功")

        if real_responses:
            return "\n\n".join(real_responses)

        return message

    def _format_users_list(self, users: List[Dict]) -> str:
        """格式化用户列表"""
        if not users:
            return "没有可用的用户"

        # 按部门分组
        dept_groups = {}
        for user in users:
            dept = user.get("department", "未知")
            if dept not in dept_groups:
                dept_groups[dept] = []
            dept_groups[dept].append(user)

        msg = "📋 可用的一线操作人员\n\n"

        for dept, users_list in dept_groups.items():
            msg += f"### {dept}（{len(users_list)}人）\n\n"
            for user in users_list:
                msg += f"- **{user.get('username')}** (ID: {user.get('user_id')})\n"

        return msg

    def _format_recommendation(self, recommendation: Dict) -> str:
        """格式化推荐结果"""
        recommended_user = recommendation.get("recommended_user", {})
        reasons = recommendation.get("reasons", [])
        alternatives = recommendation.get("alternatives", [])

        msg = "🎯 推荐执行人\n\n"

        if recommended_user:
            msg += f"**首选**：{recommended_user.get('username')} ({recommended_user.get('department')})\n"

        if reasons:
            msg += "\n**推荐理由**：\n"
            for reason in reasons:
                msg += f"- {reason}\n"

        if alternatives:
            msg += "\n**备选**：\n"
            for alt in alternatives:
                msg += f"- {alt.get('username')}\{alt.get('department')}\n"

        return msg

    def _format_analysis(self, analysis: Dict) -> str:
        """格式化分析结果"""
        msg = "📊 风险分析结果\n\n"

        if "analysis" in analysis:
            msg += "**分析**：\n"
            msg += str(analysis["analysis"])

        if "key_findings" in analysis:
            msg += "\n**关键发现**：\n"
            for finding in analysis["key_findings"]:
                msg += f"- {finding}\n"

        return msg


__all__ = ["SkillHandler"]
