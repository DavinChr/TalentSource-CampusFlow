# Konteks Proyek: CampusFlow
**Academic Campus Facility & Event Coordinator**
*(Koordinator Fasilitas & Acara Kampus Akademik)*

---

## 1. Tujuan Proyek
**CampusFlow** adalah sistem orkestrasi agen AI otonom yang dirancang untuk mengelola permintaan kampus yang kompleks dan melibatkan banyak departemen menggunakan instruksi bahasa alami (*natural language*). 

Sistem ini **bukan sekadar chatbot biasa**, melainkan sebuah **agen alur kerja otonom yang terkendali (*controlled autonomous workflow agent*)**. Sistem ini mampu:
- Mengurai permintaan pengguna (*request decomposition*).
- Memvalidasi setiap prasyarat secara berurutan di berbagai sumber data terisolasi melalui *Model Context Protocol* (MCP).
- Menegakkan aturan bisnis dan batasan keamanan secara deterministik (pasti dan terukur).
- Melakukan penulisan/pemesanan ke database secara transaksional **hanya setelah semua validasi lulus**.
- Mengirimkan notifikasi ke departemen kampus terkait sesuai alur kerja.

---

## 2. Kondisi Repositori Saat Ini
- **Direktori Utama Proyek:** `D:\TalentSource\CampusFlow`
- **File yang Ada:**
  - `prompts/00_MASTER_PROMPT.md`: Dokumen acuan utama spesifikasi dan panduan fase pengerjaan.
- **Status Repositori:** Proyek baru (*green-field*). Tidak ada kode warisan atau struktur usang yang bentrok.
- **Manajemen Versi:** Berada di repositori Git lokal pada cabang `master`.

---

## 3. Tumpukan Teknologi & Lingkungan Eksekusi

