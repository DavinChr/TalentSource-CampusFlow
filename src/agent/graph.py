"""
CampusFlow — Orchestration Graph (LangGraph State Machine)
==========================================================
Graf orkestrasi alur kerja agen otonom terkendali (Controlled Autonomous Workflow Agent).
Prinsip Ponytail: Fail-fast, no speculative boilerplate, lean linear conditional loop.
"""

from langgraph.graph import StateGraph, START, END

from src.agent.state import AgentState
from src.agent.nodes.parse_request import parse_request
from src.agent.nodes.validate_requirements import validate_requirements
from src.agent.nodes.check_room import check_room
from src.agent.nodes.validate_capacity import validate_capacity
from src.agent.nodes.check_equipment import check_equipment
from src.agent.nodes.authorize_booking import authorize_booking
from src.agent.nodes.create_booking import create_booking
from src.agent.nodes.send_notification import send_notification

STOP_STATUSES = {
    "INVALID_REQUEST", "NEEDS_CLARIFICATION", "ROOM_UNAVAILABLE",
    "INSUFFICIENT_CAPACITY", "EQUIPMENT_UNAVAILABLE", "EQUIPMENT_STATUS_UNKNOWN",
    "WORKFLOW_ABORTED", "DATABASE_ERROR",
}


def _next(step: str):
    """Router generik ponytail: lanjut ke node berikutnya kecuali jika status gagal/klarifikasi."""
    return lambda s: END if s.get("workflow_status") in STOP_STATUSES else step


def build_campusflow_graph():
    builder = StateGraph(AgentState)

    # 1. Daftarkan simpul
    nodes = [
        ("parse_request", parse_request),
        ("validate_requirements", validate_requirements),
        ("check_room", check_room),
        ("validate_capacity", validate_capacity),
        ("check_equipment", check_equipment),
        ("authorize_booking", authorize_booking),
        ("create_booking", create_booking),
        ("send_notification", send_notification),
    ]
    for name, fn in nodes:
        builder.add_node(name, fn)

    # 2. Rangkaian tepi kondisional terarah (fail-fast pipeline)
    builder.add_edge(START, "parse_request")

    pipeline = [
        ("parse_request", "validate_requirements"),
        ("validate_requirements", "check_room"),
        ("check_room", "validate_capacity"),
        ("validate_capacity", "check_equipment"),
        ("check_equipment", "authorize_booking"),
        ("authorize_booking", "create_booking"),
        ("create_booking", "send_notification"),
    ]
    for curr, nxt in pipeline:
        builder.add_conditional_edges(curr, _next(nxt), {nxt: nxt, END: END})

    builder.add_edge("send_notification", END)

    return builder.compile()


campusflow_agent = build_campusflow_graph()
