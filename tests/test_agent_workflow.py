"""
CampusFlow — End-to-End LangGraph Agent Workflow Tests
======================================================
Pengujian otomatis alur kerja graf status agen LangGraph (Phase 5):
1. Test Jalur Sukses Penuh (TC-01):
   - Ruangan kosong, kapasitas cukup, alat OPERATIONAL.
   - Transaksi database berhasil (booking_reference terbentuk).
   - Notifikasi multi-departemen terkirim ke academic_facilities dan it_support.
2. Test Human-in-the-Loop (Klarifikasi Jam Hilang):
   - Instruksi tanpa jam tidak berhalusinasi, graf berhenti pada status NEEDS_CLARIFICATION.
3. Test Deteksi Bentrok Waktu (TC-02):
   - Deteksi slot terisi, graf berhenti pada status ROOM_UNAVAILABLE tanpa menulis ke DB.
4. Test Kapasitas Melebihi Batas (TC-03):
   - Deteksi over-capacity, graf berhenti pada INSUFFICIENT_CAPACITY.
5. Test Kontradiksi Bukti Fisik Alat (INV-004):
   - DB mencatat ACTIVE namun FS mencatat FAULTY, graf berhenti pada WORKFLOW_ABORTED.
"""

from datetime import date
import sqlite3
from pathlib import Path
import pytest

from src.agent.graph import campusflow_agent
from src.agent.state import new_state

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"
SEED_PATH = BASE_DIR / "data" / "database" / "seed.sql"


