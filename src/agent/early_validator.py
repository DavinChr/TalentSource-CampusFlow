"""
CampusFlow — Early Constraint & Fast-Fail Validator
===================================================
Memvalidasi kendala permintaan secara dini (Early Fast-Fail) sebelum sistem
mengajukan pertanyaan klarifikasi lebih lanjut kepada pengguna.

Jika suatu permintaan sudah pasti tidak bisa dipenuhi sejak awal:
- Ruangan sedang UNDER_RENOVATION / tidak aktif
- Peralatan yang diminta tidak ada dan tidak bisa add-on (misal: smartboard di LH-201)
- Jumlah peserta melampaui kapasitas maksimal ruangan
- Tanggal pemesanan sudah lewat di masa lalu
- Jam mulai >= jam selesai
- Jadwal ruangan sudah bentrok dengan pemesanan lain

Sistem akan LANGSUNG menolak dan menginformasikannya kepada pengguna beserta
saran alternatif, tanpa perlu meminta pengguna mengisi sisa informasi lainnya.
"""

from datetime import date
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from src.agent.llm import LLMBookingExtraction
from src.agent.room_recommender import find_room_recommendations

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"

# Tipe alat yang bisa dialokasikan sebagai unit portabel/add-on
PORTABLE_EQUIPMENT_TYPES = {
    "projector",
    "microphone",
    "sound_system",
    "whiteboard",
}


def _get_room_by_name(conn: sqlite3.Connection, room_name: str) -> Optional[Dict[str, Any]]:
    """Mencari data ruangan berdasarkan kode atau nama ruangan."""
    query = """
        SELECT r.id, r.room_code, r.room_name, r.room_type, r.capacity, r.status,
               b.code as building_code, b.name as building_name
        FROM rooms r
        JOIN buildings b ON b.id = r.building_id
        WHERE LOWER(r.room_code) = LOWER(?) OR LOWER(r.room_name) = LOWER(?)
    """
    row = conn.execute(query, (room_name.strip(), room_name.strip())).fetchone()
    if row:
        return dict(row)

    # Cek pencarian parsial jika belum ketemu
    query_like = """
        SELECT r.id, r.room_code, r.room_name, r.room_type, r.capacity, r.status,
               b.code as building_code, b.name as building_name
        FROM rooms r
        JOIN buildings b ON b.id = r.building_id
        WHERE LOWER(r.room_name) LIKE LOWER(?)
        LIMIT 1
    """
    row_like = conn.execute(query_like, (f"%{room_name.strip()}%",)).fetchone()
    return dict(row_like) if row_like else None


