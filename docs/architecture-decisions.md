# Catatan Keputusan Arsitektur: CampusFlow
**Architecture Decision Records (ADR)**

Dokumen ini mencatat seluruh keputusan arsitektural penting yang diambil untuk proyek CampusFlow, beserta konteks, alternatif yang dipertimbangkan, konsekuensi teknis, serta pemisahan antara fakta, asumsi, keputusan, dan pertanyaan terbuka.

---

## Ringkasan Keputusan Arsitektur (ADR Matrix)

| ID | Judul Keputusan | Status | Dampak Utama |
|---|---|---|---|
| **ADR-001** | Penggunaan LangGraph StateGraph untuk Mesin Status Alur Kerja | **DITERIMA** | Menjamin alur kerja deterministik, transisi eksplisit, dan mencegah loop tak terhingga. |
| **ADR-002** | Model Context Protocol (MCP) sebagai Lapisan Abstraksi Alat | **DITERIMA** | Menstandarisasi interaksi data eksternal melalui protokol JSON-RPC standar industri. |
| **ADR-003** | Basis Data SQLite dengan Mode WAL dan Transaksi Terisolasi | **DITERIMA** | ACID terjamin, bebas overhead server eksternal, pencegahan *double-booking* secara fisik. |
| **ADR-004** | Sandbox Filesystem Mandiri untuk Verifikasi Log Pemeliharaan | **DITERIMA** | Menjaga integritas riwayat servis fisik alat tanpa memanipulasi database secara palsu. |
| **ADR-005** | Server Mock API Notifikasi dengan Perutean Terstruktur | **DITERIMA** | Simulasi pengiriman pesan kampus multi-departemen yang terisolasi dan mudah diuji. |
| **ADR-006** | Pemisahan Logika Deterministik dari Penalaran Probabilistik LLM | **DITERIMA** | Menghilangkan risiko halusinasi pada aturan bisnis, kapasitas, dan bentrok jadwal. |
| **ADR-007** | Strategi NLU Ganda: Antarmuka LLM Pluggable + Fallback Deterministik | **DITERIMA** | Memastikan seluruh pengujian otomatis dapat berjalan 100% offline tanpa biaya kuota. |
| **ADR-008** | Penanganan Kegagalan Parsial (*Partial Failure Isolation*) | **DITERIMA** | Mempertahankan status reservasi sah jika hanya notifikasi yang gagal terkirim. |
| **ADR-009** | Jejak Audit Terstruktur (*Structured Audit Tracing*) | **DITERIMA** | Menyimpan riwayat observasi bukti alat secara transparan dan mudah diaudit. |
| **ADR-010** | Strategi Pengujian Otomatis 10 Skenario Acuan | **DITERIMA** | Menjamin keandalan sistem terhadap seluruh kasus sukses maupun variasi kegagalan. |

---

## Rincian Catatan Keputusan

### ADR-001: Penggunaan LangGraph StateGraph untuk Mesin Status Alur Kerja

- **Konteks:** Agen perlu mengeksekusi alur pemesanan multi-langkah yang melibatkan pengecekan berurutan dan penghentian bersyarat.
- **Alternatif yang Dipertimbangkan:**
  1. *Single LLM Call with Function Calling:* Mudah dibuat tetapi rentan melompati langkah validasi penting dan sulit diaudit.
  2. *LangChain ReAct Agent murni:* Fleksibel, tetapi rawan loop tanpa akhir dan tidak memiliki penegakan status eksplisit.
  3. *LangGraph StateGraph:* Menawarkan graf status terarah dengan simpul terisolasi dan transisi bersyarat (*conditional edges*).
- **Fakta Terdokumentasi:** LangGraph mengizinkan state terstruktur dan transisi deterministik yang dapat dihentikan kapan saja jika terjadi galat.
- **Asumsi:** Alur kerja reservasi fasilitas kampus bersifat sekuensial dengan percabangan kegagalan yang jelas.
- **Keputusan:** Menggunakan `LangGraph` untuk mengorkestrasi graf alur kerja dengan simpul eksplisit (`parse_request`, `validate_requirements`, `check_room`, `validate_capacity`, `check_equipment`, `authorize_booking`, `create_booking`, `send_notification`, `finalize_workflow`, `handle_failure`).
- **Konsekuensi:** Arsitektur menjadi sangat terstruktur dan mudah diuji; kode terorganisir per simpul fungsi.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-002: Model Context Protocol (MCP) sebagai Lapisan Abstraksi Alat

