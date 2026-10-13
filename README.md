# CampusFlow — Academic Facility & Event Coordinator

Sistem orkestrasi agen AI berbasis alur kerja terkendali (*Controlled Autonomous Workflow Agent*) yang mengotomatisasi pemrosesan permintaan peminjaman fasilitas kampus, verifikasi ketersediaan ruangan, pemeriksaan kondisi fisik peralatan via Model Context Protocol (MCP), dan penalaran bahasa alami secara cerdas.

---

## 📌 Prasyarat Sistem

* **Python:** Versi 3.10 atau lebih baru (direkomendasikan Python 3.12).
* **Git**
* **Google Gemini API Key:** Dapatkan secara gratis melalui [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Panduan Instalasi & Persiapan

### 1. Buka Direktori Proyek
Buka terminal (PowerShell / Command Prompt) dan masuk ke direktori proyek:
```powershell
cd CampusFlow
```

### 2. Buat dan Aktifkan Virtual Environment
Sangat disarankan menggunakan *virtual environment* lokal agar dependensi terisolasi:

* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
* **Windows (Command Prompt):**
  ```cmd
  python -m venv .venv
  .\.venv\Scripts\activate.bat
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Pasang Dependensi
Pasang semua pustaka yang dibutuhkan menggunakan pip:
```powershell
pip install -r requirements.txt
```

### 4. Konfigurasi API Key (.env)
Salin berkas template `.env.example` menjadi `.env`:
```powershell
copy .env.example .env
```
Buka berkas `.env` dan masukkan API Key Gemini Anda:
```env
GEMINI_API_KEY=masukkan_api_key_anda_disini
GEMINI_MODEL=gemini-3.5-flash-lite
```

---

## 🎮 Cara Menjalankan Sistem

### Mode 1: Sesi Obrolan Interaktif dengan AI (Gemini)
Gunakan mode ini untuk mengobrol bolak-balik langsung dengan asisten CampusFlow di terminal:

```powershell
python -m src.agent.llm
```
*(atau jika tidak menggunakan aktivasi venv: `.\.venv\Scripts\python.exe -m src.agent.llm`)*

**Contoh Skenario Percakapan (Human-in-the-Loop):**
1. **Anda:** `Pesan auditorium utama untuk workshop AI 100 orang besok`
2. **Asisten AI:** *"Mohon maaf, jam berapa acara workshop AI tersebut akan dimulai dan selesai?"*
3. **Anda:** `Mulai jam 09:00 sampai 11:00 ya, pastikan proyektor siap`
4. **Asisten AI:** *"Baik, seluruh data pemesanan telah lengkap!"* (Menampilkan rincian ruangan, tanggal, waktu, peserta, dan alat).
5. Ketik `keluar` atau `exit` untuk mengakhiri sesi.

---

### Mode 2: Uji Coba Pengurai Deterministik (Offline / Cepat)
Mode ini menguji kemampuan logika regex sistem dalam membedah kalimat pengguna tanpa koneksi internet atau kuota API:

```powershell
python -m src.agent.parser
```

Sistem akan secara otomatis mengeksekusi 3 skenario uji:
* **Kasus 1:** Kalimat lengkap (ekstraksi ruangan, tanggal, jam, peserta, dan alat).
* **Kasus 2:** Penanggalan relatif (*"besok"* dihitung otomatis dari tanggal sistem).
* **Kasus 3:** Jam tidak disebutkan (sistem membiarkan nilai `null` dan tidak mengarang).

---

### Mode 3: Inisialisasi & Verifikasi Basis Data SQLite
Basis data kampus menggunakan SQLite lokal. Untuk memeriksa integritas data awal:

```powershell
python data/database/init_db.py --verify
```
*(Untuk mereset ulang basis data ke data acuan awal: `python data/database/init_db.py --reset`)*

---

## 🏛️ Daftar Ruangan Kampus Resmi (Data Awal)

| Kode Ruangan | Nama Ruangan | Kapasitas | Tipe Ruangan |
| :--- | :--- | :---: | :--- |
| `AUD-01` | Auditorium Utama | 300 orang | Auditorium |
| `SR-101` | Ruang Seminar 101 | 50 orang | Seminar Room |
| `SR-102` | Ruang Seminar 102 | 50 orang | Seminar Room |
| `CR-301` | Ruang Konferensi Eksekutif | 20 orang | Conference Room |
| `LH-201` | Ruang Kuliah 201 | 80 orang | Lecture Hall |
| `LH-202` | Ruang Kuliah 202 | 120 orang | Lecture Hall |
| `LAB-401` | Laboratorium Komputer | 40 orang | Computer Lab |
| `SR-ENG1` | Ruang Seminar Teknik | 30 orang | Seminar Room |

---

## 📁 Struktur Direktori

```text
CampusFlow/
├── data/
│   ├── database/          # Skema SQLite (schema.sql), data awal (seed.sql), dan init_db.py
│   └── filesystem/        # Berkas fisik inventaris & catatan status operasional alat
├── docs/
│   ├── SRS_CampusFlow.md  # Dokumen Spesifikasi Kebutuhan Perangkat Lunak formal (SRS)
│   └── *.pdf              # Dokumen SRS versi cetak PDF
├── src/
│   ├── agent/             # Modul penalaran agen
│   │   ├── llm.py         # Integrasi Google Gemini & sesi obrolan interaktif
│   │   ├── parser.py      # Pengurai deterministik (NLU) ramah orang awam
│   │   └── state.py       # Struktur status formulir digital pemesanan
│   └── mcp/               # Server Model Context Protocol (DB, FileSystem, Notifikasi)
├── .env.example           # Template konfigurasi variabel lingkungan
├── README.md              # Dokumentasi panduan penggunaan proyek
└── requirements.txt       # Daftar dependensi pustaka Python
```
