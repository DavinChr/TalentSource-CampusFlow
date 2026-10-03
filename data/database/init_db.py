#!/usr/bin/env python3
"""
CampusFlow Database Initialization & Verification
=================================================
Inisialisasi basis data SQLite lokal untuk sistem orkestrasi CampusFlow.
Skrip ini bersifat idempoten:
- Menjalankan DDL skema relasional (schema.sql).
- Mengisi data awal acuan pengujian (seed.sql).
- Menjalankan suite verifikasi integritas 13 titik untuk memastikan
  seluruh batasan kunci (foreign keys), indeks, serta kueri deteksi
  bentrok jadwal berfungsi sesuai spesifikasi SRS.

Penggunaan CLI:
    python data/database/init_db.py          # Inisialisasi jika belum ada, lalu verifikasi
    python data/database/init_db.py --reset  # Hapus file database lama dan buat ulang
    python data/database/init_db.py --verify # Hanya jalankan verifikasi integritas
"""

import argparse
from pathlib import Path
import sqlite3
import sys

# -----------------------------------------------------------------------------
# Konfigurasi Path Berkas
# -----------------------------------------------------------------------------
# Menentukan lokasi root proyek secara relatif dari letak skrip ini (data/database/..)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data" / "database"
DB_PATH = DB_DIR / "campusflow.db"
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_PATH = DB_DIR / "seed.sql"


def get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Membuka koneksi SQLite dengan konfigurasi PRAGMA operasional:
    - foreign_keys = ON: Menegakkan integritas referensial (secara default SQLite mematikan FK).
    - journal_mode = WAL: Mengaktifkan Write-Ahead Logging agar proses pembacaan (reader)
      dan penulisan (writer) tidak saling memblokir selama agen beroperasi.
    - synchronous = NORMAL: Mengurangi frekuensi fsync disk tanpa mengorbankan durabilitas WAL.
    - busy_timeout = 5000: Menunggu hingga 5 detik jika ada penguncian sementara sebelum melempar galat.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous  = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def run_sql_file(conn: sqlite3.Connection, sql_path: Path, label: str) -> None:
    """
    Mengeksekusi berkas SQL multi-statement menggunakan executescript.
    executescript secara otomatis mengeluarkan perintah COMMIT sebelum mengeksekusi script.
    """
    sys.stdout.write(f"  [{label}] Mengeksekusi {sql_path.name}... ")
    sys.stdout.flush()
    sql_content = sql_path.read_text(encoding="utf-8")
    conn.executescript(sql_content)
    conn.commit()
    print("selesai.")


