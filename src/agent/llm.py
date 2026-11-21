"""
CampusFlow — LLM Engine (Google Gemini Integration)
===================================================
Modul integrasi LLM menggunakan Google GenAI SDK resmi (google-genai)
untuk penguraian bahasa alami, penalaran interaktif (Human-in-the-Loop),
serta pembentukan respons ramah kepada pengguna kampus.
"""

from datetime import date
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings

# Redam peringatan AFC dan log verbose dari pustaka pihak ketiga (google_genai, httpx, httpcore)
warnings.filterwarnings("ignore")
for _log_name in ("google_genai", "google_genai.models", "httpx", "httpcore", "urllib3"):
    logging.getLogger(_log_name).setLevel(logging.ERROR)

import dotenv
from google import genai
from pydantic import BaseModel, Field

# Muat file konfigurasi .env
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
dotenv.load_dotenv(dotenv_path=ENV_PATH)

# Daftar kode dan nama ruangan resmi di kampus (sesuai seed.sql)
KNOWN_ROOMS = {
    "AUD-01": "Auditorium Utama (Kapasitas: 300 orang, Gedung Utama; alias: audit, auditorium)",
    "SR-101": "Ruang Seminar 101 (Kapasitas: 50 orang)",
    "SR-102": "Ruang Seminar 102 (Kapasitas: 50 orang)",
    "CR-301": "Ruang Konferensi Eksekutif (Kapasitas: 20 orang)",
    "LH-201": "Ruang Kuliah 201 (Kapasitas: 80 orang)",
    "LH-202": "Ruang Kuliah 202 (Kapasitas: 120 orang)",
    "LAB-401": "Laboratorium Komputer (Kapasitas: 40 orang; alias: lab komputer)",
    "SR-ENG1": "Ruang Seminar Teknik (Kapasitas: 30 orang)",
    # UNPAR Rooms (Universitas Katolik Parahyangan)
    "PPAG-AUD": "Auditorium Utama PPAG (Kapasitas: 800 orang, Gedung PPAG; alias: audit ppag, auditorium ppag)",
    "PPAG-LT1": "Lecture Theater 1 PPAG (Kapasitas: 90 orang, Gedung PPAG)",
    "PPAG-LT2": "Lecture Theater 2 PPAG (Kapasitas: 90 orang, Gedung PPAG)",
    "PPAG-LT3": "Lecture Theater 3 PPAG (Kapasitas: 90 orang, Gedung PPAG)",
    "PPAG-201": "Lacture Hall PPAG (Kapasitas: 160 orang, Gedung PPAG)",
    "PPAG-202": "Ruang Kuliah PPAG 202 (Kapasitas: 60 orang, Gedung PPAG)",
    "PPAG-203": "Ruang Multifungsi (Kapasitas: 300 orang, Gedung PPAG; alias: ruang mulfung, mulfung, serbaguna ppag, mulfung ppag)",
    "G0-OR": "Operation Room Rektorat (Kapasitas: 50 orang, Gedung 0)",
    "G9-AULA": "Aula Driekore - FE (Kapasitas: 250 orang, Gedung 9; alias: aula fe, driekore, aula driekore)",
    "G9-101": "Ruang Kuliah 9101 (Kapasitas: 60 orang, Gedung 9)",
    "G9-LAB1": "Laboratorium Komputer Komputasi Lanjut 1 (Kapasitas: 30 orang, Gedung 9)",
    "G9-LAB2": "Laboratorium Komputer Komputasi Lanjut 2 (Kapasitas: 30 orang, Gedung 9)",
    "G9-LAB3": "Laboratorium Komputer Komputasi Lanjut 3 (Kapasitas: 60 orang, Gedung 9)",
    "G2-MC": "Ruang Peradilan Semu / Moot Court (Kapasitas: 50 orang, Gedung 2 FH)",
    "G2-SEM": "Ruang Seminar B. Arief Sidharta (Kapasitas: 60 orang, Gedung 2 FH)",
}

# Daftar kategori peralatan resmi
KNOWN_EQUIPMENT = [
    "projector",
    "microphone",
    "sound_system",
    "smartboard",
    "whiteboard",
    "video_conferencing",
]


