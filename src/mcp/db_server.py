#!/usr/bin/env python3
"""
CampusFlow — Database MCP Server (campusflow-db)
================================================
Server MCP resmi untuk mengakses basis data SQLite CampusFlow secara aman
dan terisolasi via protokol Model Context Protocol (stdio).

Fitur Keamanan:
- Read-only queries untuk seluruh operasi pemeriksaan.
- Penulisan pemesanan tunggal atomik (ACID) via create_booking_transactional.
- Proteksi terhadap race-condition dengan verifikasi ulang bentrok di dalam transaksi.
- Parameterized SQL pada seluruh pemanggilan kueri.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

# -----------------------------------------------------------------------------
# Path Resolusi Basis Data
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"

server = MCPServer("campusflow-db")


def get_db_connection() -> sqlite3.Connection:
    """Membuka koneksi SQLite dengan konfigurasi PRAGMA optimal."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database tidak ditemukan di {DB_PATH}. Jalankan init_db.py terlebih dahulu.")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def _resolve_room(conn: sqlite3.Connection, identifier: str) -> Optional[sqlite3.Row]:
    """Mencari ruangan berdasarkan room_code atau room_name."""
    clean_id = identifier.strip().lower()
    query = """
        SELECT id, building_id, room_code, room_name, room_type, capacity, floor, status
        FROM rooms
        WHERE LOWER(room_code) = ? OR LOWER(room_name) = ?
    """
    return conn.execute(query, (clean_id, clean_id)).fetchone()


# =============================================================================
# Tool 1: inspect_schema
# =============================================================================
@server.tool()
def inspect_schema() -> Dict[str, Any]:
    """
    Mengembalikan skema seluruh tabel dan kolom dalam database CampusFlow.
    Gunakan tool ini untuk memeriksa struktur entitas yang tersedia.
    """
    with get_db_connection() as conn:
        tables_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        tables: List[Dict[str, Any]] = []
        for row in tables_rows:
            tbl_name = row["name"]
            cols = conn.execute(f"PRAGMA table_info({tbl_name})").fetchall()
            tables.append({
                "name": tbl_name,
                "columns": [c["name"] for c in cols],
            })
        return {"tables": tables}


# =============================================================================
# Tool 2: query_room_capacity
# =============================================================================
@server.tool()
def query_room_capacity(room_name: str) -> Dict[str, Any]:
    """
    Mengambil informasi kapasitas maksimum dan tipe ruangan.
    
    Args:
        room_name: Nama ruangan (misal: 'Auditorium Utama') atau kode ruangan (misal: 'AUD-01').
    """
    with get_db_connection() as conn:
        room = _resolve_room(conn, room_name)
        if not room:
            return {
                "found": False,
                "message": f"Ruangan '{room_name}' tidak ditemukan dalam database.",
            }
        return {
            "found": True,
            "room_id": room["id"],
            "room_code": room["room_code"],
            "room_name": room["room_name"],
            "capacity": room["capacity"],
            "room_type": room["room_type"],
            "status": room["status"],
        }


# =============================================================================
# Tool 3: check_booking_conflicts
# =============================================================================
@server.tool()
def check_booking_conflicts(
    room_id: int,
    booking_date: str,
    start_time: str,
    end_time: str,
) -> Dict[str, Any]:
    """
    Memeriksa bentrok reservasi menggunakan room_id numerik pada tanggal dan rentang jam tertentu.
    
    Formula overlap: start_time < requested_end AND end_time > requested_start.
    
    Args:
        room_id: ID integer internal ruangan.
        booking_date: Tanggal reservasi (format: 'YYYY-MM-DD').
        start_time: Waktu mulai (format: 'HH:MM', contoh '09:00').
        end_time: Waktu selesai (format: 'HH:MM', contoh '11:00').
    """
    with get_db_connection() as conn:
        query = """
            SELECT id, booking_reference, event_name, start_time, end_time, status
            FROM bookings
            WHERE room_id = ?
              AND booking_date = ?
              AND status = 'CONFIRMED'
              AND start_time < ?
              AND end_time > ?
        """
        rows = conn.execute(query, (room_id, booking_date, end_time, start_time)).fetchall()
        conflicts = [
            {
                "booking_id": r["id"],
                "booking_reference": r["booking_reference"],
                "event_name": r["event_name"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
            }
            for r in rows
        ]
        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
        }


