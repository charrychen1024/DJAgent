"""
任务管理工具 - 原子化
只负责任务CRUD，不包含业务逻辑
"""

import os
import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = None


def set_data_dir(data_dir: Path):
    """设置数据目录"""
    global DATA_DIR
    DATA_DIR = data_dir


def get_data_dir() -> Path:
    """获取数据目录"""
    global DATA_DIR
    if DATA_DIR is None:
        # 默认设置为项目根目录的data文件夹
        # __file__ = backend/agents/tools/task_manager.py
        # parent.parent.parent.parent = 项目根目录
        DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
    return DATA_DIR


def _generate_task_id() -> str:
    """生成新的任务ID"""
    tasks_file = get_data_dir() / "tasks.csv"
    task_id = "TASK_001"

    if tasks_file.exists():
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_line = lines[-1]
                    last_id = last_line.split(",")[0]
                    num = int(last_id.split("_")[1]) + 1
                    task_id = f"TASK_{num:03d}"
        except:
            pass

    return task_id


def create_task(task_info: Dict) -> Dict[str, Any]:
    """
    创建任务

    Args:
        task_info: 任务信息，包含:
            - creator_id: 创建人ID
            - creator_name: 创建人名称
            - assigned_to_id: 执行人ID
            - assigned_to_name: 执行人名称
            - risk_summary: 风险简述
            - risk_data_url: 风险数据文件路径

    Returns:
        创建结果
    """
    logger.info(f"[工具] create_task 调用: {task_info}")

    try:
        data_dir = get_data_dir()
        tasks_file = data_dir / "tasks.csv"

        # 生成任务ID
        task_id = _generate_task_id()

        # 创建时间
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 组装任务数据
        task_row = {
            "task_id": task_id,
            "creator_id": task_info.get("creator_id", ""),
            "creator_name": task_info.get("creator_name", ""),
            "assigned_to_id": task_info.get("assigned_to_id", ""),
            "assigned_to_name": task_info.get("assigned_to_name", ""),
            "status": "已创建",
            "created_time": created_time,
            "risk_summary": task_info.get("risk_summary", ""),
            "risk_data_url": task_info.get("risk_data_url", ""),
            "suggested_receiver_id": task_info.get("suggested_receiver_id", ""),
            "confirmed_receiver_id": task_info.get("confirmed_receiver_id", ""),
            "completed_time": "",
        }

        # 字段名
        fieldnames = [
            "task_id",
            "creator_id",
            "creator_name",
            "assigned_to_id",
            "assigned_to_name",
            "status",
            "created_time",
            "risk_summary",
            "risk_data_url",
            "suggested_receiver_id",
            "confirmed_receiver_id",
            "completed_time",
        ]

        # 写入CSV
        file_exists = tasks_file.exists()
        with open(tasks_file, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(task_row)

        # 初始化反馈文件
        feedback_dir = data_dir / "feedback"
        feedback_dir.mkdir(exist_ok=True)

        feedback_file = feedback_dir / f"{task_id}.json"
        feedback_data = {
            "task_id": task_id,
            "assigned_to_id": task_info.get("assigned_to_id", ""),
            "assigned_to_name": task_info.get("assigned_to_name", ""),
            "chat_history": [],
            "uploaded_files": [],
            "feedback_summary": "",
            "status": "已创建",
        }

        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[工具] create_task 成功: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "task": task_row,
            "message": f"任务 {task_id} 创建成功",
        }

    except Exception as e:
        logger.error(f"[工具] create_task 失败: {str(e)}")
        return {"error": f"创建任务失败: {str(e)}"}


