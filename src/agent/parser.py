"""
Parser deterministik teks permintaan -> field pemesanan terstruktur
===================================================================
Fallback tanpa LLM (REQ-NLU-05). Parser TIDAK menebak:
- field yang tidak ditemukan bernilai None;
- input bermakna ganda (dua tanggal, dua ruangan, jam tidak valid, "minggu depan"
  tanpa hari) dicatat di `ambiguities` dan field terkait dibiarkan None.
Keputusan lolos/gagal ada di node (parse_request, validate_requirements).

Aturan tanggal relatif (diputuskan di sini, perlu dikonfirmasi pengguna/mentor):
- "depan" / "next X"  -> hari X pada minggu kalender (Senin-Minggu) BERIKUTNYA.
- "ini" / "this X"    -> hari X pada minggu kalender INI (bisa sudah lewat).
- hari tanpa penanda  -> kemunculan terdekat SETELAH hari ini.
- besok / lusa / hari ini / tomorrow / today -> hitung dari `today`.
Semua tanggal dari kata relatif ditandai date_relative=True.
"""

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ponytail: tabel statis mengikuti data/database/seed.sql. Jika ruangan bertambah,
# ganti dengan pencarian ke DB atau parser LLM.
ROOMS: Dict[str, List[str]] = {
    "AUD-01": ["auditorium utama", "main auditorium"],
    "SR-101": ["ruang seminar 101", "seminar 101"],
    "SR-102": ["ruang seminar 102", "seminar 102"],
    "CR-301": ["ruang konferensi eksekutif", "konferensi eksekutif", "executive conference room"],
    "LH-201": ["ruang kuliah 201", "kuliah 201"],
    "LH-202": ["ruang kuliah 202", "kuliah 202"],
    "LAB-401": ["laboratorium komputer", "lab komputer", "computer lab"],
    "SR-ENG1": ["ruang seminar teknik", "seminar teknik"],
    # UNPAR Rooms
    "PPAG-AUD": ["auditorium utama ppag", "auditorium ppag", "ppag aud"],
    "PPAG-LT1": ["lecture theater 1 ppag", "lecture theater 1", "lt 1 ppag", "lt1 ppag", "ppag lt1"],
    "PPAG-LT2": ["lecture theater 2 ppag", "lecture theater 2", "lt 2 ppag", "lt2 ppag", "ppag lt2"],
    "PPAG-LT3": ["lecture theater 3 ppag", "lecture theater 3", "lt 3 ppag", "lt3 ppag", "ppag lt3"],
    "PPAG-201": ["lacture hall ppag", "lecture hall ppag", "lacture hall", "lecture hall", "ppag 201"],
    "PPAG-202": ["ruang kuliah ppag 202", "ppag 202", "ruang kuliah 202"],
    "PPAG-203": ["ruang multifungsi", "multifungsi ppag", "ruang serbaguna ppag", "ruang mulfung", "mulfung", "mulfung ppag", "ruang mulfung ppag", "ruang multifungsi ppag", "ppag 203"],
    "G0-OR": ["operation room rektorat", "operation room", "or rektorat", "g0-or"],
    "G9-AULA": ["aula driekore", "aula fe", "aula feb", "aula gedung 9", "g9-aula"],
    "G9-101": ["ruang kuliah 9101", "kelas 9101", "ruang 9101", "9101", "g9-101"],
    "G9-LAB1": ["laboratorium komputer 1", "lab komputer g9-1", "lab komputasi 1", "g9-lab1"],
    "G9-LAB2": ["laboratorium komputer 2", "lab komputer g9-2", "lab komputasi 2", "g9-lab2"],
    "G9-LAB3": ["laboratorium komputer 3", "lab komputer g9-3", "lab komputasi 3", "g9-lab3"],
    "G2-MC": ["ruang peradilan semu", "moot court", "peradilan semu", "g2-mc"],
    "G2-SEM": ["ruang seminar b. arief sidharta", "ruang seminar fh", "seminar hukum", "g2-sem"],
}

# Nilai kunci = enum equipment_type di schema.sql. Tidak ada deteksi negasi ("tanpa proyektor").
EQUIPMENT: Dict[str, str] = {
    "projector": r"proyektor|projector",
    "microphone": r"mikrofon|microphone|mic",
    "sound_system": r"sound\s*system|soundsystem|sistem\s+suara",
    "smartboard": r"smart\s*board",
    "whiteboard": r"whiteboard|papan\s+tulis",
    "video_conferencing": r"video\s*conferenc\w*|vidcon|video\s+konferensi",
}

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
_RELATIVE = {"hari ini": 0, "today": 0, "besok": 1, "tomorrow": 1, "lusa": 2, "day after tomorrow": 2}

_ID_WD = "senin|selasa|rabu|kamis|jumat|sabtu"
_EN_WD = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

_ALIAS_TO_CODE = {a: code for code, aliases in ROOMS.items() for a in (code.lower(), *aliases)}
_ROOM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(a) for a in sorted(_ALIAS_TO_CODE, key=len, reverse=True)) + r")\b",
    re.I,
)

