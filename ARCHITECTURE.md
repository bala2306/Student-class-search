# Architecture — Student Class Search

## Overview

A full-stack AI-powered course search prototype for UIUC Spring 2026. Students type natural-language queries; the system classifies intent, queries the right database, and returns structured course results.

```
┌──────────────────────────────────────────────────┐
│         Frontend  (React 18 + TypeScript + Vite) │
│   Chat Panel  │  Course Cards  │  Study Squad     │
└──────────────────────┬───────────────────────────┘
                       │  REST  (JSON)
┌──────────────────────▼───────────────────────────┐
│         Backend  (FastAPI + Python)               │
│                                                   │
│  /search  /classes  /courses/{id}/coenrollment    │
│  /graph/prereqs  /graph/workload                  │
│                                                   │
│  openai_parser → query_router → db_query          │
│                              → kg_query           │
└──────────┬───────────────────────┬────────────────┘
           │                       │
  ┌────────▼────────┐    ┌─────────▼──────────┐
  │  Supabase       │    │  Neo4j AuraDB       │
  │  (PostgreSQL)   │    │  (Graph DB)         │
  │                 │    │                     │
  │  instructors    │    │  Course node        │
  │  courses        │    │  HAS_PREREQUISITE   │
  │  schedules      │    │  OFTEN_TAKEN_WITH   │
  │  course_full ◄──┘    └─────────────────────┘
  │  (view)         │
  └─────────────────┘
           │
  ┌────────▼────────┐
  │  OpenAI API     │
  │  GPT-3.5-turbo  │
  │  (intent parse) │
  └─────────────────┘
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Type-safe components, instant HMR, built-in dev proxy to backend |
| Styling | Tailwind CSS | Utility-first, no unused CSS in production |
| Backend | FastAPI + Python | Async I/O, auto OpenAPI docs, Pydantic runtime validation |
| Relational DB | Supabase (PostgreSQL) | Free tier, managed, Python client, Row Level Security |
| Graph DB | Neo4j AuraDB | Native graph traversal for prerequisite chains and co-enrollment |
| AI | OpenAI GPT-3.5-turbo | Function calling for reliable structured extraction; 10× cheaper than GPT-4 |

---

## Data Source

**Kaggle dataset**: [`ak3395/uiuc-course-catalog-and-class-schedule-spring-2026`](https://www.kaggle.com/datasets/ak3395/uiuc-course-catalog-and-class-schedule-spring-2026)

Original source: UIUC Data Discovery repository maintained by Prof. Wade Fagen-Ulmschneider.

| Metric | Value |
|---|---|
| Raw rows | 12,823 (one per section component) |
| Unique courses | 4,502 (after deduplication) |
| Departments | 187 subject codes |
| Instructors | 2,324 |
| Schedule records | 6,541 |

**Ingestion pipeline** (`scripts/ingest_local.py`):
1. Deduplicate 12,823 rows → 4,502 canonical courses (prefer Lecture > Discussion > Lab; prefer timed over ARRANGED)
2. Load to Supabase (batch inserts, 500 rows/chunk)
3. Build Neo4j knowledge graph (Course, Instructor, Department, Room nodes + edges)
4. Run cohort engine → `OFTEN_TAKEN_WITH` edges via collaborative filtering on 5,000 synthetic student schedules

---

## Database Schema

```sql
instructors  (id, name, department, email)
courses      (id, course_code, title, subject, course_level, credits,
              description, semester, enrollment_status, instruction_type,
              degree_attributes, instructor_id)
schedules    (id, course_id, day_of_week, start_time, end_time, room, building)

-- Denormalized read view
course_full  = courses LEFT JOIN instructors LEFT JOIN schedules
```

---

## AI Search Flow

```
User query
    │
    ▼
openai_parser.py
    ├── Fast path: local regex handles simple queries (no GPT call)
    └── GPT-3.5-turbo function call → extracts structured filters:
        {
          query_type: "filter" | "traversal" | "recommendation" | "general"
          subject, day_of_week, course_level, credits, instructor_name,
          keyword, enrollment_status, instruction_type, degree_attributes,
          base_course
        }
    │
    ▼
query_router.py
    ├── filter      → Supabase SQL on course_full view
    ├── traversal   → Neo4j HAS_PREREQUISITE traversal
    │                 (falls back to description-text search in Supabase)
    ├── recommendation → Neo4j OFTEN_TAKEN_WITH traversal
    └── general     → empty results + helpful message
    │
    ▼
JSON response (CourseResult list) → Frontend renders course cards
```

**Conversation history**: The last few turns are included in every GPT call so follow-up queries like "now only 3-credit ones" inherit prior filters automatically.

**Supported natural-language filters** (examples):
- `"Show me CS classes on Mondays"` → subject=CS, day=Monday
- `"Open online ECON courses"` → enrollment_status=Open, instruction_type=Online, subject=ECON
- `"What can I take after CS225?"` → traversal, base_course=CS225
- `"Courses often taken with STAT400"` → recommendation, base_course=STAT400
- `"Find a humanities gen-ed"` → degree_attributes=humanities
- `"Show me machine learning courses"` → keyword=machine learning

---

## Design Decisions

**Two databases (SQL + Graph)**
Filter queries (subject, day, level) are best served by indexed SQL. Relationship traversals (prerequisite chains, co-enrollment) are graph problems — recursive SQL CTEs are complex and slow. Each database does what it's best at.

**Function calling over free-form GPT output**
Returning raw JSON from GPT is unreliable. Function calling forces a valid schema with enum constraints, eliminating parsing errors entirely.

**Local regex fast-path**
Simple queries like "CS classes on Monday" are parsed locally in <1ms without a GPT call. Only ambiguous or complex queries reach OpenAI, reducing cost and latency.

**Exact subject match (not ILIKE)**
Using `eq("subject", "CS")` instead of `ilike("%CS%")` prevents false matches where "BCS" or "ACCY" would match a "CS" substring search.

---

## Limitations

| Issue | Impact | Notes |
|---|---|---|
| Single semester | Can't compare across semesters | Spring 2026 only |
| Prerequisite inference | ~70% accuracy | Parsed from description text via regex; not from official prereq data |
| Synthetic co-enrollment | OFTEN_TAKEN_WITH edges are modeled | Generated from 5,000 synthetic student schedules; no real enrollment data |
| No auth | All users share the same read view | Acceptable for a prototype; Supabase Auth + RLS available for production |
| Static enrollment status | Open/Closed reflects catalog snapshot | Not real-time; status may have changed since data was captured |
