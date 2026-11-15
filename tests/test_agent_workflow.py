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


@pytest.mark.asyncio
async def test_multipurpose_add_on_equipment_flow():
    """Menguji alur pemesanan Ruang Multifungsi (PPAG-203) dengan peralatan add-on portabel."""
    prompt = (
        "Pesan Ruang Multifungsi PPAG untuk yudisium 200 orang pada 2027-01-08 "
        "jam 08:00 sampai 11:00 dengan proyektor, sound system, dan mic."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-11-15")
    initial_state["parsed_request"] = {
        "room_name": "PPAG-203",
        "event_name": "yudisium",
        "booking_date": "2027-01-08",
        "date_relative": False,
        "start_time": "08:00",
        "end_time": "11:00",
        "attendee_count": 200,
        "required_equipment": ["projector", "sound_system", "microphone"],
        "notes": "Prasmanan, 230 kursi, 12 sofa dosen",
    }

    final_state = await campusflow_agent.ainvoke(initial_state)

    # 1. Alur kerja harus berhasil penuh
    assert final_state["workflow_status"] == "COMPLETED"
    assert final_state["all_validations_passed"] is True
    assert final_state["booking_authorized"] is True
    assert final_state["booking_reference"] is not None

    # 2. Peralatan teralokasi sebagai add-on portabel aktif
    eq_results = final_state["equipment_results"]
    assert len(eq_results) >= 3
    add_ons = [eq for eq in eq_results if eq.get("is_add_on")]
    assert len(add_ons) == 3
    eq_types = {eq["equipment_type"] for eq in add_ons}
    assert {"projector", "sound_system", "microphone"}.issubset(eq_types)

    # 3. Notifikasi ke IT Support memuat instruksi pengiriman add-on
    notifs = final_state["notification_details"]["notifications"]
    it_notif = next(n for n in notifs if n.get("department_key") == "it_support" or "TI" in n.get("department", ""))
    assert it_notif is not None
    payload = it_notif.get("payload", {})
    assert "add_on_equipment" in payload
    assert len(payload["add_on_equipment"]) == 3
    assert "Prasmanan" in payload.get("notes", "")

    # 4. Tersimpan di database SQLite
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT r.room_code, b.attendee_count, b.notes FROM bookings b JOIN rooms r ON r.id = b.room_id WHERE b.booking_reference = ?",
        (final_state["booking_reference"],),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "PPAG-203"
    assert row[1] == 200


@pytest.mark.asyncio
async def test_room_under_renovation_tc05():
    """TC-05: Ruangan berstatus UNDER_RENOVATION ditolak pada validasi ketersediaan."""
    prompt = (
        "Pesan Laboratorium Komputer untuk praktikum 25 orang pada 27 September 2026 "
        "jam 08:00 sampai 10:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")
    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "ROOM_UNAVAILABLE"
    assert final_state["booking_reference"] is None
    assert any("UNDER_RENOVATION" in e for e in final_state["errors"])


@pytest.mark.asyncio
async def test_invalid_time_range_rejection_tc06():
    """TC-06: Parameter waktu tidak valid (jam mulai >= jam selesai)."""
    prompt = (
        "Pesan Ruang Kuliah 201 untuk kuliah tamu 40 orang pada 28 September 2026 "
        "jam 15:00 sampai 13:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")
    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "INVALID_REQUEST"
    assert final_state["booking_reference"] is None
    assert any("Jam mulai harus lebih awal dari jam selesai" in e for e in final_state["errors"])


@pytest.mark.asyncio
async def test_equipment_not_available_tc07():
    """TC-07: Peralatan yang diminta tidak terpasang di ruangan."""
    prompt = (
        "Pesan Ruang Kuliah 201 untuk presentasi 40 orang pada 29 September 2026 "
        "jam 10:00 sampai 12:00 dengan smartboard."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")
    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "EQUIPMENT_UNAVAILABLE"
    assert final_state["booking_reference"] is None
    assert any("smartboard" in e.lower() for e in final_state["errors"])


@pytest.mark.asyncio
async def test_room_not_found_rejection_tc08():
    """TC-08: Ruangan tidak terdaftar / fiktif."""
    prompt = (
        "Pesan Hall Serbaguna Lantai 9 untuk reuni 50 orang pada 30 September 2026 "
        "jam 10:00 sampai 12:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")
    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] in ("INVALID_REQUEST", "ROOM_UNAVAILABLE")
    assert final_state["booking_reference"] is None


@pytest.mark.asyncio
async def test_back_to_back_valid_booking_tc09():
    """TC-09: Waktu bersinggungan sah (back-to-back boundary)."""
    # Di seed.sql: SR-101 terisi 13:00 - 15:00 pada 2026-09-23.
    # Kita pesan 15:00 - 17:00 (tepat saat acara sebelumnya selesai).
    prompt = (
        "Pesan Ruang Seminar 101 untuk koordinasi riset 20 orang pada 23 September 2026 "
        "jam 15:00 sampai 17:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")
    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] == "COMPLETED"
    assert final_state["booking_reference"] is not None
    assert final_state["booking_authorized"] is True


