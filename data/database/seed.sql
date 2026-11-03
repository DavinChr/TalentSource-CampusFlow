-- =============================================================
-- CampusFlow Seed Data
-- Realistic campus data supporting all 10 test scenarios
-- =============================================================

-- ─── BUILDINGS ───────────────────────────────────────────────
INSERT INTO buildings (code, name, address, floors) VALUES
    ('MAIN', 'Gedung Utama Kampus',       'Jl. Kampus Raya No. 1, Lantai 1-4',  4),
    ('SCI',  'Gedung Ilmu Pengetahuan',   'Jl. Kampus Raya No. 2, Sayap Timur', 5),
    ('ENG',  'Gedung Teknik & Rekayasa',  'Jl. Kampus Raya No. 3, Sayap Barat', 3),
    -- Universitas Katolik Parahyangan (UNPAR)
    ('PPAG', 'Gedung Pusat Pembelajaran Arntz-Geise (PPAG 1 & 2)', 'Jl. Ciumbuleuit No. 94, Bandung', 14),
    ('G0',   'Gedung 0 (Rektorat & Kantor Pusat)',                 'Jl. Ciumbuleuit No. 94, Bandung', 4),
    ('G9',   'Gedung 9 (Fakultas Ekonomi & Bisnis)',             'Jl. Ciumbuleuit No. 94, Bandung', 5),
    ('G2',   'Gedung 2 (Fakultas Hukum)',                        'Jl. Ciumbuleuit No. 94, Bandung', 3);

-- ─── ROOMS ───────────────────────────────────────────────────
INSERT INTO rooms (building_id, room_code, room_name, room_type, capacity, floor, status) VALUES
    -- Gedung Utama (building_id = 1)
    (1, 'AUD-01',  'Auditorium Utama',        'auditorium',       300, 1, 'ACTIVE'),
    (1, 'SR-101',  'Ruang Seminar 101',        'seminar_room',      50, 1, 'ACTIVE'),
    (1, 'SR-102',  'Ruang Seminar 102',        'seminar_room',      50, 2, 'ACTIVE'),
    (1, 'CR-301',  'Ruang Konferensi Eksekutif','conference_room',  20, 3, 'ACTIVE'),
    -- Gedung Ilmu Pengetahuan (building_id = 2)
    (2, 'LH-201',  'Ruang Kuliah 201',         'lecture_hall',      80, 2, 'ACTIVE'),
    (2, 'LH-202',  'Ruang Kuliah 202',         'lecture_hall',     120, 2, 'ACTIVE'),
    -- Gedung Teknik (building_id = 3)
    (3, 'LAB-401', 'Laboratorium Komputer',    'computer_lab',      40, 1, 'UNDER_RENOVATION'),
    (3, 'SR-ENG1', 'Ruang Seminar Teknik',     'seminar_room',      30, 1, 'ACTIVE'),
    -- UNPAR: Gedung PPAG
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-AUD', 'Auditorium Utama PPAG',         'auditorium',       800, 2,  'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-LT1', 'Lecture Theater 1 PPAG',        'lecture_hall',      90, 12, 'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-LT2', 'Lecture Theater 2 PPAG',        'lecture_hall',      90, 12, 'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-LT3', 'Lecture Theater 3 PPAG',        'lecture_hall',      90, 12, 'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-201', 'Lacture Hall PPAG',             'lecture_hall',     160, 9,  'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-202', 'Ruang Kuliah PPAG 202',         'lecture_hall',      60, 4,  'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'PPAG'), 'PPAG-203', 'Ruang Multifungsi',             'multipurpose',     300, 1,  'ACTIVE'),
    -- UNPAR: Gedung 0 Rektorat
    ((SELECT id FROM buildings WHERE code = 'G0'),   'G0-OR',    'Operation Room Rektorat',       'conference_room',   50, 4,  'ACTIVE'),
    -- UNPAR: Gedung 9 FEB
    ((SELECT id FROM buildings WHERE code = 'G9'),   'G9-AULA',  'Aula Driekore (Aula FE)',       'auditorium',       250, 4,  'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'G9'),   'G9-101',   'Ruang Kuliah 9101',             'lecture_hall',      60, 1,  'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'G9'),   'G9-LAB1',  'Laboratorium Komputer Komputasi Lanjut 1', 'computer_lab', 30, 0, 'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'G9'),   'G9-LAB2',  'Laboratorium Komputer Komputasi Lanjut 2', 'computer_lab', 30, 0, 'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'G9'),   'G9-LAB3',  'Laboratorium Komputer Komputasi Lanjut 3', 'computer_lab', 60, 0, 'ACTIVE'),
    -- UNPAR: Gedung 2 FH
    ((SELECT id FROM buildings WHERE code = 'G2'),   'G2-MC',    'Ruang Peradilan Semu (Moot Court)', 'seminar_room',  50, 1,  'ACTIVE'),
    ((SELECT id FROM buildings WHERE code = 'G2'),   'G2-SEM',   'Ruang Seminar B. Arief Sidharta',   'seminar_room',  60, 2,  'ACTIVE');

