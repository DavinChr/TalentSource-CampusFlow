"""
Simpul create_booking
=====================
Eksekusi penulisan pemesanan ke basis data secara transaksional (ACID):
- Penegakan Invariant INV-001: Dilarang menulis jika all_validations_passed / booking_authorized False!
- Memanggil create_booking_transactional di campusflow-db.
- Mencatat booking_id dan booking_reference (BK-YYYY-NNN).
- Jika berhasil -> lanjut ke NOTIFICATION.
- Jika transaksi gagal -> DATABASE_ERROR.
"""

from typing import Dict, Any
from src.agent.state import AgentState, add_audit
from src.agent.mcp_client import call_db


async def create_booking(state: AgentState) -> Dict[str, Any]:
    # Guardrail Invariant INV-001
    if not state.get("all_validations_passed") or not state.get("booking_authorized"):
        msg = "Pelanggaran Invariant Keamanan INV-001: Percobaan penulisan DB sebelum seluruh validasi lulus."
        return {
            "workflow_status": "WORKFLOW_ABORTED",
            "errors": state["errors"] + [msg],
            "audit_trail": add_audit(state, "create_booking", {"security_violation": msg}, "ABORT", "WORKFLOW_ABORTED"),
        }

    req = state["parsed_request"]
    room_id = (state.get("selected_room") or {}).get("id") or (state.get("room_availability_details") or {}).get("room_id")
    res = await call_db("create_booking_transactional", {
        "room_id": room_id,
        "user_identifier": state["requester"],
        "event_name": req["event_name"],
        "booking_date": req["booking_date"],
        "start_time": req["start_time"],
        "end_time": req["end_time"],
        "attendee_count": req["attendee_count"],
        "notes": req.get("notes") or "",
    })

    errors = list(state["errors"])
    if res.get("status") == "CREATED":
        next_status = "BOOKING_WRITE"
        decision = "PASS"
        booking_id = res.get("booking_id")
        booking_ref = res.get("booking_reference")
    else:
        next_status = "DATABASE_ERROR"
        decision = "REJECT"
        booking_id = None
        booking_ref = None
        errors.append(res.get("message", "Gagal menyimpan pemesanan ke basis data."))

    return {
        "booking_id": booking_id,
        "booking_reference": booking_ref,
        "workflow_status": next_status,
        "errors": errors,
        "audit_trail": add_audit(
            state,
            "create_booking",
            res,
            decision,
            next_status,
        ),
    }
