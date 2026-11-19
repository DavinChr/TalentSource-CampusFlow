"""
Unit Tests untuk Early Validator (Fast-Fail Check)
==================================================
Memverifikasi bahwa sistem mampu menolak permintaan yang mustahil secara dini:
1. Ruangan yang sedang direnovasi (UNDER_RENOVATION) langsung ditolak.
2. Fasilitas peralatan tetap yang tidak ada (mis. smartboard di LH-201) langsung ditolak.
3. Kapasitas ruangan yang tidak cukup langsung ditolak dengan rekomendasi ruangan besar.
4. Tanggal masa lalu langsung ditolak.
5. Jam mulai >= jam selesai langsung ditolak.
6. Bentrok jadwal langsung ditolak.
7. Permintaan sah lolos validasi dini (valid = True).
"""

import pytest
from src.agent.llm import LLMBookingExtraction
from src.agent.early_validator import check_early_constraints


def test_early_renovation_rejection():
    """Ruangan yang sedang direnovasi (LAB-401) langsung ditolak sejak awal."""
    ext = LLMBookingExtraction(
        room_name="LAB-401",
        event_name="praktikum koding",
        attendee_count=25,
    )
    result = check_early_constraints(ext, "2026-11-15")
    assert result["valid"] is False
    assert result["status"] == "ROOM_UNAVAILABLE"
    assert "UNDER_RENOVATION" in result["message"]
    assert len(result["recommendations"]) > 0


def test_early_equipment_impossible_rejection():
    """Peralatan tetap yang tidak tersedia di ruangan (smartboard di LH-201) langsung ditolak."""
    ext = LLMBookingExtraction(
        room_name="LH-201",
        required_equipment=["smartboard"],
    )
    result = check_early_constraints(ext, "2026-11-15")
    assert result["valid"] is False
    assert result["status"] == "EQUIPMENT_UNAVAILABLE"
    assert "smartboard" in result["message"].lower()
    # Harus menyajikan rekomendasi ruangan alternatif yang memiliki smartboard
    assert len(result["recommendations"]) > 0
    room_codes = [r["room_code"] for r in result["recommendations"]]
    assert any(code in room_codes for code in ["CR-301", "PPAG-LT1", "PPAG-LT2", "PPAG-201"])


def test_early_insufficient_capacity_rejection():
    """Jumlah peserta melebihi kapasitas ruangan langsung ditolak sejak awal."""
    ext = LLMBookingExtraction(
        room_name="SR-101",  # Kapasitas 50
        attendee_count=200,
    )
    result = check_early_constraints(ext, "2026-11-15")
    assert result["valid"] is False
    assert result["status"] == "INSUFFICIENT_CAPACITY"
    assert "50 orang" in result["message"]
    assert "200 peserta" in result["message"]
    # Harus merekomendasikan ruangan yang menampung 200+ orang
    assert len(result["recommendations"]) > 0
    assert all(r["capacity"] >= 200 for r in result["recommendations"])


def test_early_past_date_rejection():
    """Tanggal di masa lalu langsung ditolak."""
    ext = LLMBookingExtraction(
        room_name="AUD-01",
        booking_date="2020-01-01",
    )
    result = check_early_constraints(ext, "2026-11-15")
    assert result["valid"] is False
    assert result["status"] == "INVALID_REQUEST"
    assert "sudah lewat" in result["message"]


def test_early_invalid_time_rejection():
    """Jam mulai >= jam selesai langsung ditolak."""
    ext = LLMBookingExtraction(
        room_name="AUD-01",
        start_time="15:00",
        end_time="13:00",
    )
    result = check_early_constraints(ext, "2026-11-15")
    assert result["valid"] is False
    assert result["status"] == "INVALID_REQUEST"
    assert "Jam mulai" in result["message"]


def test_early_schedule_conflict_rejection():
    """Bentrok jadwal pada reservasi terkonfirmasi langsung ditolak."""
    # AUD-01 terisi pada 2026-09-23 jam 08:00 - 12:00
    ext = LLMBookingExtraction(
        room_name="AUD-01",
        booking_date="2026-09-23",
        start_time="09:00",
        end_time="11:00",
    )
    result = check_early_constraints(ext, "2026-09-21")
    assert result["valid"] is False
    assert result["status"] == "ROOM_UNAVAILABLE"
    assert "bentrok" in result["message"].lower()


def test_early_valid_request_passes():
    """Permintaan yang sah (PPAG-203 untuk yudisium dengan add-on proyektor) lolos validasi dini."""
    ext = LLMBookingExtraction(
        room_name="PPAG-203",
        booking_date="2027-01-08",
        start_time="08:00",
        end_time="11:00",
        attendee_count=200,
        required_equipment=["projector", "sound_system", "microphone"],
    )
    result = check_early_constraints(ext, "2026-11-15")
    assert result["valid"] is True
    assert result["status"] == "OK"
