import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routes.search import router as search_router
from routes.classes import router as classes_router
from routes.coenrollment import router as coenrollment_router
from routes.graph import router as graph_router

app = FastAPI(
    title="Student Class Search API",
    description="AI-powered university course search with knowledge graph co-enrollment insights",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)
app.include_router(classes_router)
app.include_router(coenrollment_router)
app.include_router(graph_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
