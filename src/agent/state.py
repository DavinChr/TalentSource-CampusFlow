"""
CampusFlow — Manajemen Status Agen (Agent State)
================================================
Modul ini mendefinisikan wadah data terstruktur (AgentState) yang dibawa dan
diperbarui di setiap langkah alur kerja agen.

Bahasa Awam:
Bayangkan AgentState seperti sebuah 'Formulir Digital' pemesanan ruangan.
Formulir ini mencatat semua hal: apa yang diminta pemohon, hasil pengecekan
ruangan di database, hasil pengecekan peralatan, sampai nomor bukti pemesanan.
Setiap petugas (simpul/node) membaca formulir ini dan menambahkan catatannya.
"""

from datetime import date, datetime, timezone
from typing import Any, List, Literal, Optional, TypedDict
import uuid

# Daftar status tahapan alur kerja yang valid (mesin status)
WorkflowStatus = Literal[
    "REQUEST_RECEIVED",         # Permintaan baru diterima dari pengguna
    "REQUEST_PARSED",           # Teks berhasil diurai menjadi data terstruktur
    "REQUIREMENTS_VALIDATED",   # Syarat dasar (waktu & peserta) dinyatakan lengkap
    "ROOM_SEARCH",              # Proses pencarian data ruangan
    "ROOM_AVAILABILITY_CHECK",  # Pengecekan jadwal bentrok di ruangan
    "CAPACITY_VALIDATION",      # Pengecekan kapasitas ruangan vs jumlah peserta
    "EQUIPMENT_CHECK",          # Pengecekan ketersediaan dan status fisik alat
    "EQUIPMENT_STATUS_CHECK",   # Verifikasi log operasional peralatan di filesystem
    "BOOKING_AUTHORIZATION",    # Evaluasi otorisasi (apakah semua syarat lolos)
    "BOOKING_WRITE",            # Proses transaksi penyimpanan pemesanan ke basis data
    "COMPLETED",                # Alur kerja pemesanan selesai dengan sukses penuh
    "INVALID_REQUEST",          # Permintaan tidak valid / data tidak dapat diproses
    "ROOM_UNAVAILABLE",         # Ruangan bentrok / tidak tersedia pada jam tersebut
    "INSUFFICIENT_CAPACITY",    # Kapasitas ruangan tidak cukup menampung peserta
    "EQUIPMENT_UNAVAILABLE",    # Peralatan yang diminta rusak atau tidak tersedia
    "EQUIPMENT_STATUS_UNKNOWN", # Status kondisi fisik alat tidak dapat diverifikasi
    "WORKFLOW_ABORTED",         # Alur kerja dibatalkan karena ada syarat gagal
    "DATABASE_ERROR",           # Terjadi kegagalan saat penulisan ke basis data
    "NEEDS_CLARIFICATION",      # Perlu konfirmasi balik ke pengguna (ada info kurang)
]

# Status ketersediaan sumber daya
ResourceStatus = Literal["AVAILABLE", "UNAVAILABLE", "UNKNOWN", "ERROR"]

# Status kondisi fisik peralatan kampus
EquipmentStatus = Literal[
    "OPERATIONAL",        # Berfungsi normal dan siap digunakan
    "UNDER_MAINTENANCE",  # Sedang dalam perbaikan / servis
    "FAULTY",             # Mengalami kerusakan aktif
    "UNKNOWN",            # Kondisi fisik tidak dapat dipastikan
    "CONFLICT",           # Terdapat perbedaan antara status DB dan catatan fisik
    "NOT_FOUND"           # Data peralatan tidak ditemukan
]


class BookingRequest(TypedDict):
    """
    Menyimpan hasil penguraian teks pemesanan dari pengguna.
    Jika suatu informasi belum disebutkan pengguna, nilainya adalah None.
    """
    room_name: Optional[str]          # Kode ruangan resmi kampus, contoh: "AUD-01", "SR-101"
    event_name: Optional[str]         # Nama kegiatan/acara, contoh: "Workshop AI"
    booking_date: Optional[str]       # Tanggal pemesanan format YYYY-MM-DD
    date_relative: bool               # True jika tanggal berasal dari kata relatif ("besok", "lusa")
    date_text: Optional[str]          # Teks asli penyebutan tanggal oleh pengguna
    start_time: Optional[str]         # Jam mulai (format 24 jam HH:MM), contoh: "09:00"
    end_time: Optional[str]           # Jam selesai (format 24 jam HH:MM), contoh: "11:00"
    attendee_count: Optional[int]     # Perkiraan jumlah peserta acara (orang)
    required_equipment: List[str]     # Daftar alat yang dibutuhkan, contoh: ["projector"]


