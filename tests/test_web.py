"""
Unit & Integration Tests untuk CampusFlow Web UI
================================================
Memverifikasi fungsionalitas antarmuka web, perutean endpoint REST,
katalog ruangan, riwayat notifikasi fisik, dan peresetan sesi.
"""

import pytest
from starlette.testclient import TestClient
from src.web import app


@pytest.fixture
def client():
    return TestClient(app)


def test_web_index_html(client):
    """Memastikan halaman utama HTML dapat diakses dan memuat komponen UI."""
    response = client.get("/")
    assert response.status_code == 200
    assert "CampusFlow" in response.text
    assert "Notifikasi Departemen Lain" in response.text
    assert "Jejak Audit Alur Kerja" in response.text


def test_api_rooms_catalog(client):
    """Memastikan katalog ruangan dari database mengembalikan data lengkap."""
    response = client.get("/api/rooms")
    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    rooms = data["rooms"]
    assert len(rooms) >= 20
    # Verifikasi keberadaan ruangan UNPAR PPAG-203
    room_codes = [r["room_code"] for r in rooms]
    assert "PPAG-203" in room_codes
    assert "AUD-01" in room_codes


def test_api_notifications_outbox(client):
    """Memastikan pembacaan arsip berkas fisik notifikasi berjalan lancar."""
    response = client.get("/api/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert isinstance(data["notifications"], list)


def test_api_session_reset(client):
    """Memastikan endpoint reset sesi membersihkan status percakapan."""
    response = client.post("/api/reset", json={"session_id": "test_reset_session"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "RESET"


def test_api_booking_amendment_scenario(client):
    """
    Skenario Edit / Penambahan Fasilitas Pasca-Booking:
    1. Pesan ruangan sampai COMPLETED.
    2. Kirim pesan susulan: 'aduh lupa juga, perlu meja registrasi 2 biji, sama kursi tambahan 4 deh'
    3. Sistem HARUS memperbarui catatan reservasi (BOOKING_AMENDED), BUKAN bentrok dengan dirinya sendiri!
    """
    session_id = "test_amendment_session"
    client.post("/api/reset", json={"session_id": session_id})

    # Step 1: Pesan ruangan
    res1 = client.post("/api/chat", json={
        "session_id": session_id,
        "message": "Pesan Ruang Kuliah PPAG 202 untuk workshop AI 40 orang pada 2026-12-28 jam 09:00 sampai 11:00, pastikan proyektor siap.",
        "today": "2026-11-20",
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] in ("COMPLETED", "COMPLETED_PARTIAL")
    booking_ref = data1["booking_reference"]
    assert booking_ref is not None

    # Step 2: Kirim pesan susulan penambahan fasilitas pasca-konfirmasi
    res2 = client.post("/api/chat", json={
        "session_id": session_id,
        "message": "aduh lupa juga, perlu meja registrasi 2 biji, sama kursi tambahan 4 deh, sama kalau ada taplak meja mau",
        "today": "2026-11-20",
    })
    assert res2.status_code == 200
    data2 = res2.json()
    # Harus sukses diperbarui tanpa bentrok diri sendiri!
    assert data2["status"] == "BOOKING_AMENDED"
    assert "berhasil diperbarui" in data2["reply"]
    assert data2["booking_reference"] == booking_ref
    assert "meja registrasi" in data2["booking"]["updated_notes"]

