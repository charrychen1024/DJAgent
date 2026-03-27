"""
超时提醒系统的辅助函数模块

用于处理时间计算、日期解析等与超时检测相关的工具函数。
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def parse_deadline(deadline_str: str) -> Optional[datetime]:
    """
    解析截止时间字符串，支持多种格式

    支持的格式：
    - ISO格式: "2026-03-23T18:00:00"
    - 日期+时间: "2026-03-23 18:00:00" 或 "2026-03-23 18:00"
    - 仅日期: "2026-03-23" (默认为 23:59:59)

    Args:
        deadline_str: 截止时间字符串

    Returns:
        datetime对象，如果解析失败则返回None
    """
    if not deadline_str or not isinstance(deadline_str, str):
        logger.warning(f"[时间工具] 无效的deadline字符串: {deadline_str}")
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S",        # ISO格式
        "%Y-%m-%d %H:%M:%S",        # 完整日期时间
        "%Y-%m-%d %H:%M",           # 日期 + 小时:分钟
        "%Y-%m-%d",                 # 仅日期
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(deadline_str.strip(), fmt)

            # 如果只有日期，设置为当天的23:59:59
            if fmt == "%Y-%m-%d":
                dt = dt.replace(hour=23, minute=59, second=59)

            return dt
        except ValueError:
            continue

    logger.warning(f"[时间工具] 无法解析deadline: {deadline_str}")
    return None


def calculate_remaining_time(deadline: datetime) -> Tuple[int, int]:
    """
    计算距离截止时间还剩多少小时和分钟

    Args:
        deadline: 截止时间

    Returns:
        元组 (小时, 分钟)，如果已超期则返回 (-1, -1)
    """
    try:
        now = datetime.now()
        delta = deadline - now

        if delta.total_seconds() < 0:
            # 已超期
            return (-1, -1)

        total_seconds = delta.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        return (hours, minutes)
    except Exception as e:
        logger.error(f"[时间工具] 计算剩余时间失败: {str(e)}")
        return (0, 0)


def is_about_to_timeout(deadline: datetime, warn_before_hours: int) -> bool:
    """
    判断任务是否即将超时

    Args:
        deadline: 截止时间
        warn_before_hours: 提前多少小时判定为"即将超时"

    Returns:
        True表示即将超时（在预警时间内），False表示还未接近超时
    """
    try:
        now = datetime.now()
        warn_time = deadline - timedelta(hours=warn_before_hours)

        # 即将超时的条件：当前时间在[warn_time, deadline)之间
        return warn_time <= now < deadline
    except Exception as e:
        logger.error(f"[时间工具] 判断即将超时失败: {str(e)}")
        return False


def is_already_timeout(deadline: datetime) -> bool:
    """
    判断任务是否已超时

    Args:
        deadline: 截止时间

    Returns:
        True表示已超时，False表示未超时
    """
    try:
        now = datetime.now()
        return now > deadline
    except Exception as e:
        logger.error(f"[时间工具] 判断已超时失败: {str(e)}")
        return False


def format_datetime_for_display(dt: datetime) -> str:
    """
    格式化datetime对象为用户友好的显示格式

    Args:
        dt: datetime对象

    Returns:
        格式化的时间字符串 (例: "2026-03-23 18:00")
    """
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        logger.error(f"[时间工具] 格式化时间失败: {str(e)}")
        return str(dt)


def calculate_deadline_from_now(hours: int) -> datetime:
    """
    计算从现在起指定小时后的时间

    Args:
        hours: 小时数

    Returns:
        计算后的datetime对象
    """
    return datetime.now() + timedelta(hours=hours)


def get_readable_remaining_time(deadline: datetime) -> str:
    """
    获取人类可读的剩余时间描述

    Args:
        deadline: 截止时间

    Returns:
        描述字符串 (例: "还剩2小时30分钟" 或 "已超期")
    """
    hours, minutes = calculate_remaining_time(deadline)

    if hours == -1:
        return "已超期"

    if hours == 0:
        if minutes == 0:
            return "即将超期"
        return f"还剩{minutes}分钟"

    return f"还剩{hours}小时{minutes}分钟"


def validate_deadline(deadline_str: str, min_hours: int = 1) -> Tuple[bool, Optional[datetime], str]:
    """
    验证deadline字符串是否有效

    Args:
        deadline_str: 截止时间字符串
        min_hours: deadline距离现在的最少小时数

    Returns:
        元组 (是否有效, 解析后的datetime, 错误消息)
    """
    # 尝试解析
    deadline = parse_deadline(deadline_str)
    if deadline is None:
        return False, None, "无法解析deadline格式"

    # 检查deadline是否已过期
    if is_already_timeout(deadline):
        return False, None, "deadline已过期，必须设置为未来时间"

    # 检查deadline是否距离现在足够远
    hours, _ = calculate_remaining_time(deadline)
    if hours < min_hours:
        return False, None, f"deadline距离现在至少需要{min_hours}小时"

    return True, deadline, ""


# 用于测试的常用时间常数
if __name__ == "__main__":
    # 示例：测试各个函数
    test_deadline = calculate_deadline_from_now(2)
    print(f"测试deadline: {format_datetime_for_display(test_deadline)}")
    print(f"剩余时间: {get_readable_remaining_time(test_deadline)}")
    print(f"即将超时? {is_about_to_timeout(test_deadline, warn_before_hours=1)}")
    print(f"已超时? {is_already_timeout(test_deadline)}")
