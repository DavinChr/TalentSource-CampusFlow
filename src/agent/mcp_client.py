"""
CampusFlow — MCP In-Process Client Adapter
==========================================
Adapter pemanggilan alat MCP langsung ke instance server internal
(campusflow-db, campusflow-fs, campusflow-notification) sesuai skema MCP standar.
"""

import json
from typing import Any, Dict

from src.mcp.db_server import server as db_server
from src.mcp.fs_server import server as fs_server
from src.mcp.notification_server import server as notification_server


async def call_mcp_tool(server_instance, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Memanggil alat MCP dan mengurai payload JSON responsnya."""
    result = await server_instance.call_tool(tool_name, arguments)
    if not result.content:
        return {}
    text_content = result.content[0].text
    try:
        return json.loads(text_content)
    except json.JSONDecodeError:
        return {"raw_text": text_content}


async def call_db(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Helper untuk memanggil campusflow-db."""
    return await call_mcp_tool(db_server, tool_name, arguments)


async def call_fs(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Helper untuk memanggil campusflow-fs."""
    return await call_mcp_tool(fs_server, tool_name, arguments)


async def call_notification(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Helper untuk memanggil campusflow-notification."""
    return await call_mcp_tool(notification_server, tool_name, arguments)
