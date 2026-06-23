import os
import re
import csv
from pathlib import Path
from supabase import create_client, Client
from models.schemas import SearchFilters, CourseResult
from services.security import safe_like_term, validate_day
from services.semantic_search import semantic_search_courses
from typing import List

_client: Client | None = None

SUBJECT_TERMS = {
    "CS": ["CS", "Computer Science"],
    "CSE": ["CSE"],
    "MATH": ["MATH", "Mathematics"],
    "STAT": ["STAT", "Statistics"],
    "IS": ["IS"],
    "INFO": ["INFO"],
    "ECE": ["ECE"],
    "DS": ["DS", "Data Science"],
    "AI": ["AI", "Artificial Intelligence"],
    "PHYS": ["PHYS", "Physics"],
    "CHEM": ["CHEM", "Chemistry"],
    "BIOL": ["BIOL", "Biology"],
    "ECON": ["ECON", "Economics"],
    "BUS": ["BUS", "Business"],
    "PSYC": ["PSYC", "Psychology"],
    "ENGL": ["ENGL", "English"],
    "HIST": ["HIST", "History"],
    "CEE": ["CEE"],
    "ME": ["ME"],
    "ACCY": ["ACCY"],
    "PHIL": ["PHIL"],
    "SOC": ["SOC"],
    "ANTH": ["ANTH"],
    "ASTR": ["ASTR"],
    "LING": ["LING"],
}

COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4})\s*[- ]?\s*(\d{3})\b", re.IGNORECASE)


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client


async def run_sql_query(filters: SearchFilters, limit: int = 25) -> List[CourseResult]:
    sb = get_client()
    has_keyword = bool(filters.keyword)
    subject_order = _subject_order(filters.subject)
    keyword_code = _normalize_course_code(filters.keyword)

    if len(subject_order) > 1 and not has_keyword:
        return _run_multi_subject_query(sb, filters, subject_order, limit)

    query = sb.table("course_full").select("*")

    if filters.subject:
        terms = _subject_search_terms(filters.subject)
        # Use exact eq match so "CS" doesn't also match "BCS", "ACCY", etc.
        if len(terms) == 1:
            query = query.eq("subject", terms[0])
        else:
            query = query.in_("subject", terms)

    if filters.instructor_name:
        query = query.ilike("instructor_name", f"%{filters.instructor_name}%")

    if filters.day_of_week:
        query = query.eq("day_of_week", filters.day_of_week)

    if filters.course_level:
        low = filters.course_level
        high = low + 99
        query = query.gte("course_level", low).lte("course_level", high)

    if filters.credits:
        query = query.eq("credits", filters.credits)

    if filters.keyword:
        keyword = safe_like_term(filters.keyword, max_chars=120)
        if not keyword:
            return []
        code = _normalize_course_code(keyword)
        search_terms = _keyword_search_terms(keyword)
        terms = []
        for term in search_terms:
            safe_term = safe_like_term(term, max_chars=80)
            if not safe_term:
                continue
            terms.extend(
                [
                    f"title.ilike.%{safe_term}%",
                    f"description.ilike.%{safe_term}%",
                    f"course_code.ilike.%{safe_term}%",
                ]
            )
        if code and code != keyword:
            terms.append(f"course_code.ilike.%{code}%")
        if terms:
            query = query.or_(",".join(terms))
        else:
            return []

    if filters.enrollment_status:
        query = query.eq("enrollment_status", filters.enrollment_status)

    if filters.instruction_type:
        query = query.eq("instruction_type", filters.instruction_type)

    if filters.degree_attributes:
        query = query.ilike("degree_attributes", f"%{filters.degree_attributes}%")

    fetch_limit = max(limit * 8, 120) if has_keyword else limit * 3
    try:
        response = query.limit(fetch_limit).execute()
        rows = response.data or []
    except Exception:
        if not has_keyword:
            raise
        rows = []

    # course_full has one row per schedule day — deduplicate by course_code
    seen: set[str] = set()
    unique: list[dict] = []
    for r in rows:
        code = r.get("course_code", "")
        if code not in seen:
            seen.add(code)
            unique.append(r)
        if not has_keyword and len(unique) >= limit:
            break

    courses = [_row_to_course(r) for r in unique]
    if has_keyword:
        lexical_courses = _rank_keyword_results(courses, filters.keyword or "", limit)
        semantic_courses = semantic_search_courses(
            filters.keyword,
            filters,
            limit=max(limit * 2, 40),
        )
        if keyword_code:
            courses = _merge_ranked_courses(lexical_courses, semantic_courses, limit)
        else:
            courses = _merge_ranked_courses(semantic_courses, lexical_courses, limit)
    elif filters.subject:
        courses = _rank_catalog_results(courses)

    if has_keyword:
        return courses[:limit]
    elif len(subject_order) > 1:
        courses = _interleave_subjects(courses, subject_order)
    return courses[:limit]


