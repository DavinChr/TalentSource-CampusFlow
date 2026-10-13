-- =============================================================
-- CampusFlow Seed Data: Universitas Katolik Parahyangan (UNPAR)
-- Berdasarkan Catatan/DATA_RUANGAN_UNPAR.txt
-- =============================================================

-- ─── BUILDINGS ───────────────────────────────────────────────
INSERT INTO buildings (code, name, address, floors) VALUES
    ('PPAG', 'Gedung Pusat Pembelajaran Arntz-Geise (PPAG 1 & 2)', 'Jl. Ciumbuleuit No. 94, Hegarmanah, Bandung', 14),
    ('G0',   'Gedung 0 (Rektorat & Kantor Pusat)',                 'Jl. Ciumbuleuit No. 94, Hegarmanah, Bandung', 4),
    ('G9',   'Gedung 9 (Fakultas Ekonomi & Bisnis)',             'Jl. Ciumbuleuit No. 94, Hegarmanah, Bandung', 5),
    ('G2',   'Gedung 2 (Fakultas Hukum)',                        'Jl. Ciumbuleuit No. 94, Hegarmanah, Bandung', 3);

-- ─── ROOMS ───────────────────────────────────────────────────
-- building_id 1: PPAG, 2: G0, 3: G9, 4: G2
INSERT INTO rooms (building_id, room_code, room_name, room_type, capacity, floor, status) VALUES
    -- PPAG (Pusat Pembelajaran Arntz-Geise)
    (1, 'PPAG-AUD', 'Auditorium Utama PPAG',         'auditorium',       800, 2,  'ACTIVE'),
    (1, 'PPAG-LT1', 'Lecture Theater 1 PPAG',        'lecture_hall',      90, 12, 'ACTIVE'),
    (1, 'PPAG-LT2', 'Lecture Theater 2 PPAG',        'lecture_hall',      90, 12, 'ACTIVE'),
    (1, 'PPAG-LT3', 'Lecture Theater 3 PPAG',        'lecture_hall',      90, 12, 'ACTIVE'),
    (1, 'PPAG-201', 'Lacture Hall PPAG',             'lecture_hall',     160, 9,  'ACTIVE'),
    (1, 'PPAG-202', 'Ruang Kuliah PPAG 202',         'lecture_hall',      60, 4,  'ACTIVE'),
    (1, 'PPAG-203', 'Ruang Multifungsi',             'multipurpose',     300, 1,  'ACTIVE'),

    -- Gedung 0 (Rektorat)
    (2, 'G0-OR',    'Operation Room Rektorat',       'conference_room',   50, 4,  'ACTIVE'),

    -- Gedung 9 (Fakultas Ekonomi & Bisnis)
    (3, 'G9-AULA',  'Aula Driekore (Aula FE)',       'auditorium',       250, 4,  'ACTIVE'),
    (3, 'G9-101',   'Ruang Kuliah 9101',             'lecture_hall',      60, 1,  'ACTIVE'),
    (3, 'G9-LAB1',  'Laboratorium Komputer Komputasi Lanjut 1', 'computer_lab', 30, 0, 'ACTIVE'),
    (3, 'G9-LAB2',  'Laboratorium Komputer Komputasi Lanjut 2', 'computer_lab', 30, 0, 'ACTIVE'),
    (3, 'G9-LAB3',  'Laboratorium Komputer Komputasi Lanjut 3', 'computer_lab', 60, 0, 'ACTIVE'),

    -- Gedung 2 (Fakultas Hukum)
    (4, 'G2-MC',    'Ruang Peradilan Semu (Moot Court)', 'seminar_room',  50, 1,  'ACTIVE'),
    (4, 'G2-SEM',   'Ruang Seminar B. Arief Sidharta',   'seminar_room',  60, 2,  'ACTIVE');

