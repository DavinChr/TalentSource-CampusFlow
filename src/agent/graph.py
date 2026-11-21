"""
CampusFlow — Orchestration Graph (LangGraph State Machine)
==========================================================
Graf orkestrasi alur kerja agen otonom terkendali (Controlled Autonomous Workflow Agent).
Prinsip Ponytail: Fail-fast, no speculative boilerplate, lean linear conditional loop.
"""

from typing import Any, Dict
from langgraph.graph import StateGraph, START, END

from src.agent.state import AgentState
from src.agent.mcp_client import call_db
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


async def persist_audit(state: AgentState) -> Dict[str, Any]:
    """Simpul penutup: menyimpan seluruh jejak audit ke tabel audit_logs (REQ-AUD-01)."""
    trace_id = state.get("trace_id") or "trace-unknown"
    trail = state.get("audit_trail") or []
    booking_id = state.get("booking_id")
    if trail:
        try:
            await call_db("record_audit_trail", {
                "trace_id": trace_id,
                "audit_trail": trail,
                "booking_id": booking_id,
            })
        except Exception:
            pass
    return {}


def _next(step: str):
    """Router generik ponytail: lanjut ke node berikutnya atau rekam audit jika status gagal/berhenti."""
    return lambda s: "persist_audit" if s.get("workflow_status") in STOP_STATUSES else step


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
        ("persist_audit", persist_audit),
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
        builder.add_conditional_edges(curr, _next(nxt), {nxt: nxt, "persist_audit": "persist_audit"})

    builder.add_edge("send_notification", "persist_audit")
    builder.add_edge("persist_audit", END)

    return builder.compile()


campusflow_agent = build_campusflow_graph()
