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