-- ─── EQUIPMENT ───────────────────────────────────────────────
INSERT INTO equipment (equipment_code, equipment_name, equipment_type, brand, model, serial_number, status) VALUES
    -- Projectors
    ('PRJ-01', 'Proyektor Seminar Epson',        'projector',   'Epson',    'EB-L615U',   'EP2024-001', 'ACTIVE'),           -- OPERATIONAL (healthy)
    ('PRJ-02', 'Proyektor Seminar BenQ',         'projector',   'BenQ',     'LU930',      'BQ2023-002', 'UNDER_MAINTENANCE'), -- BROKEN (for test 4 & 5)
    ('PRJ-03', 'Proyektor Auditorium ViewSonic', 'projector',   'ViewSonic','PA503X',     'VS2022-003', 'ACTIVE'),           -- OPERATIONAL
    ('PRJ-04', 'Proyektor Kuliah Panasonic',     'projector',   'Panasonic','PT-MZ570',   'PN2024-004', 'ACTIVE'),           -- OPERATIONAL (contradiction test: DB says ACTIVE, FS says FAULTY)
    -- Microphones
    ('MIC-01', 'Mikrofon Wireless Shure',        'microphone',  'Shure',    'ULXD2/B58',  'SH2024-001', 'ACTIVE'),
    ('MIC-02', 'Mikrofon Kabel Audio-Technica',  'microphone',  'Audio-Technica','AT4022','AT2023-001', 'ACTIVE'),
    ('MIC-03', 'Mikrofon Clip-On Seminar',       'microphone',  'Sennheiser','EW 100 G4', 'SE2024-001', 'ACTIVE'),
    -- Sound systems
    ('SND-01', 'Sound System Auditorium JBL',    'sound_system','JBL',      'PRX812W',    'JB2021-001', 'ACTIVE'),
    ('SND-02', 'Sound System Portable Yamaha',   'sound_system','Yamaha',   'DXR10mkII',  'YM2023-001', 'ACTIVE'),
    -- Smartboards
    ('SBD-01', 'Smartboard Samsung Flip',        'smartboard',  'Samsung',  'WM85B',      'SM2024-001', 'ACTIVE'),
    -- UNPAR Equipment: Projectors
    ('PRJ-PPAG-AUD', 'Proyektor Dual Laser Auditorium PPAG',  'projector',   'Barco',     'UDX-4K32',   'UNPAR-PRJ-001', 'ACTIVE'),
    ('PRJ-PPAG-202', 'Proyektor Kelas PPAG 202',              'projector',   'Epson',     'EB-L615U',   'UNPAR-PRJ-002', 'ACTIVE'),
    ('PRJ-G0-OR',    'Proyektor Operation Room Rektorat',     'projector',   'Panasonic', 'PT-MZ570',   'UNPAR-PRJ-003', 'ACTIVE'),
    ('PRJ-G9-AULA',  'Proyektor Aula Driekore FEB',           'projector',   'Sony',      'VPL-FHZ75',  'UNPAR-PRJ-004', 'ACTIVE'),
    ('PRJ-G9-101',   'Proyektor Ruang Kuliah 9101',           'projector',   'Epson',     'EB-2250U',   'UNPAR-PRJ-005', 'ACTIVE'),
    ('PRJ-G9-LAB1',  'Proyektor Lab Komputer G9-1',           'projector',   'BenQ',      'MH733',      'UNPAR-PRJ-006', 'ACTIVE'),
    ('PRJ-G9-LAB2',  'Proyektor Lab Komputer G9-2',           'projector',   'BenQ',      'MH733',      'UNPAR-PRJ-007', 'ACTIVE'),
    ('PRJ-G9-LAB3',  'Proyektor Lab Komputer G9-3',           'projector',   'BenQ',      'MH733',      'UNPAR-PRJ-008', 'ACTIVE'),
    ('PRJ-G2-MC',    'Proyektor Ruang Sidang Moot Court',     'projector',   'Epson',     'EB-X500',    'UNPAR-PRJ-009', 'ACTIVE'),
    ('PRJ-G2-SEM',   'Proyektor Seminar B. Arief Sidharta',   'projector',   'Panasonic', 'PT-VMZ51',   'UNPAR-PRJ-010', 'ACTIVE'),
    -- UNPAR Sound Systems
    ('SND-PPAG-AUD', 'Line Array Sound System Auditorium',    'sound_system','L-Acoustics','Kiva II',    'UNPAR-SND-001', 'ACTIVE'),
    ('SND-PPAG-LT1', 'Sound System Lecture Theater 1 PPAG',   'sound_system','Yamaha',    'CBR12',      'UNPAR-SND-002', 'ACTIVE'),
    ('SND-PPAG-LT2', 'Sound System Lecture Theater 2 PPAG',   'sound_system','Yamaha',    'CBR12',      'UNPAR-SND-003', 'ACTIVE'),
    ('SND-PPAG-LT3', 'Sound System Lecture Theater 3 PPAG',   'sound_system','Yamaha',    'CBR12',      'UNPAR-SND-004', 'ACTIVE'),
    ('SND-PPAG-201', 'Sound System Lecture Hall PPAG',        'sound_system','Yamaha',    'DXR10mkII',  'UNPAR-SND-005', 'ACTIVE'),
    ('SND-G0-OR',    'Sound System Operation Room Rektorat',  'sound_system','Bose',      'FreeSpace',  'UNPAR-SND-006', 'ACTIVE'),
    ('SND-G9-AULA',  'Sound System Aula Driekore FE',         'sound_system','JBL',       'PRX812W',    'UNPAR-SND-007', 'ACTIVE'),
    ('SND-G2-MC',    'Sound System Moot Court Peradilan Semu','sound_system','Yamaha',    'StagePas',   'UNPAR-SND-008', 'ACTIVE'),
    ('SND-G2-SEM',   'Sound System Seminar B. Arief Sidharta','sound_system','JBL',       'EON615',     'UNPAR-SND-009', 'ACTIVE'),
    -- UNPAR Microphones
    ('MIC-PPAG-AUD', 'Wireless Microphone Shure Concert Rig', 'microphone',  'Shure',     'Axient Dig', 'UNPAR-MIC-001', 'ACTIVE'),
    ('MIC-PPAG-LT1', 'Wireless Microphone Shure LT1',         'microphone',  'Shure',     'BLX24',      'UNPAR-MIC-002', 'ACTIVE'),
    ('MIC-PPAG-LT2', 'Wireless Microphone Shure LT2',         'microphone',  'Shure',     'BLX24',      'UNPAR-MIC-003', 'ACTIVE'),
    ('MIC-PPAG-LT3', 'Wireless Microphone Shure LT3',         'microphone',  'Shure',     'BLX24',      'UNPAR-MIC-004', 'ACTIVE'),
    ('MIC-PPAG-201', 'Wireless Microphone Sennheiser LH',     'microphone',  'Sennheiser','EW-D',       'UNPAR-MIC-005', 'ACTIVE'),
    ('MIC-G0-OR',    'Microphone Delegate OR Rektorat',       'microphone',  'Bosch',     'CCS 900',    'UNPAR-MIC-006', 'ACTIVE'),
    ('MIC-G9-AULA',  'Microphone Podium Aula FE',             'microphone',  'Shure',     'SM58',       'UNPAR-MIC-007', 'ACTIVE'),
    ('MIC-G2-MC',    'Set Microphone Meja Hakim/Jaksa/Pembela','microphone', 'Audio-Technica','Pro 49Q',  'UNPAR-MIC-008', 'ACTIVE'),
    ('MIC-G2-SEM',   'Microphone Seminar FH',                 'microphone',  'Sennheiser','E835',       'UNPAR-MIC-009', 'ACTIVE'),
    -- UNPAR Smartboards
    ('SBD-PPAG-LT1', 'Smartboard Samsung Flip LT1 PPAG',      'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-001', 'ACTIVE'),
    ('SBD-PPAG-LT2', 'Smartboard Samsung Flip LT2 PPAG',      'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-002', 'ACTIVE'),
    ('SBD-PPAG-LT3', 'Smartboard Samsung Flip LT3 PPAG',      'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-003', 'ACTIVE'),
    ('SBD-PPAG-201', 'Smartboard Besar Lecture Hall PPAG',    'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-004', 'ACTIVE'),
    -- UNPAR Whiteboards
    ('WBD-PPAG-LT1', 'Whiteboard Kaca LT1',                   'whiteboard',  'Custom',    'Magnetic',   'UNPAR-WBD-001', 'ACTIVE'),
    ('WBD-PPAG-LT2', 'Whiteboard Kaca LT2',                   'whiteboard',  'Custom',    'Magnetic',   'UNPAR-WBD-002', 'ACTIVE'),
    ('WBD-PPAG-LT3', 'Whiteboard Kaca LT3',                   'whiteboard',  'Custom',    'Magnetic',   'UNPAR-WBD-003', 'ACTIVE'),
    ('WBD-PPAG-202', 'Whiteboard Ruang Kuliah 202',           'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-004', 'ACTIVE'),
    ('WBD-G9-101',   'Whiteboard Ruang Kuliah 9101',          'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-005', 'ACTIVE'),
    ('WBD-G9-LAB1',  'Whiteboard Lab Komputer 1',             'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-006', 'ACTIVE'),
    ('WBD-G9-LAB2',  'Whiteboard Lab Komputer 2',             'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-007', 'ACTIVE'),
    ('WBD-G9-LAB3',  'Whiteboard Lab Komputer 3',             'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-008', 'ACTIVE'),
    ('WBD-G2-SEM',   'Whiteboard Seminar B. Arief Sidharta',  'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-009', 'ACTIVE'),
    -- UNPAR Computers
    ('CMP-G9-LAB1',  '30 Unit PC Core i7 Lab Komputasi 1',    'computer',    'Dell',      'OptiPlex',   'UNPAR-CMP-001', 'ACTIVE'),
    ('CMP-G9-LAB2',  '30 Unit PC Core i7 Lab Komputasi 2',    'computer',    'Dell',      'OptiPlex',   'UNPAR-CMP-002', 'ACTIVE'),
    ('CMP-G9-LAB3',  '60 Unit PC Core i7 Lab Komputasi 3',    'computer',    'Dell',      'OptiPlex',   'UNPAR-CMP-003', 'ACTIVE'),
    -- UNPAR Lighting & Stage
    ('LIT-PPAG-AUD', 'Stage Lighting Rig Auditorium PPAG',    'lighting',    'ETC',       'ColorSource','UNPAR-LIT-001', 'ACTIVE'),
    ('STG-G9-AULA',  'Panggung Acara Aula Driekore',          'stage',       'Custom',    'Stage-FE',   'UNPAR-STG-001', 'ACTIVE');