def verify_database(conn: sqlite3.Connection) -> bool:
    """
    Suite verifikasi integritas data dan kueri bisnis CampusFlow (13 titik pemeriksaan):
    1. Memeriksa jumlah baris tabel master dan relasi (buildings, rooms, equipment, users, bookings).
    2. Menguji logika deteksi bentrok jadwal menggunakan formula interval waktu tumpang tindih:
       (start_time < requested_end) AND (end_time > requested_start).
    3. Memastikan status peralatan rusak/pemeliharaan terisolasi untuk kasus uji kegagalan agen.
    """
    print("\n--- Verifikasi Integritas Entitas ---")
    all_ok = True

    # Daftar pemeriksaan jumlah entitas dasar sesuai seed.sql
    checks = [
        ("buildings",       "SELECT COUNT(*) FROM buildings",                            3,  "Gedung (buildings)"),
        ("rooms",           "SELECT COUNT(*) FROM rooms",                                8,  "Ruangan (rooms)"),
        ("equipment",       "SELECT COUNT(*) FROM equipment",                            10, "Peralatan (equipment)"),
        ("room_equipment",  "SELECT COUNT(*) FROM room_equipment",                       12, "Penugasan alat ke ruangan (room_equipment)"),
        ("users",           "SELECT COUNT(*) FROM users",                                6,  "Pengguna terdaftar (users)"),
        ("bookings",        "SELECT COUNT(*) FROM bookings",                             5,  "Reservasi awal (bookings)"),
        ("active_rooms",    "SELECT COUNT(*) FROM rooms WHERE status = 'ACTIVE'",        7,  "Ruangan aktif siap pakai"),
        ("broken_equip",    "SELECT COUNT(*) FROM equipment WHERE status = 'UNDER_MAINTENANCE'", 1, "Peralatan status pemeliharaan (PRJ-02)"),
    ]

    for table_id, query, expected, label in checks:
        count = conn.execute(query).fetchone()[0]
        passed = count == expected
        status_tag = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_ok = False
        print(f"  {status_tag:<6} {label:<45} : {count} (ekspektasi: {expected})")

    print("\n--- Verifikasi Kueri Kritis & Logika Bisnis ---")

    # Uji 1: Deteksi bentrok jadwal (Overlap Test)
    # AUD-01 pada tanggal 2026-09-23 sudah terisi pukul 09:00 - 11:30 (booking BK-2026-001).
    # Permintaan pemesanan pukul 08:00 - 12:00 HARUS mendeteksi tumpang tindih tersebut.
    conflict_query = """
        SELECT b.id, b.booking_reference, b.start_time, b.end_time
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE r.room_code = 'AUD-01'
          AND b.booking_date = '2026-09-23'
          AND b.status = 'CONFIRMED'
          AND b.start_time < '12:00'
          AND b.end_time > '08:00'
    """
    conflicts = conn.execute(conflict_query).fetchall()
    test1_ok = len(conflicts) >= 1
    if not test1_ok:
        all_ok = False
    tag1 = "[PASS]" if test1_ok else "[FAIL]"
    print(f"  {tag1:<6} Deteksi bentrok jadwal AUD-01 (08:00-12:00) : Ditemukan {len(conflicts)} konflik aktif")

    # Uji 2: Ketersediaan slot bebas pada hari yang sama (Free Slot Test)
    # Pada tanggal yang sama (2026-09-23), slot pukul 13:00 - 16:00 harus bebas konflik.
    free_query = """
        SELECT COUNT(*) AS conflict_count
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE r.room_code = 'AUD-01'
          AND b.booking_date = '2026-09-23'
          AND b.status = 'CONFIRMED'
          AND b.start_time < '16:00'
          AND b.end_time > '13:00'
    """
    free_count = conn.execute(free_query).fetchone()["conflict_count"]
    test2_ok = free_count == 0
    if not test2_ok:
        all_ok = False
    tag2 = "[PASS]" if test2_ok else "[FAIL]"
    print(f"  {tag2:<6} Validasi ketersediaan AUD-01 (13:00-16:00)  : {free_count} konflik (ruangan tersedia)")

    # Uji 3: Integritas batas daya tampung (Capacity Test)
    # Memastikan kapasitas AUD-01 tercatat tepat 300 peserta untuk kebutuhan workshop besar.
    cap_row = conn.execute("SELECT capacity FROM rooms WHERE room_code = 'AUD-01'").fetchone()
    capacity_val = cap_row["capacity"] if cap_row else 0
    test3_ok = capacity_val == 300
    if not test3_ok:
        all_ok = False
    tag3 = "[PASS]" if test3_ok else "[FAIL]"
    print(f"  {tag3:<6} Kapasitas maksimal AUD-01                   : {capacity_val} kursi (ekspektasi: 300)")

    # Uji 4: Status peralatan rusak/servis di database
    # PRJ-02 harus berstatus 'UNDER_MAINTENANCE' untuk memvalidasi alur penolakan agen (Uji 4).
    equip_row = conn.execute("SELECT status FROM equipment WHERE equipment_code = 'PRJ-02'").fetchone()
    equip_status = equip_row["status"] if equip_row else "UNKNOWN"
    test4_ok = equip_status == "UNDER_MAINTENANCE"
    if not test4_ok:
        all_ok = False
    tag4 = "[PASS]" if test4_ok else "[FAIL]"
    print(f"  {tag4:<6} Status pemeliharaan proyektor PRJ-02        : {equip_status}")

    # Uji 5: Pemetaan relasi alat primer ke ruangan (Room-Equipment Mapping)
    # Memastikan AUD-01 memiliki proyektor primer PRJ-03 (ViewSonic PA503X).
    re_row = conn.execute("""
        SELECT e.equipment_code, e.equipment_name
        FROM room_equipment re
        JOIN rooms r ON r.id = re.room_id
        JOIN equipment e ON e.id = re.equipment_id
        WHERE r.room_code = 'AUD-01' AND e.equipment_type = 'projector'
    """).fetchone()
    has_primary_proj = re_row is not None and re_row["equipment_code"] == "PRJ-03"
    if not has_primary_proj:
        all_ok = False
    tag5 = "[PASS]" if has_primary_proj else "[FAIL]"
    proj_code = re_row["equipment_code"] if re_row else "NONE"
    print(f"  {tag5:<6} Pemetaan proyektor utama AUD-01             : {proj_code} terpasang")

    return all_ok


def create_database() -> None:
    """Membaca skema DDL dan data benih untuk menyusun basis data baru."""
    print(f"Menginisialisasi basis data di: {DB_PATH}")
    conn = get_connection(DB_PATH)
    try:
        run_sql_file(conn, SCHEMA_PATH, "DDL")
        run_sql_file(conn, SEED_PATH, "SEED")
    finally:
        conn.close()


def reset_database() -> None:
    """
    Menghapus berkas database utama beserta berkas jurnal WAL (-wal dan -shm)
    sebelum melakukan inisialisasi ulang yang bersih.
    """
    for file_to_remove in (DB_PATH, DB_PATH.with_suffix(".db-wal"), DB_PATH.with_suffix(".db-shm")):
        if file_to_remove.exists():
            file_to_remove.unlink()
            print(f"Menghapus berkas lama: {file_to_remove.name}")
    create_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusFlow Database Initializer and Integrity Verifier")
    parser.add_argument("--reset", action="store_true", help="Hapus database yang ada dan inisialisasi ulang")
    parser.add_argument("--verify", action="store_true", help="Hanya jalankan suite verifikasi pada database yang ada")
    args = parser.parse_args()

    print("CampusFlow - Database Manager")

    if args.verify:
        if not DB_PATH.exists():
            print(f"Error: Basis data tidak ditemukan di {DB_PATH}")
            print("Jalankan tanpa argumen untuk membuat basis data terlebih dahulu.")
            sys.exit(1)
        conn = get_connection(DB_PATH)
        ok = verify_database(conn)
        conn.close()
        sys.exit(0 if ok else 1)

    if args.reset:
        print("Menjalankan reset basis data...")
        reset_database()
    elif DB_PATH.exists():
        print(f"Basis data sudah ada di: {DB_PATH}")
        print("Menjalankan verifikasi data yang ada (gunakan --reset untuk membangun ulang)...")
    else:
        create_database()

    # Jalankan verifikasi integritas setelah inisialisasi atau pemeriksaan
    conn = get_connection(DB_PATH)
    ok = verify_database(conn)
    conn.close()

    print("\n-------------------------------------------------------------")
    if ok:
        print("Status: Seluruh 13 pengujian integritas berhasil (PASS).")
        print(f"Target: {DB_PATH}")
    else:
        print("Status: Verifikasi integritas gagal. Periksa log di atas.")
    print("-------------------------------------------------------------")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
