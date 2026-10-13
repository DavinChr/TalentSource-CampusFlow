"""
Simpul validate_capacity
========================
Memvalidasi kapasitas ruangan terhadap jumlah peserta via campusflow-db:
- Memanggil query_room_capacity.
- Membandingkan kapasitas resmi dengan attendee_count.
- Jika kapasitas kurang -> tolak (INSUFFICIENT_CAPACITY).
- Jika cukup -> lanjut ke pengecekan peralatan / otorisasi.
"""

from typing import Dict, Any
from src.agent.state import AgentState, add_audit
from src.agent.mcp_client import call_db


async def validate_capacity(state: AgentState) -> Dict[str, Any]:
    req = state["parsed_request"]
    room_name = req["room_name"]
    attendee_count = req["attendee_count"] or 0

    res = await call_db("query_room_capacity", {"room_name": room_name})
    errors = list(state["errors"])

    if not res.get("found", False):
        errors.append(f"Ruangan {room_name} tidak ditemukan di sistem.")
        return {
            "workflow_status": "INVALID_REQUEST",
            "errors": errors,
            "audit_trail": add_audit(state, "validate_capacity", res, "REJECT", "INVALID_REQUEST"),
        }

    capacity = res.get("capacity", 0)
    passed = capacity >= attendee_count

    if passed:
        next_status = "CAPACITY_VALIDATION"
        decision = "PASS"
        validation_res = {
            "passed": True,
            "reason": f"Kapasitas ruangan {room_name} ({capacity} orang) mencukupi untuk {attendee_count} peserta.",
            "details": res,
        }
    else:
        next_status = "INSUFFICIENT_CAPACITY"
        decision = "REJECT"
        msg = f"Kapasitas ruangan {room_name} ({capacity} orang) tidak mencukupi untuk {attendee_count} peserta."
        errors.append(msg)
        validation_res = {
            "passed": False,
            "reason": msg,
            "details": res,
        }

    return {
        "capacity_validation": validation_res,
        "workflow_status": next_status,
        "errors": errors,
        "audit_trail": add_audit(
            state,
            "validate_capacity",
            {"capacity": capacity, "attendee_count": attendee_count, "passed": passed},
            decision,
            next_status,
        ),
    }
