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
    logger.info(f"[MCP-TOOL] create_task called with args keys: {list(args.keys())}")
    result = create_task(args["task_info"])
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
