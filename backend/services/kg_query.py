import os
from neo4j import GraphDatabase
from models.schemas import CourseResult, CoEnrollResult, GraphNode, GraphLink
from services.db_query import get_catalog_recommendation_candidates, get_courses_by_codes
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
    return _driver


async def run_graph_query(query_type: str, base_course: str) -> List[CourseResult]:
    driver = get_driver()

    if query_type == "prereq_unlock":
        cypher = """
            MATCH (c:Course)-[:HAS_PREREQUISITE]->(prereq:Course {code: $code})
            RETURN c.code AS code, c.title AS title, c.subject AS subject,
                   c.level AS level, c.credits AS credits, c.semester AS semester
            ORDER BY c.level
        """
    elif query_type == "prereq_required":
        cypher = """
            MATCH (c:Course {code: $code})-[:HAS_PREREQUISITE]->(prereq:Course)
            RETURN prereq.code AS code, prereq.title AS title, prereq.subject AS subject,
                   prereq.level AS level, prereq.credits AS credits, prereq.semester AS semester
            ORDER BY prereq.level
        """
    elif query_type == "coenrollment":
        cypher = """
            MATCH (anchor:Course {code: $code})-[r:OFTEN_TAKEN_WITH]->(other:Course)
            RETURN other.code AS code, other.title AS title, other.subject AS subject,
                   other.level AS level, other.credits AS credits, other.semester AS semester,
                   r.frequency AS frequency, r.co_occurrence_count AS co_count
            ORDER BY r.frequency DESC
            LIMIT 5
        """
    else:
        return []

    with driver.session() as session:
        result = session.run(cypher, code=base_course)
        records = [dict(r) for r in result]

    if not records:
        return []

    codes = [r["code"] for r in records]
    enriched = await get_courses_by_codes(codes)
    enriched_map = {c.course_code: c for c in enriched}

    out = []
    for r in records:
        code = r["code"]
        base = enriched_map.get(code)
        if base:
            out.append(base)
        else:
            out.append(
                CourseResult(
                    course_code=code,
                    title=r.get("title", ""),
                    subject=r.get("subject", ""),
                    course_level=r.get("level"),
                    credits=float(r["credits"]) if r.get("credits") else None,
                    semester=r.get("semester"),
                )
            )
    return out


