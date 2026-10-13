"""
Tes parser dan dua simpul pertama (parse_request, validate_requirements).
Tanpa DB dan tanpa MCP. "Hari ini" dikunci ke Senin 2026-09-21 agar deterministik.
"""

from datetime import date

import pytest

from src.agent.nodes import parse_request, validate_requirements
from src.agent.parser import parse_request_text
from src.agent.state import new_state

TODAY = date(2026, 9, 21)  # Senin


def parse(text):
    return parse_request_text(text, TODAY)


# --- Parser: kalimat lengkap ---------------------------------------------------

def test_srs_demo_request_relative_date():
    r = parse("Pesan auditorium utama untuk workshop AI 100 orang pada Selasa depan "
              "jam 09:00 sampai 11:00, pastikan proyektor berfungsi.")
    assert r["room_name"] == "AUD-01"
    assert r["event_name"] == "workshop AI"
    assert r["booking_date"] == "2026-09-29"      # Selasa di minggu kalender berikutnya
    assert r["date_relative"] is True
    assert (r["start_time"], r["end_time"]) == ("09:00", "11:00")
    assert r["attendee_count"] == 100
    assert r["required_equipment"] == ["projector"]
    assert r["ambiguities"] == []


def test_srs_tc01_explicit_date_is_not_relative():
    r = parse("Pesan auditorium utama untuk workshop AI 100 orang pada 23 September 2026 "
              "jam 09:00 sampai 11:00, pastikan proyektor berfungsi.")
    assert r["booking_date"] == "2026-09-23"
    assert r["date_relative"] is False
    assert r["event_name"] == "workshop AI"


def test_iso_date_digits_not_read_as_time():
    r = parse("Pesan SR-101 untuk rapat prodi 30 orang tanggal 2026-09-23 jam 13:00-15:00")
    assert r["room_name"] == "SR-101"
    assert r["booking_date"] == "2026-09-23"
    assert (r["start_time"], r["end_time"]) == ("13:00", "15:00")
    assert r["attendee_count"] == 30
    assert r["event_name"] == "rapat prodi"


def test_english_master_prompt_example_has_no_time():
    r = parse("Book the main auditorium for a 100-person AI workshop next Tuesday, "
              "check if the projector is working, and notify the facilities team.")
    assert r["room_name"] == "AUD-01"
    assert r["event_name"] == "AI workshop"
    assert r["booking_date"] == "2026-09-29"
    assert r["attendee_count"] == 100
    assert r["required_equipment"] == ["projector"]
    assert r["start_time"] is None and r["end_time"] is None   # jam tidak disebut -> harus ditanyakan


# --- Parser: tanggal relatif ---------------------------------------------------

@pytest.mark.parametrize("phrase, expected", [
    ("besok", "2026-09-22"),
    ("lusa", "2026-09-23"),
    ("hari ini", "2026-09-21"),
    ("tomorrow", "2026-09-22"),
    ("hari rabu", "2026-09-23"),        # tanpa penanda: terdekat setelah hari ini
    ("hari senin", "2026-09-28"),       # hari ini Senin -> Senin berikutnya, bukan hari ini
    ("rabu ini", "2026-09-23"),         # minggu kalender ini
    ("this friday", "2026-09-25"),
    ("kamis depan", "2026-10-01"),      # minggu kalender berikutnya
    ("next monday", "2026-09-28"),
    ("hari minggu depan", "2026-10-04"),
])
def test_relative_date_rules(phrase, expected):
    r = parse(f"Pesan AUD-01 untuk rapat {phrase} jam 09:00-10:00 20 orang")
    assert r["booking_date"] == expected
    assert r["date_relative"] is True


# --- Parser: ambigu / tidak lengkap (tidak boleh menebak) ----------------------

def test_vague_request_guesses_nothing():
    r = parse("Pesan ruangan untuk workshop minggu depan")
    assert r["room_name"] is None
    assert r["booking_date"] is None
    assert r["start_time"] is None and r["end_time"] is None
    assert r["attendee_count"] is None
    assert r["event_name"] == "workshop"
    assert any("minggu" in a for a in r["ambiguities"])


def test_minggu_depan_is_not_sunday():
    assert parse("Pesan AUD-01 untuk rapat minggu depan 20 orang")["booking_date"] is None


def test_two_rooms_is_ambiguous():
    r = parse("Pesan auditorium utama atau seminar 101 untuk rapat besok jam 09:00-10:00 20 orang")
    assert r["room_name"] is None
    assert any("ruangan" in a for a in r["ambiguities"])