class LLMBookingExtraction(BaseModel):
    """Skema ekstraksi terstruktur dari pesan pengguna."""
    room_name: Optional[str] = Field(
        default=None,
        description="Kode ruangan kanonik kampus (mis. 'AUD-01', 'SR-101') atau None jika tidak spesifik/ambigu",
    )
    event_name: Optional[str] = Field(
        default=None,
        description="Nama acara atau kegiatan (mis. 'workshop AI', 'rapat koordinasi')",
    )
    booking_date: Optional[str] = Field(
        default=None,
        description="Tanggal pemesanan dalam format ISO YYYY-MM-DD atau None jika belum pasti/ambigu",
    )
    date_relative: bool = Field(
        default=False,
        description="True jika tanggal diekstrak dari kata relatif ('besok', 'Selasa depan', 'lusa')",
    )
    date_text: Optional[str] = Field(
        default=None,
        description="Frasa asli pengguna untuk tanggal (mis. 'Selasa depan', 'besok')",
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Jam mulai dalam format 24 jam HH:MM (mis. '09:00') atau None jika tidak diinfokan pengguna",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="Jam selesai dalam format 24 jam HH:MM (mis. '11:00') atau None jika tidak diinfokan pengguna",
    )
    attendee_count: Optional[int] = Field(
        default=None,
        description="Estimasi jumlah peserta (orang/pax) atau None jika tidak disebutkan",
    )
    required_equipment: List[str] = Field(
        default_factory=list,
        description="Daftar tipe alat yang diminta pengguna, subset dari: projector, microphone, sound_system, smartboard, whiteboard, video_conferencing",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Daftar field esensial yang masih belum disediakan pengguna (mis. 'start_time', 'end_time', 'attendee_count', 'room_name', 'booking_date')",
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Catatan jika ada ketaksaan/ambiguitas (mis. 'Selasa depan ambigu antara 22 September atau 29 September')",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Catatan tambahan, permintaan khusus fasilitas/meja/kursi tamu, tata letak, atau instruksi logistik dari pengguna",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True jika ada field wajib yang hilang (terutama jam mulai/selesai) atau tanggal ambigu yang membutuhkan interaksi tanya balik ke pengguna",
    )
    clarification_message: Optional[str] = Field(
        default=None,
        description="Kalimat tanya klarifikasi yang sopan, ramah, dan interaktif dalam bahasa Indonesia untuk menanyakan jam atau tanggal yang ambigu kepada pengguna",
    )


class GeminiAgentClient:
    """Klien LLM Gemini untuk agen CampusFlow."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY belum disetel! Harap masukkan API key di file .env."
            )
        self.client = genai.Client(api_key=self.api_key)

    def parse_user_request(
        self,
        user_message: str,
        today: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        current_extraction: Optional[LLMBookingExtraction] = None,
    ) -> LLMBookingExtraction:
        """Mengekstrak informasi pemesanan menggunakan model Gemini dengan jaminan skema terstruktur."""
        locked_context = ""
        if current_extraction:
            locked_parts = []
            if current_extraction.room_name:
                locked_parts.append(f"- Ruangan: {current_extraction.room_name}")
            if current_extraction.event_name:
                locked_parts.append(f"- Acara: {current_extraction.event_name}")
            if current_extraction.booking_date:
                locked_parts.append(f"- Tanggal: {current_extraction.booking_date}")
            if current_extraction.start_time and current_extraction.end_time:
                locked_parts.append(f"- Jam/Waktu: {current_extraction.start_time} - {current_extraction.end_time}")
            if current_extraction.attendee_count:
                locked_parts.append(f"- Estimasi Peserta: {current_extraction.attendee_count} orang")
            if current_extraction.required_equipment:
                locked_parts.append(f"- Peralatan: {', '.join(current_extraction.required_equipment)}")
            if locked_parts:
                locked_context = (
                    "\n\nDATA TERVERIFIKASI DARI SESI SEJAUH INI (SUDAH TERKUNCI, JANGAN DIUBAH / JANGAN DITANYAKAN LAGI):\n"
                    + "\n".join(locked_parts)
                    + "\n*PENTING*: Jika jam atau tanggal sudah ada di atas, JANGAN bertanya soal jam/tanggal lagi!"
                )

        system_instruction = f"""Anda adalah asisten AI fasilitas kampus akademik CampusFlow.
Tugas Anda adalah memahami permintaan reservasi fasilitas/ruangan kampus dari pengguna secara cermat dan teliti.

KONTEKS SISTEM:
- Tanggal hari ini (today): {today}
- Ruangan resmi di kampus:
{json.dumps(KNOWN_ROOMS, indent=2, ensure_ascii=False)}
- Tipe peralatan yang dikenali: {KNOWN_EQUIPMENT}{locked_context}

