# Student Class Search Application

AI-powered university course discovery and schedule planning prototype with knowledge graph-based co-enrollment insights.

## Overview

This full-stack application demonstrates AI-powered natural language course search using a two-stage GPT pipeline, PostgreSQL (Supabase) for structured data, and Neo4j knowledge graphs for relationship-based queries. Students can search for courses using natural language, explore prerequisites, and discover which courses are often taken together.

## Features

- **Natural Language Search**: Ask questions like "Show me CS classes on Mondays" or "What can I take after CS201?"
- **AI-Powered Query Understanding**: Two-GPT pipeline for intent classification and RAG-grounded responses
- **Knowledge Graph Integration**: Neo4j-based prerequisite chains and co-enrollment recommendations
- **Study Squad Finder**: Discover related courses from graph data and semantic catalog similarity
- **Schedule Conflict Detection**: Automatic time conflict checking for co-enrolled courses
- **Workload Insight**: Credit totals and workload percentile for selected courses

## Tech Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Visualization**: D3.js (for prerequisite graph visualization)

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI/LLM**: OpenAI GPT-3.5-turbo (function calling for structured extraction)
- **Databases**:
  - PostgreSQL (Supabase) - Course catalog, schedules, instructors
  - Neo4j AuraDB - Knowledge graph for prerequisites and co-enrollment
- **Data Processing**: Pandas, scikit-learn

### Architecture
```
┌──────────────┐
│   Frontend   │  React + TypeScript (Vite dev server: 5173)
└──────┬───────┘
       │ HTTP/JSON
┌──────▼────────┐
│  Backend API  │  FastAPI (uvicorn: 8000)
└───┬───────┬───┘
    │       │
    ▼       ▼
┌────────┐ ┌─────────┐
│Supabase│ │ Neo4j   │
│Postgres│ │ AuraDB  │
└────────┘ └─────────┘
       │
       ▼
   ┌────────┐
   │ OpenAI │  GPT-3.5-turbo (2-call pipeline)
   └────────┘
```

## Data Source

**Kaggle Dataset**: University Courses Dataset
- The application uses a university course catalog CSV containing course codes, titles, descriptions, instructors, schedules, and prerequisites
- Dataset location: `Dataset/course-catalog.csv`
- Ingested using the pipeline in `backend/scripts/ingest_local.py`

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Accounts/Keys**:
  - OpenAI API key
  - Supabase project (free tier)
  - Neo4j AuraDB instance (free tier)

## Setup Instructions

### 1. Clone the Repository
```bash
cd /Users/bala/Documents/Astute\ Business\ Solutions/student-class-search
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your credentials:
#   - SUPABASE_URL
#   - SUPABASE_KEY
#   - SUPABASE_DSN
#   - NEO4J_URI
#   - NEO4J_USER
#   - NEO4J_PASSWORD
#   - OPENAI_API_KEY
```

### 3. Database Setup

**Supabase (PostgreSQL):**
```bash
# Run the schema in your Supabase SQL editor
cat database/schema.sql
# Copy and execute in: Supabase Dashboard → SQL Editor → New Query
```

**Neo4j AuraDB:**
```bash
# Run constraints in your Neo4j browser
cat database/neo4j_constraints.cypher
# Copy and execute in: Neo4j Browser → Query tab
```

### 4. Data Ingestion

Place your course catalog CSV in `Dataset/course-catalog.csv`, then run:

```bash
cd backend
python -m scripts.ingest_local

# This runs 3 steps:
#   1. Clean & deduplicate CSV
#   2. Load into Supabase (instructors, courses, schedules)
#   3. Build Neo4j knowledge graph
```

### 5. Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 6. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 7. Access the Application

Open your browser to `http://localhost:5173` and start searching!

**Example queries to try:**
- "Show me CS classes on Mondays"
- "Find classes taught by Dr. Smith"
- "What 300-level math courses are available?"
- "What can I take after CS201?"
- "What courses are often taken with MATH221?"

## API Endpoints

### Core Search
- `POST /search` - Natural language course search
  - Body: `{query: string, history: HistoryMessage[]}`
  - Returns: Structured filters, course results, RAG response

### Data Access
- `GET /classes` - Raw course data with optional filters
  - Query params: `subject`, `day`, `level`, `limit`

### Knowledge Graph
- `GET /courses/{code}/coenrollment` - Co-enrollment recommendations
- `GET /graph/prereqs` - Prerequisite tree visualization
- `GET /graph/workload` - Workload insight for selected courses

