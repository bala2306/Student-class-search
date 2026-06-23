from fastapi import APIRouter, Query, HTTPException
from models.schemas import GraphResponse, WorkloadInsight
from services.kg_query import get_prereq_graph
from services.workload_engine import compute_workload_metrics
from services.security import SecurityViolation, validate_course_code

router = APIRouter()


@router.get("/graph/prereqs", response_model=GraphResponse)
async def prereq_graph(
    course: str = Query(..., description="Course code, e.g. CS301"),
    depth: int = Query(2, ge=1, le=3),
):
    try:
        safe_course = validate_course_code(course)
    except SecurityViolation as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        nodes, links = await get_prereq_graph(safe_course, depth)
    except Exception as e:
        if "ServiceUnavailable" in type(e).__name__ or "connection" in str(e).lower():
            raise HTTPException(status_code=503, detail="Graph database temporarily unavailable.")
        raise

    if not nodes:
        raise HTTPException(status_code=404, detail=f"No graph data found for course {safe_course}.")

    return GraphResponse(nodes=nodes, links=links)


@router.get("/graph/workload", response_model=WorkloadInsight)
async def workload_insight(
    courses: str = Query(..., description="Comma-separated course codes, e.g. CS301,MATH240,STAT400"),
):
    try:
        codes = [validate_course_code(c) for c in courses.split(",") if c.strip()]
    except SecurityViolation as e:
        raise HTTPException(status_code=400, detail=str(e))

    if len(codes) < 1:
        raise HTTPException(status_code=400, detail="Provide at least 1 course code.")

    result = compute_workload_metrics(codes)
    return WorkloadInsight(
        courses=codes,
        total_credits=result["total_credits"],
        workload_tier=result["workload_tier"],
        workload_percentile=result["workload_percentile"],
        peer_schedule_count=result["peer_schedule_count"],
    )