### Lingkungan Sistem & Runtime
- **Sistem Operasi:** Windows 11 (PowerShell).
- **Runtime Python:**
  - Versi Utama: Python `3.14.0` (`C:\Python314\`)
  - Versi Cadangan: Python `3.12` (`py -3.12`)
  - *Catatan Penting:* Direktori `site-packages` global bersifat *read-only* untuk hak akses standar, sehingga pustaka proyek wajib diisolasi di dalam *Virtual Environment* lokal (`.venv`).
- **Runtime Node.js:** Node.js `v24.11.1`, npm `11.6.2`.
- **Database Engine:** SQLite 3 (versi 3.50.4 bawaan modul standar Python `sqlite3`), mendukung transaksi ACID, *foreign keys*, dan berjalan mandiri tanpa perlu server database eksternal terpisah.

### Pustaka & Framework Utama
- **Orkestrasi Agen:** `LangGraph` & `langchain-core` untuk membangun mesin status (*state machine*) eksplisit dan alur kerja ReAct.
- **Model Context Protocol (MCP):** SDK resmi Python `mcp` (`mcp>=2.2.0`, `mcp-types`, `pydantic>=2.7.4`), berkomunikasi via protokol standar JSON-RPC 2.0 melalui *stdio*.
- **Validasi Data & Skema:** `pydantic` v2 untuk parsing struktur permintaan pengguna, penegakan skema data, dan model status (*state*).
- **Pengujian (Testing):** `pytest` dan `pytest-asyncio` untuk pengujian unit, integrasi, mock MCP, hingga uji menyeluruh (*end-to-end*).

---

## 4. Desain Arsitektur Server MCP
CampusFlow memerlukan tiga server MCP independen yang saling terisolasi dan berkomunikasi melalui protokol standar MCP (*stdio*):

1. **Server MCP Database (`campusflow-db`):**
   - Fungsi utama: Mengelola data ruangan, kapasitas, jadwal, dan pencatatan reservasi.
   - Perangkat (*tools*) yang disediakan: `inspect_schema`, `query_room_availability`, `query_room_capacity`, `check_booking_conflicts`, `query_equipment`, `create_booking_transactional`.
   - Batasan Keamanan: Menggunakan prinsip *least-privilege*, kueri SQL berparameter, komit/rollback transaksi eksplisit, dan mencegah agen mengeksekusi perintah SQL berbahaya secara sembarangan.
2. **Server MCP Filesystem (`campusflow-fs`):**
   - Fungsi utama: Mengakses file dokumen operasional kampus di `data/filesystem/` (misalnya: catatan pemeliharaan/servis, inventaris perangkat, status alat).
   - Perangkat (*tools*) yang disediakan: `read_file`, `search_maintenance_log`, `get_equipment_status`.
   - Batasan Keamanan: Akses baca saja (*read-only sandbox*) khusus pada folder operasional fasilitas kampus, mencegah pembacaan file sistem lain (*path traversal guard*).
3. **Server MCP Notifikasi Mock API (`campusflow-notification`):**
   - Fungsi utama: Menyimulasikan sistem pesan/notifikasi internal kampus.
   - Perangkat (*tools*) yang disediakan: `send_department_notification`, `get_notification_status`, `list_department_notifications`.
   - Perutean (*Routing*): Mengarahkan pesan ke departemen yang tepat secara terstruktur (Fasilitas Akademik, Dukungan TI, Pemeliharaan, atau Urusan Acara).

---

## 5. Batasan & Aturan Keamanan (Guardrails)

1. **Aturan Mutlak (Non-Negotiable Rule):**
   - **DILARANG MENULIS RESERVASI KE DATABASE SEBELUM SEMUA VALIDASI SELESAI DAN LULUS.**
   - Urutan alur kerja wajib:
     $$\text{Urai Permintaan} \to \text{Validasi Syarat} \to \text{Cek Ketersediaan Ruangan} \to \text{Cek Kapasitas} \to \text{Cek Kebutuhan Alat} \to \text{Verifikasi Status Operasional Alat} \to \text{Otorisasi} \to \text{Tulis DB (Transaksional)} \to \text{Kirim Notifikasi}$$
2. **Logika Bisnis Deterministik vs Penalaran Probabilistik LLM:**
   - LLM hanya dipakai untuk memahami bahasa manusia, mengekstrak maksud pengguna, mengurai tugas, dan menyusun teks penjelasan.
   - Perhitungan kapasitas ruangan, deteksi bentrok jadwal waktu, batasan transaksi database, dan perpindahan status alur kerja dijalankan oleh program secara deterministik (pasti/matematis), bukan ditebak oleh LLM.
3. **Penalaran Berbasis Bukti Nyata (*Evidence-Based Reasoning*):**
   - Agen tidak boleh mengarang (*halusinasi*) kondisi alat atau ketersediaan ruangan.
   - Status harus dibedakan tegas: `AVAILABLE` (Tersedia), `UNAVAILABLE` (Tidak Tersedia), `UNKNOWN` (Tidak Diketahui), dan `ERROR` (Kesalahan). Status `UNKNOWN` dilarang disamakan dengan `AVAILABLE`.
4. **Strategi Tanpa Ketergantungan API Key Berbayar (*Offline Fallback*):**
   - Lingkungan lokal saat ini belum memiliki API key pihak ketiga (`OPENAI_API_KEY`, dll.).
   - Arsitektur mendukung integrasi LLM eksternal via variabel lingkungan (OpenAI, Anthropic, Gemini), namun juga dilengkapi mesin pengurai offline deterministik (*Mock/Deterministic NLU Parser*) agar 10 skenario pengujian otomatis dan demo utama dapat diuji secara mandiri tanpa biaya ataupun limit kuota API.

---

## 6. Komponen yang Perlu Dibangun
1. **Infrastruktur Lingkungan:** Virtual environment (`.venv`) serta file dependensi (`requirements.txt` / `pyproject.toml`).
2. **Dokumentasi Lengkap:** Folder `docs/` (`research.md`, `problem-definition.md`, `architecture-decisions.md`, `architecture.md`, `workflow.md`, `state-machine.md`, `data-model.md`, `mcp-database.md`, `mcp-filesystem.md`, `mcp-notification.md`, `testing.md`).
3. **Lapisan Database:** Skema SQLite (`buildings`, `rooms`, `equipment`, `room_equipment`, `bookings`, `audit_logs`), data awal (*seed data*) realistis yang mencakup skenario bentrok jadwal dan masalah pemeliharaan alat.
4. **File Operasional Kampus:** Catatan pemeliharaan dan inventaris peralatan di `data/filesystem/`.
5. **Server MCP:** Tiga server mandiri (`mcp_db_server.py`, `mcp_fs_server.py`, `mcp_notification_server.py`).
6. **Orkestrator Agen:** Alur kerja graf status LangGraph dengan guardrail deterministik dan pencatatan jejak eksekusi (*audit trail*).
7. **Suite Uji Otomatis:** 10 skenario pengujian mencakup skenario sukses, ruangan tidak tersedia, kapasitas kurang, proyektor rusak, status tidak diketahui, kegagalan DB, kegagalan notifikasi, informasi bertentangan, permintaan ambigu, dan reservasi duplikat.
8. **Antarmuka CLI & Demo:** Skrip eksekusi interaktif untuk mendemonstrasikan kasus penggunaan utama.

---

## 7. Rencana Eksekusi Berdasarkan Fase

| Fase | Deskripsi | Hasil Keluaran (*Deliverables*) |
|---|---|---|
| **Fase 0** | **Inisialisasi Proyek (SELESAI)** | Audit lingkungan & repositori, `PROJECT_CONTEXT.md`, rencana kerja |
| **Fase 1** | **Riset & Brainstorming** | `docs/research.md`, `docs/problem-definition.md`, `docs/architecture-decisions.md` |
| **Fase 2** | **Desain Sistem Arsitektur** | `docs/architecture.md`, `docs/workflow.md`, `docs/state-machine.md`, `docs/data-model.md`, `docs/mcp-architecture.md` (dengan diagram Mermaid) |
| **Fase 3** | **Database & Data Uji (Seed Data)** | Skema SQLite, skrip inisialisasi, data simulasi ruangan & alat, kueri transaksi reservasi |
| **Fase 4** | **Infrastruktur Server MCP** | Server MCP Database, Filesystem, Notifikasi Mock API, serta dokumen panduan masing-masing MCP |
| **Fase 5** | **Orkestrasi Agen (LangGraph)** | Graf alur kerja LangGraph, fungsi simpul (*nodes*), pengurai permintaan, pencatat jejak eksekusi |
| **Fase 6** | **Guardrails & Uji Keamanan** | Penegakan invariant keamanan, pencegahan halusinasi, isolasi transaksi, sanitasi input |
| **Fase 7** | **Pengujian Otomatis Menyeluruh** | Pengujian Uji 1 sampai Uji 10 (Skenario sukses, bentrok, alat rusak, error DB, error notifikasi, dll.) |
| **Fase 8** | **Audit Akhir & Demonstrasi** | Demo kasus utama ("Pesan auditorium utama untuk workshop AI 100 orang..."), demo kasus gagal, `README.md`, laporan audit akhir |
  
---
