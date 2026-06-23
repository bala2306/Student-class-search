from fastapi import APIRouter, HTTPException
from models.schemas import SearchFilters, SearchRequest, SearchResponse
from services.advising import (
    advising_clarification_response,
    advising_focus,
    advising_subject_for_focus,
    is_pending_advising_followup,
    is_physics_ece_advising_query,
    needs_advising_clarification,
)
from services.openai_parser import parse_query
from services.query_router import route_query
from services.rag_responder import generate_response
from services.security import SecurityViolation, sanitize_history, validate_user_query

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        query = validate_user_query(request.query)
        history = sanitize_history(
            [{"role": h.role, "content": h.content} for h in request.history]
        )
    except SecurityViolation as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    # Call 1: extract structured filters (with conversation history for multi-turn context)
    filters = await parse_query(query, history)

    if needs_advising_clarification(query, history, filters):
        response_text = advising_clarification_response()
        return SearchResponse(
            query=query,
            query_type="advising",
            response_text=response_text,
            filters_extracted=filters.model_dump(exclude={"query_type"}),
            results=[],
            result_count=0,
            graph_context=None,
            message=response_text,
        )

    if is_pending_advising_followup(query, history):
        focus = advising_focus(query, history)
        if focus is None:
            response_text = advising_clarification_response()
            return SearchResponse(
                query=query,
                query_type="advising",
                response_text=response_text,
                filters_extracted=filters.model_dump(exclude={"query_type"}),
                results=[],
                result_count=0,
                graph_context=None,
                message=response_text,
            )
        filters = SearchFilters(
            query_type="filter",
            subject=advising_subject_for_focus(focus),
        )
    elif is_physics_ece_advising_query(query, filters):
        focus = advising_focus(query, history)
        if focus is not None:
            filters = SearchFilters(
                query_type="filter",
                subject=advising_subject_for_focus(focus),
            )

    # For general queries (greetings), generate response immediately without search
    if filters.query_type == "general":
        response_text = await generate_response(query, [], history, None)
        return SearchResponse(
            query=query,
            query_type="general",
            response_text=response_text,
            filters_extracted={},
            results=[],
            result_count=0,
            graph_context=None,
            message=response_text,
        )

    # Retrieve from the correct store (Supabase SQL or Neo4j Cypher)
    results, graph_context = await route_query(filters)

    # Call 2: generate RAG-grounded natural language response
    response_text = await generate_response(query, results, history, graph_context)

    for r in results:
        r.graph_context = graph_context

    return SearchResponse(
        query=query,
        query_type=filters.query_type,
        response_text=response_text,
        filters_extracted=filters.model_dump(exclude={"query_type"}),
        results=results,
        result_count=len(results),
        graph_context=graph_context,
        message=response_text,   # kept for backwards compat
    )
