from fastapi import APIRouter, HTTPException, Query
from models.schemas import CoEnrollResponse
from services.kg_query import get_coenrollment
from services.db_query import get_courses_by_codes
from services.security import SecurityViolation, validate_course_code, validate_day, validate_time
from typing import Optional

router = APIRouter()


@router.get("/courses/{code}/coenrollment", response_model=CoEnrollResponse)
async def coenrollment(code: str, anchor_day: Optional[str] = Query(None),
                       anchor_start: Optional[str] = Query(None),
                       anchor_end: Optional[str] = Query(None)):
    try:
        safe_code = validate_course_code(code)
        safe_anchor_day = validate_day(anchor_day)
        safe_anchor_start = validate_time(anchor_start)
        safe_anchor_end = validate_time(anchor_end)
    except SecurityViolation as e:
        raise HTTPException(status_code=400, detail=str(e))

    anchor_schedule = None
    if safe_anchor_day and safe_anchor_start and safe_anchor_end:
        anchor_schedule = {
            "day_of_week": safe_anchor_day,
            "start_time": safe_anchor_start,
            "end_time": safe_anchor_end,
        }

    try:
        recommendations = await get_coenrollment(safe_code, anchor_schedule)
    except Exception as e:
        if "ServiceUnavailable" in type(e).__name__ or "connection" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Co-enrollment data is temporarily unavailable.",
            )
        raise

    if not recommendations:
        # Check if the course exists at all
        courses = await get_courses_by_codes([safe_code])
        if not courses:
            raise HTTPException(status_code=404, detail=f"Course {safe_code} not found.")

    return CoEnrollResponse(anchor_course=safe_code, recommendations=recommendations)
