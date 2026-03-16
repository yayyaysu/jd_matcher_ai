# SQLite Schema Report

Legacy SQLite source: `jd-matcher/data/jobs.db`

## Table: jobs
Columns:
- `id TEXT PRIMARY KEY`
- `company TEXT NULL`
- `role_title TEXT NULL`
- `url TEXT NULL`
- `jd_text TEXT NOT NULL`
- `created_at TEXT NOT NULL DEFAULT datetime('now')`

Indexes:
- primary key on `id`

Row count at inspection time: `81`

## Table: job_analysis
Columns:
- `job_id TEXT NOT NULL`
- `cluster TEXT NOT NULL`
- `fit_score INTEGER NOT NULL`
- `years_required TEXT NOT NULL`
- `cluster_reason TEXT NOT NULL`
- `must_have_keywords TEXT NOT NULL`
- `nice_to_have_keywords TEXT NOT NULL`
- `domain_keywords TEXT NOT NULL`
- `top_gaps TEXT NOT NULL`
- `screening_risks TEXT NOT NULL`
- `recommended_resume_version TEXT NOT NULL`
- `resume_tweak_suggestions TEXT NOT NULL`
- `analysis_version INTEGER NOT NULL`
- `created_at TEXT NOT NULL DEFAULT datetime('now')`
- `resume_hash TEXT NULL`

Primary key:
- composite primary key on `job_id`, `analysis_version`

Foreign keys:
- `job_id` references `jobs.id`

Row count at inspection time: `81`

## Table: workflow
Columns:
- `job_id TEXT PRIMARY KEY`
- `priority TEXT NOT NULL`
- `status TEXT NOT NULL`
- `next_action TEXT NOT NULL`
- `applied_date TEXT NULL`
- `notes TEXT NULL`
- `updated_at TEXT NOT NULL DEFAULT datetime('now')`
- `applied INTEGER NOT NULL DEFAULT 0`

Foreign keys:
- `job_id` references `jobs.id`

Row count at inspection time: `81`

## Table: resume_strategy
Columns:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `resume_variant TEXT NOT NULL`
- `cluster TEXT NOT NULL`
- `cluster_summary TEXT NOT NULL`
- `resume_plan_md TEXT NOT NULL`
- `resume_hash TEXT NOT NULL`
- `analysis_version INTEGER NOT NULL`
- `cluster_input_hash TEXT NOT NULL`
- `filter_company TEXT NULL`
- `filter_min_score INTEGER NULL`
- `output_filename TEXT NULL`
- `generated_at TEXT NOT NULL DEFAULT datetime('now')`

Row count at inspection time: `2`

## Type mapping used for MySQL
- `INTEGER` -> `INT`
- `TEXT` -> `TEXT`
- `REAL` -> `FLOAT`
- `DATETIME/TEXT timestamp` -> `DATETIME`
- `BOOLEAN/INTEGER flag` -> `TINYINT(1)` via SQLAlchemy `Boolean`

## Notes on complex fields
- `must_have_keywords`, `nice_to_have_keywords`, `domain_keywords`, `top_gaps`, `screening_risks`, `resume_tweak_suggestions` are JSON-like strings in SQLite and are preserved as `TEXT` in MySQL to avoid data loss.
- `cluster_summary` is also preserved as `TEXT` because the source stores serialized JSON text.