_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY_RE = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_ALT})(?:\s+(\d{{4}}))?\b", re.I)
_REL_RE = re.compile(r"\b(hari\s+ini|today|besok|tomorrow|lusa|day\s+after\s+tomorrow)\b", re.I)
# "minggu" (Indonesia) baru dianggap hari Minggu bila didahului "hari"; "minggu depan" = pekan depan.
_WEEKDAY_RE = re.compile(
    rf"\b(?:(?:(next|this)\s+)?({_EN_WD})"
    rf"|(?:hari\s+)?({_ID_WD})(?:\s+(depan|ini))?"
    rf"|hari\s+(minggu)(?:\s+(depan|ini))?)\b",
    re.I,
)
_WEEK_PHRASE_RE = re.compile(r"\b(?:(?:minggu|pekan)\s+(?:depan|ini)|(?:next|this)\s+week)\b", re.I)

_SEP = r"(?:-|–|sampai(?:\s+dengan)?|sampe|s/d|hingga|to|until)"
_T_MIN = re.compile(rf"\b(\d{{1,2}})[:.](\d{{2}})\s*{_SEP}\s*(\d{{1,2}})[:.](\d{{2}})\b", re.I)
_T_CUE = re.compile(
    rf"\b(?:jam|pukul|from|at)\s*(\d{{1,2}})(?:[:.](\d{{2}}))?\s*{_SEP}\s*(\d{{1,2}})(?:[:.](\d{{2}}))?\b",
    re.I,
)
_T_ONE = re.compile(r"\b(?:jam|pukul|from|at)\s*(\d{1,2})[:.](\d{2})\b", re.I)

_ATT_RE = re.compile(
    r"\b(\d{1,4})\s*-?\s*(?:orang|peserta|pax|people|persons?|attendees|participants)\b", re.I
)

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
    """Mengembalikan semua kecocokan dan teks dengan bagian yang cocok diganti spasi.

    Spasi (bukan penghapusan) dipakai agar indeks tetap sejajar dan bagian yang
    sudah dipakai tidak terbaca ulang oleh ekstraktor berikutnya (mis. angka
    pada tanggal ISO terbaca sebagai jam).
    """
    matches = list(rx.finditer(text))
    for m in reversed(matches):
        text = text[: m.start()] + " " * (m.end() - m.start()) + text[m.end():]
    return matches, text


def _resolve_weekday(m: "re.Match[str]", today: date) -> date:
    modifier = (m.group(1) or m.group(4) or m.group(6) or "").lower()
    weekday = _WEEKDAYS[(m.group(2) or m.group(3) or m.group(5)).lower()]
    this_monday = today - timedelta(days=today.weekday())
    if modifier in ("depan", "next"):
        return this_monday + timedelta(days=7 + weekday)
    if modifier in ("ini", "this"):
        return this_monday + timedelta(days=weekday)
    return today + timedelta(days=(weekday - today.weekday() - 1) % 7 + 1)


def _extract_dates(text: str, today: date):
    found: List[Tuple[date, bool, str]] = []
    bad: List[str] = []

    def scan(rx, convert, relative):
        nonlocal text
        matches, text = _consume(rx, text)
        for m in matches:
            try:
                found.append((convert(m), relative, " ".join(m.group(0).split())))
            except ValueError:  # mis. 31 Februari
                bad.append(m.group(0).strip())

    scan(_ISO_RE, lambda m: date(int(m[1]), int(m[2]), int(m[3])), False)
    scan(_DMY_RE, lambda m: date(int(m[3] or today.year), _MONTHS[m[2].lower()], int(m[1])), False)
    scan(_REL_RE, lambda m: today + timedelta(days=_RELATIVE[" ".join(m[1].lower().split())]), True)
    scan(_WEEKDAY_RE, lambda m: _resolve_weekday(m, today), True)
    return found, bad, text


def _extract_times(text: str):
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
    """Mengurai teks bebas menjadi field pemesanan. Lihat docstring modul untuk aturannya."""
    today = today or date.today()
    work = text
    ambiguities: List[str] = []

    # 1. Ruangan (diblank lebih dulu agar kata seperti "komputer" tidak terbaca sebagai alat)
    matches, work = _consume(_ROOM_RE, work)
    rooms = sorted({_ALIAS_TO_CODE[" ".join(m.group(0).lower().split())] for m in matches})
    room_name = rooms[0] if len(rooms) == 1 else None
    if len(rooms) > 1:
        ambiguities.append(f"Lebih dari satu ruangan disebut: {', '.join(rooms)}.")

    # 2. Tanggal
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
        ambiguities.append("Tanggal belum spesifik (hanya menyebut minggu/pekan); sebutkan hari atau tanggal.")

    # 3. Jam
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

    # 4. Jumlah peserta
    matches, work = _consume(_ATT_RE, work)
    counts = {int(m[1]) for m in matches}
    attendee_count = next(iter(counts)) if len(counts) == 1 else None
    if len(counts) > 1:
        ambiguities.append("Lebih dari satu jumlah peserta disebut: " + ", ".join(map(str, sorted(counts))) + ".")

    # 5. Peralatan
    equipment = sorted(k for k, pat in EQUIPMENT.items() if re.search(rf"\b(?:{pat})\b", work, re.I))

    # 6. Nama acara: frasa setelah "untuk"/"for" sampai kata penghenti
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
