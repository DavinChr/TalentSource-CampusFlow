# Definisi Masalah & Ruang Lingkup: CampusFlow
**Academic Campus Facility & Event Coordinator**

Dokumen ini mendefinisikan batas masalah, persona pengguna, spektrum masukan, batas cakupan sistem (*boundaries*), serta analisis kegagalan (*failure modes*) yang menjadi landasan rekayasa sistem CampusFlow.

---

## 1. Latar Belakang & Domain Masalah

### Fakta Terdokumentasi
1. **Fragmentasi Data Antar Departemen Kampus:**
   - Jadwal penggunaan ruangan umumnya disimpan di basis data akademik atau kalender terpusat.
   - Status pemeliharaan fisik dan kebersihan berada di catatan kerja tim fasilitas/properti.
   - Kelaikan operasional perangkat multimedia (proyektor, HDMI, mikrofon, amplifier) dicatat secara terpisah oleh tim TI atau bahkan hanya ada pada buku log fisik/file teks servis.
2. **Celah Validasi Sebelum Reservasi (*Prerequisite Validation Gap*):**
   - Sistem pemesanan konvensional hanya memeriksa ketersediaan slot waktu ruangan di kalender tanpa memverifikasi kelaikan peralatan pendukung yang diminta.
   - Akibatnya, pemesanan dapat dikonfirmasi meskipun proyektor utama di ruangan tersebut sedang rusak atau dalam perbaikan, yang memicu kekacauan pada hari pelaksanaan acara.
3. **Kelemahan Chatbot LLM Generatif Biasa:**
   - Chatbot biasa cenderung memberikan jawaban yang terdengar meyakinkan (*plausible*) namun kerap berhalusinasi mengonfirmasi reservasi tanpa memeriksa database secara nyata atau mengabaikan bentrok jadwal.

### Asumsi
- Diperlukan agen cerdas yang menggabungkan kemampuan pemahaman bahasa alami dengan mesin eksekusi deterministik yang tidak pernah melompati langkah validasi prasyarat.

### Keputusan Proyek
- CampusFlow dirancang sebagai sistem yang menjembatani kesenjangan ini dengan mengintegrasikan ketiga sumber informasi secara independen melalui Model Context Protocol (MCP) dan hanya mengesahkan reservasi jika seluruh rantai validasi terpenuhi.

---

## 2. Pemangku Kepentingan & Persona (*Stakeholders & Personas*)

| Persona | Peran | Kebutuhan Utama | Titik Masalah (*Pain Points*) |
|---|---|---|---|
| **Dosen / Penyelenggara Acara** | Pemohon (*Requester*) | Memesan ruangan yang sesuai dengan kapasitas peserta dan memastikan proyektor/alat berfungsi dengan satu instruksi bahasa alami sederhana. | Sering kali baru tahu proyektor rusak saat acara sudah dimulai; alur pemesanan manual antar bagian yang berbelit-belit. |
| **Tim Fasilitas Kampus (*Academic Facilities*)** | Pengelola Ruangan | Menerima data reservasi yang teratur, jadwal yang tidak tumpang tindih, dan daftar kebutuhan tata letak ruangan. | Terjadinya *double-booking*; menerima keluhan pengguna akibat ketidakcocokan kapasitas. |
| **Tim Dukungan TI & Multimedia** | Pengelola Perangkat | Menerima pemberitahuan awal kebutuhan alat; sistem tidak memesan alat yang sedang dalam status rusak/perbaikan. | Peralatan yang rusak dipaksakan dipakai pengguna tanpa konfirmasi perbaikan selesai. |
| **Tim Pemeliharaan (*Maintenance*)** | Teknisi Perbaikan | Menjaga integritas log perbaikan agar tercatat akurat dan mencegah ruangan bermasalah digunakan. | Sulit mengoordinasikan jadwal perbaikan dengan jadwal acara yang padat. |

---

## 3. Spektrum Masukan Pengguna (*Input Spectrum*)

CampusFlow menerima berbagai variasi instruksi bahasa alami:

1. **Permintaan Lengkap & Jelas (*Explicit & Complete Request*):**
   - *Contoh:* `"Pesan auditorium utama untuk workshop AI 100 orang pada Selasa depan jam 09:00 sampai 11:00, pastikan proyektor berfungsi, dan beri tahu tim fasilitas."`
   - *Penanganan:* Sistem mengurai entitas secara lengkap, melakukan resolusi tanggal absolut, memvalidasi kapasitas dan status proyektor, lalu mengeksekusi alur secara mulus.
2. **Permintaan dengan Tanggal/Waktu Relatif (*Relative Temporal Request*):**
   - *Contoh:* `"Pesan ruang seminar B besok lusa jam 14:00 untuk rapat evaluasi."`
   - *Penanganan:* Sistem menggunakan tanggal acuan sistem saat ini untuk mengonversi waktu relatif menjadi tanggal kalender absolut (`YYYY-MM-DD`).
3. **Permintaan Ambigu / Informasi Kurang (*Ambiguous / Incomplete Request*):**
   - *Contoh:* `"Pesan ruangan untuk rapat minggu depan."` (Tidak ada nama ruangan, jam, kapasitas, atau tanggal pasti).
   - *Penanganan:* Sistem **DILARANG MENGARANG DATA**. Alur kerja berhenti pada status `INVALID_REQUEST / NEEDS_CLARIFICATION` dan meminta pengguna melengkapi data yang hilang.
