from models.schemas import SearchFilters, CourseResult
from services.db_query import get_courses_requiring, run_sql_query
from services.kg_query import run_graph_query
from typing import Tuple, List, Optional


async def route_query(filters: SearchFilters) -> Tuple[List[CourseResult], Optional[str]]:
    if filters.query_type == "general":
        return [], None

    if filters.query_type == "filter":
        # If no specific filters, return a sample of courses to help the user get started
        # This handles broad queries like "what courses can I pick?" or "show me courses"
        results = await run_sql_query(filters, limit=25 if _has_filter_criteria(filters) else 10)
        return results, None

    elif filters.query_type == "traversal":
        if not filters.base_course:
            results = await run_sql_query(filters)
            return results, None
        try:
            results = await run_graph_query("prereq_unlock", filters.base_course)
        except Exception:
            results = []
        if not results:
            results = await get_courses_requiring(filters.base_course)
        return results, f"courses_unlocked_by_{filters.base_course}"

    elif filters.query_type == "recommendation":
        if not filters.base_course:
            results = await run_sql_query(filters)
            return results, None
        try:
            results = await run_graph_query("coenrollment", filters.base_course)
        except Exception:
            results = []
        return results, f"often_taken_with_{filters.base_course}"

    return [], None


def _has_filter_criteria(filters: SearchFilters) -> bool:
    return any(
        [
            filters.subject,
            filters.instructor_name,
            filters.day_of_week,
            filters.course_level,
            filters.credits,
            filters.keyword,
            filters.enrollment_status,
            filters.instruction_type,
            filters.degree_attributes,
        ]
    )
