"""
通用数据查询工具 - 支持自然语言查询
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import csv

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
# 风险数据目录
RISK_DATA_DIR = DATA_DIR / "risk_data"


def list_tables() -> Dict[str, Any]:
    """
    列出可用的数据表

    Returns:
        可用的数据表列表
    """
    logger.info("[工具] list_tables 调用")

    try:
        tables = []

        # 风险数据表 (在 risk_data 子目录)
        risk_files = list(RISK_DATA_DIR.glob("risk_data_*.csv"))
        for f in risk_files:
            tables.append({
                "name": f.name,
                "type": "risk_data",
                "description": f"风险数据表"
            })

        # 月度风险数据表 (在 risk_data 子目录)
        monthly_files = list(RISK_DATA_DIR.glob("risk_data_monthly_*.csv"))
        for f in monthly_files:
            tables.append({
                "name": f.name,
                "type": "risk_data_monthly",
                "description": "月度风险数据表"
            })

        # 任务表
        if (DATA_DIR / "tasks.csv").exists():
            tables.append({
                "name": "tasks.csv",
                "type": "task",
                "description": "任务表"
            })

        # 用户表
        if (DATA_DIR / "users.csv").exists():
            tables.append({
                "name": "users.csv",
                "type": "user",
                "description": "用户表"
            })

        return {
            "success": True,
            "tables": tables,
            "count": len(tables)
        }

    except Exception as e:
        logger.error(f"[工具] list_tables 失败: {e}")
        return {"error": str(e)}


def describe_table(table_name: str) -> Dict[str, Any]:
    """
    获取表结构

    Args:
        table_name: 表名

    Returns:
        表结构信息
    """
    logger.info(f"[工具] describe_table 调用: {table_name}")

    try:
        file_path = DATA_DIR / table_name
        if not file_path.exists():
            return {"error": f"表 {table_name} 不存在"}

        # 读取表头获取字段
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []

            # 读取前3行获取样本数据
            samples = []
            f.seek(0)
            for i, row in enumerate(reader):
                if i >= 3:
                    break
                samples.append(row)

            return {
                "success": True,
                "table_name": table_name,
                "fields": fields,
                "sample_data": samples[:3]
            }

    except Exception as e:
        logger.error(f"[工具] describe_table 失败: {e}")
        return {"error": str(e)}


def query_data(query: str, table_name: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """
    通用数据查询工具

    用户可以用自然语言描述想要查询的数据，系统会自动处理。

    Args:
        query: 自然语言查询，如"查询最近一个月的风险数据"
        table_name: 表名（可选，不指定时根据query推断）
        limit: 返回结果数量限制

    Returns:
        查询结果
    """
    logger.info(f"[工具] query_data 调用: query={query}, table={table_name}, limit={limit}")

    try:
        # 1. 如果没有指定表名，先列出可用表
        if not table_name:
            tables_result = list_tables()
            if "error" in tables_result:
                return tables_result
            return {
                "message": "请指定要查询的表。可用表：",
                "tables": tables_result.get("tables", [])
            }

        # 2. 获取表结构
        table_desc = describe_table(table_name)
        if "error" in table_desc:
            return table_desc

        # 3. 读取数据
        file_path = DATA_DIR / table_name
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []

            # 读取所有数据（实际生产环境应该用数据库）
            all_data = list(reader)

            # 4. 返回表结构和数据样本
            # 注意：真正的自然语言到SQL的转换需要LLM辅助
            # 这里返回数据样本，让用户选择如何过滤
            result_data = all_data[:limit]

            return {
                "success": True,
                "table_name": table_name,
                "fields": fields,
                "total_count": len(all_data),
                "returned_count": len(result_data),
                "data": result_data,
                "message": f"表 {table_name} 共有 {len(all_data)} 条数据，返回前 {len(result_data)} 条"
            }

    except Exception as e:
        logger.error(f"[工具] query_data 失败: {e}")
        return {"error": str(e)}


def query_risk_data_by_criteria(
    criteria: str,
    filename: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    按条件查询风险数据

    这是一个更具体的查询接口，适合在LLM理解了用户意图后调用。

    Args:
        criteria: 查询条件描述，如"高风险"、"运单号开头WLYD"等
        filename: 风险数据文件名，如 risk_data_001.csv
        limit: 返回结果数量限制

    Returns:
        查询结果
    """
    logger.info(f"[工具] query_risk_data_by_criteria 调用: criteria={criteria}, filename={filename}")

    try:
        # 确定要查询的文件
        if not filename:
            # 默认查询最新的风险数据文件
            files = sorted(RISK_DATA_DIR.glob("risk_data_*.csv"))
            if not files:
                return {"error": "没有找到风险数据文件"}
            filename = files[-1].name

        file_path = RISK_DATA_DIR / filename
        if not file_path.exists():
            return {"error": f"文件 {filename} 不存在"}

        # 读取并过滤数据
        results = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []

            for row in reader:
                # 简单关键字匹配（生产环境应该用更智能的匹配）
                criteria_lower = criteria.lower()
                match = False

                # 检查所有字段
                for field, value in row.items():
                    if value and criteria_lower in str(value).lower():
                        match = True
                        break

                if match:
                    results.append(row)

                    if len(results) >= limit:
                        break

        return {
            "success": True,
            "criteria": criteria,
            "filename": filename,
            "count": len(results),
            "data": results,
            "fields": fields
        }

    except Exception as e:
        logger.error(f"[工具] query_risk_data_by_criteria 失败: {e}")
        return {"error": str(e)}


__all__ = [
    'list_tables',
    'describe_table',
    'query_data',
    'query_risk_data_by_criteria'
]
