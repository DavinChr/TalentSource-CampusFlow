# CampusFlow — Academic Campus Facility & Event Coordinator

Sistem orkestrasi agen AI berbasis alur kerja otonom terkendali (*Controlled Autonomous Workflow Agent*) untuk mengelola permohonan fasilitas kampus lintas departemen secara cerdas, aman, dan transaksional.

CampusFlow memadukan penalaran bahasa alami **Google Gemini LLM**, arsitektur mesin status **LangGraph**, dan isolasi data standar **Model Context Protocol (MCP)** dengan penegakan aturan bisnis secara deterministik.

---

## 🌟 Fitur Utama Sistem

1. **Orkestrasi Multi-Server Model Context Protocol (MCP)**:
   * `campusflow-db`: Server basis data SQLite transaksional (ACID) untuk jadwal, kapasitas, dan pencatatan reservasi.
   * `campusflow-fs`: Server akses berkas operasional fisik (*read-only sandbox*) untuk status operasional alat dan log servis teknisi.
   * `campusflow-notification`: Server pesan internal untuk pengiriman notifikasi resmi ke **Fasilitas Akademik** dan **Dukungan TI & Multimedia**.

2. **Proactive Human-in-the-Loop (HITL) & Rekomendasi Ruangan**:
   * **Perekomendasi Pilihan Ganda (`room_recommender.py`)**: Jika pengguna belum tahu nama ruangan spesifik (misal: hanya menyebut *"butuh aula besar"* atau *"lab komputer 30 orang"*), sistem secara proaktif menyajikan pilihan ganda bernomor (`[1]`, `[2]`, `[3]`) dari database.
   * **Klarifikasi Ramah**: Jika informasi penting (seperti jam mulai/selesai) hilang atau tanggal ambigu (*"Selasa depan"*), agen mengajukan pertanyaan klarifikasi secara sopan tanpa menebak atau berhalusinasi.

3. **Penalaran Berbasis Bukti Nyata (*Evidence-Based Reasoning*)**:
   * Status operasional alat di berkas log teknisi lapangan diutamakan di atas status database. Jika terjadi kontradiksi (di database `ACTIVE`, tapi log servis fisik mencatat `FAULTY`), alur kerja seketika dibatalkan (*WORKFLOW_ABORTED*).

4. **Penegakan Transaksi Bersyarat (*Non-Negotiable Guardrails*)**:
   * **Dilarang keras menulis ke database sebelum semua validasi lolos**: Waktu $\to$ Kapasitas $\to$ Ketersediaan Alat $\to$ Kesehatan Fisik Alat $\to$ Otorisasi $\to$ Tulis DB $\to$ Notifikasi.
   * **Degradasi Anggun (*Graceful Partial Failure*)**: Jika penulisan database reservasi sukses namun pengiriman notifikasi departemen gagal/timeout, reservasi tetap berstatus `CONFIRMED` dan insiden dicatat ke jejak audit (*Audit Trail*).

---

## 🏛️ Master Data Kampus & Ruangan UNPAR

Sistem memuat 7 gedung, 23 ruangan aktif, dan 56 peralatan mencakup kampus acuan dan **Universitas Katolik Parahyangan (UNPAR)**:

| Kode Gedung | Nama Gedung | Contoh Kode Ruangan | Kapasitas | Tipe Ruangan | Fasilitas Utama |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **PPAG** | Pusat Pembelajaran Arntz-Geise | `PPAG-AUD` | 800 | Auditorium | Dual Laser Barco, Line Array L-Acoustics, Shure Rig |
| **PPAG** | Pusat Pembelajaran Arntz-Geise | `PPAG-LT1` – `LT3` | 90 | Lecture Theater | Smartboard Samsung Flip, Yamaha Sound, Shure Mic |
| **PPAG** | Pusat Pembelajaran Arntz-Geise | `PPAG-201` | 160 | Lecture Hall | Smartboard 85", Sound System Yamaha, Mic |
| **PPAG** | Pusat Pembelajaran Arntz-Geise | `PPAG-202` | 60 | Lecture Hall | Proyektor Epson, Whiteboard |
| **PPAG** | Pusat Pembelajaran Arntz-Geise | `PPAG-203` | 300 | Multipurpose | Ruang serbaguna / fleksibel |
| **G0** | Gedung 0 (Rektorat) | `G0-OR` | 50 | Conference Room | Proyektor Panasonic, Bose Sound, Bosch Delegate Mic |
| **G9** | Gedung 9 (FEB) | `G9-AULA` | 250 | Auditorium | Proyektor Sony, Sound JBL, Panggung Acara |
| **G9** | Gedung 9 (FEB) | `G9-101` | 60 | Lecture Hall | Proyektor Epson, Whiteboard |
| **G9** | Gedung 9 (FEB) | `G9-LAB1` – `LAB3`| 30 – 60 | Computer Lab | 30–60 Unit PC Dell OptiPlex Core i7, Proyektor |
| **G2** | Gedung 2 (Fakultas Hukum) | `G2-MC` | 50 | Seminar / Court | Ruang Sidang Semu (Moot Court), Sound, Mic Meja |
| **G2** | Gedung 2 (Fakultas Hukum) | `G2-SEM` | 60 | Seminar Room | Proyektor Panasonic, Sound JBL, Mic Sennheiser |
| **MAIN** | Gedung Utama | `AUD-01` | 300 | Auditorium | Proyektor ViewSonic, Sound JBL, Shure Mic |
| **MAIN** | Gedung Utama | `SR-101`, `SR-102` | 50 | Seminar Room | Proyektor Epson / BenQ, Mic |
| **SCI** | Gedung Sains | `LH-201`, `LH-202` | 80 – 120 | Lecture Hall | Proyektor Panasonic, Sound Yamaha |
| **ENG** | Gedung Teknik | `LAB-401` | 40 | Computer Lab | *(Status: UNDER_RENOVATION)* |

