-- ============================================================
-- 20-row sample for quick local Supabase testing
-- Run AFTER schema.sql
-- ============================================================

INSERT INTO instructors (id, name, department, email) VALUES
    ('11111111-0000-0000-0000-000000000001', 'Dr. Alice Ramos',    'Computer Science', 'aramos@univ.edu'),
    ('11111111-0000-0000-0000-000000000002', 'Prof. Bob Nguyen',   'Mathematics',      'bnguyen@univ.edu'),
    ('11111111-0000-0000-0000-000000000003', 'Dr. Carol Chen',     'Statistics',       'cchen@univ.edu'),
    ('11111111-0000-0000-0000-000000000004', 'Prof. David Park',   'Physics',          'dpark@univ.edu'),
    ('11111111-0000-0000-0000-000000000005', 'Dr. Elena Vasquez',  'Computer Science', 'evasquez@univ.edu')
ON CONFLICT DO NOTHING;

INSERT INTO courses (id, course_code, title, subject, course_level, credits, description, instructor_id, semester, max_enrollment) VALUES
    ('22222222-0000-0000-0000-000000000001', 'CS101',    'Intro to Programming',       'Computer Science', 100, 3.0, 'Fundamentals of programming using Python.',                              '11111111-0000-0000-0000-000000000001', 'Fall 2025', 40),
    ('22222222-0000-0000-0000-000000000002', 'CS201',    'Data Structures',            'Computer Science', 200, 3.0, 'Prerequisite: CS101. Arrays, linked lists, trees, hash tables.',          '11111111-0000-0000-0000-000000000001', 'Fall 2025', 35),
    ('22222222-0000-0000-0000-000000000003', 'CS301',    'Algorithms',                 'Computer Science', 300, 3.0, 'Prerequisite: CS201. Sorting, searching, dynamic programming.',           '11111111-0000-0000-0000-000000000005', 'Fall 2025', 30),
    ('22222222-0000-0000-0000-000000000004', 'CS401',    'Operating Systems',          'Computer Science', 400, 3.0, 'Prerequisite: CS301. Processes, memory management, file systems.',        '11111111-0000-0000-0000-000000000005', 'Fall 2025', 25),
    ('22222222-0000-0000-0000-000000000005', 'CS450',    'Machine Learning',           'Computer Science', 400, 3.0, 'Prerequisite: CS301. Supervised and unsupervised learning.',              '11111111-0000-0000-0000-000000000001', 'Fall 2025', 30),
    ('22222222-0000-0000-0000-000000000006', 'MATH140',  'Calculus I',                 'Mathematics',      100, 4.0, 'Limits, derivatives, and integrals.',                                    '11111111-0000-0000-0000-000000000002', 'Fall 2025', 50),
    ('22222222-0000-0000-0000-000000000007', 'MATH240',  'Linear Algebra',             'Mathematics',      200, 3.0, 'Prerequisite: MATH140. Vectors, matrices, eigenvalues.',                  '11111111-0000-0000-0000-000000000002', 'Fall 2025', 40),
    ('22222222-0000-0000-0000-000000000008', 'MATH340',  'Differential Equations',     'Mathematics',      300, 3.0, 'Prerequisite: MATH240. ODEs and systems.',                                '11111111-0000-0000-0000-000000000002', 'Fall 2025', 35),
    ('22222222-0000-0000-0000-000000000009', 'STAT400',  'Probability & Statistics',   'Statistics',       400, 3.0, 'Prerequisite: MATH240. Distributions, hypothesis testing.',               '11111111-0000-0000-0000-000000000003', 'Fall 2025', 30),
    ('22222222-0000-0000-0000-000000000010', 'STAT410',  'Regression Analysis',        'Statistics',       400, 3.0, 'Prerequisite: STAT400. Simple and multiple regression.',                  '11111111-0000-0000-0000-000000000003', 'Fall 2025', 25),
    ('22222222-0000-0000-0000-000000000011', 'PHYS101',  'Physics I',                  'Physics',          100, 4.0, 'Mechanics, kinematics, energy.',                                          '11111111-0000-0000-0000-000000000004', 'Fall 2025', 45),
    ('22222222-0000-0000-0000-000000000012', 'PHYS201',  'Physics II',                 'Physics',          200, 4.0, 'Prerequisite: PHYS101. Electromagnetism and waves.',                      '11111111-0000-0000-0000-000000000004', 'Fall 2025', 40),
    ('22222222-0000-0000-0000-000000000013', 'CS350',    'Database Systems',           'Computer Science', 300, 3.0, 'Prerequisite: CS201. Relational algebra, SQL, indexing.',                 '11111111-0000-0000-0000-000000000005', 'Fall 2025', 30),
    ('22222222-0000-0000-0000-000000000014', 'CS360',    'Computer Networks',          'Computer Science', 300, 3.0, 'Prerequisite: CS201. TCP/IP, routing, socket programming.',               '11111111-0000-0000-0000-000000000001', 'Fall 2025', 30),
    ('22222222-0000-0000-0000-000000000015', 'CS480',    'Distributed Systems',        'Computer Science', 400, 3.0, 'Prerequisite: CS360. Consistency, replication, consensus.',               '11111111-0000-0000-0000-000000000005', 'Fall 2025', 25),
    ('22222222-0000-0000-0000-000000000016', 'MATH420',  'Real Analysis',              'Mathematics',      400, 3.0, 'Prerequisite: MATH340. Sequences, series, continuity.',                   '11111111-0000-0000-0000-000000000002', 'Fall 2025', 20),
    ('22222222-0000-0000-0000-000000000017', 'CS310',    'Software Engineering',       'Computer Science', 300, 3.0, 'Prerequisite: CS201. Agile, design patterns, testing.',                   '11111111-0000-0000-0000-000000000001', 'Fall 2025', 35),
    ('22222222-0000-0000-0000-000000000018', 'STAT300',  'Applied Statistics',         'Statistics',       300, 3.0, 'Prerequisite: MATH140. Descriptive stats, ANOVA.',                        '11111111-0000-0000-0000-000000000003', 'Fall 2025', 30),
    ('22222222-0000-0000-0000-000000000019', 'CS460',    'Computer Vision',            'Computer Science', 400, 3.0, 'Prerequisite: CS450. Image processing, CNNs, object detection.',          '11111111-0000-0000-0000-000000000005', 'Fall 2025', 20),
    ('22222222-0000-0000-0000-000000000020', 'CS490',    'Capstone Project',           'Computer Science', 400, 3.0, 'Prerequisite: CS301. Team-based software project.',                       '11111111-0000-0000-0000-000000000001', 'Fall 2025', 20)
