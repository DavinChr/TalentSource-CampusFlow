"""
Simpul parse_request
====================
Mengekstrak entitas pemesanan dari teks bebas lewat parser deterministik.
Tidak memanggil MCP. Bila ada field wajib yang hilang atau ambigu, status
langsung INVALID_REQUEST dan graf berhenti tanpa menyentuh database (Fast-Fail).
"""

from datetime import date

from src.agent.parser import parse_request_text
from src.agent.state import AgentState, add_audit

# Field wajib -> label untuk pesan ke pengguna.
FIELD_LABELS = {
    "room_name": "ruangan",
    "event_name": "nama acara",
    "booking_date": "tanggal",
    "start_time": "jam mulai",
    "end_time": "jam selesai",
    "attendee_count": "jumlah peserta",
}


def parse_request(state: AgentState) -> dict:
    if state.get("parsed_request"):
        fields = dict(state["parsed_request"])
        missing = [k for k in FIELD_LABELS if fields.get(k) is None]
        ambiguities = []
    else:
        fields = parse_request_text(state["request_raw"], date.fromisoformat(state["today"]))
        ambiguities = fields.pop("ambiguities")
        missing = [k for k in FIELD_LABELS if fields[k] is None]

    errors = list(state["errors"])
    if missing:
        errors.append("Data belum lengkap: " + ", ".join(FIELD_LABELS[k] for k in missing) + ".")
    errors += ambiguities

    invalid = bool(missing or ambiguities)
    status = "INVALID_REQUEST" if invalid else "REQUEST_PARSED"
    return {
        "parsed_request": fields,
        "missing_fields": missing,
        "errors": errors,
        "workflow_status": status,
        "audit_trail": add_audit(
            state,
            "parse_request",
            {"parsed": fields, "missing": missing, "ambiguities": ambiguities},
            "REJECT" if invalid else "PASS",
            status,
        ),
    }
