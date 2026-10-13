"""
Simpul validate_requirements
============================
Validasi deterministik terhadap field yang sudah diurai (tanpa MCP):
1. Tanggal relatif ("Selasa depan") harus dikonfirmasi pengguna (REQ-NLU-04).
2. Tanggal tidak boleh sudah lewat terhadap state["today"].
3. start_time harus lebih awal dari end_time (REQ-NLU-03).
4. Jumlah peserta harus positif.

Format tanggal/jam sudah dijamin parser (ISO dan HH:MM berpadding nol), sehingga
perbandingan string jam valid.
"""

from datetime import date

from src.agent.state import AgentState, add_audit

_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def validate_requirements(state: AgentState) -> dict:
    req = state["parsed_request"]
    booking_date = date.fromisoformat(req["booking_date"])
    errors = list(state["errors"])
    missing = list(state["missing_fields"])

    if req["date_relative"] and not state["date_confirmed"]:
        missing.append("date_confirmation")
        errors.append(
            f"Tanggal '{req['date_text']}' dihitung sebagai {_HARI[booking_date.weekday()]}, "
            f"{booking_date.isoformat()}. Konfirmasi tanggal ini atau sebutkan tanggal eksplisit."
        )
    if booking_date < date.fromisoformat(state["today"]):
        errors.append(f"Tanggal {booking_date.isoformat()} sudah lewat.")
    if req["start_time"] >= req["end_time"]:
        errors.append("Jam mulai harus lebih awal dari jam selesai.")
    if req["attendee_count"] <= 0:
        errors.append("Jumlah peserta harus lebih dari 0.")

    invalid = len(errors) > len(state["errors"])
    status = "INVALID_REQUEST" if invalid else "REQUIREMENTS_VALIDATED"
    return {
        "missing_fields": missing,
        "errors": errors,
        "workflow_status": status,
        "audit_trail": add_audit(
            state,
            "validate_requirements",
            {"booking_date": req["booking_date"], "date_relative": req["date_relative"],
             "date_confirmed": state["date_confirmed"], "errors": errors[len(state["errors"]):]},
            "REJECT" if invalid else "PASS",
            status,
        ),
    }
