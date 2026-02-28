# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always use `uv` to run Python and manage dependencies — never call `python`, `pip`, or `uvicorn` directly.

**Install dependencies:**
```bash
uv sync
```

**Run the app:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app is served at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

**Add a dependency:**
```bash
uv add <package>
```

There are no tests or linting configured in this project.

## Architecture

This is a full-stack RAG chatbot. The **backend** (`backend/`) is a FastAPI server that also statically serves the **frontend** (`frontend/`). Course documents live in `docs/`.

### RAG Pipeline

The system has two distinct phases:

**Ingestion (on startup):** `app.py` calls `rag_system.add_course_folder("../docs")`. Each `.txt` file is parsed by `document_processor.py` into a `Course` object + list of `CourseChunk` objects, then stored in two ChromaDB collections in `vector_store.py`:
- `course_catalog` — one entry per course (title, instructor, link, lesson metadata)
- `course_content` — one entry per text chunk (800-char, sentence-aware, with 100-char overlap)

**Query (per request):** `POST /api/query` → `rag_system.query()` → `ai_generator.generate_response()` → two Claude API calls:
1. First call includes the `search_course_content` tool. If Claude invokes it, `CourseSearchTool` runs a ChromaDB vector similarity search (optionally filtering by course/lesson).
2. Second call receives the retrieved chunks and synthesizes the final answer.

Sources collected during tool execution are returned alongside the answer for display in the UI.

### Key Design Decisions

- **Tool-calling for retrieval:** Claude decides when to search (not every query triggers retrieval). Claude is instructed to search at most once per query.
- **Course title as primary key:** `Course.title` is used as the ChromaDB document ID in `course_catalog`, and as the filter key in `course_content`. Duplicate courses are skipped on re-ingestion.
- **Session history is a formatted string:** `SessionManager` stores exchanges in memory (not a DB) and serializes them into a plain `User: ... \nAssistant: ...` string that is appended to the system prompt. Max 2 exchanges (4 messages) are retained.
- **Chunk context prefix:** The first chunk of each lesson is prefixed with `"Lesson N content: ..."` to help retrieval. There is a known inconsistency — the last lesson processed uses a different prefix format (`"Course X Lesson N content: ..."`).

### Document Format

Course `.txt` files must follow this structure for correct parsing:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson body text>

Lesson 1: <title>
...
```

### Configuration

All tunable parameters are in `backend/config.py` (single `Config` dataclass, loaded once as `config`):
- `ANTHROPIC_MODEL` — Claude model to use
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — chunking parameters
- `MAX_RESULTS` — number of ChromaDB results returned per search
- `MAX_HISTORY` — conversation turns retained per session
- `CHROMA_PATH` — where ChromaDB persists to disk (`./chroma_db` relative to `backend/`)