-- ─── EQUIPMENT ───────────────────────────────────────────────
INSERT INTO equipment (equipment_code, equipment_name, equipment_type, brand, model, serial_number, status) VALUES
    -- Projectors
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

    -- Sound Systems
    ('SND-PPAG-AUD', 'Line Array Sound System Auditorium',    'sound_system','L-Acoustics','Kiva II',    'UNPAR-SND-001', 'ACTIVE'),
    ('SND-PPAG-LT1', 'Sound System Lecture Theater 1 PPAG',   'sound_system','Yamaha',    'CBR12',      'UNPAR-SND-002', 'ACTIVE'),
    ('SND-PPAG-LT2', 'Sound System Lecture Theater 2 PPAG',   'sound_system','Yamaha',    'CBR12',      'UNPAR-SND-003', 'ACTIVE'),
    ('SND-PPAG-LT3', 'Sound System Lecture Theater 3 PPAG',   'sound_system','Yamaha',    'CBR12',      'UNPAR-SND-004', 'ACTIVE'),
    ('SND-PPAG-201', 'Sound System Lecture Hall PPAG',        'sound_system','Yamaha',    'DXR10mkII',  'UNPAR-SND-005', 'ACTIVE'),
    ('SND-G0-OR',    'Sound System Operation Room Rektorat',  'sound_system','Bose',      'FreeSpace',  'UNPAR-SND-006', 'ACTIVE'),
    ('SND-G9-AULA',  'Sound System Aula Driekore FE',         'sound_system','JBL',       'PRX812W',    'UNPAR-SND-007', 'ACTIVE'),
    ('SND-G2-MC',    'Sound System Moot Court Peradilan Semu','sound_system','Yamaha',    'StagePas',   'UNPAR-SND-008', 'ACTIVE'),
    ('SND-G2-SEM',   'Sound System Seminar B. Arief Sidharta','sound_system','JBL',       'EON615',     'UNPAR-SND-009', 'ACTIVE'),

    -- Microphones
    ('MIC-PPAG-AUD', 'Wireless Microphone Shure Concert Rig', 'microphone',  'Shure',     'Axient Dig', 'UNPAR-MIC-001', 'ACTIVE'),
    ('MIC-PPAG-LT1', 'Wireless Microphone Shure LT1',         'microphone',  'Shure',     'BLX24',      'UNPAR-MIC-002', 'ACTIVE'),
    ('MIC-PPAG-LT2', 'Wireless Microphone Shure LT2',         'microphone',  'Shure',     'BLX24',      'UNPAR-MIC-003', 'ACTIVE'),
    ('MIC-PPAG-LT3', 'Wireless Microphone Shure LT3',         'microphone',  'Shure',     'BLX24',      'UNPAR-MIC-004', 'ACTIVE'),
    ('MIC-PPAG-201', 'Wireless Microphone Sennheiser LH',     'microphone',  'Sennheiser','EW-D',       'UNPAR-MIC-005', 'ACTIVE'),
    ('MIC-G0-OR',    'Microphone Delegate OR Rektorat',       'microphone',  'Bosch',     'CCS 900',    'UNPAR-MIC-006', 'ACTIVE'),
    ('MIC-G9-AULA',  'Microphone Podium Aula FE',             'microphone',  'Shure',     'SM58',       'UNPAR-MIC-007', 'ACTIVE'),
    ('MIC-G2-MC',    'Set Microphone Meja Hakim/Jaksa/Pembela','microphone', 'Audio-Technica','Pro 49Q',  'UNPAR-MIC-008', 'ACTIVE'),
    ('MIC-G2-SEM',   'Microphone Seminar FH',                 'microphone',  'Sennheiser','E835',       'UNPAR-MIC-009', 'ACTIVE'),

    -- Smartboards
    ('SBD-PPAG-LT1', 'Smartboard Samsung Flip LT1 PPAG',      'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-001', 'ACTIVE'),
    ('SBD-PPAG-LT2', 'Smartboard Samsung Flip LT2 PPAG',      'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-002', 'ACTIVE'),
    ('SBD-PPAG-LT3', 'Smartboard Samsung Flip LT3 PPAG',      'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-003', 'ACTIVE'),
    ('SBD-PPAG-201', 'Smartboard Besar Lecture Hall PPAG',    'smartboard',  'Samsung',   'WM85B',      'UNPAR-SBD-004', 'ACTIVE'),

    -- Whiteboards
    ('WBD-PPAG-LT1', 'Whiteboard Kaca LT1',                   'whiteboard',  'Custom',    'Magnetic',   'UNPAR-WBD-001', 'ACTIVE'),
    ('WBD-PPAG-LT2', 'Whiteboard Kaca LT2',                   'whiteboard',  'Custom',    'Magnetic',   'UNPAR-WBD-002', 'ACTIVE'),
    ('WBD-PPAG-LT3', 'Whiteboard Kaca LT3',                   'whiteboard',  'Custom',    'Magnetic',   'UNPAR-WBD-003', 'ACTIVE'),
    ('WBD-PPAG-202', 'Whiteboard Ruang Kuliah 202',           'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-004', 'ACTIVE'),
    ('WBD-G9-101',   'Whiteboard Ruang Kuliah 9101',          'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-005', 'ACTIVE'),
    ('WBD-G9-LAB1',  'Whiteboard Lab Komputer 1',             'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-006', 'ACTIVE'),
    ('WBD-G9-LAB2',  'Whiteboard Lab Komputer 2',             'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-007', 'ACTIVE'),
    ('WBD-G9-LAB3',  'Whiteboard Lab Komputer 3',             'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-008', 'ACTIVE'),
    ('WBD-G2-SEM',   'Whiteboard Seminar B. Arief Sidharta',  'whiteboard',  'Custom',    'Standard',   'UNPAR-WBD-009', 'ACTIVE'),

    -- Computers
    ('CMP-G9-LAB1',  '30 Unit PC Core i7 Lab Komputasi 1',    'computer',    'Dell',      'OptiPlex',   'UNPAR-CMP-001', 'ACTIVE'),
    ('CMP-G9-LAB2',  '30 Unit PC Core i7 Lab Komputasi 2',    'computer',    'Dell',      'OptiPlex',   'UNPAR-CMP-002', 'ACTIVE'),
    ('CMP-G9-LAB3',  '60 Unit PC Core i7 Lab Komputasi 3',    'computer',    'Dell',      'OptiPlex',   'UNPAR-CMP-003', 'ACTIVE'),

    -- Stage & Lighting
    ('LIT-PPAG-AUD', 'Stage Lighting Rig Auditorium PPAG',    'lighting',    'ETC',       'ColorSource','UNPAR-LIT-001', 'ACTIVE'),
    ('STG-G9-AULA',  'Panggung Acara Aula Driekore',          'stage',       'Custom',    'Stage-FE',   'UNPAR-STG-001', 'ACTIVE');