-- ─── ROOM EQUIPMENT ASSIGNMENTS ──────────────────────────────
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    -- AUD-01 (Auditorium Utama): PRJ-03, MIC-01, SND-01
    (1, 3, 1),  -- PRJ-03 (primary projector)
    (1, 5, 1),  -- MIC-01 (wireless mic)
    (1, 8, 1),  -- SND-01 (main sound system)
    -- SR-101 (Seminar 101): PRJ-01, MIC-02
    (2, 1, 1),  -- PRJ-01 (ACTIVE — healthy)
    (2, 6, 1),  -- MIC-02
    -- SR-102 (Seminar 102): PRJ-02 (UNDER_MAINTENANCE), MIC-03
    (3, 2, 1),  -- PRJ-02 (UNDER_MAINTENANCE — for equipment fail tests)
    (3, 7, 1),  -- MIC-03
    -- CR-301 (Conference): SBD-01
    (4, 10, 1), -- SBD-01
    -- LH-201 (Kuliah 201): PRJ-04 (DB=ACTIVE but FS=FAULTY — conflict test)
    (5, 4, 1),  -- PRJ-04 (DB says ACTIVE, filesystem says FAULTY — contradiction)
    -- LH-202 (Kuliah 202): PRJ-01, SND-02
    (6, 1, 0),  -- PRJ-01 (shared, non-primary)
    (6, 9, 1),  -- SND-02
    -- SR-ENG1 (Seminar Teknik): MIC-03
    (8, 7, 0);  -- MIC-03 (shared)

