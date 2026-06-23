"""
Ingestion pipeline using the local course-catalog.csv dataset.

Source: student-class-search/Dataset/course-catalog.csv
Steps:
  1  Clean & deduplicate CSV → one canonical section per unique course code
  2  Load instructors, courses, schedules into Supabase
  3  Build Neo4j knowledge graph (Course, Instructor, Department, Room nodes + edges)

Usage (from backend/ directory):
    python -m scripts.ingest_local        # all 3 steps
    python -m scripts.ingest_local 2 3    # skip step 1 (prep already done)
"""

import os
import re
import sys
import subprocess
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "Dataset", "course-catalog.csv"
)
PREPPED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "courses_prepped.csv")

# Section type priority — pick the best section type per course
TYPE_PRIORITY = {"LEC": 0, "LCD": 1, "SEM": 2, "ONL": 3, "PR": 4, "LBD": 5, "IND": 6, "DIS": 7, "LAB": 8, "INT": 9}

# Days of week expansion: each char in the string maps to a day
DAY_CHAR_MAP = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "R": "Thursday", "F": "Friday"}


# ── Parsing helpers ────────────────────────────────────────────────────────────

def parse_credits(raw: str) -> float | None:
    """Extract the first number from strings like '3 hours.', '3 OR 4 hours.'"""
    m = re.search(r'\d+', str(raw or ""))
    return float(m.group()) if m else None


def parse_time_24h(raw: str) -> str | None:
    """Convert '09:00 AM' / '02:00 PM' to '09:00' / '14:00'."""
    s = str(raw or "").strip()
    if not s or s.upper() in ("ARRANGED", "NAN", ""):
        return None
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def expand_days(raw: str) -> list[str]:
    """'TR' → ['Tuesday','Thursday'], 'MWF' → ['Monday','Wednesday','Friday']"""
    s = str(raw or "").strip()
    if not s or s.upper() in ("ARRANGED", "NAN", ""):
        return []
    return [DAY_CHAR_MAP[c] for c in s if c in DAY_CHAR_MAP]