def find_rooms_with_equipment(equipment_type: str, attendee_count: Optional[int] = None, limit: int = 3) -> List[Dict[str, Any]]:
    """Mencari ruangan yang memiliki peralatan tertentu yang aktif."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        query = """
            SELECT DISTINCT r.id, r.room_code, r.room_name, r.room_type, r.capacity,
                   b.name as building_name, b.code as building_code
            FROM rooms r
            JOIN room_equipment re ON re.room_id = r.id
            JOIN equipment e ON e.id = re.equipment_id
            JOIN buildings b ON b.id = r.building_id
            WHERE LOWER(e.equipment_type) = LOWER(?) AND r.status = 'ACTIVE' AND b.code IN ('PPAG', 'G0', 'G9', 'G2')
            ORDER BY r.capacity ASC
        """
        rows = conn.execute(query, (equipment_type.strip().lower(),)).fetchall()
        rooms = [dict(r) for r in rows]
        if attendee_count:
            # Utamakan kapasitas yang cukup
            rooms.sort(key=lambda r: (r["capacity"] < attendee_count, abs(r["capacity"] - attendee_count)))
        for idx, r in enumerate(rooms[:limit], start=1):
            r["option_number"] = idx
        return rooms[:limit]
    finally:
        conn.close()


def check_early_constraints(
    extraction: Optional[LLMBookingExtraction],
    today_str: str,
) -> Dict[str, Any]:
    """
    Memvalidasi kendala dini (Early Constraints / Fast-Fail).
    Mengembalikan dict:
      {
         "valid": bool,
         "status": str ("OK" atau kode penolakan spesifik),
         "message": str (alasan spesifik penolakan),
         "recommendations": list (opsi ruangan alternatif jika ada)
      }
    """
    if not extraction:
        return {"valid": True, "status": "OK", "message": "", "recommendations": []}

    today = date.fromisoformat(today_str) if today_str else date.today()

    # 1. Validasi Tanggal Sudah Lewat
    if extraction.booking_date:
        try:
            b_date = date.fromisoformat(extraction.booking_date)
            if b_date < today:
                return {
                    "valid": False,
                    "status": "INVALID_REQUEST",
                    "message": f"Tanggal {extraction.booking_date} sudah lewat (tanggal acuan sistem: {today.isoformat()}). Pemesanan hanya dapat diajukan untuk tanggal di masa mendatang.",
                    "recommendations": [],
                }
        except ValueError:
            pass

    # 2. Validasi Jam Mulai vs Jam Selesai
    if extraction.start_time and extraction.end_time:
        if extraction.start_time >= extraction.end_time:
            return {
                "valid": False,
                "status": "INVALID_REQUEST",
                "message": f"Jam mulai ({extraction.start_time}) harus lebih awal dari jam selesai ({extraction.end_time}).",
                "recommendations": [],
            }

    if not DB_PATH.exists():
        return {"valid": True, "status": "OK", "message": "", "recommendations": []}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        room_data = None
        if extraction.room_name:
            room_data = _get_room_by_name(conn, extraction.room_name)

            # 3. Ruangan Tidak Ditemukan
            if not room_data:
                recs = find_room_recommendations(attendee_count=extraction.attendee_count, hint_text=extraction.room_name, limit=3)
                return {
                    "valid": False,
                    "status": "ROOM_UNAVAILABLE",
                    "message": f"Ruangan '{extraction.room_name}' tidak terdaftar di sistem kampus.",
                    "recommendations": recs,
                }

            # 4. Ruangan Sedang Direnovasi / Tidak Aktif
            if room_data["status"] != "ACTIVE":
                recs = find_room_recommendations(attendee_count=extraction.attendee_count or room_data["capacity"], hint_text=room_data["room_type"], limit=3)
                return {
                    "valid": False,
                    "status": "ROOM_UNAVAILABLE",
                    "message": f"Ruangan {room_data['room_name']} ({room_data['room_code']}) saat ini sedang berstatus {room_data['status']} dan tidak dapat dipinjam.",
                    "recommendations": recs,
                }

            # 5. Kapasitas Tidak Mencukupi
            if extraction.attendee_count and extraction.attendee_count > room_data["capacity"]:
                recs = find_room_recommendations(attendee_count=extraction.attendee_count, limit=3)
                return {
                    "valid": False,
                    "status": "INSUFFICIENT_CAPACITY",
                    "message": f"Kapasitas ruangan {room_data['room_name']} ({room_data['room_code']}) adalah {room_data['capacity']} orang, tidak mencukupi untuk {extraction.attendee_count} peserta Anda.",
                    "recommendations": recs,
                }

            # 6. Peralatan Tidak Tersedia (dan bukan peralatan add-on portabel)
            if extraction.required_equipment:
                for eq_type in extraction.required_equipment:
                    eq_norm = eq_type.strip().lower()

                    # Cek apakah terpasang di ruangan
                    q_eq = """
                        SELECT e.id FROM room_equipment re
                        JOIN equipment e ON e.id = re.equipment_id
                        WHERE re.room_id = ? AND LOWER(e.equipment_type) = ?
                    """
                    row_eq = conn.execute(q_eq, (room_data["id"], eq_norm)).fetchone()

                    # Jika tidak ada di ruangan, cek apakah bisa add-on portabel
                    if not row_eq:
                        if eq_norm not in PORTABLE_EQUIPMENT_TYPES:
                            recs = find_rooms_with_equipment(eq_norm, attendee_count=extraction.attendee_count or room_data["capacity"], limit=3)
                            return {
                                "valid": False,
                                "status": "EQUIPMENT_UNAVAILABLE",
                                "message": f"Ruangan {room_data['room_name']} ({room_data['room_code']}) tidak memiliki fasilitas '{eq_type}', dan '{eq_type}' bukan peralatan portabel/add-on.",
                                "recommendations": recs,
                            }
                        else:
                            # Cek ketersediaan unit aktif di inventaris kampus
                            q_addon = "SELECT id FROM equipment WHERE LOWER(equipment_type) = ? AND status = 'ACTIVE' LIMIT 1"
                            addon_row = conn.execute(q_addon, (eq_norm,)).fetchone()
                            if not addon_row:
                                return {
                                    "valid": False,
                                    "status": "EQUIPMENT_UNAVAILABLE",
                                    "message": f"Unit add-on portabel untuk '{eq_type}' sedang tidak tersedia di inventaris kampus.",
                                    "recommendations": [],
                                }

            # 7. Bentrok Jadwal Awal (jika ruangan, tanggal, dan jam sudah ada)
            if extraction.booking_date and extraction.start_time and extraction.end_time:
                q_conflict = """
                    SELECT event_name, start_time, end_time
                    FROM bookings
                    WHERE room_id = ?
                      AND booking_date = ?
                      AND status = 'CONFIRMED'
                      AND start_time < ?
                      AND end_time > ?
                    LIMIT 1
                """
                conflict = conn.execute(
                    q_conflict,
                    (room_data["id"], extraction.booking_date, extraction.end_time, extraction.start_time),
                ).fetchone()

                if conflict:
                    recs = find_room_recommendations(attendee_count=extraction.attendee_count or room_data["capacity"], limit=3)
                    return {
                        "valid": False,
                        "status": "ROOM_UNAVAILABLE",
                        "message": (
                            f"Jadwal bentrok pada {extraction.booking_date} ({extraction.start_time} - {extraction.end_time}). "
                            f"Ruangan {room_data['room_name']} telah terisi acara '{conflict['event_name']}' ({conflict['start_time']} - {conflict['end_time']})."
                        ),
                        "recommendations": recs,
                    }

    finally:
        conn.close()

    return {"valid": True, "status": "OK", "message": "", "recommendations": []}
