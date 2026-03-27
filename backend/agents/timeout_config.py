"""
超时提醒系统配置管理模块

用于管理任务超时检测和提醒的配置参数，包括：
- 检测周期（分钟）
- 预警时间（小时）
- 任务类型的默认超时时间
- 提醒功能的启用/禁用状态
"""

from dataclasses import dataclass
from typing import Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaskTypeConfig:
    """单个任务类型的超时配置"""
    task_type: str  # "日度" 或 "月度"
    default_deadline_hours: int  # 默认超时时间（小时）


class TimeoutReminderConfig:
    """超时提醒系统配置类"""

    def __init__(self):
        # 检测周期（分钟）- 每隔多少分钟检测一次超时任务
        self.check_interval_minutes = 5

        # 预警时间（小时）- 在截止时间前多少小时发送即将超时提醒
        self.warn_before_hours = 1

        # 是否启用超时提醒功能
        self.enabled = True

        # 任务类型配置
        self.task_type_configs: Dict[str, TaskTypeConfig] = {
            "日度": TaskTypeConfig(
                task_type="日度",
                default_deadline_hours=24
            ),
            "月度": TaskTypeConfig(
                task_type="月度",
                default_deadline_hours=72
            )
        }

        # 最大重试次数（当StaffAgent不可用时）
        self.max_retries = 3

        # 重试间隔（秒）- 使用指数退避
        self.retry_delay_seconds = 2

        # 并发限制 - 同时发送多少个提醒
        self.max_concurrent_notifications = 3

        # 要监测的任务状态
        self.monitored_statuses = ["反馈中", "已下发"]

        logger.info("[超时提醒配置] 初始化完成")
        logger.info(f"  检测周期: {self.check_interval_minutes} 分钟")
        logger.info(f"  预警时间: {self.warn_before_hours} 小时")
        logger.info(f"  监测状态: {', '.join(self.monitored_statuses)}")

    def get_default_deadline(self, task_type: str) -> int:
        """
        获取指定任务类型的默认超时时间（小时）

        Args:
            task_type: 任务类型（"日度" 或 "月度"）

        Returns:
            超时时间（小时）
        """
        config = self.task_type_configs.get(task_type)
        if config:
            return config.default_deadline_hours

        # 如果类型未定义，使用日度默认值
        logger.warning(f"[超时提醒配置] 未定义任务类型 '{task_type}'，使用日度默认值（24小时）")
        return 24

    def set_check_interval(self, minutes: int):
        """
        设置检测周期

        Args:
            minutes: 周期（分钟），最少1分钟
        """
        if minutes < 1:
            logger.warning(f"[超时提醒配置] 检测周期不能少于1分钟，使用默认值")
            return

        self.check_interval_minutes = minutes
        logger.info(f"[超时提醒配置] 检测周期已更新: {minutes} 分钟")

    def set_warn_before_hours(self, hours: int):
        """
        设置预警时间

        Args:
            hours: 提前多少小时发送预警
        """
        if hours < 0:
            logger.warning(f"[超时提醒配置] 预警时间不能为负，使用默认值")
            return

        self.warn_before_hours = hours
        logger.info(f"[超时提醒配置] 预警时间已更新: {hours} 小时")

    def set_enabled(self, enabled: bool):
        """
        启用或禁用超时提醒功能

        Args:
            enabled: True启用，False禁用
        """
        self.enabled = enabled
        status = "已启用" if enabled else "已禁用"
        logger.info(f"[超时提醒配置] 超时提醒功能{status}")

    def to_dict(self) -> dict:
        """
        将配置转换为字典格式（用于API返回）

        Returns:
            配置字典
        """
        return {
            "enabled": self.enabled,
            "check_interval_minutes": self.check_interval_minutes,
            "warn_before_hours": self.warn_before_hours,
            "max_retries": self.max_retries,
            "max_concurrent_notifications": self.max_concurrent_notifications,
            "monitored_statuses": self.monitored_statuses,
            "task_types": {
                task_type: config.default_deadline_hours
                for task_type, config in self.task_type_configs.items()
            }
        }


# 全局配置实例
timeout_config = TimeoutReminderConfig()
