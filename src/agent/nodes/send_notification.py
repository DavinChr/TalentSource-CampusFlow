"""
Simpul send_notification
========================
Pengiriman notifikasi multi-departemen via campusflow-notification:
- academic_facilities : selalu dikirimi notifikasi reservasi ruangan berhasil.
- it_support          : dikirimi notifikasi persiapan alat jika ada required_equipment.
- Jika semua sukses  -> workflow_status = COMPLETED.
- Jika ada yang gagal -> workflow_status = COMPLETED_PARTIAL (reservasi tetap sah).
"""

import os
from typing import Dict, Any
from src.agent.state import AgentState, add_audit
from src.agent.mcp_client import call_notification


async def send_notification(state: AgentState) -> Dict[str, Any]:
    req = state["parsed_request"]
    booking_ref = state.get("booking_reference") or "UNKNOWN"
    it_dept_code = os.getenv("NOTIFICATION_IT_DEPT", "it_support")

    notifications_sent = []
    errors = list(state["errors"])
    all_success = True

    # 1. Notifikasi ke Fasilitas Akademik
    fac_payload = {
        "booking_reference": booking_ref,
        "room_name": req["room_name"],
        "event_name": req["event_name"],
        "date": req["booking_date"],
        "time": f"{req['start_time']} - {req['end_time']}",
        "attendee_count": req["attendee_count"],
        "requester": state["requester"],
        "notes": req.get("notes"),
    }
    fac_res = await call_notification("send_department_notification", {
        "department_key": "academic_facilities",
        "subject": f"Konfirmasi Reservasi Ruangan: {booking_ref}",
        "payload": fac_payload,
    })
    fac_res["payload"] = fac_payload
    fac_res["subject"] = f"Konfirmasi Reservasi Ruangan: {booking_ref}"
    notifications_sent.append(fac_res)
    if fac_res.get("status") != "SENT":
        all_success = False
        errors.append("Gagal mengirim notifikasi ke academic_facilities.")

    # 2. Notifikasi ke IT Support & Multimedia (jika ada peralatan)
    if req.get("required_equipment"):
        add_on_list = [
            f"{eq.get('equipment_name')} ({eq.get('equipment_code')})"
            for eq in (state.get("equipment_results") or [])
            if eq.get("is_add_on")
        ]
        it_payload = {
            "booking_reference": booking_ref,
            "room_name": req["room_name"],
            "equipment": req["required_equipment"],
            "date": req["booking_date"],
            "time": f"{req['start_time']} - {req['end_time']}",
            "notes": req.get("notes"),
        }
        subject = f"Permintaan Persiapan Multimedia: {booking_ref}"
        if add_on_list:
            it_payload["add_on_equipment"] = add_on_list
            it_payload["dispatch_notes"] = "Peralatan add-on portabel perlu dikirim dan disiapkan di ruangan oleh tim IT Support."
            subject = f"Permintaan Persiapan & Pengiriman Add-On Multimedia: {booking_ref}"

        it_res = await call_notification("send_department_notification", {
            "department_key": it_dept_code,
            "subject": subject,
            "payload": it_payload,
        })
        it_res["payload"] = it_payload
        it_res["subject"] = subject
        notifications_sent.append(it_res)
        if it_res.get("status") != "SENT":
            all_success = False
            errors.append(f"Gagal mengirim notifikasi ke {it_dept_code}.")

    if all_success:
        next_status = "COMPLETED"
        notif_status = "SENT"
        decision = "PASS"
    else:
        next_status = "COMPLETED_PARTIAL"
        notif_status = "FAILED"
        decision = "PARTIAL"

    return {
        "notification_status": notif_status,
        "notification_details": {"notifications": notifications_sent},
        "workflow_status": next_status,
        "errors": errors,
        "audit_trail": add_audit(
            state,
            "send_notification",
            {"notifications": notifications_sent},
            decision,
            next_status,
        ),
    }