- **Konteks:** Sistem membutuhkan akses ke tiga domain data berbeda: basis data ruangan/jadwal, file teks pemeliharaan alat, dan layanan pengiriman notifikasi.
- **Alternatif yang Dipertimbangkan:**
  1. *Fungsi Python Internal Biasa:* Cepat, tetapi mengaburkan batasan arsitektur terdistribusi dan tidak memenuhi spesifikasi teknis proyek.
  2. *Model Context Protocol (MCP) via stdio:* Mengikuti standar terbuka resmi, mengisolasi tanggung jawab tiap server, dan menggunakan protokol JSON-RPC 2.0.
- **Fakta Terdokumentasi:** Pustaka resmi Python `mcp` (`mcp>=2.2.0`) telah terbukti dapat dipasang dan dijalankan di lingkungan Windows.
- **Asumsi:** Komunikasi via `stdio` memiliki latensi minimal dan tidak memerlukan port jaringan terbuka.
- **Keputusan:** Membangun 3 server MCP mandiri berbasis stdio: `campusflow-db`, `campusflow-fs`, dan `campusflow-notification`.
- **Konsekuensi:** Pemisahan hak akses (*least-privilege*) terjaga sempurna; agen hanya berkomunikasi dengan server melalui alat MCP resmi.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-003: Basis Data SQLite dengan Mode WAL dan Transaksi Terisolasi

- **Konteks:** Sistem memerlukan penyimpanan data relasional untuk gedung, ruangan, kapasitas, jadwal reservasi, dan peralatan yang mendukung transaksi ACID tanpa ketergantungan server terpisah.
- **Alternatif yang Dipertimbangkan:**
  1. *PostgreSQL:* Sangat kuat untuk produksi skala besar, tetapi membutuhkan instalasi service server dan konfigurasi kredensial lokal tambahan.
  2. *SQLite 3 terbenam (Embedded SQLite):* Sudah terintegrasi langsung dalam pustaka standar Python `sqlite3`, mendukung transaksi ACID, foreign keys, dan mode WAL (*Write-Ahead Logging*).
- **Fakta Terdokumentasi:** Modul `sqlite3` bawaan Python versi 3.14/3.12 mendukung `PRAGMA foreign_keys = ON;` dan transaksi atomik `BEGIN IMMEDIATE`.
- **Asumsi:** Beban simulasi demo dan pengujian lokal dapat ditangani secara optimal oleh SQLite.
- **Keputusan:** Menggunakan SQLite 3 dengan mode WAL untuk menjamin integritas transaksi dan mencegah bentrok pemesanan simultan (*double-booking*).
- **Konsekuensi:** Portabilitas maksimal (berkas `.db` lokal), zero-configuration untuk pengujian, dan penjaminan ACID yang kokoh.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-004: Sandbox Filesystem Mandiri untuk Verifikasi Log Pemeliharaan

- **Konteks:** Status fisik peralatan (seperti proyektor yang baru saja diservis atau mengalami kabel putus) sering kali dicatat di catatan pemeliharaan harian tim teknisi dan belum diperbarui ke database utama.
- **Alternatif yang Dipertimbangkan:**
  1. *Akses filesystem tanpa batas:* Risiko keamanan tinggi jika agen mencoba membaca direktori di luar proyek (*directory traversal*).
  2. *Filesystem Sandbox Scoped:* Membatasi seluruh pembacaan berkas hanya di dalam folder `data/filesystem/`.
- **Fakta Terdokumentasi:** Validasi path menggunakan `os.path.commonpath` efektif menangkal serangan traversal jalur (seperti `../../`).
- **Asumsi:** Catatan pemeliharaan disimpan dalam format teks terstruktur yang mencantumkan ID alat, tanggal inspeksi, status operasional, dan keterangan teknisi.
- **Keputusan:** Mengimplementasikan Filesystem MCP dengan sandbox ketat pada folder `data/filesystem/` yang hanya mengizinkan operasi pembacaan (*read-only*).
- **Konsekuensi:** Keamanan terjamin; tidak ada risiko penulisan atau kebocoran file sistem operasi.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-005: Mock Campus Notification API Design & Departmental Routing