def _run_multi_subject_query(
    sb: Client,
    filters: SearchFilters,
    subject_order: list[str],
    limit: int,
) -> list[CourseResult]:
    courses: list[CourseResult] = []
    per_subject_limit = max(limit * 3, 75)

    for subject in subject_order:
        query = sb.table("course_full").select("*")
        terms = _subject_search_terms(subject)
        if len(terms) == 1:
            query = query.eq("subject", terms[0])
        else:
            query = query.in_("subject", terms)

        if filters.instructor_name:
            query = query.ilike("instructor_name", f"%{filters.instructor_name}%")

        if filters.day_of_week:
            query = query.eq("day_of_week", filters.day_of_week)

        if filters.course_level:
            low = filters.course_level
            high = low + 99
            query = query.gte("course_level", low).lte("course_level", high)

        if filters.credits:
            query = query.eq("credits", filters.credits)

        if filters.enrollment_status:
            query = query.eq("enrollment_status", filters.enrollment_status)

        if filters.instruction_type:
            query = query.eq("instruction_type", filters.instruction_type)

        if filters.degree_attributes:
            query = query.ilike("degree_attributes", f"%{filters.degree_attributes}%")

        response = query.limit(per_subject_limit).execute()
        subject_courses = _dedupe_courses([_row_to_course(row) for row in response.data or []])
        courses.extend(_rank_catalog_results(subject_courses))

    return _interleave_subjects(_dedupe_courses(courses), subject_order)[:limit]


async def get_courses_by_codes(codes: List[str]) -> List[CourseResult]:
    sb = get_client()
    response = (
        sb.table("course_full")
        .select("*")
        .in_("course_code", codes)
        .execute()
    )
    rows = response.data or []
    return _dedupe_courses([_row_to_course(r) for r in rows])


async def get_courses_requiring(base_course: str, limit: int = 25) -> List[CourseResult]:
    sb = get_client()
    code = _normalize_course_code(base_course)
    if not code:
        return []

    spaced = _space_course_code(code)
    # Prefix with space so "%  CS 201%" does NOT match "BCS 201" (word boundary guard)
    terms = [f" {code}", f" {spaced}"]

    response = (
        sb.table("course_full")
        .select("*")
        .or_(",".join(f"description.ilike.%{term}%" for term in terms))
        .limit(max(limit * 8, 120))
        .execute()
    )
    rows = response.data or []
    courses = [
        _row_to_course(r)
        for r in rows
        if r.get("course_code") != code and _prerequisite_clause_mentions(r.get("description") or "", code)
    ]
    return _rank_unlocked_courses(code, _dedupe_courses(courses))[:limit]


async def get_catalog_recommendation_candidates(limit: int = 5000) -> List[CourseResult]:
    local_courses = _load_local_catalog_courses(limit)
    if local_courses:
        return local_courses

    sb = get_client()
    rows: list[dict] = []
    page_size = 1000
    start = 0
    while len(rows) < limit:
        end = min(start + page_size - 1, limit - 1)
        response = sb.table("course_full").select("*").range(start, end).execute()
        page = response.data or []
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size

    return _dedupe_courses([_row_to_course(r) for r in rows])[:limit]


