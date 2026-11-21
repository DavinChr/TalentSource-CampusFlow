"""
CampusFlow — UNPAR Room Text Synchronizer
=========================================
Membaca file Catatan/DATA_RUANGAN_UNPAR.txt (atau data/campus_rooms_unpar.txt)
secara otomatis untuk:
1. Memasukkan / memperbarui (upsert) Gedung & Ruangan ke database SQLite.
2. Menyediakan kamus ruangan aktif UNPAR secara dinamis untuk LLM & Recommender.
"""

from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRIMARY_TXT = BASE_DIR / "Catatan" / "DATA_RUANGAN_UNPAR.txt"
FALLBACK_TXT = BASE_DIR / "data" / "campus_rooms_unpar.txt"
DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"


def get_unpar_txt_path() -> Optional[Path]:
    """Mengembalikan path berkas teks UNPAR yang ada."""
    if PRIMARY_TXT.exists():
        return PRIMARY_TXT
    if FALLBACK_TXT.exists():
        return FALLBACK_TXT
    return None


def parse_unpar_text_file(txt_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Mengurai berkas teks UNPAR menjadi data terstruktur gedung dan ruangan.
    Format per ruangan:
      [KODE_RUANGAN]
      Nama Ruangan   : ...
      Gedung         : <KODE> - <NAMA>
      Lantai         : ...
      Tipe           : ...
      Kapasitas      : ...
      Status         : ...
      Peralatan      : ...
      Catatan Khusus : ...
    """
    path = txt_path or get_unpar_txt_path()
    if not path or not path.exists():
        return {"buildings": [], "rooms": []}

    content = path.read_text(encoding="utf-8")

    # 1. Parsing Gedung (Bagian 1)
    buildings = []
    # Pola: [KODE] Nama Gedung — Alamat
    bld_section_match = re.search(r"1\.\s*DAFTAR MASTER GEDUNG.*?(?=2\.\s*DAFTAR DETAIL|$)", content, re.DOTALL | re.I)
    if bld_section_match:
        bld_text = bld_section_match.group(0)
        for m in re.finditer(r"\[([A-Z0-9]+)\]\s+([^—\n]+?)(?:\s*—\s*([^\n]*))?$", bld_text, re.MULTILINE):
            b_code = m.group(1).strip()
            b_name = m.group(2).strip()
            b_addr = (m.group(3) or "Jl. Ciumbuleuit No. 94, Bandung").strip()
            buildings.append({
                "code": b_code,
                "name": b_name,
                "address": b_addr,
                "floors": 10,
            })

    # 2. Parsing Ruangan (Bagian 2)
    # Split per blok [KODE]
    rooms = []
    room_pattern = re.compile(
        r"\[([A-Z0-9_\-]+)\]\s*\n"
        r"Nama Ruangan\s*:\s*([^\n]+)\n"
        r"Gedung\s*:\s*([^\n]+)\n"
        r"(?:Lantai\s*:\s*([^\n]+)\n)?"
        r"(?:Tipe\s*:\s*([^\n]+)\n)?"
        r"(?:Kapasitas\s*:\s*([^\n]+)\n)?"
        r"(?:Status\s*:\s*([^\n]+)\n)?"
        r"(?:Peralatan\s*:\s*([^\n]+)\n)?"
        r"(?:Catatan Khusus\s*:\s*([^\n]+))?",
        re.IGNORECASE
    )

    for m in room_pattern.finditer(content):
        code = m.group(1).strip()
        name = m.group(2).strip()
        gedung_raw = m.group(3).strip()
        floor_raw = (m.group(4) or "1").strip()
        room_type = (m.group(5) or "lecture_hall").strip().lower()
        cap_raw = (m.group(6) or "40").strip()
        status = (m.group(7) or "ACTIVE").strip().upper()
        equipment_raw = (m.group(8) or "").strip()
        notes = (m.group(9) or "").strip()

        # Ekstrak kode gedung dari "PPAG - Pusat..." atau "G9"
        b_code = gedung_raw.split("-")[0].strip().split()[0].strip()

        # Ekstrak angka kapasitas
        cap_match = re.search(r"\d+", cap_raw)
        capacity = int(cap_match.group(0)) if cap_match else 40

        # Ekstrak angka lantai pertama
        fl_match = re.search(r"\d+", floor_raw)
        floor = int(fl_match.group(0)) if fl_match else 1

        rooms.append({
            "room_code": code,
            "room_name": name,
            "building_code": b_code,
            "floor": floor,
            "room_type": room_type,
            "capacity": capacity,
            "status": status,
            "equipment": equipment_raw,
            "notes": notes,
        })

    return {"buildings": buildings, "rooms": rooms}


def sync_unpar_rooms_to_db(db_path: Optional[Path] = None) -> int:
    """
    Menyelaraskan ruangan dari berkas teks UNPAR langsung ke database SQLite.
    Menggunakan INSERT OR REPLACE / UPDATE agar idempoten dan aman.
    """
    target_db = db_path or DB_PATH
    if not target_db.exists():
        return 0

    data = parse_unpar_text_file()
    if not data["rooms"]:
        return 0

    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    count = 0
    try:
        # 1. Pastikan gedung terdaftar
        for b in data["buildings"]:
            conn.execute("""
                INSERT INTO buildings (code, name, address, floors)
                VALUES (:code, :name, :address, :floors)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    address = excluded.address
            """, b)
        conn.commit()

        # 2. Sinkronkan ruangan
        for r in data["rooms"]:
            # Ambil building_id
            b_row = conn.execute("SELECT id FROM buildings WHERE code = ?", (r["building_code"],)).fetchone()
            if not b_row:
                # Fallback: buat gedung jika belum ada
                conn.execute(
                    "INSERT INTO buildings (code, name, address, floors) VALUES (?, ?, ?, ?)",
                    (r["building_code"], f"Gedung {r['building_code']}", "Kampus UNPAR", 5)
                )
                conn.commit()
                b_row = conn.execute("SELECT id FROM buildings WHERE code = ?", (r["building_code"],)).fetchone()

            b_id = b_row["id"]

            conn.execute("""
                INSERT INTO rooms (building_id, room_code, room_name, room_type, capacity, floor, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(room_code) DO UPDATE SET
                    building_id = excluded.building_id,
                    room_name   = excluded.room_name,
                    room_type   = excluded.room_type,
                    capacity    = excluded.capacity,
                    floor       = excluded.floor,
                    status      = excluded.status
            """, (b_id, r["room_code"], r["room_name"], r["room_type"], r["capacity"], r["floor"], r["status"]))
            count += 1

        conn.commit()
    finally:
        conn.close()

    return count


def load_dynamic_known_rooms() -> Dict[str, str]:
    """
    Membangun kamus KNOWN_ROOMS dinamis langsung dari berkas teks UNPAR
    sehingga LLM selalu memiliki data teranyar tanpa perlu edit kode python.
    """
    data = parse_unpar_text_file()
    if not data["rooms"]:
        return {}

    dynamic_dict = {}
    for r in data["rooms"]:
        code = r["room_code"]
        name = r["room_name"]
        cap = r["capacity"]
        bld = r["building_code"]
        desc = f"{name} (Kapasitas: {cap} orang, Gedung {bld})"
        if r.get("notes"):
            desc += f"; Catatan: {r['notes']}"
        dynamic_dict[code] = desc

    return dynamic_dict
