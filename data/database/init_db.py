#!/usr/bin/env python3
"""
CampusFlow Database Initialization Script
=========================================
Membuat dan menginisialisasi database SQLite CampusFlow dari schema.sql dan seed.sql.
Aman dijalankan berulang kali (idempotent): jika database sudah ada, hanya verifikasi.

Penggunaan:
    python data/database/init_db.py              # Buat + isi database
    python data/database/init_db.py --reset      # Hapus & buat ulang
    python data/database/init_db.py --verify     # Hanya verifikasi data
"""

import sqlite3
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# ─── Path Configuration ────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent.parent   # project root
DB_DIR      = BASE_DIR / "data" / "database"
DB_PATH     = DB_DIR / "campusflow.db"
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_PATH   = DB_DIR / "seed.sql"


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Membuka koneksi dengan PRAGMA yang tepat."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous  = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def run_sql_file(conn: sqlite3.Connection, sql_path: Path, label: str) -> None:
    """Menjalankan seluruh isi satu file SQL."""
    print(f"  ↳ Menjalankan {label}: {sql_path.name}...", end=" ")
    sql = sql_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    print("✅")


def verify_database(conn: sqlite3.Connection) -> bool:
    """Verifikasi bahwa database berisi data yang benar dan terstruktur."""
    print("\n📋 Verifikasi Database:")
    all_ok = True

    checks = [
        ("buildings",       "SELECT COUNT(*) FROM buildings",                            3,  "gedung"),
        ("rooms",           "SELECT COUNT(*) FROM rooms",                                8,  "ruangan"),
        ("equipment",       "SELECT COUNT(*) FROM equipment",                            10, "peralatan"),
        ("room_equipment",  "SELECT COUNT(*) FROM room_equipment",                       12, "penugasan alat"),
        ("users",           "SELECT COUNT(*) FROM users",                                6,  "pengguna"),
        ("bookings",        "SELECT COUNT(*) FROM bookings",                             5,  "reservasi"),
        ("active_rooms",    "SELECT COUNT(*) FROM rooms WHERE status = 'ACTIVE'",        7,  "ruangan aktif"),
        ("broken_equip",    "SELECT COUNT(*) FROM equipment WHERE status = 'UNDER_MAINTENANCE'", 1, "alat dalam perbaikan"),
    ]

    for name, query, expected, label in checks:
        count = conn.execute(query).fetchone()[0]
        status = "✅" if count == expected else "❌"
        if count != expected:
            all_ok = False
        print(f"  {status} {label}: {count} (diharapkan: {expected})")

    # Verifikasi query deteksi bentrok
    print("\n🔍 Verifikasi Query Kritis:")

    # Test: AUD-01 pada 2026-09-23 08:00-12:00 HARUS bentrok
    rows = conn.execute("""
        SELECT b.id, b.booking_reference FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE r.room_code = 'AUD-01'
          AND b.booking_date = '2026-09-23'
          AND b.status = 'CONFIRMED'
          AND b.start_time < '12:00'
          AND b.end_time > '08:00'
    """).fetchall()
    ok = len(rows) >= 1
    print(f"  {'✅' if ok else '❌'} Deteksi bentrok AUD-01 (2026-09-23 08:00-12:00): ditemukan {len(rows)} reservasi")
    if not ok:
        all_ok = False

    # Test: AUD-01 pada 2026-09-23 13:00-16:00 HARUS tersedia
    rows2 = conn.execute("""
        SELECT COUNT(*) AS cnt FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE r.room_code = 'AUD-01'
          AND b.booking_date = '2026-09-23'
          AND b.status = 'CONFIRMED'
          AND b.start_time < '16:00'
          AND b.end_time > '13:00'
    """).fetchone()
    ok2 = rows2["cnt"] == 0
    print(f"  {'✅' if ok2 else '❌'} AUD-01 tersedia (2026-09-23 13:00-16:00): konflik = {rows2['cnt']}")
    if not ok2:
        all_ok = False

    # Test: Kapasitas AUD-01
    cap = conn.execute("SELECT capacity FROM rooms WHERE room_code = 'AUD-01'").fetchone()
    ok3 = cap and cap["capacity"] == 300
    print(f"  {'✅' if ok3 else '❌'} Kapasitas AUD-01: {cap['capacity'] if cap else 'N/A'} (diharapkan: 300)")
    if not ok3:
        all_ok = False

    # Test: PRJ-02 dalam status UNDER_MAINTENANCE di DB
    equip = conn.execute("SELECT status FROM equipment WHERE equipment_code = 'PRJ-02'").fetchone()
    ok4 = equip and equip["status"] == "UNDER_MAINTENANCE"
    print(f"  {'✅' if ok4 else '❌'} Status PRJ-02 di DB: {equip['status'] if equip else 'N/A'} (diharapkan: UNDER_MAINTENANCE)")
    if not ok4:
        all_ok = False

    # Test: PRJ-03 terdaftar di AUD-01
    re_row = conn.execute("""
        SELECT e.equipment_code FROM room_equipment re
        JOIN rooms r ON r.id = re.room_id
        JOIN equipment e ON e.id = re.equipment_id
        WHERE r.room_code = 'AUD-01' AND e.equipment_type = 'projector'
    """).fetchone()
    ok5 = re_row and re_row["equipment_code"] == "PRJ-03"
    print(f"  {'✅' if ok5 else '❌'} PRJ-03 terdaftar di AUD-01: {'ya' if ok5 else 'tidak'}")
    if not ok5:
        all_ok = False

    return all_ok


