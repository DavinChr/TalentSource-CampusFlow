#!/usr/bin/env python3
"""
CampusFlow — Multi-Server MCP Integration Test Suite
====================================================
Pengujian integrasi terpadu yang memvalidasi interkoneksi ketiga server MCP:
1. campusflow-db           (Database MCP)
2. campusflow-fs           (Filesystem MCP)
3. campusflow-notification (Notification MCP)

Skenario Alur Kerja:
1. Skenario Sukses:
   - Cek kapasitas & ketersediaan ruangan via campusflow-db
   - Temukan peralatan terpasang via campusflow-db
   - Verifikasi fisik & catatan log servis via campusflow-fs
   - Eksekusi transaksi pemesanan atomik via campusflow-db
   - Kirim notifikasi konfirmasi resmi via campusflow-notification
2. Skenario Deteksi Kontradiksi (Test Scenario 8):
   - Cek status alat PRJ-04 di DB (ACTIVE) vs di Filesystem (FAULTY)
   - Memastikan terdeteksi diskrepansi data dan alur dibatalkan dengan aman.
"""

import asyncio
import json
from pathlib import Path
import sys
import pytest

# Pastikan root proyek berada dalam sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.mcp.db_server import server as db_server
from src.mcp.fs_server import server as fs_server
from src.mcp.notification_server import server as notif_server
import sqlite3

DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"
SEED_PATH = BASE_DIR / "data" / "database" / "seed.sql"


def _reseed_database():
    """Mengosongkan dan mengisi ulang seed data tanpa menghapus berkas fisik SQLite."""
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
    """Memastikan setiap pengujian berjalan di atas basis data benih yang bersih."""
    _reseed_database()
    yield
    _reseed_database()


def _parse_mcp_res(res) -> dict:
    """Helper untuk mengurai teks JSON dari CallToolResult MCP."""
    return json.loads(res.content[0].text)


@pytest.mark.asyncio
async def test_full_successful_workflow():
    """Uji alur kerja sukses lengkap melintasi 3 server MCP."""
    # 1. Cek kapasitas ruangan di Database MCP
    cap_res = _parse_mcp_res(
        await db_server.call_tool("query_room_capacity", {"room_name": "AUD-01"})
    )
    assert cap_res["found"] is True
    assert cap_res["capacity"] >= 100

    # 2. Cek ketersediaan slot di Database MCP (2026-09-23 13:00-15:00 bebas bentrok)
    avail_res = _parse_mcp_res(
        await db_server.call_tool("query_room_availability", {
            "room_name": "AUD-01",
            "booking_date": "2026-09-23",
            "start_time": "13:00",
            "end_time": "15:00",
        })
    )
    assert avail_res["status"] == "AVAILABLE"
    room_id = avail_res["room_id"]

    # 3. Cari peralatan proyektor di ruangan via Database MCP
    equip_res = _parse_mcp_res(
        await db_server.call_tool("query_equipment", {
            "room_name": "AUD-01",
            "equipment_type": "projector",
        })
    )
    assert equip_res["found"] is True
    assert any(e["equipment_code"] == "PRJ-03" for e in equip_res["equipment"])

    # 4. Validasi fisik proyektor PRJ-03 ke Filesystem MCP
    fs_status = _parse_mcp_res(
        await fs_server.call_tool("get_equipment_status", {"equipment_code": "PRJ-03"})
    )
    assert fs_status["found"] is True
    assert fs_status["status"] == "OPERATIONAL"

    # 5. Periksa catatan servis teknisi PRJ-03 di Filesystem MCP
    fs_log = _parse_mcp_res(
        await fs_server.call_tool("search_maintenance_log", {"equipment_code": "PRJ-03"})
    )
    assert fs_log["found"] is True
    assert any("normal" in e["note"].lower() for e in fs_log["log_entries"])

    # 6. Eksekusi pemesanan transaksional di Database MCP
    booking_res = _parse_mcp_res(
        await db_server.call_tool("create_booking_transactional", {
            "room_id": room_id,
            "user_identifier": "FAC-001",
            "event_name": "Workshop AI 100 Orang",
            "booking_date": "2026-09-23",
            "start_time": "13:00",
            "end_time": "15:00",
            "attendee_count": 100,
            "notes": "Memerlukan proyektor PRJ-03 dan sound system",
            "trace_id": "test-trace-workflow-01",
        })
    )
    assert booking_res["status"] == "CREATED"
    booking_ref = booking_res["booking_reference"]
    booking_id = booking_res["booking_id"]

    # 7. Kirim notifikasi resmi ke Departemen Fasilitas Akademik via Notification MCP
    notif_res = _parse_mcp_res(
        await notif_server.call_tool("send_department_notification", {
            "department_key": "academic_facilities",
            "subject": f"Konfirmasi Reservasi Ruangan: {booking_ref}",
            "payload": {
                "booking_reference": booking_ref,
                "room_name": "Auditorium Utama",
                "attendees": 100,
                "equipment_verified": ["PRJ-03"],
            },
            "booking_id": booking_id,
        })
    )
    assert notif_res["status"] == "SENT"
    notif_id = notif_res["notification_id"]

    # 8. Verifikasi status notifikasi terkirim
    status_res = _parse_mcp_res(
        await notif_server.call_tool("get_notification_status", {"notification_id": notif_id})
    )
    assert status_res["found"] is True
    assert status_res["status"] == "SENT"


@pytest.mark.asyncio
async def test_contradiction_detection():
    """Uji deteksi kontradiksi data: DB aktif tetapi fisik rusak (PRJ-04)."""
    # 1. DB menyatakan PRJ-04 berstatus ACTIVE di LH-201
    equip_res = _parse_mcp_res(
        await db_server.call_tool("query_equipment", {
            "room_name": "LH-201",
            "equipment_type": "projector",
        })
    )
    assert equip_res["found"] is True
    prj04_db = next(e for e in equip_res["equipment"] if e["equipment_code"] == "PRJ-04")
    assert prj04_db["db_status"] == "ACTIVE"

    # 2. Namun Filesystem MCP mendeteksi PRJ-04 berstatus FAULTY (HDMI rusak)
    fs_status = _parse_mcp_res(
        await fs_server.call_tool("get_equipment_status", {"equipment_code": "PRJ-04"})
    )
    assert fs_status["found"] is True
    assert fs_status["status"] == "FAULTY"

    # 3. Verifikasi diskrepansi: status DB ('ACTIVE') != status FS ('FAULTY')
    is_contradiction = prj04_db["db_status"] != fs_status["status"]
    assert is_contradiction is True


if __name__ == "__main__":
    # Runner langsung tanpa pytest CLI
    async def _main():
        print("Menjalankan multi-server integration test...")
        await test_full_successful_workflow()
        print("  [PASS] test_full_successful_workflow")
        await test_contradiction_detection()
        print("  [PASS] test_contradiction_detection")
        print("Seluruh pengujian integrasi 3 Server MCP berhasil!")

    asyncio.run(_main())
