"""
MCP Server Server log - Enhanced with better logging
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict
from claude_agent_sdk import tool, create_sdk_mcp_server

# Add backend path
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)

# Import all tools
from tools import (
    list_users,
    create_task,
    assign_task,
    get_task_detail,
    parse_csv,
    parse_excel,
    parse_pdf,
    parse_word,
    read_risk_data,
    update_task_status,
    save_chat_message,
    save_uploaded_file_from_path,
    list_uploaded_files,
)

# Import data query tools
from tools.data_query import (
    list_tables,
    describe_table,
    query_data,
    query_risk_data_by_criteria,
)

# Import SSE events
try:
    from sse_events import notify_task_created, notify_task_completed
    SSE_AVAILABLE = True
    logger.info("[MCP] SSE 事件模块导入成功")
except ImportError as e:
    SSE_AVAILABLE = False
    logger.warning(f"[MCP] SSE 事件模块导入失败: {e}")

# ============ Define MCP Tools ============


@tool(
    name="list_users",
    description="List available users in the system. Use this when user asks about available staff or wants to see user list. Input: role (string, optional) - filter by role.",
    input_schema={"role": str},
)
async def tool_list_users(args: Dict[str, Any]) -> Dict[str, Any]:
    """List users tool"""
    logger.info(f"[MCP-TOOL] list_users called with args: {args}")
    result = list_users(args.get("role"))
    logger.info(f"[MCP-TOOL] list_users returned: {result.get('count', 0)} users")
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="create_task",
    description="Create a new verification task. Input: task_info (dict) containing creator_id, creator_name, assigned_to_id, assigned_to_name, risk_summary, task_type (optional, '日度' or '月度', default '日度').",
    input_schema={"task_info": dict},
)
async def tool_create_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create task tool"""
    import json
    logger.info(f"[MCP-TOOL] create_task called with args keys: {list(args.keys())}")

    # 处理 task_info 可能是字符串或缺失的情况
    task_info = args.get("task_info")
    if task_info is None:
        return {"content": [{"type": "text", "text": "错误: task_info 不能为空"}], "is_error": True}
    if isinstance(task_info, str):
        try:
            task_info = json.loads(task_info)
            logger.info(f"[MCP-TOOL] Parsed task_info from string")
        except json.JSONDecodeError:
            return {"content": [{"type": "text", "text": "错误: task_info 必须是有效的 JSON 对象"}], "is_error": True}

    result = create_task(task_info)
    logger.info(f"[MCP-TOOL] create_task returned: {result.get('task_id', 'N/A')}")

    # 后端自动触发 StaffAgent 通知（不依赖前端 SSE 连接）
    if result.get("success"):
        task_id = result.get("task_id")
        assigned_to_id = task_info.get("assigned_to_id")
        assigned_to_name = task_info.get("assigned_to_name")

        if assigned_to_id and assigned_to_name:
            try:
                from .session_manager import get_or_create_staff_agent
                staff_agent = await get_or_create_staff_agent(assigned_to_id, assigned_to_name)
                notify_result = await staff_agent.notify_new_task(task_id, task_info)
                logger.info(f"[MCP-TOOL] StaffAgent 通知已发送: {assigned_to_name} (ID: {assigned_to_id})")

                # 推送 SSE 事件通知 IM 端有新消息（即使没有订阅者也尝试推送）
                # 使用 result.get("task", {}) 获取完整任务对象
                full_task_info = result.get("task", {})
                if SSE_AVAILABLE:
                    try:
                        from .sse_events import sse_manager
                        await sse_manager.publish_to_staff(
                            assigned_to_id,
                            "task_message_received",
                            {
                                "task_id": task_id,
                                "task_info": full_task_info,  # 使用完整任务对象
                                "message": notify_result.get("message", "") if isinstance(notify_result, dict) else ""
                            }
                        )
                        logger.info(f"[MCP-TOOL] SSE task_message_received 推送成功: {task_id}")
                    except Exception as e:
                        logger.warning(f"[MCP-TOOL] SSE 推送失败（不影响主流程）: {e}")
            except Exception as e:
                logger.error(f"[MCP-TOOL] StaffAgent 通知失败: {e}", exc_info=True)

    # 推送 SSE 事件
    if result.get("success") and SSE_AVAILABLE:
        try:
            task_id = result.get("task_id")
            creator_id = task_info.get("creator_id", "")
            await notify_task_created(creator_id, task_id, task_info)
            logger.info(f"[MCP-TOOL] SSE 事件推送成功: {task_id}")
        except Exception as e:
            logger.error(f"[MCP-TOOL] SSE 事件推送失败: {e}")

    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="assign_task",
    description="Assign a task to an executor. Input: task_id, assigned_to_id, assigned_to_name, status, feedback_deadline (optional, format: YYYY-MM-DD HH:MM:SS).",
    input_schema={
        "task_id": str,
        "assigned_to_id": str,
        "assigned_to_name": str,
        "status": str,
        "feedback_deadline": str,
    },
)
async def tool_assign_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """Assign task tool"""
    logger.info(f"[MCP-TOOL] assign_task called for task: {args.get('task_id')}")

    try:
        result = assign_task(
            args["task_id"],
            args["assigned_to_id"],
            args["assigned_to_name"],
            args.get("status", "已下发"),
            args.get("feedback_deadline", ""),  # 支持自定义反馈截止时间
        )
        
        # 检查是否分配成功
        if result.get("success"):
            logger.info(f"[MCP-TOOL] assign_task completed successfully for task: {args.get('task_id')}")
            error_flag = False
            return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}
        else:
            # 分配失败，记录失败原因并设置状态为"下发失败"
            error_msg = result.get("error", "未知错误")
            logger.error(f"[MCP-TOOL] assign_task failed for task {args.get('task_id')}: {error_msg}")
            
            # 调用 update_task_status 设置状态为"下发失败"
            try:
                from tools import update_task_status
                failure_result = update_task_status(
                    args["task_id"],
                    "下发失败",
                    f"分配失败原因: {error_msg}",
                    "",
                    ""
                )
                logger.info(f"[MCP-TOOL] Task status updated to '下发失败' for task: {args.get('task_id')}")
            except Exception as status_err:
                logger.error(f"[MCP-TOOL] Failed to update task status to '下发失败': {status_err}")
            
            error_flag = True
            return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}
            
    except Exception as e:
        # 捕获异常，处理下发失败情况
        logger.error(f"[MCP-TOOL] assign_task exception for task {args.get('task_id')}: {str(e)}", exc_info=True)
        
        # 尝试设置状态为"下发失败"
        try:
            from tools import update_task_status
            failure_result = update_task_status(
                args["task_id"],
                "下发失败",
                f"分配异常: {str(e)}",
                "",
                ""
            )
            logger.info(f"[MCP-TOOL] Task status updated to '下发失败' after exception for task: {args.get('task_id')}")
        except Exception as status_err:
            logger.error(f"[MCP-TOOL] Failed to update task status to '下发失败': {status_err}")
        
        error_flag = True
        return {"content": [{"type": "text", "text": f"分配任务失败: {str(e)}"}], "is_error": error_flag}