# =============================================================================
# Tool 4: query_room_availability
# =============================================================================
@server.tool()
def query_room_availability(
    room_name: str,
    booking_date: str,
    start_time: str,
    end_time: str,
) -> Dict[str, Any]:
    """
    Memeriksa apakah suatu ruangan berstatus aktif dan tersedia (tanpa bentrok)
    pada jadwal yang diminta.
    
    Args:
        room_name: Nama atau kode ruangan (misal: 'AUD-01' atau 'Auditorium Utama').
        booking_date: Tanggal yang diajukan (YYYY-MM-DD).
        start_time: Waktu mulai (HH:MM).
        end_time: Waktu selesai (HH:MM).
    """
    with get_db_connection() as conn:
        room = _resolve_room(conn, room_name)
        if not room:
            return {
                "status": "NOT_FOUND",
                "message": f"Ruangan '{room_name}' tidak ditemukan.",
            }
        
        if room["status"] != "ACTIVE":
            return {
                "status": "UNAVAILABLE",
                "room_id": room["id"],
                "room_code": room["room_code"],
                "room_name": room["room_name"],
                "reason": f"Ruangan sedang berstatus {room['status']}.",
                "conflicts": [],
            }

        conflict_result = check_booking_conflicts(
            room_id=room["id"],
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
        )

        if conflict_result["has_conflict"]:
            return {
                "status": "UNAVAILABLE",
                "room_id": room["id"],
                "room_code": room["room_code"],
                "room_name": room["room_name"],
                "reason": "Terdeteksi bentrok dengan reservasi yang sudah terkonfirmasi.",
                "conflicts": conflict_result["conflicts"],
            }

        return {
            "status": "AVAILABLE",
            "room_id": room["id"],
            "room_code": room["room_code"],
            "room_name": room["room_name"],
            "conflicts": [],
        }


