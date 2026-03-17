# System Design

## Purpose

JD Matcher v2 is a full-stack job targeting system. It stores raw job descriptions, parses them into structured analysis with OpenAI, tracks application workflow, and generates cluster-level resume strategy output.

The repository is organized to support:
- production-like backend boundaries
- Streamlit operational UI
- AI-assisted development and maintenance
- interview presentation of architecture decisions

## Architecture Diagram

```text
Streamlit UI / CLI
        |
        v
FastAPI Routers
        |
        v
Service Layer
   |        |        |
   v        v        v
 MySQL    Redis    OpenAI
        \
         v
     Output Files
```

## High-Level Data Flow

### Main Product Flow

1. User adds a job description in Streamlit or CLI.
2. FastAPI router validates input and delegates to a service.
3. `JobService` persists the job and creates initial workflow state.
4. `ParserService` loads the current resume, checks Redis cache, and calls OpenAI when needed.
5. Parsed output is stored in `job_analysis` and workflow priority is updated.
6. `StrategyService` aggregates analyzed jobs by cluster and filters.
7. Redis cache is checked before generating strategy.
8. Strategy markdown is stored in `resume_strategy` and written to `data/outputs/`.
9. FastAPI returns structured data back to UI.

### Compatibility Flow

The repository still contains compatibility endpoints:
- `POST /analysis/jd`
- `GET /history`

These support the earlier simplified analysis mode and should remain stable unless explicitly retired.

## Folder Structure

### `app/`

- `api/routers/`
  FastAPI route handlers. Keep them thin.
- `services/`
  Business logic and orchestration.
- `db/models/`
  SQLAlchemy models.
- `cache/`
  Redis client access.
- `prompts/`
  OpenAI prompt text and JSON schemas.
- `middleware/`
  Request logging middleware.
- `core/`
  Configuration.
- `schemas/`
  Request and response models.

### `ui/`

Streamlit application and pages.

### `data/outputs/`

Generated markdown, csv, and token usage logs.

### `docs/`

Final documentation set only:
- `operation_guide.md`
- `system_design.md`

## Backend Responsibilities

## Routers

Routers must only:
- validate request input
- resolve dependencies
- call services
- translate service exceptions into HTTP responses

Routers must not:
- perform SQL queries directly
- build cache keys
- contain OpenAI prompt logic
- implement business rules

Current routers:
- `/jobs`
- `/strategy`
- `/health`
- `/analysis`
- `/history`

## Services

### `JobService`

Responsibilities:
- create jobs
- delete jobs
- update workflow state
- query job dashboard data

### `ParserService`

Responsibilities:
- load resume content
- build parser cache key
- call OpenAI parser client when cache miss occurs
- persist `job_analysis`
- update workflow priority and next action

### `StrategyService`

Responsibilities:
- fetch analyzed rows by cluster and filters
- aggregate keywords and gaps
- compute cluster input fingerprint
- validate Redis cache against current fingerprint
- persist `resume_strategy`
- write strategy markdown files

### `ExportService`

Responsibilities:
- generate `jobs.csv`
- generate `dash.md`
- generate `resume_versions.md`

### `OpenAIClient`

Responsibilities:
- centralize all OpenAI Responses API calls
- enforce JSON schema output
- retry transient API failures
- write token usage log

All OpenAI calls must remain centralized here.

## Database Structure

The repository uses MySQL as the primary persistent store.

### `jobs`

Purpose:
- store original job descriptions and basic metadata

Important columns:
- `id`
- `company`
- `role_title`
- `url`
- `jd_text`
- `created_at`

### `job_analysis`

Purpose:
- store parser output for a job and analysis version

Important relationship:
- `job_analysis.job_id -> jobs.id`

Fields include cluster, fit score, keyword lists, gaps, and resume recommendation.

### `workflow`

Purpose:
- track application state and next action

Fields include:
- `priority`
- `status`
- `next_action`
- `applied`
- `applied_date`