async def get_all_raw(subject: str | None, day: str | None, level: int | None, limit: int) -> list:
    sb = get_client()
    query = sb.table("course_full").select("*")

    if subject:
        safe_subject = safe_like_term(subject, max_chars=20)
        if safe_subject:
            query = query.ilike("subject", f"%{safe_subject}%")
    if day:
        query = query.eq("day_of_week", validate_day(day))
    if level:
        query = query.gte("course_level", level).lte("course_level", level + 99)

    response = query.limit(limit).execute()
    return response.data or []


def _row_to_course(r: dict) -> CourseResult:
    return CourseResult(
        course_code=r.get("course_code", ""),
        title=r.get("title", ""),
        subject=r.get("subject", ""),
        course_level=r.get("course_level"),
        credits=float(r["credits"]) if r.get("credits") is not None else None,
        instructor_name=r.get("instructor_name"),
        day_of_week=r.get("day_of_week"),
        start_time=r.get("start_time"),
        end_time=r.get("end_time"),
        room=r.get("room"),
        building=r.get("building"),
        semester=r.get("semester"),
        description=r.get("description"),
        enrollment_status=r.get("enrollment_status"),
        instruction_type=r.get("instruction_type"),
        degree_attributes=r.get("degree_attributes"),
    )


def _load_local_catalog_courses(limit: int) -> list[CourseResult]:
    path = Path(__file__).resolve().parents[1] / "data" / "courses_prepped.csv"
    if not path.exists():
        return []

    courses: list[CourseResult] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append(_local_row_to_course(row))
            if len(courses) >= limit:
                break
    return _dedupe_courses(courses)


def _local_row_to_course(r: dict) -> CourseResult:
    try:
        level = int(float(r.get("level") or 0)) or None
    except ValueError:
        level = None

    try:
        credits = float(r.get("credits") or 0)
    except ValueError:
        credits = 0.0

    return CourseResult(
        course_code=r.get("course_code", ""),
        title=r.get("title", ""),
        subject=r.get("subject", ""),
        course_level=level,
        credits=credits if credits > 0 else None,
        instructor_name=r.get("instructor"),
        day_of_week=_first_day_from_raw(r.get("days_raw")),
        start_time=r.get("start_time") or None,
        end_time=r.get("end_time") or None,
        room=r.get("room") or None,
        building=r.get("building") or None,
        semester=r.get("semester") or None,
        description=r.get("description") or None,
    )


def _first_day_from_raw(days_raw: str | None) -> str | None:
    if not days_raw:
        return None

    day_names = {
        "M": "Monday",
        "T": "Tuesday",
        "W": "Wednesday",
        "R": "Thursday",
        "F": "Friday",
    }
    for char in days_raw:
        day = day_names.get(char.upper())
        if day:
            return day
    return None


def _subject_search_terms(subject: str) -> list[str]:
    if "|" in subject:
        terms: list[str] = []
        for part in subject.split("|"):
            terms.extend(_subject_search_terms(part))
        return list(dict.fromkeys(terms))

    cleaned = _sanitize_or_term(subject).strip()
    if not cleaned:
        return []

    upper = cleaned.upper()
    if upper in SUBJECT_TERMS:
        return SUBJECT_TERMS[upper]

    lower = cleaned.lower()
    for terms in SUBJECT_TERMS.values():
        if any(lower == term.lower() for term in terms):
            return terms

    return [cleaned]


def _subject_order(subject: str | None) -> list[str]:
    if not subject:
        return []
    parts = str(subject).split("|")
    return list(dict.fromkeys(_canonical_subject(part) for part in parts if _canonical_subject(part)))


def _canonical_subject(subject: str | None) -> str:
    if not subject:
        return ""

    cleaned = _sanitize_or_term(subject).strip()
    upper = cleaned.upper()
    if upper in SUBJECT_TERMS:
        return upper

    lower = cleaned.lower()
    for code, terms in SUBJECT_TERMS.items():
        if any(lower == term.lower() for term in terms):
            return code

    return upper


def _normalize_course_code(value: str | None) -> str | None:
    if not value:
        return None
    match = COURSE_CODE_RE.search(value)
    if not match:
        return None
    return f"{match.group(1).upper()}{match.group(2)}"


def _space_course_code(code: str) -> str:
    match = COURSE_CODE_RE.search(code)
    if not match:
        return code
    return f"{match.group(1).upper()} {match.group(2)}"


