"""
CampusFlow — Pengurai Kalimat Permintaan (Natural Language Parser)
===================================================================
Fungsi:
Modul ini bertugas membaca kalimat bebas yang diketik oleh pengguna, lalu
mengambil informasi-informasi penting seperti:
1. Ruangan apa yang mau dipinjam?
2. Tanggal berapa acaranya?
3. Dari jam berapa sampai jam berapa?
4. Berapa orang pesertanya?
5. Butuh peralatan apa saja (misal: proyektor, mikrofon)?
6. Apa nama acaranya?

Data Acuan:
Menggunakan data ruangan (sesuai basis data awal / seed.sql).
"""

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 1. DAFTAR RUANGAN RESMI KAMPUS (DATA AWAL)
# Kamus ini menghubungkan sebutan sehari-hari pengguna dengan kode resmi ruangan di kampus.
# Contoh: Jika pengguna mengetik "auditorium utama", sistem mencocokkannya ke kode "AUD-01".
ROOMS: Dict[str, List[str]] = {
    "AUD-01": ["auditorium utama", "main auditorium", "auditorium"],
    "SR-101": ["ruang seminar 101", "seminar 101"],
    "SR-102": ["ruang seminar 102", "seminar 102"],
    "CR-301": ["ruang konferensi eksekutif", "konferensi eksekutif", "ruang konferensi 301", "executive conference room"],
    "LH-201": ["ruang kuliah 201", "kuliah 201"],
    "LH-202": ["ruang kuliah 202", "kuliah 202"],
    "LAB-401": ["laboratorium komputer", "lab komputer", "computer lab", "lab-cs1"],
    "SR-ENG1": ["ruang seminar teknik", "seminar teknik"],
}

# 2. DAFTAR PERALATAN FASILITAS
# Pola kata untuk mendeteksi peralatan yang diminta pengguna.
# Menggunakan pola RegEx (pencocokan kata fleksibel).
EQUIPMENT: Dict[str, str] = {
    "projector": r"proyektor|projector",
    "microphone": r"mikrofon|microphone|mic",
    "sound_system": r"sound\s*system|sistem\s+suara",
    "smartboard": r"smart\s*board",
    "whiteboard": r"whiteboard|papan\s+tulis",
    "video_conferencing": r"video\s*conferenc\w*|vidcon|video\s+konferensi",
}

# 3. KAMUS NAMA BULAN & HARI (INDONESIA & INGGRIS)
_MONTHS = {
    "januari": 1, "january": 1, "februari": 2, "february": 2, "maret": 3, "march": 3,
    "april": 4, "mei": 5, "may": 5, "juni": 6, "june": 6, "juli": 7, "july": 7,
    "agustus": 8, "august": 8, "september": 9, "oktober": 10, "october": 10,
    "november": 11, "desember": 12, "december": 12,
}

_WEEKDAYS = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, "jumat": 4, "sabtu": 5, "minggu": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
    "saturday": 5, "sunday": 6,
}

_RELATIVE = {
    "hari ini": 0, "today": 0,
    "besok": 1, "tomorrow": 1,
    "lusa": 2, "day after tomorrow": 2,
}

# Pemetaan pencarian sebutan nama ruangan ke kode aslinya
_ALIAS_TO_CODE = {a: code for code, aliases in ROOMS.items() for a in (code.lower(), *aliases)}
_ROOM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(a) for a in sorted(_ALIAS_TO_CODE, key=len, reverse=True)) + r")\b",
    re.I,
)

# Pola tanggal angka format standar internasional: 2026-09-23
_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Pola tanggal teks Indonesia: 23 September 2026 atau 23 September
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DMY_RE = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_ALT})(?:\s+(\d{{4}}))?\b", re.I)

# Pola kata tanggal relatif: hari ini, besok, lusa
_REL_RE = re.compile(r"\b(hari\s+ini|today|besok|tomorrow|lusa|day\s+after\s+tomorrow)\b", re.I)

# Pola penyebutan hari dalam sepekan: "hari selasa", "selasa depan", "rabu ini"
_ID_WD = "senin|selasa|rabu|kamis|jumat|sabtu"
_EN_WD = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_WEEKDAY_RE = re.compile(
    rf"\b(?:(?:(next|this)\s+)?({_EN_WD})"
    rf"|(?:hari\s+)?({_ID_WD})(?:\s+(depan|ini))?"
    rf"|hari\s+(minggu)(?:\s+(depan|ini))?)\b",
    re.I,
)
_WEEK_PHRASE_RE = re.compile(r"\b(?:(?:minggu|pekan)\s+(?:depan|ini)|(?:next|this)\s+week)\b", re.I)

