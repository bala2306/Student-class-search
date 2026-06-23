"""
Full ingestion pipeline: Kaggle (smrezwanulazad/exam-schedule) → Supabase → Neo4j

Dataset files:
  courses.csv    — course_id, course_name, department, credits, description
  instructors.csv — instructor_id, first_name, last_name, email, phone_number, department
  timeslots.csv  — timeslot_id, day, start_time, end_time
  classrooms.csv — classroom_id, building_name, room_number, capacity, room_type
  schedule.csv   — student_id, course_id, instructor_id, classroom_id, timeslot_id

Usage:
    cd backend
    python -m scripts.ingest_kaggle        # runs all 3 steps
    python -m scripts.ingest_kaggle 2 3    # skip step 1 (download already done)
"""
import os
import re
import subprocess
from collections import defaultdict

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DATASET_SLUG = os.environ.get("KAGGLE_DATASET_SLUG", "smrezwanulazad/exam-schedule")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ── Department → course code prefix mapping ───────────────────────────────────
DEPT_PREFIX = {
    "computer science": "CS",
    "mathematics": "MATH",
    "statistics": "STAT",
    "physics": "PHYS",
    "chemistry": "CHEM",
    "biology": "BIOL",
    "engineering": "ENGR",
    "mechanical engineering": "ME",
    "electrical engineering": "EE",
    "civil engineering": "CE",
    "economics": "ECON",
    "business": "BUS",
    "management": "MGMT",
    "psychology": "PSYC",
    "sociology": "SOC",
    "history": "HIST",
    "english": "ENGL",
    "linguistics": "LING",
    "philosophy": "PHIL",
    "political science": "POLS",
    "media technology": "MDIA",
    "information technology": "IT",
    "healthcare informatics": "HI",
    "data science": "DS",
    "artificial intelligence": "AI",
}

LEVEL_BY_CREDITS = {1: 100, 2: 200, 3: 300, 4: 400}


def dept_to_prefix(dept: str) -> str:
    key = dept.strip().lower()
    for k, v in DEPT_PREFIX.items():
        if k in key:
            return v
    # Fallback: first letters of each word, max 4 chars
    return "".join(w[0] for w in dept.split()[:4]).upper()[:4]


def make_course_code(prefix: str, course_id: int, credits: int) -> str:
    level = LEVEL_BY_CREDITS.get(credits, 300)
    # Vary level within the range using course_id to avoid all 300-level
    adjusted = level + ((course_id * 10) % 90)
    return f"{prefix}{adjusted}"


# ── Step 1: Download from Kaggle ──────────────────────────────────────────────

def step1_download():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Downloading dataset '{DATASET_SLUG}' from Kaggle...")
    env = {**os.environ, "KAGGLE_USERNAME": os.environ.get("KAGGLE_USERNAME", ""),
           "KAGGLE_KEY": os.environ.get("KAGGLE_KEY", "")}
    subprocess.run(
        ["python3", "-m", "kaggle", "datasets", "download", "-d", DATASET_SLUG,
         "--unzip", "-p", DATA_DIR],
        check=True, env=env,
    )
    print("Download complete.")


# ── Step 2: Load to Supabase ──────────────────────────────────────────────────