def test_two_dates_is_ambiguous():
    r = parse("Pesan AUD-01 untuk rapat 2026-09-23 atau 2026-09-24 jam 09:00-10:00 20 orang")
    assert r["booking_date"] is None
    assert any("tanggal" in a.lower() for a in r["ambiguities"])


def test_invalid_calendar_date():
    r = parse("Pesan AUD-01 untuk rapat 31 Februari 2026 jam 09:00-10:00 20 orang")
    assert r["booking_date"] is None
    assert any("tidak valid" in a for a in r["ambiguities"])


def test_invalid_hour():
    r = parse("Pesan AUD-01 untuk rapat besok jam 25:00-26:00 20 orang")
    assert r["start_time"] is None
    assert any("Jam tidak valid" in a for a in r["ambiguities"])


def test_start_time_only():
    r = parse("Pesan AUD-01 untuk rapat besok jam 09:00 20 orang")
    assert r["start_time"] == "09:00" and r["end_time"] is None


def test_equipment_code_is_not_a_room():
    assert parse("cek PRJ-03 besok")["room_name"] is None


def test_computer_lab_name_is_not_equipment():
    r = parse("Pesan laboratorium komputer untuk pelatihan besok jam 09:00-10:00 20 orang")
    assert r["room_name"] == "LAB-401"
    assert r["required_equipment"] == []


# --- Simpul parse_request ------------------------------------------------------

def run_parse(text, **kw):
    s = new_state(text, "FAC-001", today="2026-09-21", **kw)
    return {**s, **parse_request(s)}


def test_parse_node_complete_request_passes():
    s = run_parse("Pesan AUD-01 untuk rapat 50 orang pada 23 September 2026 jam 09:00-11:00")
    assert s["workflow_status"] == "REQUEST_PARSED"
    assert s["missing_fields"] == []
    assert len(s["audit_trail"]) == 1 and s["audit_trail"][0]["decision"] == "PASS"


def test_parse_node_incomplete_request_fast_fails():
    s = run_parse("Pesan ruangan untuk workshop minggu depan")
    assert s["workflow_status"] == "INVALID_REQUEST"
    assert s["missing_fields"] == ["room_name", "booking_date", "start_time", "end_time", "attendee_count"]
    assert s["errors"] and "Data belum lengkap" in s["errors"][0]
    assert s["audit_trail"][0]["decision"] == "REJECT"


def test_parse_node_does_not_mutate_input_state():
    s = new_state("Pesan ruangan", "FAC-001", today="2026-09-21")
    parse_request(s)
    assert s["audit_trail"] == [] and s["errors"] == []


# --- Simpul validate_requirements ----------------------------------------------

def run_validate(text, **kw):
    s = run_parse(text, **kw)
    assert s["workflow_status"] == "REQUEST_PARSED", s["errors"]
    return {**s, **validate_requirements(s)}


def test_validate_passes_explicit_date():
    s = run_validate("Pesan AUD-01 untuk rapat 50 orang pada 23 September 2026 jam 09:00-11:00")
    assert s["workflow_status"] == "REQUIREMENTS_VALIDATED"


def test_validate_requires_confirmation_for_relative_date():
    text = "Pesan AUD-01 untuk rapat 50 orang pada Selasa depan jam 09:00-11:00"
    s = run_validate(text)
    assert s["workflow_status"] == "INVALID_REQUEST"
    assert "date_confirmation" in s["missing_fields"]
    assert "2026-09-29" in s["errors"][-1]

    confirmed = run_validate(text, date_confirmed=True)
    assert confirmed["workflow_status"] == "REQUIREMENTS_VALIDATED"


def test_validate_rejects_past_date():
    s = run_validate("Pesan AUD-01 untuk rapat 50 orang pada 1 September 2026 jam 09:00-11:00")
    assert s["workflow_status"] == "INVALID_REQUEST"
    assert any("sudah lewat" in e for e in s["errors"])


def test_validate_rejects_start_not_before_end():
    s = run_validate("Pesan AUD-01 untuk rapat 50 orang pada 23 September 2026 jam 11:00-09:00")
    assert s["workflow_status"] == "INVALID_REQUEST"
    assert any("lebih awal" in e for e in s["errors"])


def test_validate_rejects_zero_attendees():
    s = run_validate("Pesan AUD-01 untuk rapat 0 orang pada 23 September 2026 jam 09:00-11:00")
    assert s["workflow_status"] == "INVALID_REQUEST"
    assert any("lebih dari 0" in e for e in s["errors"])