# Pola jam mulai sampai selesai: "09:00 - 11:00", "jam 09.00 sampai 11.00"
_SEP = r"(?:-|–|sampai(?:\s+dengan)?|s/d|hingga|to|until)"
_T_MIN = re.compile(rf"\b(\d{{1,2}})[:.](\d{{2}})\s*{_SEP}\s*(\d{{1,2}})[:.](\d{{2}})\b", re.I)
_T_CUE = re.compile(
    rf"\b(?:jam|pukul|from|at)\s*(\d{{1,2}})(?:[:.](\d{{2}}))?\s*{_SEP}\s*(\d{{1,2}})(?:[:.](\d{{2}}))?\b",
    re.I,
)
_T_ONE = re.compile(r"\b(?:jam|pukul|from|at)\s*(\d{1,2})[:.](\d{2})\b", re.I)

# Pola jumlah orang/peserta: "100 orang", "40 peserta", "50 pax"
_ATT_RE = re.compile(
    r"\b(\d{1,4})\s*-?\s*(?:orang|peserta|pax|people|persons?|attendees|participants)\b", re.I
)

# Kata-kata pemisah untuk membatasi pengambilan nama acara
_STOP = (
    "pada|hari|tanggal|jam|pukul|besok|lusa|today|tomorrow|next|this|on|from|at|di|in|dan|and|"
    "minggu|pekan|week|serta|lalu|then|check|cek|periksa|notify|beritahu|kabari|pastikan|"
    "with|dengan|menggunakan|using|yang"
)
_EVENT_RE = re.compile(
    rf"\b(?:untuk|for)\s+(?:(?:an?|acara|kegiatan)\s+)?(?!(?:{_STOP})\b)(.+?)"
    rf"(?=\s*[,.;]|\s+(?:{_STOP})\b|\s*$)",
    re.I,
)


def _consume(rx: "re.Pattern[str]", text: str) -> Tuple[List["re.Match[str]"], str]:
    """
    Fungsi Pembantu:
    Mencari bagian teks yang cocok dengan pola tertentu, lalu mengganti kata
    yang sudah ditemukan dengan spasi kosong.
    Tujuannya: agar kata yang sudah terpakai (misal angka tanggal '2026') tidak
    salah dibaca ulang oleh pendeteksi berikutnya sebagai jam atau jumlah orang.
    """
    matches = list(rx.finditer(text))
    for m in reversed(matches):
        text = text[: m.start()] + " " * (m.end() - m.start()) + text[m.end():]
    return matches, text


def _resolve_weekday(m: "re.Match[str]", today: date) -> date:
    """
    Fungsi Pembantu:
    Menghitung tanggal pasti berdasarkan sebutan hari.
    Contoh: Jika hari ini Senin tanggal 21, maka 'Rabu' dihitung menjadi tanggal 23,
    dan 'Rabu depan' dihitung menjadi hari Rabu di pekan berikutnya (tanggal 30).
    """
    modifier = (m.group(1) or m.group(4) or m.group(6) or "").lower()
    weekday = _WEEKDAYS[(m.group(2) or m.group(3) or m.group(5)).lower()]
    this_monday = today - timedelta(days=today.weekday())
    if modifier in ("depan", "next"):
        return this_monday + timedelta(days=7 + weekday)
    if modifier in ("ini", "this"):
        return this_monday + timedelta(days=weekday)
    return today + timedelta(days=(weekday - today.weekday() - 1) % 7 + 1)


def _extract_dates(text: str, today: date):
    """Mendeteksi semua tanggal yang ada di dalam teks."""
    found: List[Tuple[date, bool, str]] = []
    bad: List[str] = []

    def scan(rx, convert, relative):
        nonlocal text
        matches, text = _consume(rx, text)
        for m in matches:
            try:
                found.append((convert(m), relative, " ".join(m.group(0).split())))
            except ValueError:  # Misalnya penanggalan mustahil seperti 31 Februari
                bad.append(m.group(0).strip())

    scan(_ISO_RE, lambda m: date(int(m[1]), int(m[2]), int(m[3])), False)
    scan(_DMY_RE, lambda m: date(int(m[3] or today.year), _MONTHS[m[2].lower()], int(m[1])), False)
    scan(_REL_RE, lambda m: today + timedelta(days=_RELATIVE[" ".join(m[1].lower().split())]), True)
    scan(_WEEKDAY_RE, lambda m: _resolve_weekday(m, today), True)
    return found, bad, text