def course_level(number: int) -> int:
    if number < 100:
        return 100
    return (number // 100) * 100


def primary_instructor(raw: str) -> str | None:
    """'Smith, J;Jones, K' → 'Smith, J'"""
    s = str(raw or "").strip()
    if not s or s.lower() == "nan":
        return None
    return s.split(";")[0].strip()


def normalize_subject(abbr: str) -> str:
    """Keep abbreviation as-is — it is the subject code (CS, MATH, etc.)"""
    return abbr.strip()


ENROLLMENT_MAP = {
    "open": "Open",
    "crosslistopen": "Open",
    "open (restricted)": "Open (Restricted)",
    "crosslistopen (restricted)": "Open (Restricted)",
    "closed": "Closed",
}

INSTRUCTION_MAP = {
    "lecture": "Lecture",
    "lecture-discussion": "Lecture",
    "discussion/recitation": "Discussion",
    "laboratory": "Lab",
    "laboratory-discussion": "Lab",
    "online": "Online",
    "independent study": "Independent Study",
    "practice": "Lecture",
    "seminar": "Seminar",
}


def normalize_enrollment_status(raw: str) -> str | None:
    s = str(raw or "").strip()
    return ENROLLMENT_MAP.get(s.lower()) if s and s.lower() != "nan" else None


def normalize_instruction_type(raw: str) -> str | None:
    s = str(raw or "").strip()
    return INSTRUCTION_MAP.get(s.lower()) if s and s.lower() != "nan" else None


def normalize_degree_attributes(raw: str) -> str | None:
    s = str(raw or "").strip()
    return s if s and s.lower() != "nan" else None


# ── Step 1: Prepare / deduplicate ─────────────────────────────────────────────

def step1_prepare():
    os.makedirs(os.path.dirname(PREPPED_PATH), exist_ok=True)
    df = pd.read_csv(DATASET_PATH)
    print(f"  Raw rows: {len(df)}, columns: {list(df.columns)}")

    # Build course_code from Subject + Number
    df["course_code"] = df["Subject"].str.strip() + df["Number"].astype(str).str.strip()

    # Assign type priority for deduplication
    df["_type_rank"] = df["Type Code"].map(TYPE_PRIORITY).fillna(99).astype(int)

    # Mark rows that have a real (non-ARRANGED) time
    df["_has_time"] = df["Start Time"].apply(lambda x: str(x).strip().upper() not in ("ARRANGED", "NAN", ""))

    # Sort: prefer real time first, then lowest type rank (LEC > LCD > ...)
    df_sorted = df.sort_values(["course_code", "_has_time", "_type_rank"], ascending=[True, False, True])

    # Take first row per course_code
    deduped = df_sorted.drop_duplicates(subset="course_code", keep="first").copy()
    print(f"  Unique courses after dedup: {len(deduped)}")

    # Parse fields
    deduped["credits"]            = deduped["Credit Hours"].apply(parse_credits)
    deduped["start_time"]         = deduped["Start Time"].apply(parse_time_24h)
    deduped["end_time"]           = deduped["End Time"].apply(parse_time_24h)
    deduped["days_raw"]           = deduped["Days of Week"].fillna("")
    deduped["instructor"]         = deduped["Instructors"].apply(primary_instructor)
    deduped["semester"]           = deduped["Term"].str.capitalize() + " " + deduped["Year"].astype(str)
    deduped["level"]              = deduped["Number"].astype(int).apply(course_level)
    deduped["subject"]            = deduped["Subject"].apply(normalize_subject)
    deduped["title"]              = deduped["Name"].fillna("").str.strip()
    deduped["description"]        = deduped["Description"].fillna("").str.strip()
    deduped["room"]               = deduped["Room"].fillna("").astype(str).str.strip()
    deduped["building"]           = deduped["Building"].fillna("").astype(str).str.strip()
    deduped["enrollment_status"]  = deduped["Enrollment Status"].apply(normalize_enrollment_status)
    deduped["instruction_type"]   = deduped["Type"].apply(normalize_instruction_type)
    deduped["degree_attributes"]  = deduped["Degree Attributes"].apply(normalize_degree_attributes)

    keep = ["course_code", "title", "subject", "level", "credits",
            "description", "semester", "instructor",
            "start_time", "end_time", "days_raw", "room", "building",
            "enrollment_status", "instruction_type", "degree_attributes"]
    deduped[keep].to_csv(PREPPED_PATH, index=False)
    print(f"  Saved prepped CSV to {PREPPED_PATH}")


# ── Step 2: Load to Supabase ──────────────────────────────────────────────────

CHUNK = 500  # rows per batch insert

def _fetch_all_pages(sb, table: str, select: str) -> list:
    """Fetch all rows from a table using 1000-row pages (Supabase default limit)."""
    all_rows, offset = [], 0
    while True:
        resp = sb.table(table).select(select).range(offset, offset + 999).execute()
        rows = resp.data or []
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    return all_rows


def step2_load_to_supabase():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    df = pd.read_csv(PREPPED_PATH)
    print(f"  Loading {len(df)} courses...")

    # ── Clear old data (idempotent re-run) ────────────────────────────────────
    # Delete in order: schedules → courses → instructors (FK order)
    print("  Clearing existing data...")
    sb.table("schedules").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("courses").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("instructors").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # ── Instructors ────────────────────────────────────────────────────────────
    instructor_names = sorted(set(df["instructor"].dropna().tolist()))
    instr_rows = [{"name": n} for n in instructor_names]
    for i in range(0, len(instr_rows), CHUNK):
        sb.table("instructors").insert(instr_rows[i:i+CHUNK]).execute()

    instr_map = {r["name"]: r["id"] for r in _fetch_all_pages(sb, "instructors", "id,name")}
    print(f"  Instructors inserted: {len(instr_map)}")

    # ── Courses (batch upsert) ─────────────────────────────────────────────────
    course_rows = []
    for _, row in df.iterrows():
        code  = str(row["course_code"]).strip()
        title = str(row["title"]).strip()
        if not code or not title:
            continue
        instr_name = row["instructor"] if pd.notna(row["instructor"]) else None
        course_rows.append({
            "course_code":       code,
            "title":             title,
            "subject":           str(row["subject"]),
            "course_level":      int(row["level"]) if pd.notna(row["level"]) else None,
            "credits":           float(row["credits"]) if pd.notna(row["credits"]) else None,
            "description":       str(row["description"]) if pd.notna(row["description"]) else None,
            "semester":          str(row["semester"]),
            "instructor_id":     instr_map.get(instr_name) if instr_name else None,
            "enrollment_status": row.get("enrollment_status") if pd.notna(row.get("enrollment_status", float("nan"))) else None,
            "instruction_type":  row.get("instruction_type")  if pd.notna(row.get("instruction_type",  float("nan"))) else None,
            "degree_attributes": row.get("degree_attributes") if pd.notna(row.get("degree_attributes", float("nan"))) else None,
        })

    for i in range(0, len(course_rows), CHUNK):
        sb.table("courses").insert(course_rows[i:i+CHUNK]).execute()
        print(f"  Courses inserted: {min(i+CHUNK, len(course_rows))}/{len(course_rows)}", end="\r")
    print(f"\n  Courses inserted: {len(course_rows)}")

    # ── Schedules (batch insert) ───────────────────────────────────────────────
    # Fetch all course IDs in one pass
    code_to_id = {r["course_code"]: r["id"] for r in _fetch_all_pages(sb, "courses", "id,course_code")}

    schedule_rows = []
    for _, row in df.iterrows():
        code  = str(row["course_code"]).strip()
        cid   = code_to_id.get(code)
        if not cid:
            continue
        days  = expand_days(str(row["days_raw"]))
        start = str(row["start_time"]) if pd.notna(row["start_time"]) else None
        end   = str(row["end_time"])   if pd.notna(row["end_time"])   else None
        room  = str(row["room"])   if pd.notna(row["room"])   and str(row["room"])   not in ("nan","") else None
        bldg  = str(row["building"]) if pd.notna(row["building"]) and str(row["building"]) not in ("nan","") else None
        if days and start and end:
            for day in days:
                schedule_rows.append({
                    "course_id": cid, "day_of_week": day,
                    "start_time": start, "end_time": end,
                    "room": room, "building": bldg,
                })

    for i in range(0, len(schedule_rows), CHUNK):
        sb.table("schedules").insert(schedule_rows[i:i+CHUNK]).execute()
        print(f"  Schedules inserted: {min(i+CHUNK, len(schedule_rows))}/{len(schedule_rows)}", end="\r")
    print(f"\n  Schedules inserted: {len(schedule_rows)}")


# ── Step 3: Build Neo4j Knowledge Graph ───────────────────────────────────────

def step3_build_graph():
    from services.kg_builder import build_graph
    build_graph()


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    steps = sys.argv[1:] or ["1", "2", "3"]

    if "1" in steps:
        print("\n── Step 1: Preparing local dataset ─────────────────────")
        step1_prepare()

    if "2" in steps:
        print("\n── Step 2: Loading to Supabase ─────────────────────────")
        step2_load_to_supabase()

    if "3" in steps:
        print("\n── Step 3: Building Neo4j knowledge graph ──────────────")
        step3_build_graph()

    print("\n✓ Ingestion complete.")
