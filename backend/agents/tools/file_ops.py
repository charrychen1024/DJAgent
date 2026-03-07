"""
文件操作工具 - 原子化
只负责文件存取，不包含业务逻辑
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = None

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc", ".xlsx", ".xls"}

# 最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def set_data_dir(data_dir: Path):
    """设置数据目录"""
    global DATA_DIR
    DATA_DIR = data_dir


def get_data_dir() -> Path:
    """获取数据目录"""
    global DATA_DIR
    if DATA_DIR is None:
        # 默认设置为项目根目录的data文件夹
        # __file__ = backend/agents/tools/file_ops.py
        # parent.parent.parent.parent = 项目根目录
        DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
    return DATA_DIR


def _allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return "." in filename and Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _clean_filename(filename: str) -> str:
    """清理文件名，防止路径穿越"""
    filename = secure_filename(filename)
    return filename


def save_uploaded_file(task_id: str, file_data: bytes, filename: str) -> Dict[str, Any]:
    """
    保存上传文件

    Args:
        task_id: 任务ID
        file_data: 文件二进制数据
        filename: 文件名

    Returns:
        保存结果
    """
    logger.info(f"[工具] save_uploaded_file 调用: {filename} -> task={task_id}")

    try:
        # 验证文件名
        if not _allowed_file(filename):
            return {"error": f"不支持的文件类型: {filename}"}

        # 清理文件名
        filename = _clean_filename(filename)

        # 检查文件大小
        if len(file_data) > MAX_FILE_SIZE:
            return {"error": f"文件大小超过限制: {MAX_FILE_SIZE / 1024 / 1024}MB"}

        # 创建目录
        data_dir = get_data_dir()
        upload_dir = data_dir / "uploads" / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_data)

        result = {
            "success": True,
            "filename": filename,
            "file_path": str(file_path),
            "file_size": len(file_data),
            "message": f"文件 {filename} 保存成功",
        }

        logger.info(f"[工具] save_uploaded_file 成功: {filename}")
        return result

    except Exception as e:
        logger.error(f"[工具] save_uploaded_file 失败: {str(e)}")
        return {"error": f"保存文件失败: {str(e)}"}


def save_uploaded_file_from_path(
    task_id: str, source_path: str, filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    从已有路径保存上传文件（用于后端直接读取）

    Args:
        task_id: 任务ID
        source_path: 源文件路径
        filename: 目标文件名（可选，默认使用原文件名）

    Returns:
        保存结果
    """
    logger.info(
        f"[工具] save_uploaded_file_from_path 调用: {source_path} -> task={task_id}"
    )

    try:
        source = Path(source_path)

        if not source.exists():
            return {"error": f"源文件不存在: {source_path}"}

        # 使用原文件名或指定文件名
        if filename is None:
            filename = source.name
        else:
            filename = _clean_filename(filename)

        # 验证文件类型
        if not _allowed_file(filename):
            return {"error": f"不支持的文件类型: {filename}"}

        # 检查文件大小
        file_size = source.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return {"error": f"文件大小超过限制: {MAX_FILE_SIZE / 1024 / 1024}MB"}

        # 创建目录
        data_dir = get_data_dir()
        upload_dir = data_dir / "uploads" / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 复制文件
        dest_path = upload_dir / filename
        shutil.copy2(source, dest_path)

        result = {
            "success": True,
            "filename": filename,
            "file_path": str(dest_path),
            "file_size": file_size,
            "message": f"文件 {filename} 保存成功",
        }

        logger.info(f"[工具] save_uploaded_file_from_path 成功: {filename}")
        return result

    except Exception as e:
        logger.error(f"[工具] save_uploaded_file_from_path 失败: {str(e)}")
        return {"error": f"保存文件失败: {str(e)}"}


def read_file_content(file_path: str) -> Dict[str, Any]:
    """
    读取文件内容

    Args:
        file_path: 文件路径

    Returns:
        文件内容
    """
    logger.info(f"[工具] read_file_content 调用: {file_path}")

    try:
        path = Path(file_path)

        if not path.exists():
            return {"error": f"文件不存在: {file_path}"}

        # 根据文件类型选择读取方式
        suffix = path.suffix.lower()

        if suffix == ".txt":
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content, "type": "text"}

        elif suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            return {"success": True, "content": content, "type": "json"}

        elif suffix in [".pdf", ".docx", ".doc"]:
            # 调用解析工具
            from .file_parser import parse_file

            return parse_file(str(path))

        elif suffix in [".jpg", ".jpeg", ".png"]:
            from .file_parser import parse_image

            return parse_image(str(path))

        else:
            return {"error": f"不支持读取的文件类型: {suffix}"}

    except Exception as e:
        logger.error(f"[工具] read_file_content 失败: {str(e)}")
        return {"error": f"读取文件失败: {str(e)}"}


def list_uploaded_files(task_id: str) -> Dict[str, Any]:
    """
    列出任务的上传文件

    Args:
        task_id: 任务ID

    Returns:
        文件列表
    """
    logger.info(f"[工具] list_uploaded_files 调用: {task_id}")

    try:
        data_dir = get_data_dir()
        upload_dir = data_dir / "uploads" / task_id

        if not upload_dir.exists():
            return {"success": True, "files": [], "count": 0}

        files = []
        for f in upload_dir.iterdir():
            if f.is_file():
                files.append(
                    {
                        "filename": f.name,
                        "file_path": str(f),
                        "file_size": f.stat().st_size,
                        "modified_time": datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

        return {
            "success": True,
            "files": sorted(files, key=lambda x: x["filename"]),
            "count": len(files),
        }

    except Exception as e:
        logger.error(f"[工具] list_uploaded_files 失败: {str(e)}")
        return {"error": f"列出文件失败: {str(e)}"}


def delete_file(file_path: str) -> Dict[str, Any]:
    """
    删除文件

    Args:
        file_path: 文件路径

    Returns:
        删除结果
    """
    logger.info(f"[工具] delete_file 调用: {file_path}")

    try:
        path = Path(file_path)

        if not path.exists():
            return {"error": f"文件不存在: {file_path}"}

        path.unlink()

        return {"success": True, "message": f"文件已删除: {path.name}"}

    except Exception as e:
        logger.error(f"[工具] delete_file 失败: {str(e)}")
        return {"error": f"删除文件失败: {str(e)}"}


# 导出所有工具
__all__ = [
    "save_uploaded_file",
    "save_uploaded_file_from_path",
    "read_file_content",
    "list_uploaded_files",
    "delete_file",
    "set_data_dir",
    "get_data_dir",
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE",
]