-- UNPAR Room Equipment Assignments (via lookup)
INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'PPAG-AUD' AND e.equipment_code IN ('PRJ-PPAG-AUD', 'SND-PPAG-AUD', 'MIC-PPAG-AUD', 'LIT-PPAG-AUD');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'PPAG-LT1' AND e.equipment_code IN ('SBD-PPAG-LT1', 'SND-PPAG-LT1', 'MIC-PPAG-LT1', 'WBD-PPAG-LT1');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'PPAG-LT2' AND e.equipment_code IN ('SBD-PPAG-LT2', 'SND-PPAG-LT2', 'MIC-PPAG-LT2', 'WBD-PPAG-LT2');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'PPAG-LT3' AND e.equipment_code IN ('SBD-PPAG-LT3', 'SND-PPAG-LT3', 'MIC-PPAG-LT3', 'WBD-PPAG-LT3');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'PPAG-201' AND e.equipment_code IN ('SBD-PPAG-201', 'SND-PPAG-201', 'MIC-PPAG-201');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'PPAG-202' AND e.equipment_code IN ('PRJ-PPAG-202', 'WBD-PPAG-202');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G0-OR' AND e.equipment_code IN ('PRJ-G0-OR', 'SND-G0-OR', 'MIC-G0-OR');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G9-AULA' AND e.equipment_code IN ('PRJ-G9-AULA', 'SND-G9-AULA', 'MIC-G9-AULA', 'STG-G9-AULA');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G9-101' AND e.equipment_code IN ('PRJ-G9-101', 'WBD-G9-101');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G9-LAB1' AND e.equipment_code IN ('CMP-G9-LAB1', 'PRJ-G9-LAB1', 'WBD-G9-LAB1');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G9-LAB2' AND e.equipment_code IN ('CMP-G9-LAB2', 'PRJ-G9-LAB2', 'WBD-G9-LAB2');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G9-LAB3' AND e.equipment_code IN ('CMP-G9-LAB3', 'PRJ-G9-LAB3', 'WBD-G9-LAB3');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G2-MC' AND e.equipment_code IN ('PRJ-G2-MC', 'SND-G2-MC', 'MIC-G2-MC');

