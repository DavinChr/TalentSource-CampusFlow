"""
Simpul check_equipment
======================
Memeriksa ketersediaan dan penugasan peralatan di ruangan via campusflow-db:
- Memanggil query_equipment untuk setiap required_equipment.
- Jika ada alat wajib yang tidak terdaftar di ruangan -> tolak (EQUIPMENT_UNAVAILABLE).
- Jika semua alat terdaftar -> lanjut ke verifikasi fisik alat di filesystem (authorize_booking).
"""

from typing import Dict, Any, List
from src.agent.state import AgentState, add_audit
from src.agent.mcp_client import call_db


async def check_equipment(state: AgentState) -> Dict[str, Any]:
    req = state["parsed_request"]
    required_equipment = req.get("required_equipment", [])

    # Jika tidak ada peralatan wajib yang diminta, langsung lolos
    if not required_equipment:
        return {
            "equipment_results": [],
            "workflow_status": "EQUIPMENT_CHECK",
            "audit_trail": add_audit(
                state,
                "check_equipment",
                {"required_equipment": [], "message": "Tidak ada peralatan khusus yang diminta."},
                "PASS",
                "EQUIPMENT_CHECK",
            ),
        }

    room_name = req["room_name"]
    equipment_results: List[Dict[str, Any]] = []
    errors = list(state["errors"])
    all_found = True

    for eq_type in required_equipment:
        res = await call_db("query_equipment", {
            "room_name": room_name,
            "equipment_type": eq_type,
        })
        items = res.get("equipment", [])
        if not res.get("found", False) or not items:
            all_found = False
            errors.append(f"Peralatan '{eq_type}' tidak tersedia di ruangan {room_name} dan tidak dapat disediakan sebagai unit portabel/add-on.")
        else:
            equipment_results.extend(items)

    if all_found:
        next_status = "EQUIPMENT_CHECK"
        decision = "PASS"
    else:
        next_status = "EQUIPMENT_UNAVAILABLE"
        decision = "REJECT"

    return {
        "equipment_results": equipment_results,
        "workflow_status": next_status,
        "errors": errors,
        "audit_trail": add_audit(
            state,
            "check_equipment",
            equipment_results,
            decision,
            next_status,
        ),
    }