4. **Permintaan dengan Kebutuhan Fasilitas yang Tidak Tersedia (*Unavailable Resource Request*):**
   - *Contoh:* `"Pesan ruang rapat lantai 2 dengan kapasitas 500 orang."` (Ruangan hanya muat 30 orang).
   - *Penanganan:* Sistem memvalidasi kapasitas, menggagalkan pemesanan dengan status `INSUFFICIENT_CAPACITY`, dan memberikan saran ruangan alternatif yang memenuhi syarat jika tersedia.

---

## 4. Batasan Masalah & Ruang Lingkup Sistem (*System Boundaries*)

### Dalam Cakupan (*In Scope*)
- Pemrosesan instruksi bahasa alami pemesanan fasilitas kampus.
- Resolusi entitas: nama ruangan, jenis acara, pemohon, kapasitas, tanggal/waktu, kebutuhan peralatan.
- Pengecekan ketersediaan ruangan dan kapasitas melalui Database MCP.
- Pengecekan riwayat pemeliharaan dan status fisik peralatan melalui Filesystem MCP.
- Penegakan transaksi ACID untuk pembuatan reservasi di database SQLite.
- Pengiriman notifikasi ke departemen terkait melalui Mock API MCP.
- Penanganan kegagalan terstruktur (*failure handling*) untuk 10 skenario uji acuan.
- Pencatatan jejak audit eksekusi (*audit trail*).

### Di Luar Cakupan (*Out of Scope*)
- Pembayaran sewa gedung atau integrasi *payment gateway*.
- Pembuatan akun pengguna dengan autentikasi biometrik atau OAuth SSO universitas (cukup identifikasi ID/nama pemohon).
- Kontrol perangkat keras IoT secara langsung (misal: otomatis menyalakan saklar lampu/proyektor via jaringan fisik).
- Penjadwalan mata kuliah reguler semesteran penuh (CampusFlow fokus pada pemesanan acara ad-hoc / kegiatan kampus).

---

## 5. Matriks Analisis Kegagalan (*Failure Modes & Mitigation Matrix*)

| Skenario Kegagalan | Akar Masalah | Respon Sistem yang Diharapkan | Status Akhir Alur Kerja |
|---|---|---|---|
| **Bentrok Jadwal** | Ruangan telah dipesan oleh pemohon lain pada jam yang sama | Tolak pemesanan, tampilkan informasi bentrok, dan tawarkan alternatif waktu/ruangan jika ada. | `ROOM_UNAVAILABLE` |
| **Kapasitas Kurang** | Jumlah peserta melebihi kapasitas maksimal ruangan | Tolak pemesanan, jelaskan selisih kapasitas, sarankan ruangan yang lebih besar. | `INSUFFICIENT_CAPACITY` |
| **Peralatan Rusak** | Proyektor memiliki catatan pemeliharaan aktif / rusak di file log | Tolak pemesanan ruangan untuk acara tersebut, jelaskan bahwa alat wajib tidak laik pakai. | `EQUIPMENT_UNAVAILABLE` |
| **Status Alat Tidak Diketahui** | Peralatan tidak memiliki catatan inspeksi atau data tidak ditemukan | Jangan berasumsi alat berfungsi. Tolak pemesanan sampai verifikasi fisik dilakukan. | `EQUIPMENT_STATUS_UNKNOWN` |
| **Kegagalan Database** | Disk penuh, database terkunci, atau koneksi terputus | Tangani galat secara anggun (*graceful error*), jangan laporkan reservasi berhasil. | `DATABASE_ERROR` |
| **Kegagalan Notifikasi** | Mock API notifikasi tidak merespons setelah reservasi tercatat | Pertahankan data reservasi di database, tandai notifikasi sebagai gagal (*partial success*). | `NOTIFICATION_ERROR` (Booking: SUCCESS) |
| **Informasi Kontradiktif** | DB mencatat alat "Aktif", namun log filesystem mencatat "Rusak" | Hentikan operasi penulisan, tandai bukti tidak konsisten, laporkan ke pengguna. | `WORKFLOW_ABORTED` |

---

## 6. Pemisahan Fakta, Asumsi, Keputusan, dan Pertanyaan

### Fakta Terdokumentasi
- Pemesanan fasilitas kampus melibatkan risiko tinggi terhadap kelancaran kegiatan belajar-mengajar dan acara penting.
- Pelanggaran validasi peralatan menimbulkan kerugian operasional nyata bagi civitas akademika.

### Asumsi
- Seluruh ruangan dan peralatan dalam sistem kampus memiliki pengenal unik (*unique identifier* seperti kode ruangan `AUD-01`, kode proyektor `PRJ-01`).
- Jam operasional fasilitas kampus dibatasi antara pukul 07:00 hingga 22:00 WIB.

### Keputusan Proyek
- Setiap interaksi pengguna diperlakukan sebagai transaksi alur kerja terkendali dengan jaminan: **Tidak ada reservasi yang dicatat sebelum seluruh simpul prasyarat diverifikasi secara empiris.**

### Pertanyaan Belum Terselesaikan
- *Apakah sistem perlu mendukung pembatalan atau perubahan jadwal (reschedule)?* Untuk lingkup proyek ini, fokus utama adalah orkestrasi pembuatan reservasi baru yang aman dan andal.