## How It Works

### Two-GPT Pipeline

**Call 1: Query Parsing** (`services/openai_parser.py`)
- Extracts structured filters from natural language
- Classifies intent: `filter`, `traversal`, `recommendation`, or `general`
- Uses GPT function calling for reliable structured extraction
- Maintains conversation context for multi-turn queries

**Call 2: RAG Response** (`services/rag_responder.py`)
- Takes retrieved courses and generates natural language response
- Grounded in actual course data (no hallucination)
- Concise summaries that complement the course cards

### Query Routing (`services/query_router.py`)
- **Filter queries** → Supabase SQL (structured course catalog search)
- **Traversal queries** → Neo4j Cypher (prerequisite chains)
- **Recommendation queries** → Neo4j Cypher (co-enrollment graph)

### Knowledge Graph Features
- **Prerequisite chains**: `MATCH (c:Course)-[:HAS_PREREQUISITE]->(prereq)`
- **Co-enrollment**: `MATCH (c1:Course)-[:OFTEN_TAKEN_WITH]->(c2)`
- **Catalog fallback recommendations**: Uses semantic catalog similarity when graph co-enrollment data is unavailable
- **Workload analysis**: Compares selected credit load against the enrollment workload distribution

## Project Structure

```
student-class-search/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── routes/
│   │   ├── search.py             # Natural language search endpoint
│   │   ├── classes.py            # Raw course data endpoint
│   │   ├── coenrollment.py       # Co-enrollment recommendations
│   │   └── graph.py              # Graph visualization endpoints
│   ├── services/
│   │   ├── openai_parser.py      # GPT Call 1: Extract filters
│   │   ├── rag_responder.py      # GPT Call 2: Generate response
│   │   ├── query_router.py       # Route to SQL or Cypher
│   │   ├── db_query.py           # Supabase queries
│   │   ├── kg_query.py           # Neo4j queries
│   │   ├── kg_builder.py         # Build knowledge graph
│   │   └── workload_engine.py    # Workload scoring
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   └── scripts/
│       ├── ingest_local.py       # Main data ingestion pipeline
│       └── ingest_kaggle.py      # Kaggle dataset downloader
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Main app component
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx     # Chat interface
│   │   │   ├── CourseCard.tsx    # Course result card
│   │   │   ├── StudySquadPanel.tsx  # Co-enrollment sidebar
│   │   │   └── ...
│   │   ├── context/
│   │   │   └── StudySquadContext.tsx  # State management
│   │   └── api/
│   │       └── client.ts         # API client
│   └── vite.config.ts            # Vite configuration + proxy
├── database/
│   ├── schema.sql                # Supabase PostgreSQL schema
│   └── neo4j_constraints.cypher  # Neo4j constraints
├── Dataset/
│   └── course-catalog.csv        # Source data (from Kaggle)
└── README.md                     # This file
```

## Known Limitations

1. **Data Scope**: Demo uses a single semester's course catalog; production would need multi-semester data
2. **Scalability**: Current co-enrollment computation is O(n²); production would use incremental updates
3. **Prerequisite Data**: Graph relationships are inferred from course descriptions; ideally would use structured prerequisite data
4. **LLM Costs**: GPT-3.5-turbo calls add latency (~500ms) and cost (~$0.001 per search); could be optimized with caching
5. **Local Fallback**: Regex-based parsing is available but limited compared to GPT understanding
6. **Production Deployment**: Frontend BASE URL needs environment variable configuration for production

## Future Enhancements

- [ ] Vector embeddings for semantic course similarity
- [ ] Real-time seat availability tracking
- [ ] Multi-semester schedule planning
- [ ] Professor rating integration
- [ ] Course difficulty prediction model
- [ ] Mobile-responsive design improvements
- [ ] Export schedule to calendar (iCal format)

## Development

### Running Tests
```bash
# Backend tests (if implemented)
cd backend
pytest

# Frontend tests (if implemented)
cd frontend
npm test
```

### Rebuilding Knowledge Graph
```bash
cd backend
python -m scripts.ingest_local 3
# Runs only step 3 (graph build); ingestion now has 3 steps
```

## License

This is a candidate assignment project. All rights reserved.

## Contact

For questions or issues, please contact the project maintainer.

---

**Assignment**: Student Class Search Application (Full-Stack + AI + Data Integration)
**Date**: June 2026
**Status**: Prototype Complete
