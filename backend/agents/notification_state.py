"""
通知状态管理模块

用于追踪和管理任务的超时提醒通知状态，防止重复发送相同的提醒。
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationStateManager:
    """
    管理任务的通知状态，记录：
    - 即将超时提醒是否已发送
    - 已超时提醒是否已发送
    - Manager催促次数
    - 提醒历史记录
    """

    def __init__(self, feedback_data_dir: str = "data/feedback"):
        """
        初始化通知状态管理器

        Args:
            feedback_data_dir: feedback数据目录路径
        """
        self.feedback_data_dir = feedback_data_dir
        logger.info(f"[通知状态管理] 初始化，feedback目录: {feedback_data_dir}")

    def _get_feedback_path(self, task_id: str) -> str:
        """获取任务反馈文件路径"""
        return os.path.join(self.feedback_data_dir, f"{task_id}.json")

    def _load_feedback(self, task_id: str) -> Dict[str, Any]:
        """
        加载任务的反馈数据

        Args:
            task_id: 任务ID

        Returns:
            反馈数据字典，如果文件不存在则返回空字典
        """
        feedback_path = self._get_feedback_path(task_id)

        if not os.path.exists(feedback_path):
            return {}

        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"[通知状态管理] 读取反馈文件失败 {task_id}: {str(e)}")
            return {}

    def _save_feedback(self, task_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        保存任务的反馈数据

        Args:
            task_id: 任务ID
            feedback_data: 反馈数据字典

        Returns:
            是否保存成功
        """
        feedback_path = self._get_feedback_path(task_id)

        try:
            # 确保目录存在
            Path(feedback_path).parent.mkdir(parents=True, exist_ok=True)

            with open(feedback_path, "w", encoding="utf-8") as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)

            return True
        except IOError as e:
            logger.error(f"[通知状态管理] 保存反馈文件失败 {task_id}: {str(e)}")
            return False

    def _ensure_reminder_state(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保反馈数据中存在reminder_state字段

        Args:
            feedback_data: 反馈数据字典

        Returns:
            更新后的反馈数据
        """
        if "reminder_state" not in feedback_data:
            feedback_data["reminder_state"] = {
                "about_to_timeout_sent": False,
                "about_to_timeout_sent_time": None,
                "already_timeout_sent": False,
                "already_timeout_sent_time": None,
                "manager_urged_count": 0,
                "remind_history": []
            }

        return feedback_data

    def has_about_to_timeout_sent(self, task_id: str) -> bool:
        """
        检查"即将超时"提醒是否已发送

        Args:
            task_id: 任务ID

        Returns:
            True表示已发送，False表示未发送
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        return feedback_data["reminder_state"].get("about_to_timeout_sent", False)

    def mark_about_to_timeout_sent(self, task_id: str) -> bool:
        """
        标记"即将超时"提醒已发送

        Args:
            task_id: 任务ID

        Returns:
            是否标记成功
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        feedback_data["reminder_state"]["about_to_timeout_sent"] = True
        feedback_data["reminder_state"]["about_to_timeout_sent_time"] = datetime.now().isoformat()

        # 记录到历史
        feedback_data["reminder_state"]["remind_history"].append({
            "type": "about_to_timeout",
            "sent_time": datetime.now().isoformat()
        })

        success = self._save_feedback(task_id, feedback_data)
        if success:
            logger.info(f"[通知状态管理] 任务{task_id}的'即将超时'提醒已标记为已发送")

        return success

    def has_already_timeout_sent(self, task_id: str) -> bool:
        """
        检查"已超时"提醒是否已发送

        Args:
            task_id: 任务ID

        Returns:
            True表示已发送，False表示未发送
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        return feedback_data["reminder_state"].get("already_timeout_sent", False)

    def mark_already_timeout_sent(self, task_id: str) -> bool:
        """
        标记"已超时"提醒已发送

        Args:
            task_id: 任务ID

        Returns:
            是否标记成功
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        feedback_data["reminder_state"]["already_timeout_sent"] = True
        feedback_data["reminder_state"]["already_timeout_sent_time"] = datetime.now().isoformat()

        # 记录到历史
        feedback_data["reminder_state"]["remind_history"].append({
            "type": "already_timeout",
            "sent_time": datetime.now().isoformat()
        })

        success = self._save_feedback(task_id, feedback_data)
        if success:
            logger.info(f"[通知状态管理] 任务{task_id}的'已超时'提醒已标记为已发送")

        return success

    def get_manager_urged_count(self, task_id: str) -> int:
        """
        获取Manager催促次数

        Args:
            task_id: 任务ID

        Returns:
            催促次数
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        return feedback_data["reminder_state"].get("manager_urged_count", 0)

    def increment_manager_urged_count(self, task_id: str) -> bool:
        """
        增加Manager催促次数

        Args:
            task_id: 任务ID

        Returns:
            是否增加成功
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        current_count = feedback_data["reminder_state"].get("manager_urged_count", 0)
        feedback_data["reminder_state"]["manager_urged_count"] = current_count + 1

        # 记录到历史
        feedback_data["reminder_state"]["remind_history"].append({
            "type": "manager_urged",
            "sent_time": datetime.now().isoformat(),
            "urged_count": current_count + 1
        })

        success = self._save_feedback(task_id, feedback_data)
        if success:
            logger.info(f"[通知状态管理] 任务{task_id}的Manager催促次数已增加: {current_count + 1}")

        return success

    def get_reminder_history(self, task_id: str) -> list:
        """
        获取提醒历史记录

        Args:
            task_id: 任务ID

        Returns:
            提醒历史列表
        """
        feedback_data = self._load_feedback(task_id)
        feedback_data = self._ensure_reminder_state(feedback_data)

        return feedback_data["reminder_state"].get("remind_history", [])

    def get_reminder_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取完整的提醒状态

        Args:
            task_id: 任务ID

        Returns:
            提醒状态字典，如果任务不存在则返回None
        """
        feedback_data = self._load_feedback(task_id)

        if not feedback_data:
            return None

        feedback_data = self._ensure_reminder_state(feedback_data)
        return feedback_data["reminder_state"]

    def reset_reminder_state(self, task_id: str) -> bool:
        """
        重置任务的提醒状态（仅用于测试或重新开始）

        Args:
            task_id: 任务ID

        Returns:
            是否重置成功
        """
        feedback_data = self._load_feedback(task_id)

        feedback_data["reminder_state"] = {
            "about_to_timeout_sent": False,
            "about_to_timeout_sent_time": None,
            "already_timeout_sent": False,
            "already_timeout_sent_time": None,
            "manager_urged_count": 0,
            "remind_history": []
        }

        success = self._save_feedback(task_id, feedback_data)
        if success:
            logger.info(f"[通知状态管理] 任务{task_id}的提醒状态已重置")

        return success


# 全局实例
notification_state_manager = NotificationStateManager()