INSERT INTO room_equipment (room_id, equipment_id, is_primary)
SELECT r.id, e.id, 1 FROM rooms r, equipment e WHERE r.room_code = 'G2-SEM' AND e.equipment_code IN ('PRJ-G2-SEM', 'SND-G2-SEM', 'MIC-G2-SEM', 'WBD-G2-SEM');

-- ─── USERS ───────────────────────────────────────────────────
INSERT INTO users (employee_id, full_name, email, department, role) VALUES
    ('FAC-001', 'Dr. Sari Dewi Kusuma',     'sari.dewi@kampus.ac.id',      'Fakultas Ilmu Komputer',       'faculty'),
    ('FAC-002', 'Prof. Bambang Wiranto',    'bambang.w@kampus.ac.id',      'Fakultas Teknik',              'faculty'),
    ('STF-001', 'Andi Pratama',             'andi.pratama@kampus.ac.id',   'Biro Akademik & Kemahasiswaan','staff'),
    ('STF-002', 'Rina Suhartini',           'rina.s@kampus.ac.id',         'Biro Umum & Fasilitas',        'staff'),
    ('ADM-001', 'Sistem CampusFlow',        'system@campusflow.test',      'Sistem Informasi',             'admin'),
    ('STU-001', 'Budi Santoso',             'budi.s@student.kampus.ac.id', 'Himpunan Mahasiswa TI',        'student');

