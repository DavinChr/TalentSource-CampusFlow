"""
Simpul authorize_booking
========================
Verifikasi fisik peralatan via berkas filesystem (campusflow-fs)
dan penegakan penalaran berbasis bukti (Evidence-Based Reasoning):
- Memeriksa status fisik peralatan di berkas operasional (get_equipment_status).
- Mendeteksi kontradiksi data: Jika DB mencatat ACTIVE namun berkas fisik mencatat FAULTY/UNDER_MAINTENANCE -> WORKFLOW_ABORTED (INV-004).
- Jika fisik OPERATIONAL dan seluruh pemeriksaan lulus -> BOOKING_AUTHORIZATION (all_validations_passed = True, booking_authorized = True).
"""

from typing import Dict, Any
from src.agent.state import AgentState, add_audit
from src.agent.mcp_client import call_fs


async def authorize_booking(state: AgentState) -> Dict[str, Any]:
    equipment_results = state.get("equipment_results") or []
    errors = list(state["errors"])

    # Jika tidak ada alat yang diminta, langsung lolos otorisasi
    if not equipment_results:
        return {
            "all_validations_passed": True,
            "booking_authorized": True,
            "workflow_status": "BOOKING_AUTHORIZATION",
            "audit_trail": add_audit(
                state,
                "authorize_booking",
                {"message": "Tidak ada peralatan yang memerlukan verifikasi fisik."},
                "PASS",
                "BOOKING_AUTHORIZATION",
            ),
        }

    physical_checks = []
    abort_due_to_contradiction = False
    hardware_faulty = False
    primary_status = "OPERATIONAL"

    for eq in equipment_results:
        code = eq.get("equipment_code")
        db_status = eq.get("db_status") or eq.get("status")

        fs_res = await call_fs("get_equipment_status", {"equipment_code": code})
        physical_checks.append({"db": eq, "fs": fs_res})

        fs_status = fs_res.get("status", "UNKNOWN")

        # Deteksi kontradiksi antara DB dan berkas fisik
        if db_status == "ACTIVE" and fs_status in ("FAULTY", "UNDER_MAINTENANCE"):
            abort_due_to_contradiction = True
            primary_status = "CONFLICT"
            errors.append(
                f"Diskrepansi bukti terdeteksi untuk alat {code} ({eq.get('equipment_name')}): "
                f"Basis data mencatat status '{db_status}', namun berkas pemeliharaan fisik mencatat '{fs_status}'."
            )
        elif fs_status in ("FAULTY", "UNDER_MAINTENANCE"):
            hardware_faulty = True
            primary_status = fs_status
            errors.append(
                f"Peralatan {code} ({eq.get('equipment_name')}) dalam kondisi {fs_status} berdasarkan log pemeliharaan."
            )
        elif fs_status == "UNKNOWN":
            primary_status = "UNKNOWN"
            errors.append(f"Status fisik peralatan {code} tidak dapat diverifikasi (UNKNOWN).")

    if abort_due_to_contradiction:
        next_status = "WORKFLOW_ABORTED"
        decision = "ABORT"
        authorized = False
    elif hardware_faulty:
        next_status = "EQUIPMENT_UNAVAILABLE"
        decision = "REJECT"
        authorized = False
    elif primary_status == "UNKNOWN":
        next_status = "EQUIPMENT_STATUS_UNKNOWN"
        decision = "REJECT"
        authorized = False
    else:
        next_status = "BOOKING_AUTHORIZATION"
        decision = "PASS"
        authorized = True

    return {
        "equipment_status": primary_status,
        "equipment_status_details": {"checks": physical_checks},
        "all_validations_passed": authorized,
        "booking_authorized": authorized,
        "workflow_status": next_status,
        "errors": errors,
        "audit_trail": add_audit(
            state,
            "authorize_booking",
            {"checks": physical_checks, "contradiction": abort_due_to_contradiction},
            decision,
            next_status,
        ),
    }
