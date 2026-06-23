from pydantic import BaseModel
from typing import Optional, List, Literal


class HistoryMessage(BaseModel):
    role: str        # "user" or "assistant"
    content: str


class SearchRequest(BaseModel):
    query: str
    history: List[HistoryMessage] = []


class SearchFilters(BaseModel):
    query_type: Literal["filter", "traversal", "recommendation", "general"] = "filter"
    subject: Optional[str] = None
    instructor_name: Optional[str] = None
    day_of_week: Optional[str] = None
    course_level: Optional[int] = None
    credits: Optional[float] = None
    keyword: Optional[str] = None
    base_course: Optional[str] = None
    enrollment_status: Optional[str] = None   # "Open", "Open (Restricted)", "Closed"
    instruction_type: Optional[str] = None    # "Online", "Lecture", "Lab", "Discussion"
    degree_attributes: Optional[str] = None   # keyword to match against degree_attributes


class CourseResult(BaseModel):
    course_code: str
    title: str
    subject: str
    course_level: Optional[int] = None
    credits: Optional[float] = None
    instructor_name: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room: Optional[str] = None
    building: Optional[str] = None
    semester: Optional[str] = None
    description: Optional[str] = None
    enrollment_status: Optional[str] = None
    instruction_type: Optional[str] = None
    degree_attributes: Optional[str] = None
    graph_context: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    query_type: str
    response_text: str                    # RAG-grounded GPT response (replaces hardcoded message)
    filters_extracted: dict
    results: List[CourseResult]
    result_count: int
    graph_context: Optional[str] = None
    message: Optional[str] = None        # kept for backwards compat; prefer response_text


class CoEnrollResult(BaseModel):
    course_code: str
    title: str
    subject: Optional[str] = None
    course_level: Optional[int] = None
    credits: Optional[float] = None
    frequency: float
    co_occurrence_count: int
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    has_time_conflict: bool = False
    score_source: Optional[str] = None  # "coenrollment" or "catalog_match"


class CoEnrollResponse(BaseModel):
    anchor_course: str
    recommendations: List[CoEnrollResult]


class GraphNode(BaseModel):
    id: str
    title: str
    subject: Optional[str] = None
    level: Optional[int] = None
    hops: Optional[int] = None


class GraphLink(BaseModel):
    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


class WorkloadInsight(BaseModel):
    courses: List[str]
    total_credits: float
    workload_tier: str
    workload_percentile: float
    peer_schedule_count: int