- **Konteks:** Setelah reservasi terkonfirmasi atau jika terjadi eskalasi masalah, departemen kampus terkait harus menerima pemberitahuan terstruktur.
- **Alternatif yang Dipertimbangkan:**
  1. *Integrasi email/Slack nyata:* Membutuhkan akun layanan eksternal, token bot, dan koneksi internet aktif.
  2. *Mock Notification MCP Server:* Menyimulasikan API internal kampus dengan penyimpanan memori/file log, mendukung pengiriman, pengecekan status, dan riwayat notifikasi.
- **Fakta Terdokumentasi:** Pengujian sistem otonom memerlukan kemampuan menyimulasikan kegagalan notifikasi secara deterministik (misalnya untuk menguji skenario parsial: booking sukses namun notif gagal).
- **Asumsi:** Pola notifikasi kampus dapat dipetakan secara terstruktur ke 4 departemen utama.
- **Keputusan:** Membuat server MCP `campusflow-notification` dengan kapabilitas simulasi kegagalan (*fault injection flag*) untuk menguji ketahanan alur parsial.
- **Konsekuensi:** Pengujian otomatis dapat memicu skenario kegagalan notifikasi secara presisi tanpa mengganggu layanan eksternal.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-006: Pemisahan Logika Deterministik dari Penalaran Probabilistik LLM

- **Konteks:** LLM memiliki sifat probabilistik yang dapat menyebabkan inkonsistensi saat menghitung kapasitas atau memeriksa bentrok rentang jam.
- **Alternatif yang Dipertimbangkan:**
  1. *Membiarkan LLM menyimpulkan bentrok jadwal:* Berisiko tinggi terjadi halusinasi bahwa ruangan kosong padahal ada reservasi tumpang tindih.
  2. *Penegakan Aturan Deterministik pada Simpul:* LLM hanya mengekstrak data dari teks; seluruh validasi matematika dan database dieksekusi oleh program Python.
- **Fakta Terdokumentasi:** Pengecekan interval waktu tumpang tindih ($\text{start}_1 < \text{end}_2 \land \text{end}_1 > \text{start}_2$) adalah operasi matematika biner murni yang 100% akurat jika dijalankan secara komputasional.
- **Asumsi:** Kebutuhan pengguna dapat dimodelkan secara terstruktur menggunakan skema Pydantic.
- **Keputusan:** Menerapkan aturan: **LLM untuk Pemahaman Bahasa (NLU), Kode Program Deterministik untuk Validasi Aturan Bisnis & Transaksi.**
- **Konsekuensi:** Sistem kebal terhadap halusinasi bisnis dan memiliki akurasi mutlak dalam pencegahan bentrok.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-007: Dual-Mode NLU Execution (Pluggable Cloud LLM + Fallback Deterministik)

- **Konteks:** Lingkungan kerja pengguna saat ini belum memiliki API key LLM berbayar (`OPENAI_API_KEY`, dll.), namun pengujian otomatis dan demo benchmark harus dapat berjalan kapan saja tanpa hambatan.
- **Alternatif yang Dipertimbangkan:**
  1. *Wajib API Key eksternal:* Menyebabkan proyek gagal dijalankan jika pengguna tidak memiliki kuota API.
  2. *Arsitektur Dual-Mode:* Mendukung penyedia model LLM eksternal jika API key tersedia di lingkungan, serta menyediakan pengurai berbasis pola deterministik (*Deterministic NLU Fallback*) saat API key kosong.
- **Fakta Terdokumentasi:** Uji acuan Benchmark (permintaan workshop AI 100 orang) dan 10 skenario pengujian memiliki pola sintaksis yang dapat diparsing secara deterministik.
- **Asumsi:** Fleksibilitas ini mempermudah evaluasi penguji kode dan pengujian integrasi berkelanjutan (CI/CD).
- **Keputusan:** Mengimplementasikan modul `NLUParser` yang cerdas: jika ada API key, gunakan model LLM; jika tidak ada, gunakan parser deterministik offline berbasis aturan.
- **Konsekuensi:** Proyek dapat diuji secara mandiri tanpa biaya, namun tetap siap dihubungkan ke model OpenAI / Anthropic / Gemini kapan pun diinginkan.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-008: Penanganan Kegagalan Parsial (*Partial Failure Isolation*)