async def get_coenrollment(code: str, anchor_schedule: dict | None = None) -> List[CoEnrollResult]:
    cypher = """
        MATCH (anchor:Course {code: $code})-[r:OFTEN_TAKEN_WITH]->(other:Course)
        RETURN other.code AS code, other.title AS title, other.subject AS subject,
               other.level AS level, other.credits AS credits,
               r.frequency AS frequency, r.co_occurrence_count AS co_count
        ORDER BY r.frequency DESC
        LIMIT 25
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run(cypher, code=code)
            records = [dict(r) for r in result]
    except Exception:
        records = []

    anchor_courses = await get_courses_by_codes([code])
    anchor_course = anchor_courses[0] if anchor_courses else None

    if not records and not anchor_course:
        return []

    graph_frequency = {r["code"]: float(r.get("frequency") or 0) for r in records}
    graph_counts = {r["code"]: int(r.get("co_count") or 0) for r in records}
    graph_codes = [r["code"] for r in records if r["code"] != code]
    enriched = await get_courses_by_codes(graph_codes) if graph_codes else []
    enriched_map = {c.course_code: c for c in enriched}

    combined: dict[str, CourseResult] = {}
    graph_order: list[str] = []

    for r in records:
        if r["code"] == code:
            continue
        fallback = CourseResult(
            course_code=r["code"],
            title=r.get("title", ""),
            subject=r.get("subject", ""),
            course_level=r.get("level"),
            credits=float(r["credits"]) if r.get("credits") else None,
        )
        combined[r["code"]] = enriched_map.get(r["code"], fallback)
        graph_order.append(r["code"])

    ranked_catalog: list[CourseResult] = []
    if anchor_course:
        catalog_candidates = await get_catalog_recommendation_candidates()
        ranked_catalog = _rank_catalog_recommendations(
            anchor_course,
            catalog_candidates,
            exclude={code},
        )
        for candidate in ranked_catalog:
            if candidate.course_code != code and candidate.course_code not in combined:
                combined[candidate.course_code] = candidate
            if len(combined) >= 25:
                break

    if not anchor_course:
        return _coenroll_results_from_courses(list(combined.values())[:5], graph_frequency, graph_counts, anchor_schedule)

    top: list[CourseResult] = ranked_catalog[:5]
    if not top:
        for graph_code in graph_order:
            course = combined.get(graph_code)
            if course and graph_frequency.get(graph_code, 0) > 0:
                top.append(course)
            if len(top) >= 5:
                break

    if not top:
        return []

    return _coenroll_results_from_courses(top, graph_frequency, graph_counts, anchor_schedule)


def _coenroll_results_from_courses(
    courses: list[CourseResult],
    graph_frequency: dict[str, float],
    graph_counts: dict[str, int],
    anchor_schedule: dict | None,
) -> list[CoEnrollResult]:
    out: list[CoEnrollResult] = []
    for course in courses:
        frequency = graph_frequency.get(course.course_code, 0.0)
        has_graph_signal = course.course_code in graph_frequency and frequency > 0
        out.append(
            CoEnrollResult(
                course_code=course.course_code,
                title=course.title,
                subject=course.subject,
                course_level=course.course_level,
                credits=course.credits,
                frequency=round(frequency, 4) if has_graph_signal else 0.0,
                co_occurrence_count=graph_counts.get(course.course_code, 0) if has_graph_signal else 0,
                day_of_week=course.day_of_week,
                start_time=course.start_time,
                end_time=course.end_time,
                has_time_conflict=_time_conflict(anchor_schedule, course) if anchor_schedule else False,
                score_source="coenrollment" if has_graph_signal else "catalog_match",
            )
        )
    return out


def _rank_catalog_recommendations(
    anchor: CourseResult,
    candidates: list[CourseResult],
    exclude: set[str],
) -> list[CourseResult]:
    usable = [
        course
        for course in candidates
        if course.course_code
        and course.course_code not in exclude
        and course.course_code != anchor.course_code
    ]
    if not usable:
        return []

    documents = [_course_text(anchor), *(_course_text(course) for course in usable)]
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(documents)
    except ValueError:
        return []

    similarities = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    ranked = [
        (float(similarity), course)
        for similarity, course in zip(similarities, usable)
        if similarity > 0
    ]
    ranked.sort(
        key=lambda item: (
            (item[1].subject or "") != (anchor.subject or ""),
            _level_gap(anchor, item[1]),
            _is_low_signal_course(item[1]),
            -item[0],
            item[1].course_code,
        )
    )
    return [course for _, course in ranked]


def _course_text(course: CourseResult) -> str:
    return " ".join(
        value
        for value in [
            course.subject or "",
            course.title or "",
            course.description or "",
        ]
        if value
    )


def _level_gap(anchor: CourseResult, candidate: CourseResult) -> int:
    if anchor.course_level is None or candidate.course_level is None:
        return 999
    return abs(candidate.course_level - anchor.course_level)


def _is_low_signal_course(course: CourseResult) -> bool:
    text = f"{course.title} {course.description or ''}".lower()
    return any(
        phrase in text
        for phrase in [
            "special topics",
            "independent study",
            "undergraduate open seminar",
            "honors seminar",
        ]
    )


async def get_prereq_graph(code: str, depth: int = 2) -> Tuple[List[GraphNode], List[GraphLink]]:
    driver = get_driver()
    safe_depth = max(1, min(int(depth), 3))
    cypher = f"""
        MATCH path = (c:Course)-[:HAS_PREREQUISITE*1..{safe_depth}]->(base:Course {{code: $code}})
        RETURN c.code AS src_code, c.title AS src_title, c.subject AS src_subject, c.level AS src_level,
               base.code AS tgt_code, length(path) AS hops
        UNION
        MATCH (base:Course {{code: $code}})
        RETURN base.code AS src_code, base.title AS src_title,
               base.subject AS src_subject, base.level AS src_level,
               null AS tgt_code, 0 AS hops
    """
    with driver.session() as session:
        result = session.run(cypher, code=code)
        records = [dict(r) for r in result]

    node_map: dict[str, GraphNode] = {}
    links: List[GraphLink] = []

    for r in records:
        if r["src_code"] not in node_map:
            node_map[r["src_code"]] = GraphNode(
                id=r["src_code"],
                title=r.get("src_title", r["src_code"]),
                subject=r.get("src_subject"),
                level=r.get("src_level"),
                hops=r.get("hops"),
            )
        if r.get("tgt_code"):
            links.append(GraphLink(source=r["src_code"], target=r["tgt_code"], type="HAS_PREREQUISITE"))
            if r["tgt_code"] not in node_map:
                node_map[r["tgt_code"]] = GraphNode(id=r["tgt_code"], title=r["tgt_code"], hops=0)

    return list(node_map.values()), links


def _time_conflict(a: dict, b: "CourseResult") -> bool:
    if not b.day_of_week or not (_day_set(a.get("day_of_week")) & _day_set(b.day_of_week)):
        return False
    try:
        a_start = a.get("start_time", "00:00")
        a_end = a.get("end_time", "00:00")
        b_start = b.start_time or "00:00"
        b_end = b.end_time or "00:00"
        return a_start < b_end and b_start < a_end
    except Exception:
        return False


def _day_set(value: str | None) -> set[str]:
    if not value:
        return set()

    cleaned = value.strip()
    full_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    if cleaned in full_days:
        return {cleaned}

    day_names = {
        "M": "Monday",
        "T": "Tuesday",
        "W": "Wednesday",
        "R": "Thursday",
        "F": "Friday",
    }
    return {day for char in cleaned for day in [day_names.get(char.upper())] if day}