class ValidationResult(TypedDict):
    """Hasil pemeriksaan suatu syarat (apakah lolos atau gagal, beserta alasannya)."""
    passed: bool                      # True jika lolos, False jika gagal
    reason: Optional[str]             # Penjelasan jika terjadi kegagalan
    details: Optional[Any]            # Data pendukung hasil validasi


class AuditStep(TypedDict):
    """Catatan riwayat audit tiap langkah untuk transparansi dan investigasi sistem."""
    step_index: int                   # Urutan langkah (1, 2, 3, dst.)
    timestamp: str                    # Waktu eksekusi dalam format standar ISO UTC
    step_name: str                    # Nama langkah yang sedang berjalan
    evidence: Any                     # Bukti nyata yang didapat dari database atau berkas fisik
    decision: str                     # Keputusan langkah tersebut ("PASS", "REJECT", "ABORT")
    next_state: str                   # Status alur kerja selanjutnya


class AgentState(TypedDict):
    """
    Struktur data utama alur kerja CampusFlow.
    Objek ini dibawa berpindah dari satu simpul alur ke simpul berikutnya.
    """
    # 1. Data Masukan Awal
    request_raw: str                  # Kalimat asli yang diketik oleh pengguna
    requester: str                    # ID identitas pemohon fasilitas (misal: "FAC-001")
    today: str                        # Tanggal acuan sistem saat ini (YYYY-MM-DD)
    date_confirmed: bool              # Penanda apakah pengguna sudah mengonfirmasi tanggal relatif

    # 2. Hasil Pemahaman Kalimat (Parsing)
    parsed_request: Optional[BookingRequest]
    missing_fields: List[str]         # Daftar info penting yang belum diisi (misal: jam selesai)

    # 3. Data Ruangan
    candidate_rooms: List[dict]       # Daftar ruangan yang potensial memenuhi syarat
    selected_room: Optional[dict]     # Data lengkap ruangan yang dipilih untuk dipesan

    # 4. Hasil Pemeriksaan & Validasi
    room_availability: Optional[ResourceStatus]        # Status ketersediaan jadwal ruangan
    room_availability_details: Optional[dict]          # Rincian jadwal bentrok jika ada
    capacity_validation: Optional[ValidationResult]    # Hasil cek muat tidaknya ruangan
    equipment_results: Optional[List[dict]]            # Hasil daftar peralatan ruangan
    equipment_status: Optional[EquipmentStatus]        # Status kondisi fisik peralatan
    equipment_status_details: Optional[dict]          # Bukti catatan dari log pemeliharaan fisik
    all_validations_passed: bool                       # True hanya jika semua cek di atas lulus
    booking_authorized: bool                           # True jika pemesanan sudah disetujui

    # 5. Bukti Pemesanan Akhir
    booking_id: Optional[int]                          # Nomor ID pemesanan di tabel database
    booking_reference: Optional[str]                   # Nomor referensi unik (contoh: "BK-2026-001")

    # 6. Kontrol Alur Kerja & Audit
    workflow_status: WorkflowStatus                    # Tahap status alur saat ini
    clarification_message: Optional[str]               # Pesan tanya balik jika info kurang
    errors: List[str]                                  # Catatan pesan kesalahan jika ada
    trace_id: str                                      # ID pelacak unik untuk sesi ini
    audit_trail: List[AuditStep]                       # Riwayat lengkap jejak audit alur


def new_state(
    request_raw: str,
    requester: str,
    today: Optional[str] = None,
    date_confirmed: bool = False,
) -> AgentState:
    """
    Membuat formulir status awal (state) dengan nilai default saat pengguna
    pertama kali memasukkan kalimat permintaan.
    """
    return {
        "request_raw": request_raw,
        "requester": requester,
        "today": today or date.today().isoformat(),
        "date_confirmed": date_confirmed,
        "parsed_request": None,
        "missing_fields": [],
        "candidate_rooms": [],
        "selected_room": None,
        "room_availability": None,
        "room_availability_details": None,
        "capacity_validation": None,
        "equipment_results": None,
        "equipment_status": None,
        "equipment_status_details": None,
        "all_validations_passed": False,
        "booking_authorized": False,
        "booking_id": None,
        "booking_reference": None,
        "workflow_status": "REQUEST_RECEIVED",
        "clarification_message": None,
        "errors": [],
        "trace_id": f"trace-{uuid.uuid4().hex[:12]}",
        "audit_trail": [],
    }


def add_audit(
    state: AgentState,
    step_name: str,
    evidence: Any,
    decision: str,
    next_state: str,
) -> List[AuditStep]:
    """
    Menambahkan satu catatan riwayat baru ke jejak audit tanpa merusak data sebelumnya.
    """
    step: AuditStep = {
        "step_index": len(state["audit_trail"]) + 1,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step_name": step_name,
        "evidence": evidence,
        "decision": decision,
        "next_state": next_state,
    }
    return state["audit_trail"] + [step]