ATURAN PENTING (HUMAN-IN-THE-LOOP & ANTI-HALUSINASI):
1. JANGAN PERNAH MENEBAK ATAU BERHALUSINASI TENTANG JAM ACARA!
   Jika pengguna TIDAK menyebutkan jam mulai atau jam selesai, jangan isi 'start_time' atau 'end_time'.
   Tandai `needs_clarification = True` dan buat `clarification_message` yang menanyakan jam mulai dan jam selesai acara kepada pengguna.
2. AMBIGUITAS TANGGAL RELATIF:
   Jika pengguna menyebutkan frasa seperti "Selasa depan" atau tanggal yang memiliki lebih dari satu kemungkinan tafsiran kalender,
   hitung kedua kemungkinannya, set `needs_clarification = True`, dan tanyakan kepastian tanggalnya kepada pengguna di `clarification_message`.
3. JIKA SUDAH LENGKAP:
   Jika seluruh data penting (ruangan, tanggal, jam mulai, jam selesai, jumlah peserta) sudah jelas dan tidak ambigu,
   set `needs_clarification = False` dan `clarification_message = None`.
4. REKOMENDASI OPSI RUANGAN (PILIHAN GANDA PROAKTIF):
   Jika pengguna belum menyebutkan kode/nama ruangan secara spesifik (misalnya hanya menyebut 'mau pinjem ruangan untuk kelas', 'ruang rapat', 'aula besar', atau hanya menyebut kapasitas tertentu), JANGAN kaku menolak atau meminta nama ruangan tanpa bantuan!
   Pilihlah 2-4 ruangan yang paling cocok dari daftar Ruangan Resmi di atas (berdasarkan kecocokan kapasitas dan tipe acara).
   Sajikan opsi pilihan ganda yang ramah dan bernomor: [1] Nama Ruangan (Kode) - Kapasitas, [2] ..., dst. di dalam `clarification_message`, lalu minta pengguna memilih nomor opsi atau nama ruangan tersebut.
5. PERMINTAAN KHUSUS & CATATAN LOGISTIK (NOTES):
   Jika pengguna menyebutkan kebutuhan logistik khusus (seperti: kebutuhan meja tamu, penataan kursi, proyektor ganda/tengah, tanpa kursi pada jam tertentu, dll.), ekstrak dan simpan ke field `notes` agar tersimpan permanen di database.
   Dan jika pengguna meminta alat presentasi (proyektor, mic, sound system, vidcon, smartboard), SELALU sertakan tipe alat tersebut di `required_equipment`!
"""

        contents = []
        if conversation_history:
            for turn in conversation_history:
                contents.append(f"{turn.get('role', 'user')}: {turn.get('content', '')}")
        contents.append(f"Permintaan pengguna saat ini: {user_message}")

        full_prompt = "\n".join(contents)

        candidate_models = [self.model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]
        # Hilangkan duplikasi sambil mempertahankan urutan
        unique_models = list(dict.fromkeys(m for m in candidate_models if m))

        last_error = None
        for m in unique_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                        "response_schema": LLMBookingExtraction,
                        "temperature": 0.1,  # Rendah agar deterministik dan presisi
                    },
                )
                raw_text = response.text or "{}"
                return LLMBookingExtraction.model_validate_json(raw_text)
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Gagal memanggil model Gemini setelah mencoba {unique_models}: {last_error}")

    def format_final_summary(
        self,
        state_dict: Dict[str, Any],
        user_message: str,
    ) -> str:
        """Menyusun pesan ringkasan akhir ramah kepada pengguna berdasarkan hasil alur kerja."""
        prompt = f"""Sebagai asisten resmi CampusFlow, berikan tanggapan yang sopan, profesional, dan jelas dalam Bahasa Indonesia kepada pengguna.

Hasil Eksekusi Alur Kerja:
{json.dumps(state_dict, indent=2, default=str, ensure_ascii=False)}

Instruksi Asli Pengguna:
"{user_message}"

Instruksi Format:
- Jika sukses (COMPLETED / CONFIRMED): Sebutkan nomor referensi pemesanan (booking_reference), ruangan, tanggal, jam, jumlah peserta, peralatan yang telah terverifikasi fisiknya, dan departemen yang telah dinotifikasi (academic_facilities, it_support).
- Jika ditolak / gagal: Jelaskan alasan spesifik penolakannya secara transparan berdasarkan bukti audit, tanpa menyalahkan pengguna, dan berikan saran alternatif yang konstruktif jika ada.
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": 0.3,
            },
        )
        return (response.text or "").strip()