def create_database() -> None:
    """Buat database baru dari schema dan seed."""
    print(f"\n🏗️  Membuat database: {DB_PATH}")
    conn = get_connection(DB_PATH)
    try:
        run_sql_file(conn, SCHEMA_PATH, "Schema DDL")
        run_sql_file(conn, SEED_PATH,   "Seed Data")
    finally:
        conn.close()


def reset_database() -> None:
    """Hapus database yang ada dan buat ulang."""
    if DB_PATH.exists():
        DB_PATH.unlink()
        wal = DB_PATH.with_suffix(".db-wal")
        shm = DB_PATH.with_suffix(".db-shm")
        for f in [wal, shm]:
            if f.exists():
                f.unlink()
        print(f"🗑️  Database lama dihapus: {DB_PATH}")
    create_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusFlow Database Initializer")
    parser.add_argument("--reset",  action="store_true", help="Hapus dan buat ulang database")
    parser.add_argument("--verify", action="store_true", help="Hanya verifikasi database yang sudah ada")
    args = parser.parse_args()

    print("=" * 60)
    print("  CampusFlow — Database Initialization")
    print(f"  Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.verify:
        if not DB_PATH.exists():
            print(f"\n❌ Database tidak ditemukan: {DB_PATH}")
            sys.exit(1)
        conn = get_connection(DB_PATH)
        ok = verify_database(conn)
        conn.close()
        sys.exit(0 if ok else 1)

    if args.reset:
        print("\n⚠️  Mode RESET: Database akan dihapus dan dibuat ulang.")
        reset_database()
    elif DB_PATH.exists():
        print(f"\nℹ️  Database sudah ada: {DB_PATH}")
        print("   Gunakan --reset untuk membuatnya ulang.")
    else:
        create_database()

    # Selalu verifikasi setelah pembuatan
    conn = get_connection(DB_PATH)
    ok = verify_database(conn)
    conn.close()

    print("\n" + "=" * 60)
    if ok:
        print("  ✅ Fase 3 Database: SIAP DIGUNAKAN")
        print(f"  📁 Path: {DB_PATH}")
    else:
        print("  ❌ Verifikasi GAGAL — periksa seed data.")
    print("=" * 60)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