@tool(
    name="get_task_detail",
    description="Get detailed information about a task. Input: task_id.",
    input_schema={"task_id": str},
)
async def tool_get_task_detail(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get task detail tool"""
    logger.info(f"[MCP-TOOL] get_task_detail called for task: {args.get('task_id')}")
    result = get_task_detail(args["task_id"])
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="parse_csv",
    description="Parse a CSV file and return its contents. Input: file_path.",
    input_schema={"file_path": str},
)
async def tool_parse_csv(args: Dict[str, Any]) -> Dict[str, Any]:
    """Parse CSV tool"""
    logger.info(f"[MCP-TOOL] parse_csv called for file: {args.get('file_path')}")
    result = parse_csv(args["file_path"])
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="read_risk_data",
    description="Read risk data from CSV file. Input: filename.",
    input_schema={"filename": str},
)
async def tool_read_risk_data(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read risk data tool"""
    logger.info(f"[MCP-TOOL] read_risk_data called for file: {args.get('filename')}")
    result = read_risk_data(args["filename"])
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="update_task_status",
    description="Update task status. Input: task_id, status, feedback_summary (optional), sent_time (optional), feedback_deadline (optional).",
    input_schema={"task_id": str, "status": str, "feedback_summary": str, "sent_time": str, "feedback_deadline": str},
)
async def tool_update_task_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update task status tool"""
    logger.info(f"[MCP-TOOL] update_task_status called for task: {args.get('task_id')}")
    result = update_task_status(
        args["task_id"], 
        args["status"],
        args.get("feedback_summary", ""),
        args.get("sent_time", ""),
        args.get("feedback_deadline", "")
    )

    # 推送 SSE 事件（当任务状态变为"已完成"时通知 Manager）
    if result.get("success") and args.get("status") == "已完成" and SSE_AVAILABLE:
        try:
            task_id = args.get("task_id")
            # 获取任务详情以获取 creator_id
            task_detail = get_task_detail(task_id)
            creator_id = task_detail.get("creator_id", "")
            if creator_id:
                await notify_task_completed(creator_id, task_id, task_detail)
                logger.info(f"[MCP-TOOL] SSE 任务完成事件推送成功: {task_id}")
        except Exception as e:
            logger.error(f"[MCP-TOOL] SSE 事件推送失败: {e}")

    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="save_chat_message",
    description="Save chat message to task. Input: task_id, user_id, user_name, message.",
    input_schema={"task_id": str, "user_id": str, "user_name": str, "message": str},
)
async def tool_save_chat_message(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save chat message tool"""
    logger.info(f"[MCP-TOOL] save_chat_message called for task: {args.get('task_id')}")
    result = save_chat_message(
        args["task_id"],
        args["user_id"],
        args["user_name"],
        args["message"],
    )
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="save_uploaded_file",
    description="Save uploaded file to task. Input: task_id, file_path, file_name.",
    input_schema={"task_id": str, "file_path": str, "file_name": str},
)
async def tool_save_uploaded_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save uploaded file tool"""
    logger.info(
        f"[MCP-TOOL] save_uploaded_uploaded_file called for task: {args.get('task_id')}"
    )
    result = save_uploaded_file_from_path(
        args["task_id"],
        args["file_path"],
        args["file_name"],
    )
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="list_uploaded_files",
    description="List uploaded files for a task. Input: task_id.",
    input_schema={"task_id": str},
)
async def tool_list_uploaded_files(args: Dict[str, Any]) -> Dict[str, Any]:
    """List uploaded files tool"""
    logger.info(
        f"[MCP-TOOL] list_uploaded_files called for task: {args.get('task_id')}"
    )
    result = list_uploaded_files(args["task_id"])
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="parse_excel",
    description="Parse Excel file and return its contents. Input: file_path (string), sheet_name (string, optional).",
    input_schema={"file_path": str, "sheet_name": str},
)
async def tool_parse_excel(args: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Excel tool"""
    logger.info(f"[MCP-TOOL] parse_excel called for file: {args.get('file_path')}")
    result = parse_excel(args["file_path"], args.get("sheet_name"))
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="parse_pdf",
    description="Parse PDF file and extract text. Input: file_path (string), max_pages (int, optional, default 3).",
    input_schema={"file_path": str, "max_pages": int},
)
async def tool_parse_pdf(args: Dict[str, Any]) -> Dict[str, Any]:
    """Parse PDF tool"""
    logger.info(f"[MCP-TOOL] parse_pdf called for file: {args.get('file_path')}")
    result = parse_pdf(args["file_path"], args.get("max_pages", 3))
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="parse_word",
    description="Parse Word document and extract text. Input: file_path (string).",
    input_schema={"file_path": str},
)
async def tool_parse_word(args: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Word tool"""
    logger.info(f"[MCP-TOOL] parse_word called for file: {args.get('file_path')}")
    result = parse_word(args["file_path"])
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


# ============ Data Query Tools ============


@tool(
    name="list_tables",
    description="List available data tables in the system. Use this when user wants to know what data is available.",
    input_schema={},
)
async def tool_list_tables(args: Dict[str, Any]) -> Dict[str, Any]:
    """List tables tool"""
    logger.info(f"[MCP-TOOL] list_tables called")
    result = list_tables()
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="describe_table",
    description="Get table structure and sample data. Input: table_name (string).",
    input_schema={"table_name": str},
)
async def tool_describe_table(args: Dict[str, Any]) -> Dict[str, Any]:
    """Describe table tool"""
    logger.info(f"[MCP-TOOL] describe_table called: {args.get('table_name')}")
    result = describe_table(args.get("table_name"))
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="query_data",
    description="Query data using natural language. Input: query (string), table_name (string, optional), limit (int, default 100).",
    input_schema={"query": str, "table_name": str, "limit": int},
)
async def tool_query_data(args: Dict[str, Any]) -> Dict[str, Any]:
    """Query data tool"""
    logger.info(f"[MCP-TOOL] query_data called: {args.get('query')}")
    result = query_data(
        query=args.get("query"),
        table_name=args.get("table_name"),
        limit=args.get("limit", 100)
    )
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="query_risk_data",
    description="Query risk data by criteria. Input: criteria (string), filename (string, optional), limit (int, default 50).",
    input_schema={"criteria": str, "filename": str, "limit": int},
)
async def tool_query_risk_data(args: Dict[str, Any]) -> Dict[str, Any]:
    """Query risk data by criteria tool"""
    logger.info(f"[MCP-TOOL] query_risk_data called: {args.get('criteria')}")
    result = query_risk_data_by_criteria(
        criteria=args.get("criteria"),
        filename=args.get("filename"),
        limit=args.get("limit", 50)
    )
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


# ============ Create MCP Server ============


def create_djagent_mcp_server():
    """Create DJAgent MCP server"""

    all_tools = [
        tool_list_users,
        tool_create_task,
        tool_assign_task,
        tool_get_task_detail,
        tool_parse_csv,
        tool_parse_excel,
        tool_parse_pdf,
        tool_parse_word,
        tool_read_risk_data,
        tool_update_task_status,
        tool_save_chat_message,
        tool_save_uploaded_file,
        tool_list_uploaded_files,
        # Data query tools
        tool_list_tables,
        tool_describe_table,
        tool_query_data,
        tool_query_risk_data,
    ]

    logger.info(f"[MCP-SERVER] Creating server with {len(all_tools)} tools")
    for t in all_tools:
        logger.info(f"[MCP-SERVER]   Tool: {t.name}")

    server = create_sdk_mcp_server(
        name="djagent_tools", version="1.0.0", tools=all_tools
    )

    logger.info(f"[MCP-SERVER] Server created: {list(server.keys())}")

    return server


__all__ = ["create_djagent_mcp_server"]
