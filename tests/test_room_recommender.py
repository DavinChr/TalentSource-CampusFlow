"""
CampusFlow — Unit Tests for Room Recommender Engine
===================================================
Memastikan logika rekomendasi pilihan ganda ruangan berfungsi akurat:
1. Rekomendasi berdasarkan kapasitas dan kata kunci kelas (kuliah).
2. Pemilihan nomor opsi [1-4].
3. Format teks opsi yang ramah pengguna.
"""

from src.agent.room_recommender import (
    find_room_recommendations,
    format_room_options_prompt,
    resolve_option_selection,
)


def test_recommendation_for_class_40_pax():
    recs = find_room_recommendations(attendee_count=40, hint_text="Mau pinjam ruangan untuk kelas 40 orang")
    assert len(recs) >= 3

    # Ruang kuliah harus mendapat skor tinggi dan berada di rekomendasi
    codes = [r["room_code"] for r in recs]
    assert "LH-201" in codes or "PPAG-202" in codes or "G9-101" in codes

    # Seluruh rekomendasi harus berkapasitas >= 40
    for r in recs:
        assert r["capacity"] >= 40


def test_resolve_option_by_number():
    recs = find_room_recommendations(attendee_count=40, hint_text="kelas")
    selected = resolve_option_selection("pilih nomor 1", recs)
    assert selected is not None
    assert selected["option_number"] == 1


def test_resolve_option_by_name_or_code():
    recs = find_room_recommendations(attendee_count=50, hint_text="seminar")
    selected_code = resolve_option_selection("LH-201", recs)
    if any(r["room_code"] == "LH-201" for r in recs):
        assert selected_code["room_code"] == "LH-201"

    selected_name = resolve_option_selection("ruang kuliah 201", recs)
    if any(r["room_code"] == "LH-201" for r in recs):
        assert selected_name["room_code"] == "LH-201"


def test_format_options_prompt():
    recs = find_room_recommendations(attendee_count=40, hint_text="kelas")
    prompt = format_room_options_prompt(recs, attendee_count=40, hint_text="kelas")
    assert "[1]" in prompt
    assert "Kapasitas:" in prompt
    assert any(c in prompt for c in ["LH-201", "SR-101", "PPAG-202", "G9-101"])
