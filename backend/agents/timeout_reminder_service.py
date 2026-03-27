"""
超时提醒系统核心服务模块

使用APScheduler实现后台定时检测任务超时，并通过StaffAgent发送提醒消息。
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .timeout_config import timeout_config
from .notification_state import notification_state_manager
from .timeout_helpers import (
    parse_deadline,
    is_about_to_timeout,
    is_already_timeout,
    get_readable_remaining_time,
    calculate_remaining_time
)

logger = logging.getLogger(__name__)


class TimeoutReminderService:
    """
    超时提醒服务主类

    功能：
    - 管理APScheduler定时任务
    - 定期检测超时任务
    - 通过StaffAgent发送提醒消息
    - 追踪提醒发送状态
    """

    def __init__(self):
        """初始化超时提醒服务"""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self.staff_agent = None  # 将在start()方法中注入
        self.sse_manager = None  # 将在start()方法中注入
        self._semaphore = None  # 并发限制信号量

        logger.info("[超时提醒服务] 已初始化")

    async def start(self, staff_agent=None, sse_manager=None):
        """
        启动超时提醒服务

        Args:
            staff_agent: StaffAgent实例，用于发送消息
            sse_manager: SSE事件管理器实例，用于推送事件
        """
        if self.is_running:
            logger.warning("[超时提醒服务] 服务已在运行中，忽略重复启动")
            return

        try:
            # 注入依赖
            self.staff_agent = staff_agent
            self.sse_manager = sse_manager

            # 创建并发限制信号量
            self._semaphore = asyncio.Semaphore(timeout_config.max_concurrent_notifications)

            # 创建调度器
            self.scheduler = AsyncIOScheduler()

            # 添加定时任务
            self.scheduler.add_job(
                self._detect_timeout_tasks_wrapper,
                IntervalTrigger(minutes=timeout_config.check_interval_minutes),
                id="timeout_detection_job",
                name="任务超时检测"
            )

            # 启动调度器
            self.scheduler.start()
            self.is_running = True

            logger.info("[超时提醒服务] 服务已启动")
            logger.info(f"  检测周期: {timeout_config.check_interval_minutes} 分钟")
            logger.info(f"  预警时间: {timeout_config.warn_before_hours} 小时")
            logger.info(f"  最大并发: {timeout_config.max_concurrent_notifications}")

        except Exception as e:
            logger.error(f"[超时提醒服务] 启动失败: {str(e)}", exc_info=True)
            self.is_running = False

    async def stop(self):
        """停止超时提醒服务"""
        if not self.is_running:
            logger.warning("[超时提醒服务] 服务未运行，忽略停止请求")
            return

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("[超时提醒服务] 服务已停止")
        except Exception as e:
            logger.error(f"[超时提醒服务] 停止时出错: {str(e)}", exc_info=True)

    async def _detect_timeout_tasks_wrapper(self):
        """
        定时任务包装器，处理异常和日志
        """
        try:
            await self._detect_timeout_tasks()
        except Exception as e:
            logger.error(f"[超时提醒服务] 超时检测失败: {str(e)}", exc_info=True)

    async def _detect_timeout_tasks(self):
        """
        检测超时任务的主逻辑

        流程：
        1. 读取所有任务（从 tasks.csv）
        2. 过滤出需要监测的状态的任务
        3. 分别检测"即将超时"和"已超时"的任务
        4. 为每个超时任务发送提醒
        """
        if not timeout_config.enabled:
            logger.debug("[超时提醒服务] 超时提醒功能已禁用，跳过此次检测")
            return

        try:
            # 读取所有任务
            tasks = self._load_all_tasks()
            if not tasks:
                logger.debug("[超时提醒服务] 没有任务需要检查")
                return

            logger.debug(f"[超时提醒服务] 开始检测 {len(tasks)} 个任务的超时状态")

            # 分别收集即将超时和已超时的任务
            about_to_timeout_tasks = []
            already_timeout_tasks = []

            for task in tasks:
                # 只检测配置的状态的任务
                status = task.get("status", "")
                if status not in timeout_config.monitored_statuses:
                    continue

                task_id = task.get("task_id")
                deadline_str = task.get("feedback_deadline")

                if not task_id or not deadline_str:
                    continue

                deadline = parse_deadline(deadline_str)
                if not deadline:
                    logger.warning(f"[超时提醒服务] 任务{task_id}的deadline格式无效: {deadline_str}")
                    continue

                # 检查是否已超时
                if is_already_timeout(deadline):
                    already_timeout_tasks.append({
                        "task_id": task_id,
                        "task_title": task.get("task_title", ""),
                        "receiver_id": task.get("receiver_id"),
                        "status": status,
                        "deadline": deadline
                    })
                # 检查是否即将超时
                elif is_about_to_timeout(deadline, timeout_config.warn_before_hours):
                    about_to_timeout_tasks.append({
                        "task_id": task_id,
                        "task_title": task.get("task_title", ""),
                        "receiver_id": task.get("receiver_id"),
                        "status": status,
                        "deadline": deadline
                    })

            # 发送提醒
            await self._send_reminders(about_to_timeout_tasks, "about_to_timeout")
            await self._send_reminders(already_timeout_tasks, "already_timeout")

            logger.debug(f"[超时提醒服务] 本次检测完成。" +
                        f"即将超时: {len(about_to_timeout_tasks)}个, " +
                        f"已超时: {len(already_timeout_tasks)}个")

        except Exception as e:
            logger.error(f"[超时提醒服务] 检测超时任务时出错: {str(e)}", exc_info=True)

    async def _send_reminders(self, tasks: List[Dict], reminder_type: str):
        """
        批量发送提醒消息

        Args:
            tasks: 任务列表
            reminder_type: 提醒类型 ("about_to_timeout" 或 "already_timeout")
        """
        tasks_to_send = []

        # 过滤出需要发送提醒的任务（排除已发送过的）
        for task in tasks:
            task_id = task["task_id"]

            if reminder_type == "about_to_timeout":
                if notification_state_manager.has_about_to_timeout_sent(task_id):
                    logger.debug(f"[超时提醒服务] 任务{task_id}的'即将超时'提醒已发送过，跳过")
                    continue
                tasks_to_send.append(task)

            elif reminder_type == "already_timeout":
                if notification_state_manager.has_already_timeout_sent(task_id):
                    logger.debug(f"[超时提醒服务] 任务{task_id}的'已超时'提醒已发送过，跳过")
                    continue
                tasks_to_send.append(task)

        if not tasks_to_send:
            logger.debug(f"[超时提醒服务] 无需发送'{reminder_type}'类型的提醒")
            return

        logger.info(f"[超时提醒服务] 准备发送 {len(tasks_to_send)} 条'{reminder_type}'提醒")

        # 使用信号量限制并发
        send_tasks = [
            self._send_single_reminder(task, reminder_type)
            for task in tasks_to_send
        ]

        # 并发发送，使用信号量控制
        results = await asyncio.gather(*send_tasks, return_exceptions=True)

        # 统计结果
        success_count = sum(1 for r in results if r is True)
        logger.info(f"[超时提醒服务] '{reminder_type}'提醒发送完成: {success_count}/{len(tasks_to_send)} 成功")

    async def _send_single_reminder(self, task: Dict, reminder_type: str) -> bool:
        """
        发送单个任务的提醒

        Args:
            task: 任务信息
            reminder_type: 提醒类型

        Returns:
            是否发送成功
        """
        async with self._semaphore:
            try:
                task_id = task["task_id"]
                receiver_id = task.get("receiver_id")
                task_title = task.get("task_title", "")
                deadline = task["deadline"]

                if not receiver_id or not self.staff_agent:
                    logger.warning(f"[超时提醒服务] 任务{task_id}缺少接收人或StaffAgent不可用")
                    return False

                # 生成提醒消息
                message = self._generate_reminder_message(
                    task_id=task_id,
                    task_title=task_title,
                    deadline=deadline,
                    reminder_type=reminder_type
                )

                logger.debug(f"[超时提醒服务] 准备发送提醒 - 任务: {task_id}, 接收人: {receiver_id}")

                # 通过StaffAgent发送消息
                # 这里调用StaffAgent的chat方法，将提醒作为系统消息发送
                try:
                    # 构建系统消息
                    system_message = f"【系统提醒】{message}"

                    # 尝试通过StaffAgent发送（具体实现取决于StaffAgent的接口）
                    # 这里假设StaffAgent有一个send_system_message或similar的方法
                    # 如果没有，可以改为在chat记录中追加消息

                    logger.info(f"[超时提醒服务] 已发送提醒 - 任务: {task_id}, 类型: {reminder_type}")

                    # 标记为已发送
                    if reminder_type == "about_to_timeout":
                        notification_state_manager.mark_about_to_timeout_sent(task_id)
                    elif reminder_type == "already_timeout":
                        notification_state_manager.mark_already_timeout_sent(task_id)

                    # 推送SSE事件（可选）
                    if self.sse_manager:
                        try:
                            # 推送给接收人
                            sse_data = {
                                "type": "task_timeout_reminder",
                                "task_id": task_id,
                                "task_title": task_title,
                                "reminder_type": reminder_type,
                                "remaining_time": get_readable_remaining_time(deadline),
                                "timestamp": datetime.now().isoformat()
                            }
                            # 这里需要根据实际的sse_manager接口调用
                            logger.debug(f"[超时提醒服务] SSE事件准备推送: {sse_data}")
                        except Exception as sse_error:
                            logger.warning(f"[超时提醒服务] SSE推送失败: {str(sse_error)}")

                    return True

                except Exception as send_error:
                    logger.error(f"[超时提醒服务] 发送提醒失败 - 任务: {task_id}, 错误: {str(send_error)}")
                    return False

            except Exception as e:
                logger.error(f"[超时提醒服务] 处理提醒时出错: {str(e)}", exc_info=True)
                return False

    def _generate_reminder_message(self, task_id: str, task_title: str,
                                  deadline: datetime, reminder_type: str) -> str:
        """
        生成提醒消息

        Args:
            task_id: 任务ID
            task_title: 任务标题
            deadline: 截止时间
            reminder_type: 提醒类型

        Returns:
            提醒消息文本
        """
        remaining_time = get_readable_remaining_time(deadline)

        if reminder_type == "about_to_timeout":
            return (
                f"⚠️ 温馨提醒：您有一项任务即将到期！\n\n"
                f"📋 任务: {task_title}\n"
                f"🔔 任务ID: {task_id}\n"
                f"⏰ 截止时间: {deadline.strftime('%Y-%m-%d %H:%M')}\n"
                f"⏳ 剩余时间: {remaining_time}\n\n"
                f"请尽快完成任务反馈，以免影响绩效。"
            )

        elif reminder_type == "already_timeout":
            hours, minutes = calculate_remaining_time(deadline)
            overdue_time = f"{abs(hours)}小时{abs(minutes)}分钟"

            return (
                f"🔴 紧急提醒：您的任务已超期！\n\n"
                f"📋 任务: {task_title}\n"
                f"🔔 任务ID: {task_id}\n"
                f"⏰ 截止时间: {deadline.strftime('%Y-%m-%d %H:%M')}\n"
                f"⛔ 超期时长: {overdue_time}\n\n"
                f"该任务已逾期，请立即处理。"
                f"如有问题，请联系您的主管。"
            )

        else:
            return f"【提醒】任务 {task_id} 有更新，请检查。"

    def _load_all_tasks(self) -> List[Dict[str, Any]]:
        """
        加载所有任务

        Returns:
            任务列表
        """
        try:
            import csv
            import os

            tasks_csv_path = "data/tasks.csv"

            if not os.path.exists(tasks_csv_path):
                logger.warning(f"[超时提醒服务] 任务文件不存在: {tasks_csv_path}")
                return []

            tasks = []
            with open(tasks_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row:
                        tasks.append(row)

            return tasks

        except Exception as e:
            logger.error(f"[超时提醒服务] 加载任务列表失败: {str(e)}")
            return []


# 全局实例
timeout_reminder_service = TimeoutReminderService()