# =============================================================================
# Tool 5: query_equipment
# =============================================================================
@server.tool()
def query_equipment(
    room_name: str,
    equipment_type: str = "",
    allow_add_on: bool = True,
) -> Dict[str, Any]:
    """
    Mencari daftar peralatan yang terpasang di dalam ruangan, dengan opsi filter tipe alat.
    
    Jika alat tidak terpasang permanen (built-in) di ruangan dan allow_add_on=True,
    sistem akan mencari unit portabel aktif di inventaris kampus yang dapat disiapkan
    sebagai add-on oleh tim IT Support & Fasilitas (misal: proyektor portabel, 
    sound system portabel, mikrofon wireless, papan tulis portabel).
    Peralatan instalasi tetap (smartboard, fixed PC lab, panggung aula) tidak dapat
    dijadikan add-on portabel.
    
    Args:
        room_name: Nama atau kode ruangan.
        equipment_type: Tipe alat opsional (misal: 'projector', 'microphone', 'sound_system').
        allow_add_on: Apakah boleh mencarikan alat portabel/add-on jika tidak ada built-in.
    """
    with get_db_connection() as conn:
        room = _resolve_room(conn, room_name)
        if not room:
            return {
                "found": False,
                "message": f"Ruangan '{room_name}' tidak ditemukan.",
            }

        if equipment_type.strip():
            query = """
                SELECT e.id AS equipment_id, e.equipment_code, e.equipment_name,
                       e.equipment_type, e.brand, e.status AS db_status, re.is_primary
                FROM room_equipment re
                JOIN equipment e ON e.id = re.equipment_id
                WHERE re.room_id = ? AND LOWER(e.equipment_type) = LOWER(?)
            """
            rows = conn.execute(query, (room["id"], equipment_type.strip())).fetchall()
        else:
            query = """
                SELECT e.id AS equipment_id, e.equipment_code, e.equipment_name,
                       e.equipment_type, e.brand, e.status AS db_status, re.is_primary
                FROM room_equipment re
                JOIN equipment e ON e.id = re.equipment_id
                WHERE re.room_id = ?
            """
            rows = conn.execute(query, (room["id"],)).fetchall()

        items = [
            {
                "equipment_id": r["equipment_id"],
                "equipment_code": r["equipment_code"],
                "equipment_name": r["equipment_name"],
                "equipment_type": r["equipment_type"],
                "brand": r["brand"],
                "db_status": r["db_status"],
                "is_primary": bool(r["is_primary"]),
                "is_add_on": False,
            }
            for r in rows
        ]

        # Peralatan yang dapat disediakan sebagai unit portabel / add-on
        PORTABLE_EQUIPMENT_TYPES = {
            "projector",
            "microphone",
            "sound_system",
            "whiteboard",
        }
        eq_type_norm = equipment_type.strip().lower()

        if allow_add_on and not items and eq_type_norm in PORTABLE_EQUIPMENT_TYPES:
            addon_query = """
                SELECT e.id AS equipment_id, e.equipment_code, e.equipment_name,
                       e.equipment_type, e.brand, e.status AS db_status
                FROM equipment e
                WHERE LOWER(e.equipment_type) = ?
                  AND e.status = 'ACTIVE'
                ORDER BY 
                    CASE 
                        WHEN e.equipment_name LIKE '%Portable%' OR e.equipment_name LIKE '%Seminar%' OR e.equipment_name LIKE '%Clip-On%' THEN 0
                        ELSE 1
                    END,
                    e.id ASC
                LIMIT 1
            """
            addon_row = conn.execute(addon_query, (eq_type_norm,)).fetchone()
            if addon_row:
                items.append({
                    "equipment_id": addon_row["equipment_id"],
                    "equipment_code": addon_row["equipment_code"],
                    "equipment_name": addon_row["equipment_name"],
                    "equipment_type": addon_row["equipment_type"],
                    "brand": addon_row["brand"],
                    "db_status": addon_row["db_status"],
                    "is_primary": False,
                    "is_add_on": True,
                })

        return {
            "found": len(items) > 0,
            "room_code": room["room_code"],
            "room_name": room["room_name"],
            "equipment": items,
        }