@pytest.mark.asyncio
async def test_ambiguous_relative_date_confirmation_tc10():
    """TC-10: Tanggal relatif memerlukan konfirmasi sebelum lanjut (Human-in-the-Loop)."""
    prompt = (
        "Pesan Auditorium Utama untuk briefing 50 orang Selasa depan "
        "jam 09:00 sampai 11:00."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21", date_confirmed=False)
    final_state = await campusflow_agent.ainvoke(initial_state)

    assert final_state["workflow_status"] in ("INVALID_REQUEST", "NEEDS_CLARIFICATION")
    assert final_state["booking_reference"] is None
    assert "date_confirmation" in final_state["missing_fields"]


@pytest.mark.asyncio
async def test_duplicate_booking_rejection():
    """Pencegahan pemesanan ganda (duplicate booking) pada slot waktu yang sama."""
    prompt = (
        "Pesan Ruang Seminar 101 untuk sesi 1 20 orang pada 25 September 2026 "
        "jam 13:00 sampai 15:00."
    )
    # Pemesanan pertama berhasil
    state1 = new_state(prompt, requester="FAC-001", today="2026-09-21")
    res1 = await campusflow_agent.ainvoke(state1)
    assert res1["workflow_status"] == "COMPLETED"
    assert res1["booking_reference"] is not None

    # Pemesanan kedua dengan slot waktu dan ruangan yang sama persis ditolak
    state2 = new_state(prompt, requester="FAC-002", today="2026-09-21")
    res2 = await campusflow_agent.ainvoke(state2)
    assert res2["workflow_status"] == "ROOM_UNAVAILABLE"
    assert res2["booking_reference"] is None


@pytest.mark.asyncio
async def test_notification_failure_graceful_handling(monkeypatch):
    """Test 7 SRS: Booking sukses di DB, namun pengiriman notifikasi gagal (graceful degradation)."""
    prompt = (
        "Pesan auditorium utama untuk workshop AI 100 orang pada 23 September 2026 "
        "jam 13:00 sampai 15:00, pastikan proyektor berfungsi."
    )
    initial_state = new_state(prompt, requester="FAC-001", today="2026-09-21")

    # Simulasikan kegagalan panggilan notifikasi MCP
    async def mock_call_notification(tool_name, arguments):
        return {"status": "FAILED", "error": "Simulated timeout in notification dispatch"}

    import sys
    monkeypatch.setattr(
        sys.modules["src.agent.nodes.send_notification"],
        "call_notification",
        mock_call_notification,
    )

    final_state = await campusflow_agent.ainvoke(initial_state)

    # Invariant penting: Booking di database tetap sah dan tidak dibatalkan
    assert final_state["booking_reference"] is not None
    assert final_state["booking_reference"].startswith("BK-2026-")
    assert final_state["notification_status"] == "FAILED"
    assert final_state["workflow_status"] == "COMPLETED_PARTIAL"

    # Verifikasi reservasi memang tersimpan di SQLite
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT status FROM bookings WHERE booking_reference = ?",
        (final_state["booking_reference"],),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "CONFIRMED"

    # Verifikasi jejak audit mencatat keputusan PARTIAL
    audit_steps = {a["step_name"]: a for a in final_state["audit_trail"]}
    assert "send_notification" in audit_steps
    assert audit_steps["send_notification"]["decision"] == "PARTIAL"



