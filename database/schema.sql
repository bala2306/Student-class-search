-- ============================================================
-- Student Class Search — Supabase (PostgreSQL) Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS instructors (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    department  TEXT,
    email       TEXT
);

CREATE TABLE IF NOT EXISTS courses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code         TEXT NOT NULL UNIQUE,
    title               TEXT NOT NULL,
    subject             TEXT NOT NULL,
    course_level        INTEGER,
    credits             NUMERIC(3,1),
    description         TEXT,
    instructor_id       UUID REFERENCES instructors(id),
    semester            TEXT,
    max_enrollment      INTEGER,
    current_enrollment  INTEGER DEFAULT 0,
    enrollment_status   TEXT,
    instruction_type    TEXT,
    degree_attributes   TEXT
);

CREATE INDEX IF NOT EXISTS idx_courses_subject       ON courses (subject);
CREATE INDEX IF NOT EXISTS idx_courses_course_level  ON courses (course_level);
CREATE INDEX IF NOT EXISTS idx_courses_instructor_id ON courses (instructor_id);
CREATE INDEX IF NOT EXISTS idx_courses_code          ON courses (course_code);

CREATE TABLE IF NOT EXISTS schedules (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id    UUID REFERENCES courses(id) ON DELETE CASCADE,
    day_of_week  TEXT NOT NULL,
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    room         TEXT,
    building     TEXT
);

CREATE INDEX IF NOT EXISTS idx_schedules_course_id   ON schedules (course_id);
CREATE INDEX IF NOT EXISTS idx_schedules_day_of_week ON schedules (day_of_week);

-- ── Row Level Security ────────────────────────────────────────────────────────
-- Enable RLS on all tables. The backend uses the service_role key which bypasses
-- RLS entirely, so ingestion and API queries are unaffected.
-- Public SELECT is allowed so the Supabase dashboard and read-only clients work.
-- All writes (INSERT/UPDATE/DELETE) are restricted to the service_role key only.

ALTER TABLE instructors ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses     ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules   ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read instructors" ON instructors FOR SELECT USING (true);
CREATE POLICY "public read courses"     ON courses     FOR SELECT USING (true);
CREATE POLICY "public read schedules"   ON schedules   FOR SELECT USING (true);

CREATE OR REPLACE VIEW course_full AS
SELECT
    c.id,
    c.course_code,
    c.title,
    c.subject,
    c.course_level,
    c.credits,
    c.description,
    c.semester,
    c.max_enrollment,
    c.current_enrollment,
    c.enrollment_status,
    c.instruction_type,
    c.degree_attributes,
    i.name              AS instructor_name,
    i.department,
    s.day_of_week,
    s.start_time::TEXT  AS start_time,
    s.end_time::TEXT    AS end_time,
    s.room,
    s.building
FROM courses c
LEFT JOIN instructors i ON c.instructor_id = i.id
LEFT JOIN schedules   s ON s.course_id     = c.id;