def update_task_status(task_id: str, status: str, summary: str = "") -> Dict[str, Any]:
    """
    更新任务状态

    Args:
        task_id: 任务ID
        status: 新状态（已创建/已下发/反馈中/反馈完成/已超期）
        summary: 反馈总结（可选）

    Returns:
        更新结果
    """
    logger.info(f"[工具] update_task_status 调用: {task_id} -> {status}")

    try:
        data_dir = get_data_dir()
        tasks_file = data_dir / "tasks.csv"

        if not tasks_file.exists():
            return {"error": "任务文件不存在"}

        # 读取所有任务
        rows = []
        fieldnames = []

        with open(tasks_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                if row.get("task_id") == task_id:
                    row["status"] = status
                    if status == "反馈完成":
                        row["completed_time"] = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                rows.append(row)

        # 写回
        with open(tasks_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # 更新反馈文件
        if summary:
            feedback_file = data_dir / "feedback" / f"{task_id}.json"
            feedback_data = {}

            if feedback_file.exists():
                with open(feedback_file, "r", encoding="utf-8") as f:
                    feedback_data = json.load(f)

            feedback_data["feedback_summary"] = summary
            feedback_data["status"] = status
            feedback_data["summary_timestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            feedback_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[工具] update_task_status 成功: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "new_status": status,
            "message": f"任务状态已更新为: {status}",
        }

    except Exception as e:
        logger.error(f"[工具] update_task_status 失败: {str(e)}")
        return {"error": f"更新任务状态失败: {str(e)}"}


def assign_task(
    task_id: str, assigned_to_id: str, assigned_to_name: str, status: str = "已下发"
) -> Dict[str, Any]:
    """
    分配任务给执行人

    Args:
        task_id: 任务ID
        assigned_to_id: 执行人ID
        assigned_to_name: 执行人名称
        status: 任务状态

    Returns:
        分配结果
    """
    logger.info(f"[工具] assign_task 调用: {task_id} -> {assigned_to_name}")

    try:
        data_dir = get_data_dir()
        tasks_file = data_dir / "tasks.csv"

        if not tasks_file.exists():
            return {"error": "任务文件不存在"}

        # 读取并更新
        rows = []
        fieldnames = []

        with open(tasks_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                if row.get("task_id") == task_id:
                    row["assigned_to_id"] = assigned_to_id
                    row["assigned_to_name"] = assigned_to_name
                    row["status"] = status
                rows.append(row)

        # 写回
        with open(tasks_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # 更新反馈文件
        feedback_file = data_dir / "feedback" / f"{task_id}.json"
        feedback_data = {}

        if feedback_file.exists():
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback_data = json.load(f)

        feedback_data["assigned_to_id"] = assigned_to_id
        feedback_data["assigned_to_name"] = assigned_to_name
        feedback_data["status"] = status

        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[工具] assign_task 成功: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "assigned_to": assigned_to_name,
            "message": f"任务已分配给: {assigned_to_name}",
        }

    except Exception as e:
        logger.error(f"[工具] assign_task 失败: {str(e)}")
        return {"error": f"分配任务失败: {str(e)}"}


def save_chat_message(
    task_id: str, message: str, sender: str, sender_type: str = "user"
) -> Dict[str, Any]:
    """
    保存聊天消息到反馈

    Args:
        task_id: 任务ID
        message: 消息内容
        sender: 发送者名称
        sender_type: 发送者类型（user/agent）

    Returns:
        保存结果
    """
    logger.info(f"[工具] save_chat_message 调用: {task_id}")

    try:
        data_dir = get_data_dir()
        feedback_file = data_dir / "feedback" / f"{task_id}.json"

        feedback_data = {}
        if feedback_file.exists():
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback_data = json.load(f)

        if "chat_history" not in feedback_data:
            feedback_data["chat_history"] = []

        feedback_data["chat_history"].append(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sender": sender,
                "sender_type": sender_type,
                "message": message,
            }
        )

        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "消息已保存"}

    except Exception as e:
        logger.error(f"[工具] save_chat_message 失败: {str(e)}")
        return {"error": f"保存消息失败: {str(e)}"}


# 导出所有工具
__all__ = [
    "create_task",
    "update_task_status",
    "assign_task",
    "save_chat_message",
    "set_data_dir",
    "get_data_dir",
]
