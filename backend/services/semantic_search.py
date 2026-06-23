import csv
import html
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from models.schemas import CourseResult, SearchFilters
from services.security import safe_like_term, validate_day


COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4})\s*[- ]?\s*(\d{3})\b", re.IGNORECASE)
DAY_NAMES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
}
SUBJECT_ALIASES = {
    "COMPUTER SCIENCE": "CS",
    "MATHEMATICS": "MATH",
    "STATISTICS": "STAT",
    "PHYSICS": "PHYS",
    "ELECTRICAL ENGINEERING": "ECE",
    "DATA SCIENCE": "DS",
    "ARTIFICIAL INTELLIGENCE": "AI",
}


@dataclass(frozen=True)
class IndexedCourse:
    course: CourseResult
    days_raw: str
    document: str


@dataclass(frozen=True)
class SemanticIndex:
    courses: list[IndexedCourse]
    vectorizer: TfidfVectorizer
    matrix: object
    svd: TruncatedSVD | None


def semantic_search_courses(
    query: str | None,
    filters: SearchFilters,
    limit: int = 25,
) -> list[CourseResult]:
    safe_query = safe_like_term(query, max_chars=180)
    if not safe_query:
        return []

    index = _get_semantic_index()
    if not index.courses:
        return []

    query_text = _semantic_query_text(safe_query)
    query_vector = index.vectorizer.transform([query_text])
    if index.svd is not None:
        query_vector = normalize(index.svd.transform(query_vector))
        scores = index.matrix @ query_vector.T
        scores = np.asarray(scores).ravel()
    else:
        scores = cosine_similarity(query_vector, index.matrix).ravel()

    ranked_indices = np.argsort(-scores)
    results: list[CourseResult] = []
    for raw_index in ranked_indices:
        score = float(scores[int(raw_index)])
        if score <= 0:
            break

        indexed = index.courses[int(raw_index)]
        if not _matches_filters(indexed, filters):
            continue

        results.append(indexed.course)
        if len(results) >= limit:
            break

    return results


@lru_cache(maxsize=1)
def _get_semantic_index() -> SemanticIndex:
    courses = _load_indexed_courses()
    if not courses:
        return SemanticIndex(courses=[], vectorizer=TfidfVectorizer(), matrix=[], svd=None)

    documents = [course.document for course in courses]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return SemanticIndex(courses=[], vectorizer=vectorizer, matrix=[], svd=None)

    n_components = min(256, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
    if n_components >= 2:
        svd = TruncatedSVD(n_components=n_components, random_state=7)
        semantic_matrix = normalize(svd.fit_transform(tfidf_matrix))
        return SemanticIndex(courses=courses, vectorizer=vectorizer, matrix=semantic_matrix, svd=svd)

    return SemanticIndex(courses=courses, vectorizer=vectorizer, matrix=tfidf_matrix, svd=None)


def _load_indexed_courses() -> list[IndexedCourse]:
    path = Path(__file__).resolve().parents[1] / "data" / "courses_prepped.csv"
    if not path.exists():
        return []

    indexed: list[IndexedCourse] = []
    seen: set[str] = set()
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            course = _local_row_to_course(row)
            if not course.course_code or course.course_code in seen:
                continue
            seen.add(course.course_code)
            indexed.append(
                IndexedCourse(
                    course=course,
                    days_raw=row.get("days_raw") or "",
                    document=_course_document(course),
                )
            )

    return indexed


def _local_row_to_course(row: dict) -> CourseResult:
    try:
        level = int(float(row.get("level") or 0)) or None
    except ValueError:
        level = None

    try:
        credits = float(row.get("credits") or 0)
    except ValueError:
        credits = 0.0

    return CourseResult(
        course_code=row.get("course_code", ""),
        title=html.unescape(row.get("title") or ""),
        subject=row.get("subject", ""),
        course_level=level,
        credits=credits if credits > 0 else None,
        instructor_name=row.get("instructor") or None,
        day_of_week=_first_day_from_raw(row.get("days_raw")),
        start_time=row.get("start_time") or None,
        end_time=row.get("end_time") or None,
        room=row.get("room") or None,
        building=row.get("building") or None,
        semester=row.get("semester") or None,
        description=html.unescape(row.get("description") or "") or None,
    )


def _course_document(course: CourseResult) -> str:
    code_match = COURSE_CODE_RE.search(course.course_code or "")
    course_number = code_match.group(2) if code_match else ""
    subject = course.subject or ""

    parts = [
        course.course_code or "",
        f"{subject} {course_number}".strip(),
        subject,
        course.title or "",
        course.description or "",
        course.instructor_name or "",
    ]
    return " ".join(part for part in parts if part)


def _semantic_query_text(query: str) -> str:
    lowered = query.lower()
    expansions = [query]

    if re.search(r"\bai\b", lowered) or "artificial intelligence" in lowered:
        expansions.append(
            "artificial intelligence machine learning deep learning neural networks "
            "computer vision reinforcement learning data mining natural language processing"
        )

    if "machine learning" in lowered:
        expansions.append(
            "machine learning applied machine learning deep learning reinforcement learning "
            "statistical learning neural networks"
        )

    if "data science" in lowered or "data scientist" in lowered or "analytics" in lowered:
        expansions.append(
            "data science data analytics data mining statistics statistical modeling "
            "python visualization machine learning"
        )

    if "software" in lowered or "programming" in lowered:
        expansions.append("programming software systems algorithms data structures")

    if "cyber" in lowered or "security" in lowered:
        expansions.append("cybersecurity computer security privacy cryptography networks")

    return " ".join(expansions)


def _matches_filters(indexed: IndexedCourse, filters: SearchFilters) -> bool:
    course = indexed.course

    subjects = _subject_codes(filters.subject)
    if subjects and (course.subject or "").upper() not in subjects:
        return False

    if filters.day_of_week:
        requested_day = validate_day(filters.day_of_week)
        if requested_day and requested_day not in _days_from_raw(indexed.days_raw):
            return False

    if filters.course_level:
        level = course.course_level
        if level is None or not (filters.course_level <= level <= filters.course_level + 99):
            return False

    if filters.credits is not None:
        if course.credits is None or float(course.credits) != float(filters.credits):
            return False

    if filters.instructor_name:
        instructor = safe_like_term(filters.instructor_name, max_chars=80) or ""
        if instructor.lower() not in (course.instructor_name or "").lower():
            return False

    # These fields are not present in courses_prepped.csv, so semantic fallback should not
    # claim matches for filters it cannot verify.
    if filters.enrollment_status or filters.instruction_type or filters.degree_attributes:
        return False

    return True


def _subject_codes(subject: str | None) -> set[str]:
    if not subject:
        return set()

    codes: set[str] = set()
    for raw_part in str(subject).split("|"):
        cleaned = safe_like_term(raw_part, max_chars=60)
        if not cleaned:
            continue
        upper = cleaned.upper()
        codes.add(SUBJECT_ALIASES.get(upper, upper))
    return codes


def _first_day_from_raw(days_raw: str | None) -> str | None:
    for char in days_raw or "":
        day = DAY_NAMES.get(char.upper())
        if day:
            return day
    return None


def _days_from_raw(days_raw: str) -> set[str]:
    return {DAY_NAMES[char.upper()] for char in days_raw if char.upper() in DAY_NAMES}