-- ─── EXISTING BOOKINGS (to create conflict scenarios) ─────────
INSERT INTO bookings (booking_reference, room_id, user_id, event_name, booking_date, start_time, end_time, attendee_count, status, confirmed_at) VALUES

    -- [AUD-01] Benchmark date 2026-09-23 morning OCCUPIED (Test 2 — Room Unavailable)
    ('BK-2026-001', 1, 1, 'Seminar Nasional Kecerdasan Buatan',
     '2026-09-23', '08:00', '12:00', 250, 'CONFIRMED',
     '2026-09-20T10:00:00Z'),

    -- [AUD-01] 2026-09-23 afternoon FREE (Test 1 success can use 13:00-15:00)

    -- [SR-101] Wednesday occupied — Capacity also insufficient for 100 pax (Test 3)
    ('BK-2026-002', 2, 2, 'Rapat Koordinasi Program Studi',
     '2026-09-23', '13:00', '15:00', 30, 'CONFIRMED',
     '2026-09-20T11:00:00Z'),

    -- [AUD-01] Full-day block on 2026-09-24 (for duplicate test baseline)
    ('BK-2026-003', 1, 3, 'Dies Natalis Kampus Ke-50',
     '2026-09-24', '07:00', '21:00', 280, 'CONFIRMED',
     '2026-09-18T09:00:00Z'),

    -- [LH-201] Free — but PRJ-04 has filesystem contradiction (Test 8)
    -- [SR-102] Free — but PRJ-02 is UNDER_MAINTENANCE in both DB and FS (Test 4)

    -- Completed historical booking (for realistic data)
    ('BK-2026-000', 1, 1, 'Orientasi Mahasiswa Baru 2026',
     '2026-09-10', '08:00', '17:00', 290, 'COMPLETED',
     '2026-09-05T08:00:00Z'),

    -- [SR-102] Booking on 2026-09-25 (PRJ-02 is UNDER_MAINTENANCE — test 4 uses SR-102)
    ('BK-2026-004', 3, 4, 'Rapat Tim Kurikulum',
     '2026-09-25', '09:00', '11:00', 15, 'CONFIRMED',
     '2026-09-19T08:00:00Z');