# =============================================================================
# Tool 6: create_booking_transactional
# =============================================================================
@server.tool()
def create_booking_transactional(
    room_id: int,
    user_identifier: str,
    event_name: str,
    booking_date: str,
    start_time: str,
    end_time: str,
    attendee_count: int,
    notes: Optional[str] = "",
    trace_id: str = "",
) -> Dict[str, Any]:
    """
    Menulis reservasi baru ke basis data secara transaksional (ACID).
    Memeriksa kapasitas dan memvalidasi ulang bentrok jadwal di dalam transaksi
    untuk mengeliminasi kondisi balapan (race condition).
    
    Args:
        room_id: ID integer ruangan.
        user_identifier: Nomor identitas pengguna (employee_id) atau email terdaftar.
        event_name: Judul atau nama agenda acara.
        booking_date: Tanggal acara (YYYY-MM-DD).
        start_time: Jam mulai (HH:MM).
        end_time: Jam selesai (HH:MM).
        attendee_count: Perkiraan jumlah peserta.
        notes: Catatan tambahan opsional.
        trace_id: ID jejak alur kerja untuk pencatatan audit trail.
    """
    conn = get_db_connection()
    try:
        with conn:
            # 1. Validasi ruangan dan kapasitas
            room = conn.execute("SELECT id, room_code, capacity, status FROM rooms WHERE id = ?", (room_id,)).fetchone()
            if not room:
                return {"status": "ROOM_NOT_FOUND", "message": f"Ruangan ID {room_id} tidak ditemukan."}

            if room["status"] != "ACTIVE":
                return {"status": "ROOM_INACTIVE", "message": f"Ruangan berstatus {room['status']} dan tidak dapat dipesan."}

            if attendee_count > room["capacity"]:
                return {
                    "status": "CAPACITY_EXCEEDED",
                    "message": f"Jumlah peserta ({attendee_count}) melebihi batas kapasitas ruangan ({room['capacity']}).",
                }

            # 2. Validasi identitas pengguna
            user_clean = user_identifier.strip()
            user = conn.execute(
                "SELECT id, is_active FROM users WHERE employee_id = ? OR LOWER(email) = LOWER(?)",
                (user_clean, user_clean),
            ).fetchone()
            if not user:
                return {"status": "USER_NOT_FOUND", "message": f"Pengguna '{user_identifier}' tidak terdaftar."}
            if not user["is_active"]:
                return {"status": "USER_INACTIVE", "message": "Akun pengguna tidak aktif."}

            # 3. Verifikasi ulang bentrok di dalam transaksi (cegah race condition)
            conflict_rows = conn.execute(
                """
                SELECT id, booking_reference FROM bookings
                WHERE room_id = ?
                  AND booking_date = ?
                  AND status = 'CONFIRMED'
                  AND start_time < ?
                  AND end_time > ?
                """,
                (room_id, booking_date, end_time, start_time),
            ).fetchall()
            if conflict_rows:
                return {
                    "status": "CONFLICT_DETECTED",
                    "message": "Reservasi dibatalkan: bentrok jadwal terdeteksi saat transaksi berlangsung.",
                    "conflicts": [dict(r) for r in conflict_rows],
                }

            # 4. Pembuatan nomor referensi pemesanan unik (format: BK-YYYY-NNN)
            year = booking_date.split("-")[0] if "-" in booking_date else str(datetime.now().year)
            max_row = conn.execute(
                "SELECT COUNT(*) AS total FROM bookings WHERE booking_reference LIKE ?",
                (f"BK-{year}-%",),
            ).fetchone()
            next_seq = (max_row["total"] if max_row else 0) + 1
            booking_ref = f"BK-{year}-{next_seq:03d}"

            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # 5. Insert reservasi
            cur = conn.execute(
                """
                INSERT INTO bookings (
                    booking_reference, room_id, user_id, event_name,
                    booking_date, start_time, end_time, attendee_count,
                    status, notes, created_at, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?)
                """,
                (
                    booking_ref, room["id"], user["id"], event_name.strip(),
                    booking_date, start_time, end_time, attendee_count,
                    notes.strip() if notes else None, now_iso, now_iso,
                ),
            )
            booking_id = cur.lastrowid

            # 6. Catat log audit transaksional
            tid = trace_id.strip() if trace_id.strip() else f"trace-{booking_ref.lower()}"
            conn.execute(
                """
                INSERT INTO audit_logs (
                    trace_id, booking_id, step_index, step_name,
                    workflow_status, evidence_json, decision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tid, booking_id, 1, "TRANSACTIONAL_COMMIT",
                    "SUCCESS", json.dumps({"booking_reference": booking_ref, "room_id": room_id}),
                    "COMMITTED", now_iso,
                ),
            )

            return {
                "status": "CREATED",
                "booking_id": booking_id,
                "booking_reference": booking_ref,
                "confirmed_at": now_iso,
            }
    except Exception as e:
        conn.rollback()
        return {"status": "TRANSACTION_FAILED", "message": str(e)}
    finally:
        conn.close()


# =============================================================================
# Suite Uji Mandiri (Self-Check Harness)
# =============================================================================
async def run_self_check() -> bool:
    """Menjalankan verifikasi mandiri terhadap seluruh 6 tool database."""
    print("Menjalankan self-check campusflow-db...")
    all_ok = True

    async def _test(name: str, coro, check_fn) -> None:
        nonlocal all_ok
        try:
            res = await coro
            # Ekstrak data text JSON dari CallToolResult
            raw_text = res.content[0].text
            data = json.loads(raw_text)
            passed = check_fn(data)
            status = "[PASS]" if passed else "[FAIL]"
            if not passed:
                all_ok = False
            print(f"  {status:<6} {name}")
        except Exception as err:
            all_ok = False
            print(f"  [FAIL] {name}: {err}")

    await _test(
        "inspect_schema() memuat tabel master",
        server.call_tool("inspect_schema", {}),
        lambda d: any(t["name"] == "rooms" for t in d.get("tables", [])),
    )

    await _test(
        "query_room_capacity('AUD-01') bernilai 300",
        server.call_tool("query_room_capacity", {"room_name": "AUD-01"}),
        lambda d: d.get("found") is True and d.get("capacity") == 300,
    )

    await _test(
        "check_booking_conflicts(AUD-01, 2026-09-23 08:00-12:00) mendeteksi bentrok",
        server.call_tool("check_booking_conflicts", {
            "room_id": 1, "booking_date": "2026-09-23", "start_time": "08:00", "end_time": "12:00"
        }),
        lambda d: d.get("has_conflict") is True and len(d.get("conflicts", [])) >= 1,
    )

    await _test(
        "query_room_availability('AUD-01', 2026-09-23 13:00-16:00) berstatus AVAILABLE",
        server.call_tool("query_room_availability", {
            "room_name": "AUD-01", "booking_date": "2026-09-23", "start_time": "13:00", "end_time": "16:00"
        }),
        lambda d: d.get("status") == "AVAILABLE",
    )

    await _test(
        "query_equipment('AUD-01', 'projector') menemukan PRJ-03",
        server.call_tool("query_equipment", {"room_name": "AUD-01", "equipment_type": "projector"}),
        lambda d: d.get("found") is True and any(e["equipment_code"] == "PRJ-03" for e in d.get("equipment", [])),
    )

    await _test(
        "create_booking_transactional() menolak pemesanan melebihi kapasitas",
        server.call_tool("create_booking_transactional", {
            "room_id": 1, "user_identifier": "FAC-001", "event_name": "Over Capacity Event",
            "booking_date": "2026-09-25", "start_time": "10:00", "end_time": "12:00", "attendee_count": 999
        }),
        lambda d: d.get("status") == "CAPACITY_EXCEEDED",
    )

    await _test(
        "create_booking_transactional() sukses membuat reservasi valid",
        server.call_tool("create_booking_transactional", {
            "room_id": 4, "user_identifier": "FAC-001", "event_name": "Sesi Diskusi Rektorat",
            "booking_date": "2026-09-30", "start_time": "14:00", "end_time": "15:00", "attendee_count": 10
        }),
        lambda d: d.get("status") == "CREATED" and "booking_reference" in d,
    )

    await _test(
        "create_booking_transactional() mendeteksi bentrok jika memesan slot yang baru dibuat",
        server.call_tool("create_booking_transactional", {
            "room_id": 4, "user_identifier": "STF-001", "event_name": "Rapat Tabrakan Jadwal",
            "booking_date": "2026-09-30", "start_time": "14:15", "end_time": "14:45", "attendee_count": 8
        }),
        lambda d: d.get("status") == "CONFLICT_DETECTED",
    )

    print(f"Hasil self-check: {'SELURUH PENGUJIAN LOLOS' if all_ok else 'ADA KEGAGALAN'}")
    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusFlow Database MCP Server")
    parser.add_argument("--test", action="store_true", help="Jalankan rangkaian uji mandiri internal")
    args = parser.parse_args()

    if args.test:
        success = asyncio.run(run_self_check())
        sys.exit(0 if success else 1)

    # Menjalankan server via stdio transport (default MCP)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
