"""
文件解析工具 - 原子化
只负责解析文件，不包含业务逻辑
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

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
        DATA_DIR = Path(__file__).parent.parent.parent / "data"
    return DATA_DIR


def parse_csv(file_path: str) -> Dict[str, Any]:
    """
    解析CSV文件
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        解析结果，包含行数、列名、数据预览
    """
    logger.info(f"[工具] parse_csv 调用: {file_path}")
    
    if not HAS_PANDAS:
        return {"error": "pandas未安装，无法解析CSV文件"}
    
    try:
        df = pd.read_csv(file_path)
        
        result = {
            "success": True,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict(orient='records'),
            "summary": f"CSV文件包含{len(df)}行数据，{len(df.columns)}列",
            "data": df.to_dict(orient='records')
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
    
    if not HAS_PANDAS:
        return {"error": "pandas未安装，无法解析Excel文件"}
    
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        
        result = {
            "success": True,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict(orient='records'),
            "summary": f"Excel文件包含{len(df)}行数据，{len(df.columns)}列",
            "data": df.to_dict(orient='records')
        }
        
        logger.info(f"[工具] parse_excel 成功: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"[工具] parse_excel 失败: {str(e)}")
        return {"error": f"解析Excel文件失败: {str(e)}"}


def parse_pdf(file_path: str, max_pages: int = 3) -> Dict[str, Any]:
    """
    解析PDF文件，提取文本
    
    Args:
        file_path: PDF文件路径
        max_pages: 最大读取页数
        
    Returns:
        提取的文本内容
    """
    logger.info(f"[工具] parse_pdf 调用: {file_path}")
    
    if not HAS_PYPDF2:
        return {"error": "PyPDF2未安装，无法解析PDF文件"}
    
    try:
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
                "total_pages": len(reader.pages),
                "text": full_text[:5000],
                "summary": f"PDF文件包含{len(reader.pages)}页，已提取前{total_pages}页文本"
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
    
    if not HAS_DOCX:
        return {"error": "python-docx未安装，无法解析Word文件"}
    
    try:
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        
        result = {
            "success": True,
            "paragraphs": len(paragraphs),
            "text": full_text[:5000],
            "summary": f"Word文件包含{len(paragraphs)}段文本"
        }
        
        logger.info(f"[工具] parse_word 成功: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"[工具] parse_word 失败: {str(e)}")
        return {"error": f"解析Word文件失败: {str(e)}"}


def parse_image(file_path: str) -> Dict[str, Any]:
    """
    解析图片文件，获取基本信息
    
    Args:
        file_path: 图片文件路径
        
    Returns:
        图片基本信息
    """
    logger.info(f"[工具] parse_image 调用: {file_path}")
    
    try:
        from PIL import Image
        import os
        
        with Image.open(file_path) as img:
            size = os.path.getsize(file_path)
            result = {
                "success": True,
                "format": img.format,
                "mode": img.mode,
                "size": f"{img.width}x{img.height}",
                "file_size": size,
                "summary": f"图片格式: {img.format}, 尺寸: {img.width}x{img.height}, 大小: {size/1024:.1f}KB"
            }
            
        logger.info(f"[工具] parse_image 成功: {result['summary']}")
        return result
        
    except Exception as e:
        # 如果没有PIL，只返回基本信息
        try:
            import os
            size = os.path.getsize(file_path)
            return {
                "success": True,
                "file_size": size,
                "summary": f"图片文件，大小: {size/1024:.1f}KB"
            }
        except:
            return {"error": f"解析图片文件失败: {str(e)}"}


def parse_file(file_path: str) -> Dict[str, Any]:
    """
    根据文件类型自动选择解析方法
    
    Args:
        file_path: 文件路径
        
    Returns:
        解析结果
    """
    logger.info(f"[工具] parse_file 调用: {file_path}")
    
    file_path = file_path.strip()
    lower_path = file_path.lower()
    
    if lower_path.endswith('.csv'):
        return parse_csv(file_path)
    elif lower_path.endswith(('.xlsx', '.xls')):
        return parse_excel(file_path)
    elif lower_path.endswith('.pdf'):
        return parse_pdf(file_path)
    elif lower_path.endswith(('.docx', '.doc')):
        return parse_word(file_path)
    elif lower_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
        return parse_image(file_path)
    else:
        return {"error": f"不支持的文件类型: {file_path}"}


# 导出所有工具
__all__ = [
    'parse_csv',
    'parse_excel',
    'parse_pdf',
    'parse_word',
    'parse_image',
    'parse_file',
    'set_data_dir',
    'get_data_dir'
]