-- ─── ROOM EQUIPMENT ASSIGNMENTS ──────────────────────────────
-- PPAG-AUD (room_id = 1)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (1,  1, 1), -- PRJ-PPAG-AUD
    (1, 11, 1), -- SND-PPAG-AUD
    (1, 20, 1), -- MIC-PPAG-AUD
    (1, 41, 1); -- LIT-PPAG-AUD

-- PPAG-LT1 (room_id = 2)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (2, 29, 1), -- SBD-PPAG-LT1
    (2, 12, 1), -- SND-PPAG-LT1
    (2, 21, 1), -- MIC-PPAG-LT1
    (2, 33, 1); -- WBD-PPAG-LT1

-- PPAG-LT2 (room_id = 3)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (3, 30, 1), -- SBD-PPAG-LT2
    (3, 13, 1), -- SND-PPAG-LT2
    (3, 22, 1), -- MIC-PPAG-LT2
    (3, 34, 1); -- WBD-PPAG-LT2

-- PPAG-LT3 (room_id = 4)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (4, 31, 1), -- SBD-PPAG-LT3
    (4, 14, 1), -- SND-PPAG-LT3
    (4, 23, 1), -- MIC-PPAG-LT3
    (4, 35, 1); -- WBD-PPAG-LT3

-- PPAG-201 (room_id = 5: Lacture Hall PPAG)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (5, 32, 1), -- SBD-PPAG-201 (smartboard besar)
    (5, 15, 1), -- SND-PPAG-201
    (5, 24, 1); -- MIC-PPAG-201

-- PPAG-202 (room_id = 6)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (6,  2, 1), -- PRJ-PPAG-202
    (6, 36, 1); -- WBD-PPAG-202

