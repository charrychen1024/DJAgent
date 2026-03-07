"""
数据访问工具 - 原子化
只负责数据读写，不包含业务逻辑
"""

import os
import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据目录 - 会在运行时动态设置
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
        # __file__ = backend/agents/tools/data_access.py
        # parent.parent.parent.parent = 项目根目录
        DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
    return DATA_DIR


def read_risk_data(filename: str) -> Dict[str, Any]:
    """
    读取风险数据CSV文件

    Args:
        filename: 文件名，如 risk_data_001.csv

    Returns:
        风险数据内容
    """
    logger.info(f"[工具] read_risk_data 调用: {filename}")

    try:
        data_dir = get_data_dir()

        # 支持多种路径格式
        if filename.startswith(str(data_dir)):
            file_path = Path(filename)
        else:
            file_path = data_dir / filename

        if not file_path.exists():
            return {"error": f"文件不存在: {filename}"}

        # 导入file_parser解析
        from .file_parser import parse_csv

        result = parse_csv(str(file_path))

        if "error" in result:
            return result

        return {
            "success": True,
            "filename": file_path.name,
            "data": result.get("data", []),
            "count": result.get("rows", 0),
            "columns": result.get("columns", []),
            "preview": result.get("preview", []),
        }

    except Exception as e:
        logger.error(f"[工具] read_risk_data 失败: {str(e)}")
        return {"error": f"读取风险数据失败: {str(e)}"}


def list_risk_data_files() -> Dict[str, Any]:
    """
    列出所有风险数据文件

    Returns:
        风险数据文件列表
    """
    logger.info("[工具] list_risk_data_files 调用")

    try:
        data_dir = get_data_dir()
        risk_files = []

        for f in data_dir.glob("risk_data_*.csv"):
            risk_files.append(
                {"filename": f.name, "path": str(f), "size": f.stat().st_size}
            )

        return {
            "success": True,
            "files": sorted(risk_files, key=lambda x: x["filename"]),
            "count": len(risk_files),
        }

    except Exception as e:
        logger.error(f"[工具] list_risk_data_files 失败: {str(e)}")
        return {"error": f"列出风险数据文件失败: {str(e)}"}


def list_users(role: Optional[str] = None) -> Dict[str, Any]:
    """
    列出用户/执行人员

    Args:
        role: 角色筛选（业务负责人/一线操作人员/普通分析人员）

    Returns:
        用户列表
    """
    logger.info(f"[工具] list_users 调用: role={role}")

    try:
        data_dir = get_data_dir()
        users_file = data_dir / "users.csv"

        if not users_file.exists():
            return {"error": "用户数据文件不存在"}

        users = []
        with open(users_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if role is None or row.get("role") == role:
                    users.append(
                        {
                            "user_id": row.get("user_id"),
                            "username": row.get("username"),
                            "role": row.get("role"),
                            "department": row.get("department"),
                            "employee_id": row.get("employee_id", ""),
                        }
                    )

        logger.info(f"[工具] list_users 成功: 返回{len(users)}个用户")
        return {"success": True, "users": users, "count": len(users)}

    except Exception as e:
        logger.error(f"[工具] list_users 失败: {str(e)}")
        return {"error": f"获取用户列表失败: {str(e)}"}


def get_user(user_id: str) -> Dict[str, Any]:
    """
    获取指定用户信息

    Args:
        user_id: 用户ID

    Returns:
        用户信息
    """
    logger.info(f"[工具] get_user 调用: user_id={user_id}")

    try:
        data_dir = get_data_dir()
        users_file = data_dir / "users.csv"

        if not users_file.exists():
            return {"error": "用户数据文件不存在"}

        with open(users_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("user_id") == user_id:
                    return {
                        "success": True,
                        "user": {
                            "user_id": row.get("user_id"),
                            "username": row.get("username"),
                            "role": row.get("role"),
                            "department": row.get("department"),
                            "employee_id": row.get("employee_id", ""),
                        },
                    }

        return {"error": f"用户不存在: {user_id}"}

    except Exception as e:
        logger.error(f"[工具] get_user 失败: {str(e)}")
        return {"error": f"获取用户信息失败: {str(e)}"}


def get_task(task_id: str) -> Dict[str, Any]:
    """
    查询任务详情

    Args:
        task_id: 任务ID

    Returns:
        任务详情
    """
    logger.info(f"[工具] get_task 调用: {task_id}")

    try:
        data_dir = get_data_dir()
        tasks_file = data_dir / "tasks.csv"

        if not tasks_file.exists():
            return {"error": "任务数据文件不存在"}

        with open(tasks_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("task_id") == task_id:
                    logger.info(f"[工具] get_task 成功: {task_id}")
                    return {"success": True, "task": row}

        return {"error": f"任务不存在: {task_id}"}

    except Exception as e:
        logger.error(f"[工具] get_task 失败: {str(e)}")
        return {"error": f"查询任务失败: {str(e)}"}


def get_task_detail(task_id: str) -> Dict[str, Any]:
    """
    获取任务详情（含反馈）

    Args:
        task_id: 任务ID

    Returns:
        任务详情和反馈
    """
    logger.info(f"[工具] get_task_detail 调用: {task_id}")

    try:
        # 获取任务基本信息
        task_result = get_task(task_id)
        if "error" in task_result:
            return task_result

        # 获取反馈详情
        data_dir = get_data_dir()
        feedback_file = data_dir / "feedback" / f"{task_id}.json"
        feedback = {}

        if feedback_file.exists():
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback = json.load(f)

        result = {
            "success": True,
            "task": task_result.get("task"),
            "feedback": feedback,
            "feedback_summary": feedback.get("feedback_summary", ""),
            "uploaded_files": feedback.get("uploaded_files", []),
            "status": feedback.get(
                "status", task_result.get("task", {}).get("status", "")
            ),
        }

        logger.info(f"[工具] get_task_detail 成功: {task_id}")
        return result

    except Exception as e:
        logger.error(f"[工具] get_task_detail 失败: {str(e)}")
        return {"error": f"获取任务详情失败: {str(e)}"}


def query_tasks(
    creator_id: Optional[str] = None,
    assigned_to_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    查询任务列表

    Args:
        creator_id: 创建人ID过滤
        assigned_to_id: 执行人ID过滤
        status: 状态过滤

    Returns:
        任务列表
    """
    logger.info(
        f"[工具] query_tasks 调用: creator={creator_id}, assigned={assigned_to_id}, status={status}"
    )

    try:
        data_dir = get_data_dir()
        tasks_file = data_dir / "tasks.csv"

        if not tasks_file.exists():
            return {"error": "任务数据文件不存在"}

        tasks = []
        with open(tasks_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if creator_id and row.get("creator_id") != creator_id:
                    continue
                if assigned_to_id and row.get("assigned_to_id") != assigned_to_id:
                    continue
                if status and row.get("status") != status:
                    continue
                tasks.append(row)

        logger.info(f"[工具] query_tasks 成功: 返回{len(tasks)}个任务")
        return {"success": True, "tasks": tasks, "count": len(tasks)}

    except Exception as e:
        logger.error(f"[工具] query_tasks 失败: {str(e)}")
        return {"error": f"查询任务列表失败: {str(e)}"}


# 导出所有工具
__all__ = [
    "read_risk_data",
    "list_risk_data_files",
    "list_users",
    "get_user",
    "get_task",
    "get_task_detail",
    "query_tasks",
    "set_data_dir",
    "get_data_dir",
]