def step2_load_to_supabase():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ── Load source files ──────────────────────────────────────────────────────
    courses_df    = pd.read_csv(os.path.join(DATA_DIR, "courses.csv"))
    instructors_df = pd.read_csv(os.path.join(DATA_DIR, "instructors.csv"))
    timeslots_df  = pd.read_csv(os.path.join(DATA_DIR, "timeslots.csv"))
    classrooms_df = pd.read_csv(os.path.join(DATA_DIR, "classrooms.csv"))
    schedule_df   = pd.read_csv(os.path.join(DATA_DIR, "schedule.csv"))

    print(f"  Source counts — courses: {len(courses_df)}, instructors: {len(instructors_df)}, "
          f"timeslots: {len(timeslots_df)}, classrooms: {len(classrooms_df)}, "
          f"enrollments: {len(schedule_df)}")

    # ── Build course code & level from dept + credits ──────────────────────────
    dept_counts: dict[str, int] = defaultdict(int)

    def assign_code(row):
        prefix = dept_to_prefix(str(row["department"]))
        dept_counts[prefix] += 1
        return make_course_code(prefix, int(row["course_id"]), int(row.get("credits", 3) or 3))

    courses_df["course_code"] = courses_df.apply(assign_code, axis=1)
    courses_df["course_level"] = courses_df.apply(
        lambda r: LEVEL_BY_CREDITS.get(int(r.get("credits", 3) or 3), 300), axis=1
    )

    # ── Ingest instructors (select-then-insert to avoid constraint issues) ────
    existing_resp = sb.table("instructors").select("id,name").execute()
    existing_names = {r["name"] for r in (existing_resp.data or [])}

    new_instructors = []
    for _, r in instructors_df.iterrows():
        full_name = f"{r['first_name']} {r['last_name']}"
        if full_name not in existing_names:
            new_instructors.append({
                "name": full_name,
                "department": str(r.get("department", "")),
                "email": str(r.get("email", "")),
            })
            existing_names.add(full_name)

    if new_instructors:
        sb.table("instructors").insert(new_instructors).execute()

    instr_resp = sb.table("instructors").select("id,name").execute()
    instr_map = {r["name"]: r["id"] for r in (instr_resp.data or [])}

    # Map instructor_id (UUID from source) → Supabase UUID
    source_instr_map: dict[str, str] = {}
    for _, r in instructors_df.iterrows():
        full_name = f"{r['first_name']} {r['last_name']}"
        if full_name in instr_map:
            source_instr_map[str(r["instructor_id"])] = instr_map[full_name]

    # ── Build per-course schedule info from schedule.csv ──────────────────────
    # For each course, pick the most common (instructor, classroom, timeslot) combo
    course_schedule: dict[int, dict] = {}
    for _, row in schedule_df.iterrows():
        cid = int(row["course_id"])
        if cid not in course_schedule:
            course_schedule[cid] = {
                "instructor_id": str(row.get("instructor_id", "")),
                "classroom_id": int(row.get("classroom_id", 1)),
                "timeslot_id": int(row.get("timeslot_id", 1)),
            }

    timeslot_map = {int(r["timeslot_id"]): r for _, r in timeslots_df.iterrows()}
    classroom_map = {int(r["classroom_id"]): r for _, r in classrooms_df.iterrows()}

    # ── Ingest courses + schedules ─────────────────────────────────────────────
    inserted = 0
    for _, row in courses_df.iterrows():
        cid = int(row["course_id"])
        code = row["course_code"]
        sched = course_schedule.get(cid, {})

        # Resolve instructor
        src_instr_id = sched.get("instructor_id", "")
        sb_instr_id = source_instr_map.get(src_instr_id)

        # Resolve timeslot
        ts = timeslot_map.get(sched.get("timeslot_id", 0), {})
        start_time = str(ts.get("start_time", "09:00"))
        end_time   = str(ts.get("end_time",   "10:15"))
        day        = str(ts.get("day", "Monday"))

        # Fix inverted times (some timeslots have end < start)
        if start_time > end_time:
            start_time, end_time = end_time, start_time

        # Resolve classroom
        cl = classroom_map.get(sched.get("classroom_id", 0), {})
        room     = str(cl.get("room_number", "TBD"))
        building = str(cl.get("building_name", "TBD"))

        credits = float(row.get("credits") or 3)

        course_resp = sb.table("courses").upsert(
            {
                "course_code": code,
                "title": str(row["course_name"]),
                "subject": str(row["department"]),
                "course_level": int(row["course_level"]),
                "credits": credits,
                "description": str(row.get("description", "") or ""),
                "semester": "Fall 2025",
                "instructor_id": sb_instr_id,
                "max_enrollment": int(cl.get("capacity", 30)) if cl.get("capacity") else 30,
            },
        ).execute()

        if course_resp.data:
            course_id_db = course_resp.data[0]["id"]
            if day and day != "nan":
                # Delete existing schedules for this course before re-inserting
                sb.table("schedules").delete().eq("course_id", course_id_db).execute()
                sb.table("schedules").insert(
                    {
                        "course_id": course_id_db,
                        "day_of_week": day,
                        "start_time": start_time,
                        "end_time": end_time,
                        "room": room,
                        "building": building,
                    }
                ).execute()
        inserted += 1

    print(f"  Upserted {inserted} courses with schedules.")

    # ── Store enrollment data for co-enrollment computation ───────────────────
    # Save schedule.csv with mapped course codes for workload distribution analysis.
    code_map = dict(zip(courses_df["course_id"].astype(int), courses_df["course_code"]))
    schedule_df["course_code"] = schedule_df["course_id"].astype(int).map(code_map)
    schedule_df.to_csv(os.path.join(DATA_DIR, "enrollment_mapped.csv"), index=False)
    print(f"  Saved enrollment_mapped.csv with {len(schedule_df)} rows.")


# ── Step 3: Build Neo4j Knowledge Graph ───────────────────────────────────────

def step3_build_graph():
    from services.kg_builder import build_graph
    build_graph()


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    steps = sys.argv[1:] or ["1", "2", "3"]

    if "1" in steps:
        print("\n── Step 1: Downloading Kaggle dataset ──────────────────")
        step1_download()

    if "2" in steps:
        print("\n── Step 2: Loading to Supabase ─────────────────────────")
        step2_load_to_supabase()

    if "3" in steps:
        print("\n── Step 3: Building Neo4j knowledge graph ──────────────")
        step3_build_graph()

    print("\n✓ Ingestion complete.")
