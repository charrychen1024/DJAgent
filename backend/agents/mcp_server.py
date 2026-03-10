"""
MCP Server Server log - Enhanced with better logging
"""

import sys
import logging
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
    read_risk_data,
    update_task_status,
    save_chat_message,
    save_uploaded_file_from_path,
    list_uploaded_files,
)

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
    description="Create a new verification task. Input: task_info (dict) containing creator_id, creator_name, assigned_to_id, assigned_to_name, risk_summary.",
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
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


@tool(
    name="assign_task",
    description="Assign a task to an executor. Input: task_id, assigned_to_id, assigned_to_name, status.",
    input_schema={
        "task_id": str,
        "assigned_to_id": str,
        "assigned_to_name": str,
        "status": str,
    },
)
async def tool_assign_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """Assign task tool"""
    logger.info(f"[MCP-TOOL] assign_task called for task: {args.get('task_id')}")
    result = assign_task(
        args["task_id"],
        args["assigned_to_id"],
        args["assigned_to_name"],
        args.get("status", "已下发"),
    )
    logger.info(f"[MCP-TOOL] assign_task completed")
    error_flag = "error" in result
    return {"content": [{"type": "text", "text": str(result)}], "is_error": error_flag}


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
    description="Update task status. Input: task_id, status.",
    input_schema={"task_id": str, "status": str},
)
async def tool_update_task_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update task status tool"""
    logger.info(f"[MCP-TOOL] update_task_status called for task: {args.get('task_id')}")
    result = update_task_status(args["task_id"], args["status"])
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


# ============ Create MCP Server ============


def create_djagent_mcp_server():
    """Create DJAgent MCP server"""

    all_tools = [
        tool_list_users,
        tool_create_task,
        tool_assign_task,
        tool_get_task_detail,
        tool_parse_csv,
        tool_read_risk_data,
        tool_update_task_status,
        tool_save_chat_message,
        tool_save_uploaded_file,
        tool_list_uploaded_files,
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
