"""
CampusFlow — Room Recommendation & Option Selection Engine
===========================================================
Modul cerdas perekomendasi ruangan untuk Human-in-the-Loop:
Ketika pengguna belum menentukan ruangan secara pasti (hanya menyebut tipe/keperluan
seperti 'ruang kelas' atau 'kapasitas 40 orang'), modul ini memberikan pilihan ganda
(opsi 1, 2, 3...) yang relevan dari database agar interaksi bersifat proaktif dan dinamis.
"""

from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"


def find_room_recommendations(
    attendee_count: Optional[int] = None,
    hint_text: str = "",
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """Mencari rekomendasi ruangan aktif yang paling cocok dari basis data."""
    if not DB_PATH.exists():
        return []

    hint_lower = (hint_text or "").lower()

    # Identifikasi preferensi tipe ruangan dari teks instruksi pengguna
    preferred_types = []
    if any(k in hint_lower for k in ["kelas", "kuliah", "ajar", "lecture", "materi", "pelatihan"]):
        preferred_types = ["lecture_hall", "seminar_room"]
    elif any(k in hint_lower for k in ["seminar", "workshop", "webinar", "simposium", "presentasi"]):
        preferred_types = ["seminar_room", "auditorium"]
    elif any(k in hint_lower for k in ["rapat", "meeting", "konferensi", "diskusi", "sidang"]):
        preferred_types = ["conference_room", "seminar_room"]
    elif any(k in hint_lower for k in ["komputer", "lab", "coding", "praktikum"]):
        preferred_types = ["computer_lab", "laboratory"]
    elif any(k in hint_lower for k in ["auditorium", "aula", "besar", "akbar", "wisuda"]):
        preferred_types = ["auditorium"]
    elif any(k in hint_lower for k in ["multifungsi", "serbaguna", "pameran", "fleksibel"]):
        preferred_types = ["multipurpose", "multifungsi", "auditorium"]

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # Hanya ambil ruangan dengan status ACTIVE
        query = """
            SELECT r.id, r.room_code, r.room_name, r.room_type, r.capacity, r.floor,
                   b.name as building_name, b.code as building_code
            FROM rooms r
            JOIN buildings b ON b.id = r.building_id
            WHERE r.status = 'ACTIVE'
            ORDER BY r.capacity ASC
        """
        rows = conn.execute(query).fetchall()
    finally:
        conn.close()

    candidates = [dict(r) for r in rows]
    if not candidates:
        return []

    # Scoring & pemeringkatan
    scored = []
    target_cap = attendee_count or 40

    for room in candidates:
        cap = room["capacity"]
        score = 0

        # Prioritas utama kampus UNPAR jika tersedia
        if room.get("building_code") in ("PPAG", "G0", "G9", "G2"):
            score += 500

        # Penalti jika kapasitas di bawah jumlah peserta
        if attendee_count and cap < attendee_count:
            score -= 1000
        else:
            # Semakin efisien kapasitasnya (tidak mubazir), semakin tinggi skornya
            diff = cap - target_cap
            score += max(0, 100 - diff)

        # Bonus kecocokan tipe ruangan (prioritas utama jika pengguna menyebutkan tipe spesifik)
        if room["room_type"] in preferred_types:
            idx = preferred_types.index(room["room_type"])
            score += 300 - (idx * 50)

        scored.append((score, room))

    # Urutkan berdasarkan skor tertinggi
    scored.sort(key=lambda x: x[0], reverse=True)

    recommendations = []
    for i, (_, room) in enumerate(scored[:limit], start=1):
        room_copy = dict(room)
        room_copy["option_number"] = i
        recommendations.append(room_copy)

    return recommendations


def format_room_options_prompt(
    options: List[Dict[str, Any]],
    attendee_count: Optional[int] = None,
    hint_text: Optional[str] = None,
) -> str:
    """Menyusun teks pertanyaan pilihan ganda yang sopan dan informatif."""
    if not options:
        return "Mohon sebutkan kode atau nama ruangan yang ingin Anda pesan."

    cap_str = f"kapasitas {attendee_count} orang" if attendee_count else "kegiatan Anda"
    lines = [f"Untuk kebutuhan {cap_str}, berikut beberapa pilihan ruangan yang sesuai dan tersedia:"]

    for opt in options:
        num = opt["option_number"]
        name = opt["room_name"]
        code = opt["room_code"]
        cap = opt["capacity"]
        bld = opt["building_name"]
        lines.append(f"  [{num}] {name} ({code}) — Kapasitas: {cap} orang ({bld})")

    max_opt = len(options)
    lines.append(f"\nSilakan pilih nomor [1-{max_opt}] atau ketik nama/kode ruangan yang Anda inginkan.")
    return "\n".join(lines)


def resolve_option_selection(
    user_reply: str,
    options: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Mencocokkan jawaban pengguna dengan salah satu opsi yang ditawarkan."""
    reply_clean = user_reply.strip().lower()

    # 1. Cek angka nomor opsi langsung (misal: "1", "nomor 1", "opsi 2", "pilihan 3")
    match_num = re.search(r"\b(?:opsi|pilihan|nomor|no\.?)?\s*([1-9])\b", reply_clean)
    if match_num:
        idx = int(match_num.group(1))
        for opt in options:
            if opt["option_number"] == idx:
                return opt

    # 2. Cek kode ruangan (misal: "LH-201", "lh 201", "SR-101")
    for opt in options:
        code_clean = opt["room_code"].lower().replace("-", "").replace(" ", "")
        user_no_dash = reply_clean.replace("-", "").replace(" ", "")
        if code_clean in user_no_dash or opt["room_code"].lower() in reply_clean:
            return opt

    # 3. Cek nama ruangan (misal: "ruang kuliah 201", "kuliah 201")
    for opt in options:
        name_lower = opt["room_name"].lower()
        if name_lower in reply_clean:
            return opt
        # Cek kata kunci parsial (misal: "kuliah 201")
        name_words = [w for w in name_lower.split() if w not in ("ruang", "gedung")]
        if name_words and all(w in reply_clean for w in name_words):
            return opt

    return None