def _extract_times(text: str):
    """Mendeteksi jam mulai dan jam selesai (misal: 09:00 sampai 11:00)."""
    ranges = set()
    bad: List[str] = []
    for rx in (_T_MIN, _T_CUE):
        matches, text = _consume(rx, text)
        for m in matches:
            h1, m1, h2, m2 = int(m[1]), int(m[2] or 0), int(m[3]), int(m[4] or 0)
            if max(h1, h2) > 23 or max(m1, m2) > 59:
                bad.append(m.group(0).strip())
            else:
                ranges.add((f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"))
    singles = set()
    if not ranges and not bad:
        matches, text = _consume(_T_ONE, text)
        for m in matches:
            if int(m[1]) > 23 or int(m[2]) > 59:
                bad.append(m.group(0).strip())
            else:
                singles.add(f"{int(m[1]):02d}:{int(m[2]):02d}")
    return ranges, singles, bad, text


def parse_request_text(text: str, today: Optional[date] = None) -> Dict[str, Any]:
    """
    Fungsi Eksekusi Utama:
    Menerima kalimat mentah pengguna, menguraikannya secara bertahap, dan
    mengembalikan data pesanan dalam bentuk kamus (dictionary) yang rapi.
    """
    today = today or date.today()
    work = text
    ambiguities: List[str] = []

    # 1. Mendeteksi Ruangan
    matches, work = _consume(_ROOM_RE, work)
    rooms = sorted({_ALIAS_TO_CODE[" ".join(m.group(0).lower().split())] for m in matches})
    room_name = rooms[0] if len(rooms) == 1 else None
    if len(rooms) > 1:
        ambiguities.append(f"Lebih dari satu ruangan disebut: {', '.join(rooms)}.")

    # 2. Mendeteksi Tanggal
    found, bad_dates, work = _extract_dates(work, today)
    dates = {d for d, _, _ in found}
    booking_date, date_relative, date_text = None, False, None
    if len(dates) == 1:
        booking_date = next(iter(dates)).isoformat()
        _, date_relative, date_text = found[0]
    elif len(dates) > 1:
        ambiguities.append(
            "Lebih dari satu tanggal disebut: " + ", ".join(sorted(d.isoformat() for d in dates)) + "."
        )
    ambiguities += [f"Tanggal tidak valid: '{b}'." for b in bad_dates]
    if not dates and _WEEK_PHRASE_RE.search(work):
        ambiguities.append("Tanggal belum spesifik (hanya menyebut minggu/pekan); sebutkan hari atau tanggal pasti.")

    # 3. Mendeteksi Jam
    ranges, singles, bad_times, work = _extract_times(work)
    start_time = end_time = None
    if len(ranges) == 1:
        start_time, end_time = next(iter(ranges))
    elif len(ranges) > 1:
        ambiguities.append("Lebih dari satu rentang jam disebut.")
    elif len(singles) == 1:
        start_time = next(iter(singles))
    elif len(singles) > 1:
        ambiguities.append("Lebih dari satu jam mulai disebut.")
    ambiguities += [f"Jam tidak valid: '{b}'." for b in bad_times]

    # 4. Mendeteksi Jumlah Peserta
    matches, work = _consume(_ATT_RE, work)
    counts = {int(m[1]) for m in matches}
    attendee_count = next(iter(counts)) if len(counts) == 1 else None
    if len(counts) > 1:
        ambiguities.append("Lebih dari satu jumlah peserta disebut: " + ", ".join(map(str, sorted(counts))) + ".")

    # 5. Mendeteksi Peralatan yang Dibutuhkan
    equipment = sorted(k for k, pat in EQUIPMENT.items() if re.search(rf"\b(?:{pat})\b", work, re.I))

    # 6. Mendeteksi Nama Kegiatan / Acara (kata setelah 'untuk' atau 'for')
    event_name = None
    m = _EVENT_RE.search(work)
    if m:
        event_name = " ".join(m.group(1).split()).strip(" ,.;:") or None

    return {
        "room_name": room_name,
        "event_name": event_name,
        "booking_date": booking_date,
        "date_relative": date_relative,
        "date_text": date_text,
        "start_time": start_time,
        "end_time": end_time,
        "attendee_count": attendee_count,
        "required_equipment": equipment,
        "ambiguities": ambiguities,
    }


if __name__ == "__main__":
    import json

    print("=" * 70)
    print(" CampusFlow - Uji Coba Pengurai Kalimat (Parser Deterministik)")
    print("=" * 70)

    contoh_kasus = [
        "Pesan auditorium utama untuk workshop AI 100 orang pada 23 September 2026 jam 09:00 sampai 11:00, pastikan proyektor berfungsi.",
        "Pesan Ruang Seminar 101 untuk diskusi 15 orang besok jam 10:00 sampai 12:00",
        "Pesan Ruang Konferensi 301 untuk rapat umum 50 orang pada 25 September 2026",
    ]

    for i, kalimat in enumerate(contoh_kasus, 1):
        print(f"\n[Kasus {i}]")
        print(f"Kalimat Pengguna : \"{kalimat}\"")
        hasil = parse_request_text(kalimat, today=date(2026, 9, 21))
        print("Hasil Parsing    :")
        print(json.dumps(hasil, indent=2, ensure_ascii=False))