def _prerequisite_clause_mentions(description: str, code: str) -> bool:
    match = COURSE_CODE_RE.search(code)
    if not match:
        return False

    subject = match.group(1).upper()
    number = match.group(2)
    code_re = re.compile(rf"\b{re.escape(subject)}\s*{number}\b", re.IGNORECASE)

    for prereq_match in re.finditer(r"\b(?:pre|co)requisites?\b\s*:?", description, re.IGNORECASE):
        start = prereq_match.start()
        end = description.find(".", start)
        if end == -1:
            end = min(len(description), start + 500)
        clause = description[start:end]
        if code_re.search(clause):
            return True

    return False


def _rank_unlocked_courses(base_code: str, courses: list[CourseResult]) -> list[CourseResult]:
    match = COURSE_CODE_RE.search(base_code)
    base_subject = match.group(1).upper() if match else ""

    return sorted(
        courses,
        key=lambda course: (
            (course.subject or "").upper() != base_subject,
            _is_low_signal_catalog_course(course),
            _course_number(course) or 9999,
            course.course_code,
        ),
    )


def _sanitize_or_term(value: str) -> str:
    return safe_like_term(value, max_chars=120) or ""


def _keyword_search_terms(keyword: str) -> list[str]:
    lowered = keyword.lower()
    terms: list[str] = []

    if "data science" in lowered or "data scientist" in lowered:
        terms.extend(["data science", "data analytics", "analytics", "statistical", "python"])

    if "artificial intelligence" in lowered or re.search(r"\bai\b", lowered):
        terms.extend([
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "reinforcement learning",
            "computer vision",
            "data mining",
            "neural",
        ])

    if "machine learning" in lowered:
        terms.extend(["machine learning", "applied machine learning", "deep learning"])

    if not terms:
        terms.append(keyword)
        terms.extend(
            word
            for word in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", keyword)
            if word.lower() not in {"show", "all", "course", "courses", "class", "classes", "with", "and", "the"}
        )

    return list(dict.fromkeys(_sanitize_or_term(term) for term in terms if _sanitize_or_term(term)))


def _rank_keyword_results(courses: list[CourseResult], keyword: str, limit: int) -> list[CourseResult]:
    topics = _keyword_topics(keyword)
    if not topics:
        return courses

    scored = []
    for index, course in enumerate(courses):
        score = _keyword_relevance_score(course, topics)
        if score >= _keyword_min_score(topics):
            scored.append((score, index, course))

    scored.sort(key=lambda item: (-item[0], item[2].course_level or 999, item[2].course_code))
    return [course for _, _, course in scored[:limit]]


def _rank_catalog_results(courses: list[CourseResult]) -> list[CourseResult]:
    return sorted(
        courses,
        key=lambda course: (
            _is_low_signal_catalog_course(course),
            _course_number(course) or 9999,
            course.course_code,
        ),
    )


def _course_number(course: CourseResult) -> int | None:
    match = COURSE_CODE_RE.search(course.course_code or "")
    return int(match.group(2)) if match else None


def _is_low_signal_catalog_course(course: CourseResult) -> bool:
    title = (course.title or "").lower()
    description = (course.description or "").lower()
    text = f"{title} {description}"
    low_signal_terms = [
        "individual study",
        "independent study",
        "special topics",
        "open seminar",
        "master's project",
        "doctoral research",
        "thesis research",
    ]
    return any(term in text for term in low_signal_terms)


def _keyword_topics(keyword: str) -> set[str]:
    lowered = keyword.lower()
    topics: set[str] = set()
    if "data science" in lowered or "data analytics" in lowered or "analytics" in lowered:
        topics.add("data")
    if (
        "artificial intelligence" in lowered
        or "machine learning" in lowered
        or "deep learning" in lowered
        or re.search(r"\bai\b", lowered)
    ):
        topics.add("ai")
    return topics


def _keyword_min_score(topics: set[str]) -> float:
    if "ai" in topics:
        return 4.0
    if "data" in topics:
        return 3.0
    return 1.0