def _reseed_database():
    """Mengosongkan dan mengisi ulang seed data sebelum tiap tes."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        for tbl in ("audit_logs", "bookings", "room_equipment", "equipment", "rooms", "buildings", "users"):
            conn.execute(f"DELETE FROM {tbl};")
        conn.execute("DELETE FROM sqlite_sequence;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    _reseed_database()
    yield
    _reseed_database()


@pytest.mark.asyncio
async def test_full_success_workflow_tc01():
    """TC-01: Jalur sukses penuh dengan proyektor di Auditorium Utama."""
    # Slot 13:00 - 15:00 pada 2026-09-23 kosong di AUD-01 (pagi diisi seminar lain)
    prompt = (
        "Pesan auditorium utama untuk workshop AI 100 orang pada 23 September 2026 "
        "jam 13:00 sampai 15:00, pastikan proyektor berfungsi."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")

    final_state = await campusflow_agent.ainvoke(initial_state)

    # Verifikasi status akhir alur kerja
    assert final_state["workflow_status"] == "COMPLETED"
    assert final_state["all_validations_passed"] is True
    assert final_state["booking_authorized"] is True

    # Verifikasi nomor referensi pemesanan
    assert final_state["booking_reference"] is not None
    assert final_state["booking_reference"].startswith("BK-2026-")

    # Verifikasi notifikasi resmi terkirim
    assert final_state["notification_status"] == "SENT"
    notifs = final_state["notification_details"]["notifications"]
    assert len(notifs) == 2  # academic_facilities dan it_support
    assert any(n.get("department_key") == "academic_facilities" or "Fasilitas" in n.get("department", "") for n in notifs)
    assert any(n.get("department_key") == "it_support" or "TI" in n.get("department", "") for n in notifs)

    # Verifikasi integritas audit trail
    audit_names = [a["step_name"] for a in final_state["audit_trail"]]
    assert "parse_request" in audit_names
    assert "validate_requirements" in audit_names
    assert "check_room" in audit_names
    assert "validate_capacity" in audit_names
    assert "check_equipment" in audit_names
    assert "authorize_booking" in audit_names
    assert "create_booking" in audit_names
    assert "send_notification" in audit_names


@pytest.mark.asyncio
async def test_human_in_the_loop_missing_time():
    """Human-in-the-Loop: Permintaan tanpa jam harus meminta klarifikasi, bukan menebak."""
    prompt = "Pesan auditorium utama untuk workshop AI 100 orang pada 23 September 2026, pastikan proyektor berfungsi."
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")

    final_state = await campusflow_agent.ainvoke(initial_state)

    # Graf harus berhenti di simpul parse_request (Fast-Fail / Clarify)
    assert final_state["workflow_status"] in ("INVALID_REQUEST", "NEEDS_CLARIFICATION")
    assert final_state["booking_id"] is None
    assert final_state["booking_reference"] is None
    assert "start_time" in final_state["missing_fields"]
    assert "end_time" in final_state["missing_fields"]


@pytest.mark.asyncio
async def test_schedule_conflict_rejection_tc02():
    """TC-02: Bentrok jadwal harus menolak reservasi tanpa komit database."""
    # AUD-01 sudah terisi pada 2026-09-23 jam 08:00 - 12:00 oleh Seminar Nasional AI
    prompt = (
        "Pesan auditorium utama untuk kuliah tamu 50 orang pada 23 September 2026 "
        "jam 09:00 sampai 11:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")

    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "ROOM_UNAVAILABLE"
    assert final_state["booking_reference"] is None
    assert any("bentrok" in e.lower() for e in final_state["errors"])


@pytest.mark.asyncio
async def test_capacity_exceeded_rejection_tc03():
    """TC-03: Kapasitas ruangan tidak mencukupi peserta."""
    # CR-301 berkapasitas 20 orang, diminta untuk 50 orang
    prompt = (
        "Pesan ruang konferensi eksekutif untuk rapat umum 50 orang pada 23 September 2026 "
        "jam 13:00 sampai 15:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")

    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "INSUFFICIENT_CAPACITY"
    assert final_state["booking_reference"] is None
    assert any("tidak mencukupi" in e.lower() for e in final_state["errors"])


@pytest.mark.asyncio
async def test_evidence_contradiction_aborts_workflow():
    """Invariant INV-004: Kontradiksi status DB vs Filesystem membatalkan alur kerja."""
    # Ruang Kuliah 201 (LH-201) memakai PRJ-04 (DB: ACTIVE, tapi log FS: FAULTY)
    prompt = (
        "Pesan ruang kuliah 201 untuk kuliah umum 40 orang pada 23 September 2026 "
        "jam 13:00 sampai 15:00, pastikan proyektor berfungsi."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")

    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "WORKFLOW_ABORTED"
    assert final_state["booking_reference"] is None
    assert final_state["equipment_status"] == "CONFLICT"
    assert any("diskrepansi" in e.lower() or "kontradiksi" in e.lower() for e in final_state["errors"])


@pytest.mark.asyncio
async def test_booking_with_custom_notes_persisted():
    """Memastikan catatan khusus (special notes) disimpan ke DB dan dikirim via notifikasi."""
    prompt = (
        "Pesan auditorium utama untuk workshop AI 100 orang pada 23 September 2026 "
        "jam 13:00 sampai 15:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")
    from src.agent.parser import parse_request_text
    from datetime import date as dt
    parsed = parse_request_text(prompt, dt(2026, 9, 21))
    parsed["notes"] = "Request jam 1 siang tidak ada kursi, meja tamu 3 dan 6 kursi"
    initial_state["parsed_request"] = parsed

    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "COMPLETED"
    ref = final_state["booking_reference"]
    assert ref is not None

    # Verifikasi kolom notes di database SQLite
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT notes FROM bookings WHERE booking_reference = ?", (ref,)).fetchone()
    conn.close()
    assert row is not None
    assert "tidak ada kursi" in row[0]


@pytest.mark.asyncio
async def test_unpar_booking_flow_end_to_end():
    """Menguji alur pemesanan fasilitas riil kampus UNPAR (PPAG-202 dengan proyektor)."""
    prompt = (
        "Pesan PPAG-202 untuk perkuliahan ekonomi 45 orang pada 2026-10-15 "
        "jam 09:00 sampai 11:00, pastikan proyektor berfungsi."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-10-12")
    initial_state["parsed_request"] = {
        "room_name": "PPAG-202",
        "event_name": "perkuliahan ekonomi",
        "booking_date": "2026-10-15",
        "date_relative": False,
        "start_time": "09:00",
        "end_time": "11:00",
        "attendee_count": 45,
        "required_equipment": ["projector"],
        "notes": "Kursi diatur model U-shape.",
    }

    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "COMPLETED"
    assert final_state["booking_reference"] is not None
    assert final_state["selected_room"]["room_code"] == "PPAG-202"
    assert final_state["booking_authorized"] is True

    # Verifikasi tersimpan di DB SQLite
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT r.room_code, b.notes FROM bookings b JOIN rooms r ON r.id = b.room_id WHERE b.booking_reference = ?",
        (final_state["booking_reference"],),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "PPAG-202"
    assert "U-shape" in row[1]