---

## 🚀 Panduan Instalasi & Persiapan

### 1. Klon Repositori & Masuk ke Folder Proyek
```powershell
cd CampusFlow
```

### 2. Buat dan Aktifkan Virtual Environment
* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Pasang Dependensi
```powershell
pip install -r requirements.txt
```

### 4. Konfigurasi Variabel Lingkungan (`.env`)
Salin berkas template `.env.example` menjadi `.env`:
```powershell
copy .env.example .env
```
Buka `.env` dan masukkan API Key Gemini Anda:
```env
GEMINI_API_KEY=masukkan_api_key_anda_disini
GEMINI_MODEL=gemini-3.5-flash-lite
NOTIFICATION_IT_DEPT=it_support
```

---

## 🎮 Cara Menjalankan Sistem

### Mode 1: Antarmuka Baris Perintah Interaktif Penuh (Utama / Rekomendasi)
Menjalankan agen alur kerja lengkap (Google Gemini + LangGraph + Human-in-the-Loop + Transaksi MCP + Jejak Audit):

```powershell
python src/cli.py
```
*(atau: `.\.venv\Scripts\python.exe src/cli.py`)*

**Contoh Perintah yang Bisa Dicoba:**
* *"Pesan Auditorium Utama PPAG untuk wisuda dan seminar 500 orang tanggal 15 Oktober 2026 jam 08:00 sampai 12:00, butuh proyektor dan sound system."*
* *"Carikan lab komputer untuk praktikum 30 mahasiswa minggu depan."* *(Agen akan menyajikan pilihan ganda `[1] G9-LAB1`, `[2] G9-LAB2`)*
* *"Pesan ruang peradilan semu di FH untuk latihan sidang 40 orang besok lusa jam 10:00 sampai 12:00."*

---

### Mode 2: Sesi Obrolan Terisolasi AI (Gemini Agent)
Uji penalaran ekstraksi entitas bahasa alami dan interaksi tanya balik Gemini:
```powershell
python -m src.agent.llm
```

### Mode 3: Pengurai Kalimat Deterministik (Offline / Regex)
Uji parsing entitas tanggal, jam, dan ruangan secara mandiri tanpa kuota API:
```powershell
python -m src.agent.parser
```

### Mode 4: Inisialisasi & Verifikasi Basis Data SQLite
Memeriksa integritas skema tabel, relasi foreign key, dan kalkulasi deteksi bentrok jadwal:
```powershell
python data/database/init_db.py --verify
```
Untuk mengembalikan basis data ke kondisi awal (*reset seed data*):
```powershell
python data/database/init_db.py --reset
```

---

## 🧪 Pengujian Otomatis (Pytest Suite)

CampusFlow dilengkapi rangkaian pengujian unit, integrasi server MCP, dan alur kerja end-to-end dengan total **53 pengujian (100% PASS)**:

```powershell
pytest
```