ON CONFLICT (course_code) DO NOTHING;

INSERT INTO schedules (course_id, day_of_week, start_time, end_time, room, building) VALUES
    ('22222222-0000-0000-0000-000000000001', 'Monday',    '09:00', '10:15', '1115', 'IRB'),
    ('22222222-0000-0000-0000-000000000001', 'Wednesday', '09:00', '10:15', '1115', 'IRB'),
    ('22222222-0000-0000-0000-000000000002', 'Tuesday',   '10:00', '11:15', '2460', 'AVW'),
    ('22222222-0000-0000-0000-000000000002', 'Thursday',  '10:00', '11:15', '2460', 'AVW'),
    ('22222222-0000-0000-0000-000000000003', 'Monday',    '14:00', '15:15', '1112', 'IRB'),
    ('22222222-0000-0000-0000-000000000003', 'Wednesday', '14:00', '15:15', '1112', 'IRB'),
    ('22222222-0000-0000-0000-000000000004', 'Tuesday',   '13:00', '14:15', '3120', 'CSI'),
    ('22222222-0000-0000-0000-000000000004', 'Thursday',  '13:00', '14:15', '3120', 'CSI'),
    ('22222222-0000-0000-0000-000000000005', 'Friday',    '10:00', '11:15', '2120', 'IRB'),
    ('22222222-0000-0000-0000-000000000006', 'Monday',    '08:00', '09:15', '0200', 'MTH'),
    ('22222222-0000-0000-0000-000000000006', 'Wednesday', '08:00', '09:15', '0200', 'MTH'),
    ('22222222-0000-0000-0000-000000000006', 'Friday',    '08:00', '09:15', '0200', 'MTH'),
    ('22222222-0000-0000-0000-000000000007', 'Tuesday',   '09:00', '10:15', '1311', 'MTH'),
    ('22222222-0000-0000-0000-000000000007', 'Thursday',  '09:00', '10:15', '1311', 'MTH'),
    ('22222222-0000-0000-0000-000000000008', 'Monday',    '11:00', '12:15', '1303', 'MTH'),
    ('22222222-0000-0000-0000-000000000008', 'Wednesday', '11:00', '12:15', '1303', 'MTH'),
    ('22222222-0000-0000-0000-000000000009', 'Tuesday',   '14:00', '15:15', '1313', 'MTH'),
    ('22222222-0000-0000-0000-000000000009', 'Thursday',  '14:00', '15:15', '1313', 'MTH'),
    ('22222222-0000-0000-0000-000000000010', 'Friday',    '13:00', '14:15', '1308', 'MTH'),
    ('22222222-0000-0000-0000-000000000011', 'Monday',    '10:00', '11:15', '1402', 'PHS'),
    ('22222222-0000-0000-0000-000000000011', 'Wednesday', '10:00', '11:15', '1402', 'PHS'),
    ('22222222-0000-0000-0000-000000000011', 'Friday',    '10:00', '11:15', '1402', 'PHS'),
    ('22222222-0000-0000-0000-000000000012', 'Tuesday',   '11:00', '12:15', '1408', 'PHS'),
    ('22222222-0000-0000-0000-000000000012', 'Thursday',  '11:00', '12:15', '1408', 'PHS'),
    ('22222222-0000-0000-0000-000000000013', 'Monday',    '13:00', '14:15', '2117', 'AVW'),
    ('22222222-0000-0000-0000-000000000013', 'Wednesday', '13:00', '14:15', '2117', 'AVW'),
    ('22222222-0000-0000-0000-000000000014', 'Tuesday',   '15:00', '16:15', '2460', 'AVW'),
    ('22222222-0000-0000-0000-000000000014', 'Thursday',  '15:00', '16:15', '2460', 'AVW'),
    ('22222222-0000-0000-0000-000000000015', 'Monday',    '16:00', '17:15', '3120', 'CSI'),
    ('22222222-0000-0000-0000-000000000016', 'Wednesday', '15:00', '16:15', '1303', 'MTH'),
    ('22222222-0000-0000-0000-000000000016', 'Friday',    '15:00', '16:15', '1303', 'MTH'),
    ('22222222-0000-0000-0000-000000000017', 'Tuesday',   '12:00', '13:15', '1115', 'IRB'),
    ('22222222-0000-0000-0000-000000000017', 'Thursday',  '12:00', '13:15', '1115', 'IRB'),
    ('22222222-0000-0000-0000-000000000018', 'Monday',    '15:00', '16:15', '1308', 'MTH'),
    ('22222222-0000-0000-0000-000000000018', 'Wednesday', '15:00', '16:15', '1308', 'MTH'),
    ('22222222-0000-0000-0000-000000000019', 'Friday',    '14:00', '15:15', '3120', 'CSI'),
    ('22222222-0000-0000-0000-000000000020', 'Thursday',  '16:00', '17:15', '2460', 'AVW');
