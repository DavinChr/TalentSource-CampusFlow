"""
Simpul check_room
=================
Memeriksa ketersediaan ruangan di basis data via campusflow-db:
- Memanggil query_room_availability.
- Jika status AVAILABLE -> lanjut ke validasi kapasitas.
- Jika status UNAVAILABLE (bentrok) -> tolak (ROOM_UNAVAILABLE).
"""

from typing import Dict, Any
from src.agent.state import AgentState, add_audit
from src.agent.mcp_client import call_db


async def check_room(state: AgentState) -> Dict[str, Any]:
    req = state["parsed_request"]
    if not req or not req.get("room_name"):
        return {
            "workflow_status": "INVALID_REQUEST",
            "errors": state["errors"] + ["Ruangan tidak ditemukan dalam permintaan."],
        }

    # Validasi kelengkapan parameter esensial sebelum memanggil basis data
    missing_params = []
    if not req.get("booking_date"):
        missing_params.append("tanggal pemesanan")
    if not req.get("start_time"):
        missing_params.append("jam mulai")
    if not req.get("end_time"):
        missing_params.append("jam selesai")

    if missing_params:
        return {
            "workflow_status": "INVALID_REQUEST",
            "errors": state["errors"] + [f"Informasi belum lengkap: {', '.join(missing_params)}."],
        }

    try:
        res = await call_db("query_room_availability", {
            "room_name": req["room_name"],
            "booking_date": req["booking_date"],
            "start_time": req["start_time"],
            "end_time": req["end_time"],
        })
    except Exception as e:
        return {
            "workflow_status": "DATABASE_ERROR",
            "room_availability": "ERROR",
            "errors": state["errors"] + [f"Gagal memeriksa ketersediaan ruangan via basis data: {str(e)}"],
            "audit_trail": add_audit(
                state,
                "check_room",
                {"error": str(e)},
                "ERROR",
                "DATABASE_ERROR",
            ),
        }

    status = res.get("status", "ERROR")
    errors = list(state["errors"])

    if status == "AVAILABLE":
        next_status = "ROOM_AVAILABILITY_CHECK"
        decision = "PASS"
    elif status == "UNAVAILABLE":
        next_status = "ROOM_UNAVAILABLE"
        decision = "REJECT"
        conflicts = res.get("conflicts", [])
        if conflicts:
            c = conflicts[0]
            errors.append(
                f"Jadwal bentrok pada {req['booking_date']} {req['start_time']}–{req['end_time']}. "
                f"Ruangan telah terisi acara '{c.get('event_name')}' ({c.get('start_time')}–{c.get('end_time')})."
            )
        elif res.get("reason"):
            errors.append(f"Ruangan {req['room_name']} tidak tersedia: {res['reason']}")
        else:
            errors.append(f"Ruangan {req['room_name']} tidak tersedia pada jadwal tersebut.")
    else:
        next_status = "ROOM_UNAVAILABLE"
        decision = "REJECT"
        errors.append(res.get("message", f"Gagal mengecek ketersediaan ruangan {req['room_name']}."))

    selected_room = None
    if status == "AVAILABLE":
        selected_room = {"id": res.get("room_id"), "room_code": res.get("room_code")}

    return {
        "selected_room": selected_room,
        "room_availability": status if status in ("AVAILABLE", "UNAVAILABLE", "UNKNOWN", "ERROR") else "ERROR",
        "room_availability_details": res,
        "workflow_status": next_status,
        "errors": errors,
        "audit_trail": add_audit(
            state,
            "check_room",
            res,
            decision,
            next_status,
        ),
    }
