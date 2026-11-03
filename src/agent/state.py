"""
AgentState CampusFlow
=====================
Struktur status yang dibawa antar simpul graf, mengikuti docs/state-machine.md.

Aturan pemakaian: simpul TIDAK mengubah state yang diterima. Setiap simpul
mengembalikan dict berisi hanya key yang berubah (pola update LangGraph).
Daftar (errors, audit_trail) tidak memakai reducer, jadi simpul wajib
mengembalikan daftar utuh yang sudah ditambah (lihat add_audit).

Selisih dengan docs/state-machine.md (sengaja):
- `booking_id` bertipe int (sesuai kolom DB) dan ada `booking_reference` (BK-YYYY-NNN).
- Tambahan: requester, today, date_confirmed, missing_fields.
"""

from datetime import date, datetime, timezone
from typing import Any, List, Literal, Optional, TypedDict
import uuid

WorkflowStatus = Literal[
    "REQUEST_RECEIVED", "REQUEST_PARSED", "REQUIREMENTS_VALIDATED",
    "ROOM_SEARCH", "ROOM_AVAILABILITY_CHECK", "CAPACITY_VALIDATION",
    "EQUIPMENT_CHECK", "EQUIPMENT_STATUS_CHECK", "BOOKING_AUTHORIZATION",
    "BOOKING_WRITE", "NOTIFICATION", "COMPLETED", "COMPLETED_PARTIAL",
    "INVALID_REQUEST", "ROOM_UNAVAILABLE", "INSUFFICIENT_CAPACITY",
    "EQUIPMENT_UNAVAILABLE", "EQUIPMENT_STATUS_UNKNOWN",
    "WORKFLOW_ABORTED", "DATABASE_ERROR", "NOTIFICATION_ERROR",
    "NEEDS_CLARIFICATION",
]

# UNKNOWN tidak boleh disamakan dengan AVAILABLE (INV-002).
ResourceStatus = Literal["AVAILABLE", "UNAVAILABLE", "UNKNOWN", "ERROR"]
EquipmentStatus = Literal[
    "OPERATIONAL", "UNDER_MAINTENANCE", "FAULTY", "UNKNOWN", "CONFLICT", "NOT_FOUND"
]
NotificationStatus = Literal["SENT", "FAILED", "PENDING", "NOT_REQUIRED"]


class BookingRequest(TypedDict):
    """Hasil penguraian teks pengguna. Field yang tidak ditemukan bernilai None."""
    room_name: Optional[str]          # kode ruangan kanonik, mis. "AUD-01"
    event_name: Optional[str]
    booking_date: Optional[str]       # YYYY-MM-DD
    date_relative: bool               # True bila tanggal berasal dari kata relatif ("besok", "Selasa depan")
    date_text: Optional[str]          # teks asli penyebut tanggal, untuk pesan konfirmasi
    start_time: Optional[str]         # HH:MM
    end_time: Optional[str]           # HH:MM
    attendee_count: Optional[int]
    required_equipment: List[str]     # nilai enum equipment_type, mis. ["projector"]


class ValidationResult(TypedDict):
    passed: bool
    reason: Optional[str]
    details: Optional[Any]


class AuditStep(TypedDict):
    step_index: int
    timestamp: str                    # ISO 8601 UTC
    step_name: str
    evidence: Any                     # bukti mentah dari parser/alat MCP
    decision: str
    next_state: str


class AgentState(TypedDict):
    # Masukan
    request_raw: str
    requester: str                    # employee_id pemohon (dari sesi, bukan dari teks)
    today: str                        # YYYY-MM-DD; dasar penghitungan tanggal relatif
    date_confirmed: bool              # True bila pengguna sudah mengonfirmasi tanggal relatif

    # Hasil parsing
    parsed_request: Optional[BookingRequest]
    missing_fields: List[str]

    # Ruangan
    candidate_rooms: List[dict]
    selected_room: Optional[dict]

    # Hasil validasi
    room_availability: Optional[ResourceStatus]
    room_availability_details: Optional[dict]
    capacity_validation: Optional[ValidationResult]
    equipment_results: Optional[List[dict]]
    equipment_status: Optional[EquipmentStatus]
    equipment_status_details: Optional[dict]
    all_validations_passed: bool
    booking_authorized: bool

    # Hasil booking
    booking_id: Optional[int]
    booking_reference: Optional[str]

    # Notifikasi
    notification_status: Optional[NotificationStatus]
    notification_details: Optional[dict]

    # Kontrol alur
    workflow_status: WorkflowStatus
    clarification_message: Optional[str]
    errors: List[str]
    trace_id: str
    audit_trail: List[AuditStep]


def new_state(
    request_raw: str,
    requester: str,
    today: Optional[str] = None,
    date_confirmed: bool = False,
) -> AgentState:
    """Membuat state awal (status REQUEST_RECEIVED)."""
    return {
        "request_raw": request_raw,
        "requester": requester,
        "today": today or date.today().isoformat(),
        "date_confirmed": date_confirmed,
        "parsed_request": None,
        "missing_fields": [],
        "candidate_rooms": [],
        "selected_room": None,
        "room_availability": None,
        "room_availability_details": None,
        "capacity_validation": None,
        "equipment_results": None,
        "equipment_status": None,
        "equipment_status_details": None,
        "all_validations_passed": False,
        "booking_authorized": False,
        "booking_id": None,
        "booking_reference": None,
        "notification_status": None,
        "notification_details": None,
        "workflow_status": "REQUEST_RECEIVED",
        "clarification_message": None,
        "errors": [],
        "trace_id": f"trace-{uuid.uuid4().hex[:12]}",
        "audit_trail": [],
    }


def add_audit(
    state: AgentState, step_name: str, evidence: Any, decision: str, next_state: str
) -> List[AuditStep]:
    """Mengembalikan audit_trail baru (state asli tidak diubah)."""
    step: AuditStep = {
        "step_index": len(state["audit_trail"]) + 1,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step_name": step_name,
        "evidence": evidence,
        "decision": decision,
        "next_state": next_state,
    }
    return state["audit_trail"] + [step]
