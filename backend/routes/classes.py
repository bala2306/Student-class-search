from fastapi import APIRouter, HTTPException, Query
from services.db_query import get_all_raw
from services.security import SecurityViolation, safe_like_term, validate_day
from typing import Optional

router = APIRouter()


@router.get("/classes")
async def list_classes(
    subject: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    level: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        safe_subject = safe_like_term(subject, max_chars=20) if subject else None
        if subject and not safe_subject:
            raise SecurityViolation("Invalid subject filter.")
        safe_day = validate_day(day)
    except SecurityViolation as e:
        raise HTTPException(status_code=400, detail=str(e))

    rows = await get_all_raw(subject=safe_subject, day=safe_day, level=level, limit=limit)
    return {"results": rows, "count": len(rows)}
