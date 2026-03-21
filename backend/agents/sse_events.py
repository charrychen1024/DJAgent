"""
SSE 事件推送模块 - 提供统一的实时事件推送功能
"""

import asyncio
import json
import logging
from typing import Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class SSEEventManager:
    """SSE 事件管理器，用于推送实时通知"""

    def __init__(self):
        self._clients: Dict[str, list] = defaultdict(list)
        logger.info("[SSE] 事件管理器初始化")

    def subscribe(self, user_id: str, queue: asyncio.Queue):
        """订阅用户的事件流"""
        self._clients[user_id].append(queue)
        logger.info(f"[SSE] 用户 {user_id} 订阅成功，当前订阅数: {len(self._clients[user_id])}")

    def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        """取消订阅"""
        if queue in self._clients[user_id]:
            self._clients[user_id].remove(queue)
            logger.info(f"[SSE] 用户 {user_id} 取消订阅")

    async def publish(self, user_id: str, event_type: str, data: dict):
        """向指定用户推送事件"""
        if user_id not in self._clients or not self._clients[user_id]:
            logger.info(f"[SSE] 用户 {user_id} 无订阅者，跳过推送")
            return

        message = json.dumps({"type": event_type, **data})
        for queue in self._clients[user_id]:
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"[SSE] 推送失败: {e}")

        logger.info(f"[SSE] 向用户 {user_id} 推送事件 {event_type}")

    async def publish_to_manager(self, manager_id: str, event_type: str, data: dict):
        """向 Manager 推送事件"""
        await self.publish(manager_id, event_type, data)

    async def publish_to_staff(self, staff_id: str, event_type: str, data: dict):
        """向 Staff 推送事件"""
        await self.publish(staff_id, event_type, data)


# 全局 SSE 事件管理器
sse_manager = SSEEventManager()


# ============ 便捷函数 ============

async def notify_task_created(creator_id: str, task_id: str, task_info: dict):
    """
    任务创建成功后推送通知

    Args:
        creator_id: 创建者 employee_id (如 EMP_001)
        task_id: 任务ID
        task_info: 任务信息
    """
    # creator_id 和 assigned_to_id 都是 employee_id (如 EMP_001)
    # Staff 端连接 SSE 时用的也是 employee_id，直接推送即可
    
    # 推送给创建者 (Manager) - creator_id 就是 employee_id
    await sse_manager.publish_to_manager(
        creator_id,
        "task_created",
        {
            "task_id": task_id,
            "task_info": task_info,
        }
    )

    # 推送给执行人 (Staff) - assigned_to_id 就是 employee_id
    assigned_to_id = task_info.get("assigned_to_id")
    if assigned_to_id:
        await sse_manager.publish_to_staff(
            assigned_to_id,
            "new_task",
            {
                "task_id": task_id,
                "task_info": task_info,
            }
        )


async def notify_task_updated(manager_id: str, task_id: str, status: str, task_info: dict = None):
    """
    任务状态更新后推送通知

    Args:
        manager_id: Manager ID
        task_id: 任务ID
        status: 新状态
        task_info: 任务信息（可选）
    """
    await sse_manager.publish_to_manager(
        manager_id,
        "task_updated",
        {
            "task_id": task_id,
            "status": status,
            "task_info": task_info or {},
        }
    )


async def notify_task_completed(manager_id: str, task_id: str, task_info: dict = None):
    """
    任务完成后推送通知（反馈完成）

    Args:
        manager_id: Manager ID
        task_id: 任务ID
        task_info: 任务信息（可选）
    """
    await sse_manager.publish_to_manager(
        manager_id,
        "task_completed",
        {
            "task_id": task_id,
            "status": "反馈完成",
            "task_info": task_info or {},
        }
    )