### Cakupan Skenario Acuan SRS Formal:
* **TC-01 (Jalur Sukses Penuh)**: Auditorium Utama, kapasitas pas, proyektor OPERATIONAL $\to$ `COMPLETED`, terbit referensi `BK-2026-xxx`.
* **TC-02 (Bentrok Jadwal Waktu)**: Deteksi slot terisi $\to$ `ROOM_UNAVAILABLE`, tidak ada penulisan ke database.
* **TC-03 (Kapasitas Melampaui Batas)**: Jumlah peserta melebihi kapasitas ruangan $\to$ `INSUFFICIENT_CAPACITY`.
* **TC-04 (Kontradiksi Bukti Fisik)**: DB mencatat `ACTIVE` tapi log fisik teknisi mencatat `FAULTY` $\to$ `WORKFLOW_ABORTED`.
* **TC-05 (Ruangan Renovasi)**: `LAB-401` berstatus `UNDER_RENOVATION` $\to$ ditolak di validasi awal.
* **TC-06 (Parameter Waktu Tidak Valid)**: Jam mulai $\ge$ jam selesai (misal `15:00 s/d 13:00`) $\to$ `INVALID_REQUEST`.
* **TC-07 (Peralatan Tidak Tersedia)**: Ruangan tidak memiliki peralatan yang diminta $\to$ `EQUIPMENT_UNAVAILABLE`.
* **TC-08 (Ruangan Fiktif / Tidak Terdaftar)**: Permintaan ruangan tidak dikenal $\to$ `INVALID_REQUEST` / `ROOM_UNAVAILABLE`.
* **TC-09 (Waktu Bersinggungan Sah)**: Selesai tepat saat acara berikutnya mulai (*back-to-back*) $\to$ `COMPLETED` tanpa bentrok palsu.
* **TC-10 (Konfirmasi Tanggal Relatif Ambigu)**: Frasa *"Selasa depan"* memerlukan konfirmasi pemohon (*Human-in-the-Loop*).
* **Pencegahan Pemesanan Ganda**: Dua pemesanan identik pada ruangan dan jam yang sama dicegah secara atomik.
* **Penanganan Kegagalan Notifikasi**: Database tetap `CONFIRMED`, notifikasi `FAILED`, alur berstatus `COMPLETED_PARTIAL`.
* **Alur Fasilitas UNPAR**: Uji end-to-end pemesanan ruangan `PPAG-202` UNPAR beserta catatan tata letak meja-kursi.

---

## 📁 Struktur Direktori Proyek

```text
CampusFlow/
├── data/
│   ├── database/
│   │   ├── schema.sql                     # Skema DDL 6 tabel relasional
│   │   ├── seed.sql                       # Data awal master gedung, ruang, alat, booking
│   │   ├── seed_unpar.sql                 # Data spesifik kampus UNPAR
│   │   ├── init_db.py                     # Skrip inisialisasi & 13-point verifier
│   │   └── campusflow.db                  # File fisik SQLite (WAL mode)
│   ├── filesystem/
│   │   ├── equipment_inventory.txt        # Inventaris nomor seri peralatan
│   │   ├── equipment_status.txt           # Catatan status operasional teknisi lapangan
│   │   ├── maintenance_logs.txt           # Riwayat perbaikan berkala peralatan
│   │   └── notifications_outbox.txt       # Log fisik transmisi notifikasi departemen
│   └── campus_rooms_unpar.txt             # Katalog lengkap fasilitas UNPAR
│
├── docs/
│   ├── SRS_CampusFlow.md                  # Spesifikasi Kebutuhan Formal IEEE
│   └── *.md                               # Dokumen desain sistem, arsitektur, & alur kerja
│
├── src/
│   ├── cli.py                             # Program demo terminal interaktif utama
│   ├── agent/                             # Otak & Orkestrasi Agen Cerdas
│   │   ├── graph.py                       # Perakitan StateGraph LangGraph
│   │   ├── llm.py                         # Integrasi Google Gemini & Pydantic Extraction
│   │   ├── parser.py                      # Pengurai kalimat deterministik regex offline
│   │   ├── room_recommender.py            # Mesin pemberi rekomendasi pilihan ganda
│   │   ├── state.py                       # Definisi AgentState & Audit Trail
│   │   ├── mcp_client.py                  # Adapter penghubung agen ke server MCP
│   │   └── nodes/                         # 8 simpul tugas validasi & eksekusi terisolasi
│   └── mcp/                               # 3 Server Model Context Protocol (stdio)
│       ├── db_server.py                   # Server MCP Database
│       ├── fs_server.py                   # Server MCP Filesystem
│       └── notification_server.py         # Server MCP Notifikasi Departemen
│
├── tests/                                 # 53 Pengujian Otomatis (Pytest)
│   ├── test_agent_parser.py               # Uji pemahaman teks & penanggalan
│   ├── test_agent_workflow.py             # Uji 10 skenario SRS end-to-end
│   ├── test_mcp_integration.py            # Uji komunikasi server MCP
│   └── test_room_recommender.py           # Uji algoritma rekomendasi ruangan
│
├── .env.example                           # Template variabel lingkungan
├── pytest.ini                             # Konfigurasi pengujian pytest
├── requirements.txt                       # Daftar dependensi pustaka Python
└── README.md                              # Dokumentasi resmi proyek
```