-- G0-OR (room_id = 8: Operation Room Rektorat)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (8,  3, 1), -- PRJ-G0-OR
    (8, 16, 1), -- SND-G0-OR
    (8, 25, 1); -- MIC-G0-OR

-- G9-AULA (room_id = 9: Aula Driekore FE)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (9,  4, 1), -- PRJ-G9-AULA
    (9, 17, 1), -- SND-G9-AULA
    (9, 26, 1), -- MIC-G9-AULA
    (9, 42, 1); -- STG-G9-AULA

-- G9-101 (room_id = 10)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (10,  5, 1), -- PRJ-G9-101
    (10, 37, 1); -- WBD-G9-101

-- G9-LAB1 (room_id = 11)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (11, 38, 1), -- CMP-G9-LAB1 (30 unit PC)
    (11,  6, 1), -- PRJ-G9-LAB1
    (11, 39, 1); -- WBD-G9-LAB1

-- G9-LAB2 (room_id = 12)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (12, 39, 1), -- CMP-G9-LAB2 (30 unit PC)
    (12,  7, 1), -- PRJ-G9-LAB2
    (12, 40, 1); -- WBD-G9-LAB2

-- G9-LAB3 (room_id = 13)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (13, 40, 1), -- CMP-G9-LAB3 (60 unit PC)
    (13,  8, 1), -- PRJ-G9-LAB3
    (13, 40, 1); -- WBD-G9-LAB3

-- G2-MC (room_id = 14: Ruang Peradilan Semu)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (14,  9, 1), -- PRJ-G2-MC
    (14, 18, 1), -- SND-G2-MC
    (14, 27, 1); -- MIC-G2-MC

-- G2-SEM (room_id = 15: Ruang Seminar B. Arief Sidharta)
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    (15, 10, 1), -- PRJ-G2-SEM
    (15, 19, 1), -- SND-G2-SEM
    (15, 28, 1), -- MIC-G2-SEM
    (15, 41, 1); -- WBD-G2-SEM

-- ─── USERS ───────────────────────────────────────────────────
INSERT INTO users (employee_id, full_name, email, department, role) VALUES
    ('FAC-001', 'Nama Orang 1',         'dummy@test.com',          'Fakultas Ekonomi',             'faculty'),
    ('FAC-002', 'Nama Orang 2',         'dummy2@test.com',         'Fakultas Hukum',               'faculty'),
    ('FAC-003', 'Nama Orang 3',         'dummy3@test.com',         'Fakultas Sains',               'faculty'),
    ('FAC-004', 'Nama Orang 4',         'dummy4@test.com',         'Fakultas Teknologi Rekayasa',  'faculty'),
    ('STF-001', 'Nama Orang 5',         'dummy5@test.com',         'ASP',      'staff'),
    ('STF-002', 'Nama Orang 6',         'dummy6@test.com',         'DITMAWA',           'staff'),
    ('ADM-001', 'Sistem CampusFlow',    'dummy7@test.com',         'Lembaga Pengembangan TI',     'admin'),
    ('STU-001', 'Nama Orang 7',         'dummy8@test.com',         'Senat Mahasiswa',              'student');

-- ─── EXISTING BOOKINGS (Untuk skenario pengujian & bentrok) ──
INSERT INTO bookings (booking_reference, room_id, user_id, event_name, booking_date, start_time, end_time, attendee_count, status, confirmed_at) VALUES
    -- [PPAG-AUD] Slot pagi terisi (2026-09-23 jam 08:00 - 12:00)
    ('BK-UNPAR-001', 1, 1, 'Seminar Nasional & Dies Natalis UNPAR',
     '2026-09-23', '08:00', '12:00', 600, 'CONFIRMED',
     '2026-09-20T10:00:00Z'),

    -- [PPAG-202] Kuliah reguler pagi terisi (2026-09-23 jam 13:00 - 15:00)
    ('BK-UNPAR-002', 6, 2, 'Kuliah Umum Pengantar Ekonomi',
     '2026-09-23', '13:00', '15:00', 50, 'CONFIRMED',
     '2026-09-20T11:00:00Z');
