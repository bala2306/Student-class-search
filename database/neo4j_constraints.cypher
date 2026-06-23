// ============================================================
// Student Class Search — Neo4j AuraDB Constraints & Indexes
// Run these in Neo4j Browser before the first ingest
// ============================================================

CREATE CONSTRAINT course_code_unique IF NOT EXISTS
FOR (c:Course) REQUIRE c.code IS UNIQUE;

CREATE CONSTRAINT instructor_name_unique IF NOT EXISTS
FOR (i:Instructor) REQUIRE i.name IS UNIQUE;

CREATE CONSTRAINT department_name_unique IF NOT EXISTS
FOR (d:Department) REQUIRE d.name IS UNIQUE;

CREATE INDEX course_subject IF NOT EXISTS
FOR (c:Course) ON (c.subject);

CREATE INDEX course_level IF NOT EXISTS
FOR (c:Course) ON (c.level);

CREATE INDEX course_semester IF NOT EXISTS
FOR (c:Course) ON (c.semester);