def _keyword_relevance_score(course: CourseResult, topics: set[str]) -> float:
    subject = (course.subject or "").upper()
    title = (course.title or "").lower()
    padded_title = f" {title} "
    description = (course.description or "").lower()
    score = 0.0

    if "ai" in topics:
        score += _subject_topic_score(subject, {
            "CS": 7.0,
            "CSE": 7.0,
            "ECE": 5.5,
            "STAT": 4.0,
            "MATH": 3.5,
            "IS": 4.0,
            "INFO": 4.0,
            "DS": 4.5,
            "AI": 4.5,
        }, default=-2.5)
        score += _text_score(padded_title, {
            "artificial intelligence": 8.0,
            "machine learning": 8.0,
            "deep learning": 7.5,
            "reinforcement learning": 7.0,
            "computer vision": 6.0,
            "data mining": 5.5,
            "neural": 5.0,
            " ai ": 5.0,
        })
        score += _text_score(f" {description} ", {
            "artificial intelligence": 2.5,
            "machine learning": 2.5,
            "deep learning": 2.3,
            "reinforcement learning": 2.2,
            "computer vision": 2.0,
            "data mining": 1.8,
            "neural": 1.5,
        })

    if "data" in topics:
        score += _subject_topic_score(subject, {
            "CS": 5.0,
            "CSE": 5.0,
            "STAT": 5.0,
            "MATH": 3.5,
            "IS": 4.5,
            "INFO": 4.5,
            "DS": 5.0,
            "AI": 3.0,
        }, default=-1.0)
        score += _text_score(padded_title, {
            "data science": 7.0,
            "data analytics": 6.0,
            "data mining": 6.0,
            "machine learning": 5.0,
            "advanced data": 4.5,
            "analytics": 4.0,
            "statistical": 3.0,
        })
        score += _text_score(description, {
            "data science": 2.5,
            "data analytics": 2.2,
            "data mining": 2.2,
            "machine learning": 2.0,
            "analytics": 1.5,
            "statistical": 1.0,
        })

    if _is_incidental_topic_match(subject, title, description, topics):
        score -= 5.0

    return score


def _subject_topic_score(subject: str, weights: dict[str, float], default: float) -> float:
    return weights.get(subject, default)


def _text_score(text: str, weights: dict[str, float]) -> float:
    return sum(weight for phrase, weight in weights.items() if phrase in text)


def _is_incidental_topic_match(subject: str, title: str, description: str, topics: set[str]) -> bool:
    core_subjects = {"CS", "CSE", "ECE", "STAT", "MATH", "IS", "INFO", "DS", "AI"}
    if subject in core_subjects:
        return False

    strong_title_terms = [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "computer vision",
        "data science",
        "data analytics",
        "data mining",
        "analytics",
    ]
    if any(term in title for term in strong_title_terms):
        return False

    if "ai" in topics:
        desc_hits = sum(
            term in description
            for term in [
                "artificial intelligence",
                "machine learning",
                "deep learning",
                "computer vision",
                "neural",
                "data mining",
            ]
        )
        return desc_hits <= 1

    return False


def _dedupe_courses(courses: list[CourseResult]) -> list[CourseResult]:
    seen: set[str] = set()
    out: list[CourseResult] = []
    for course in courses:
        if course.course_code in seen:
            continue
        seen.add(course.course_code)
        out.append(course)
    return out


def _merge_ranked_courses(
    primary: list[CourseResult],
    secondary: list[CourseResult],
    limit: int,
) -> list[CourseResult]:
    merged: list[CourseResult] = []
    seen: set[str] = set()

    for course in [*primary, *secondary]:
        if course.course_code in seen:
            continue
        seen.add(course.course_code)
        merged.append(course)
        if len(merged) >= limit:
            break

    return merged


def _interleave_subjects(courses: list[CourseResult], subject_order: list[str]) -> list[CourseResult]:
    buckets: dict[str, list[CourseResult]] = {subject: [] for subject in subject_order}
    rest: list[CourseResult] = []

    for course in courses:
        subject = _canonical_subject(course.subject)
        if subject in buckets:
            buckets[subject].append(course)
        else:
            rest.append(course)

    out: list[CourseResult] = []
    while any(buckets.values()):
        for subject in subject_order:
            if buckets[subject]:
                out.append(buckets[subject].pop(0))

    return out + rest
