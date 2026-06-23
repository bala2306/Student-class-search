import os
import re
from neo4j import GraphDatabase
from supabase import create_client

PREREQ_PATTERN = re.compile(r'\b([A-Z]{2,4}\d{3})\b')

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
    return _driver


def _fetch_all(sb, table: str, select: str = "*") -> list:
    all_rows, offset = [], 0
    while True:
        rows = sb.table(table).select(select).range(offset, offset + 999).execute().data or []
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    return all_rows


def build_graph():
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    courses = _fetch_all(sb, "course_full")

    driver = get_driver()
    known_codes: set[str] = set()

    with driver.session() as session:
        for c in courses:
            code = c["course_code"]
            known_codes.add(code)

            session.run(
                """
                MERGE (c:Course {code: $code})
                SET c.title = $title, c.subject = $subject,
                    c.level = $level, c.credits = $credits,
                    c.semester = $semester
                """,
                code=code,
                title=c["title"],
                subject=c["subject"],
                level=c["course_level"],
                credits=float(c["credits"] or 0),
                semester=c["semester"],
            )

            if c["instructor_name"]:
                session.run(
                    """
                    MERGE (i:Instructor {name: $name})
                    SET i.department = $dept
                    WITH i
                    MATCH (c:Course {code: $code})
                    MERGE (c)-[:TAUGHT_BY]->(i)
                    """,
                    name=c["instructor_name"],
                    dept=c["department"],
                    code=code,
                )

            if c["subject"]:
                session.run(
                    """
                    MERGE (d:Department {name: $subject})
                    WITH d
                    MATCH (c:Course {code: $code})
                    MERGE (c)-[:IN_DEPARTMENT]->(d)
                    """,
                    subject=c["subject"],
                    code=code,
                )

            if c["room"] and c["day_of_week"]:
                session.run(
                    """
                    MERGE (r:Room {building: $building, room_number: $room})
                    WITH r
                    MATCH (c:Course {code: $code})
                    MERGE (c)-[s:SCHEDULED_IN]->(r)
                    SET s.day_of_week = $day, s.start_time = $start, s.end_time = $end
                    """,
                    building=c["building"] or "TBD",
                    room=c["room"],
                    code=code,
                    day=c["day_of_week"],
                    start=str(c["start_time"]),
                    end=str(c["end_time"]),
                )

        # Second pass: prerequisite edges from description text
        for row in _fetch_all(sb, "courses", "course_code,description"):
            course_code = row["course_code"]
            description = row.get("description") or ""
            prereqs = PREREQ_PATTERN.findall(description)
            for prereq_code in set(prereqs):
                if prereq_code != course_code and prereq_code in known_codes:
                    session.run(
                        """
                        MATCH (c:Course {code: $code}), (p:Course {code: $prereq})
                        MERGE (c)-[:HAS_PREREQUISITE]->(p)
                        """,
                        code=course_code,
                        prereq=prereq_code,
                    )

    print(f"Graph build complete. Processed {len(known_codes)} courses.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    build_graph()