### `resume_strategy`

Purpose:
- store generated strategy markdown and strategy metadata

Fields include:
- `cluster`
- `resume_variant`
- `cluster_summary`
- `resume_plan_md`
- `resume_hash`
- `analysis_version`
- `cluster_input_hash`

### `analysis_records`

Purpose:
- support compatibility analysis endpoint history

This table is not part of the main parser/strategy pipeline, but is still used by `/analysis/jd` and `/history`.

## Redis Cache Structure

Redis is used only for AI-response caching in the main product pipeline.

### Parser Cache

Key pattern:

`parser_cache:{job_id}:{resume_hash}:{analysis_version}`

Value:
- structured parser response payload

### Strategy Cache

Key pattern:

`strategy_cache:{cluster}:{company}:{score}:{resume_hash}:{analysis_version}`

Notes:
- `company` uses `all` when no company filter is applied
- `score` uses `all` when no minimum score is applied
- stored payload also includes `cluster_input_hash`
- cache is only considered valid when stored `cluster_input_hash` matches the current recomputed fingerprint

This design keeps the Redis namespace readable while still preventing stale strategy reuse.

## Parser Workflow

1. Load job by `job_id`.
2. Load current resume text and compute `resume_hash`.
3. Build parser cache key.
4. Check Redis cache.
5. If Redis misses, check MySQL `job_analysis` for same resume hash and analysis version.
6. If both miss, call OpenAI parser using:
   - `parser_prompt.txt`
   - `PARSER_SCHEMA`
7. Persist results into `job_analysis`.
8. Update `workflow.priority` and `workflow.next_action`.
9. Cache the public parser payload in Redis.

## Strategist Workflow

1. Load analyzed jobs for the selected cluster and filters.
2. Aggregate must-have keywords, domain keywords, and gaps.
3. Compute `cluster_input_hash` from the filtered analysis set.
4. Build readable strategy cache key.
5. Check Redis cache and verify the stored `cluster_input_hash`.
6. If Redis misses, check `resume_strategy` in MySQL.
7. If both miss, call OpenAI strategist using:
   - `strategist_prompt.txt`
   - `STRATEGIST_SCHEMA`
8. Persist markdown and metadata to `resume_strategy`.
9. Write markdown file to `data/outputs/`.

## Middleware

Current middleware:
- `RequestLoggingMiddleware`

Purpose:
- log incoming request method and path
- log response status and latency

This middleware is useful and should remain unless replaced by a more complete observability layer.

## Important Design Decisions

- Keep routers thin.
- Keep business logic in services.
- Keep OpenAI integration centralized in `OpenAIClient`.
- Keep MySQL as the source of truth.
- Use Redis only as cache, never as system of record.
- Keep Streamlit as a thin operational UI.
- Preserve compatibility endpoints unless there is an explicit deprecation decision.

## Safe Modification Rules

- Never place business logic in routers.
- Never add direct OpenAI calls outside `app/services/openai_client.py`.
- Never treat Redis as persistent storage.
- Never change database schema casually; add migrations or explicit review first.
- Never expose internal fields such as hashes in the UI.
- Keep UI logic limited to calling existing API endpoints.
- If a change affects cache semantics, preserve key readability and invalidation safety.
- If a change touches parser or strategist output shape, update schemas and prompts together.

## Endpoint Summary

### Jobs

- `POST /jobs/add`
- `POST /jobs/analyze`
- `GET /jobs`
- `PATCH /jobs/{job_id}/workflow`
- `DELETE /jobs/{job_id}`

### Strategy

- `POST /strategy/generate`
- `GET /strategy`

### Compatibility / Support

- `POST /analysis/jd`
- `GET /history`
- `GET /health`

## Recommended Extension Pattern

If you add a feature:

1. Add request/response schema first.
2. Add or extend a service.
3. Keep router changes minimal.
4. Update Streamlit only through existing endpoints.
5. Update this document if data flow or responsibilities change.