- **Konteks:** Apa yang harus dilakukan jika reservasi berhasil dicatat ke dalam database, tetapi server notifikasi gagal merespons?
- **Alternatif yang Dipertimbangkan:**
  1. *Batalkan reservasi (Rollback):* Merugikan pengguna karena slot ruangan yang sah ikut hilang hanya karena layanan pesan terganggu sesaat.
  2. *Pertahankan reservasi dan laporkan status parsial:* Simpan bukti reservasi yang sah, tandai kegagalan pada bagian notifikasi, dan informasikan kepada pengguna secara transparan.
- **Fakta Terdokumentasi:** Spesifikasi teknis `00_MASTER_PROMPT.md` Bagian 9 & 15 secara eksplisit mewajibkan: *booking = CREATED, notification = FAILED*.
- **Asumsi:** Pemohon memprioritaskan kepastian ruangan dibandingkan notifikasi instan.
- **Keputusan:** Menerapkan isolasi batas kegagalan: transaksi database selesai lebih dahulu secara permanen; kegagalan notifikasi dicatat sebagai status kegagalan parsial tanpa membatalkan reservasi.
- **Konsekuensi:** Alur kerja memenuhi standar keandalan enterprise dan mematuhi spesifikasi acuan secara presisi.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-009: Jejak Audit Terstruktur (*Structured Audit Tracing*)

- **Konteks:** Pengguna, teknisi, dan auditor membutuhkan transparansi mengenai alasan mengapa suatu reservasi disetujui atau ditolak.
- **Alternatif yang Dipertimbangkan:**
  1. *Mencetak log konsol tanpa struktur:* Sulit dianalisis oleh mesin dan tidak persisten.
  2. *Tabel Audit Database + Struktur State Trace:* Setiap langkah mencatat waktu, simpul graf, bukti alat (*evidence*), dan status keputusan.
- **Fakta Terdokumentasi:** Jejak audit terstruktur memudahkan proses debugging (*troubleshooting*) dan evaluasi sistem berbasis agen.
- **Asumsi:** Format JSON terstruktur adalah representasi terbaik untuk jejak eksekusi.
- **Keputusan:** Membuat tabel database `audit_logs` dan atribut `audit_trail` pada state LangGraph untuk menyimpan riwayat setiap langkah secara berurutan.
- **Konsekuensi:** Observabilitas sistem mencapai 100%; setiap keputusan memiliki bukti empiris yang tercatat.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.

---

### ADR-010: Strategi Pengujian Otomatis 10 Skenario Acuan

- **Konteks:** Sistem harus membuktikan keandalannya melalui pengujian otomatis komprehensif sebelum dinyatakan selesai.
- **Alternatif yang Dipertimbangkan:**
  1. *Uji manual interaktif saja:* Rentan terlewatnya kasus tepi (*edge cases*) dan regresi kode.
  2. *Suite Pytest Otomatis:* Mencakup pengujian unit, pengujian komponen MCP, pengujian transisi state machine, dan 10 skenario acuan end-to-end.
- **Fakta Terdokumentasi:** `pytest` mendukung eksekusi pengujian asinkron (`pytest-asyncio`) yang diperlukan untuk menguji alur kerja LangGraph dan server MCP.
- **Asumsi:** Ke-10 skenario uji acuan mencakup seluruh kemungkinan jalur positif dan negatif dari sistem.
- **Keputusan:** Mengembangkan suite pengujian otomatis di direktori `tests/` yang memvalidasi Uji 1 hingga Uji 10 secara terprogram.
- **Konsekuensi:** Validasi otomatis dapat dijalankan dengan satu perintah (`pytest`), memberikan bukti nyata bahwa seluruh kriteria selesai (*Definition of Done*) terpenuhi.
- **Pertanyaan Belum Terselesaikan:** Tidak ada.
