"""
智能体工具函数模块
包含文档解析、风险数据分析、任务管理等工具
"""

import os
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# 文档解析依赖（可选安装）
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logging.warning("pandas未安装，CSV/Excel解析功能不可用")

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    logging.warning("PyPDF2未安装，PDF解析功能不可用")

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    logging.warning("python-docx未安装，Word解析功能不可用")

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent / "data"


# ==================== 文档解析工具 ====================

def parse_csv(file_path: str) -> Dict[str, Any]:
    """
    解析CSV文件
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        解析结果，包含行数、列名、数据预览
    """
    logger.info(f"[工具] parse_csv 调用: {file_path}")
    
    try:
        if not HAS_PANDAS:
            return {"error": "pandas未安装，无法解析CSV文件"}
        
        df = pd.read_csv(file_path)
        
        result = {
            "success": True,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict(orient='records'),
            "summary": f"CSV文件包含{len(df)}行数据，{len(df.columns)}列"
        }
        
        logger.info(f"[工具] parse_csv 成功: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"[工具] parse_csv 失败: {str(e)}")
        return {"error": f"解析CSV文件失败: {str(e)}"}


def parse_excel(file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    """
    解析Excel文件
    
    Args:
        file_path: Excel文件路径
        sheet_name: 工作表名称，默认第一个
        
    Returns:
        解析结果
    """
    logger.info(f"[工具] parse_excel 调用: {file_path}")
    
    try:
        if not HAS_PANDAS:
            return {"error": "pandas未安装，无法解析Excel文件"}
        
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        
        result = {
            "success": True,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict(orient='records'),
            "summary": f"Excel文件包含{len(df)}行数据，{len(df.columns)}列"
        }
        
        logger.info(f"[工具] parse_excel 成功: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"[工具] parse_excel 失败: {str(e)}")
        return {"error": f"解析Excel文件失败: {str(e)}"}


def parse_pdf(file_path: str, max_pages: int = 10) -> Dict[str, Any]:
    """
    解析PDF文件，提取文本
    
    Args:
        file_path: PDF文件路径
        max_pages: 最大读取页数
        
    Returns:
        提取的文本内容
    """
    logger.info(f"[工具] parse_pdf 调用: {file_path}")
    
    try:
        if not HAS_PYPDF2:
            return {"error": "PyPDF2未安装，无法解析PDF文件"}
        
        text_content = []
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = min(len(reader.pages), max_pages)
            
            for i in range(total_pages):
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    text_content.append(f"[第{i+1}页]\n{text}")
            
            full_text = "\n\n".join(text_content)
            
            result = {
                "success": True,
                "pages": total_pages,
                "text": full_text[:5000],  # 限制文本长度
                "summary": f"PDF文件包含{total_pages}页，已提取文本"
            }
            
            logger.info(f"[工具] parse_pdf 成功: {result['summary']}")
            return result
            
    except Exception as e:
        logger.error(f"[工具] parse_pdf 失败: {str(e)}")
        return {"error": f"解析PDF文件失败: {str(e)}"}


def parse_word(file_path: str) -> Dict[str, Any]:
    """
    解析Word文件，提取文本
    
    Args:
        file_path: Word文件路径
        
    Returns:
        提取的文本内容
    """
    logger.info(f"[工具] parse_word 调用: {file_path}")
    
    try:
        if not HAS_DOCX:
            return {"error": "python-docx未安装，无法解析Word文件"}
        
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        
        result = {
            "success": True,
            "paragraphs": len(paragraphs),
            "text": full_text[:5000],  # 限制文本长度
            "summary": f"Word文件包含{len(paragraphs)}段文本"
        }
        
        logger.info(f"[工具] parse_word 成功: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"[工具] parse_word 失败: {str(e)}")
        return {"error": f"解析Word文件失败: {str(e)}"}


# ==================== 业务工具 ====================

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
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return {"error": f"文件不存在: {filename}"}
        
        return parse_csv(str(file_path))
        
    except Exception as e:
        logger.error(f"[工具] read_risk_data 失败: {str(e)}")
        return {"error": f"读取风险数据失败: {str(e)}"}


def list_users(role: Optional[str] = None) -> Dict[str, Any]:
    """
    列出用户/执行人员
    
    Args:
        role: 角色筛选（业务负责人/一线操作人员）
        
    Returns:
        用户列表
    """
    logger.info(f"[工具] list_users 调用: role={role}")
    
    try:
        users_file = DATA_DIR / "users.csv"
        if not users_file.exists():
            return {"error": "用户数据文件不存在"}
        
        users = []
        with open(users_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if role is None or row.get('role') == role:
                    users.append({
                        "user_id": row.get('user_id'),
                        "username": row.get('username'),
                        "employee_id": row.get('employee_id', ''),
                        "name": row.get('username'),
                        "role": row.get('role'),
                        "department": row.get('department')
                    })
        
        logger.info(f"[工具] list_users 成功: 返回{len(users)}个用户")
        return {"success": True, "users": users}
        
    except Exception as e:
        logger.error(f"[工具] list_users 失败: {str(e)}")
        return {"error": f"获取用户列表失败: {str(e)}"}


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    查询任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务详情
    """
    logger.info(f"[工具] get_task_status 调用: {task_id}")
    
    try:
        tasks_file = DATA_DIR / "tasks.csv"
        if not tasks_file.exists():
            return {"error": "任务数据文件不存在"}
        
        with open(tasks_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('task_id') == task_id:
                    logger.info(f"[工具] get_task_status 成功: {task_id}")
                    return {"success": True, "task": row}
        
        return {"error": f"任务不存在: {task_id}"}
        
    except Exception as e:
        logger.error(f"[工具] get_task_status 失败: {str(e)}")
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
        task_result = get_task_status(task_id)
        if "error" in task_result:
            return task_result
        
        # 获取反馈详情
        feedback_file = DATA_DIR / "feedback" / f"{task_id}.json"
        feedback = {}
        if feedback_file.exists():
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback = json.load(f)
        
        result = {
            "success": True,
            "task": task_result.get("task"),
            "feedback_summary": feedback.get("feedback_summary", ""),
            "uploaded_files": feedback.get("uploaded_files", []),
            "status": feedback.get("status", task_result.get("task", {}).get("status", ""))
        }
        
        logger.info(f"[工具] get_task_detail 成功: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"[工具] get_task_detail 失败: {str(e)}")
        return {"error": f"获取任务详情失败: {str(e)}"}


# ==================== 工具注册 ====================

# 可注册给Agent的工具列表
AGENT_TOOLS = [
    parse_csv,
    parse_excel,
    parse_pdf,
    parse_word,
    read_risk_data,
    list_users,
    get_task_status,
    get_task_detail,
]

logger.info(f"[工具] 已加载{len(AGENT_TOOLS)}个工具: {[t.__name__ for t in AGENT_TOOLS]}")
