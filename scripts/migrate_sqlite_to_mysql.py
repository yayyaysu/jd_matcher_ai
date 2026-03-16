from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, and_, create_engine, func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from create_mysql_tables import create_mysql_tables, resolve_mysql_url


SQLITE_TABLE_ORDER = ["jobs", "workflow", "job_analysis", "resume_strategy"]
DATETIME_COLUMNS = {
    "jobs": {"created_at"},
    "workflow": {"applied_date", "updated_at"},
    "job_analysis": {"created_at"},
    "resume_strategy": {"generated_at"},
}
BOOLEAN_COLUMNS = {"workflow": {"applied"}}
PRIMARY_KEYS = {
    "jobs": ["id"],
    "workflow": ["job_id"],
    "job_analysis": ["job_id", "analysis_version"],
    "resume_strategy": ["id"],
}


def detect_sqlite_path(explicit_path: str | None = None) -> Path:
    if explicit_path:
        sqlite_path = Path(explicit_path).resolve()
        if sqlite_path.exists():
            return sqlite_path
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    project_root = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    search_roots = [
        project_root.parent / "jd-matcher" / "data",
        project_root.parent / "jd-matcher",
        Path("/legacy/jd-matcher/data"),
        Path("/legacy/jd-matcher"),
    ]
    for search_root in search_roots:
        if search_root.exists() and search_root.is_dir():
            candidates.extend(sorted(search_root.glob("*.db")))
    if not candidates:
        raise FileNotFoundError("No SQLite database found under jd-matcher/data or jd-matcher root")
    return candidates[0]


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return datetime.fromisoformat(text)


def normalize_value(table_name: str, column_name: str, value: Any) -> Any:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    if column_name in DATETIME_COLUMNS.get(table_name, set()):
        return parse_datetime(value)
    if column_name in BOOLEAN_COLUMNS.get(table_name, set()):
        return bool(value)
    return value


def connect_sqlite(sqlite_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def load_sqlite_rows(conn: sqlite3.Connection, table_name: str) -> list[dict[str, Any]]:
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(row) for row in rows]


def row_exists(mysql_conn, table, record: dict[str, Any], pk_columns: list[str]) -> bool:
    condition = and_(*[table.c[column] == record[column] for column in pk_columns])
    stmt = select(func.count()).select_from(table).where(condition)
    return bool(mysql_conn.execute(stmt).scalar())


def migrate_table(sqlite_conn: sqlite3.Connection, mysql_conn, metadata: MetaData, table_name: str) -> tuple[int, int]:
    table = metadata.tables[table_name]
    pk_columns = PRIMARY_KEYS[table_name]
    migrated = 0
    skipped = 0

    for raw_record in load_sqlite_rows(sqlite_conn, table_name):
        record = {
            column_name: normalize_value(table_name, column_name, raw_record.get(column_name))
            for column_name in table.c.keys()
            if column_name in raw_record
        }

        if row_exists(mysql_conn, table, record, pk_columns):
            skipped += 1
            continue

        mysql_conn.execute(table.insert().values(**record))
        migrated += 1

    return migrated, skipped


def safe_json_loads(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def dedupe_strings(values: list[str]) -> list[str]:
    output: list[str] = []
    seen = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def load_analysis_records_from_sqlite(sqlite_conn: sqlite3.Connection) -> list[dict[str, Any]]:
    sqlite_tables = set(load_sqlite_tables(sqlite_conn))
    if "job_analysis" not in sqlite_tables:
        jobs_rows = load_sqlite_rows(sqlite_conn, "jobs")
        return [
            {
                "jd_text": row["jd_text"],
                "matched_keywords": [],
                "missing_keywords": [],
                "score": 0.0,
                "cluster": "C2",
                "created_at": normalize_value("jobs", "created_at", row.get("created_at")),
            }
            for row in jobs_rows
        ]

    query = """
    SELECT
        j.jd_text,
        ja.cluster,
        ja.fit_score,
        ja.must_have_keywords,
        ja.domain_keywords,
        ja.top_gaps,
        COALESCE(ja.created_at, j.created_at) AS created_at
    FROM job_analysis ja
    JOIN jobs j ON j.id = ja.job_id
    ORDER BY COALESCE(ja.created_at, j.created_at), ja.job_id, ja.analysis_version
    """
    rows = sqlite_conn.execute(query).fetchall()

    output = []
    for row in rows:
        matched_keywords = dedupe_strings(
            safe_json_loads(row["must_have_keywords"]) + safe_json_loads(row["domain_keywords"])
        )
        missing_keywords = dedupe_strings(safe_json_loads(row["top_gaps"]))
        missing_set = {value.lower() for value in missing_keywords}
        matched_keywords = [value for value in matched_keywords if value.lower() not in missing_set]

        output.append(
            {
                "jd_text": row["jd_text"],
                "matched_keywords": matched_keywords,
                "missing_keywords": missing_keywords,
                "score": float(row["fit_score"] or 0),
                "cluster": row["cluster"] or "C2",
                "created_at": normalize_value("job_analysis", "created_at", row["created_at"]),
            }
        )
    return output


def analysis_record_exists(mysql_conn, table, record: dict[str, Any]) -> bool:
    stmt = (
        select(func.count())
        .select_from(table)
        .where(table.c.jd_text == record["jd_text"])
        .where(table.c.cluster == record["cluster"])
        .where(table.c.score == record["score"])
        .where(table.c.created_at == record["created_at"])
    )
    return bool(mysql_conn.execute(stmt).scalar())


def count_matching_analysis_records(mysql_conn, table, rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if analysis_record_exists(mysql_conn, table, row))


def migrate_analysis_records(sqlite_conn: sqlite3.Connection, mysql_conn, metadata: MetaData) -> tuple[int, int, int]:
    table = metadata.tables["analysis_records"]
    rows = load_analysis_records_from_sqlite(sqlite_conn)
    migrated = 0
    skipped = 0

    for row in rows:
        if analysis_record_exists(mysql_conn, table, row):
            skipped += 1
            continue

        mysql_conn.execute(table.insert().values(**row))
        migrated += 1

    return len(rows), migrated, skipped


def write_validation_report(sqlite_conn: sqlite3.Connection, mysql_conn, metadata: MetaData, report_path: Path) -> None:
    lines = ["# Migration Validation", ""]

    for table_name in SQLITE_TABLE_ORDER:
        sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"]
        mysql_count = mysql_conn.execute(select(func.count()).select_from(metadata.tables[table_name])).scalar()
        lines.append(f"SQLite {table_name} rows: {sqlite_count}")
        lines.append(f"MySQL {table_name} rows: {mysql_count}")
        lines.append("")

    derived_rows = load_analysis_records_from_sqlite(sqlite_conn)
    derived_sqlite_count = len(derived_rows)
    matching_analysis_count = count_matching_analysis_records(mysql_conn, metadata.tables["analysis_records"], derived_rows)
    mysql_analysis_total = mysql_conn.execute(select(func.count()).select_from(metadata.tables["analysis_records"])).scalar()
    lines.append(f"SQLite derived analysis_records rows: {derived_sqlite_count}")
    lines.append(f"MySQL matching legacy-derived analysis_records rows: {matching_analysis_count}")
    lines.append(f"MySQL total analysis_records rows: {mysql_analysis_total}")
    lines.append("")

    sample_jobs = mysql_conn.execute(
        select(metadata.tables["jobs"].c.id, metadata.tables["jobs"].c.company)
        .order_by(metadata.tables["jobs"].c.created_at)
        .limit(3)
    ).fetchall()
    lines.append("Sample jobs records:")
    for row in sample_jobs:
        lines.append(f"- id={row.id}, company={row.company}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def migrate(sqlite_path: Path, mysql_url: str) -> None:
    create_mysql_tables(mysql_url)
    sqlite_conn = connect_sqlite(sqlite_path)
    mysql_engine = create_engine(mysql_url, pool_pre_ping=True)
    metadata = MetaData()
    metadata.reflect(bind=mysql_engine)

    try:
        with mysql_engine.begin() as mysql_conn:
            for table_name in SQLITE_TABLE_ORDER:
                print(f"Migrating table {table_name}...")
                migrated, skipped = migrate_table(sqlite_conn, mysql_conn, metadata, table_name)
                print(f"Rows migrated: {migrated}")
                print(f"Rows skipped: {skipped}")

            print("Migrating table analysis_records...")
            source_rows, migrated, skipped = migrate_analysis_records(sqlite_conn, mysql_conn, metadata)
            print(f"Source rows: {source_rows}")
            print(f"Rows migrated: {migrated}")
            print(f"Rows skipped: {skipped}")

            report_path = Path(__file__).resolve().parents[1] / "docs" / "migration_validation.md"
            write_validation_report(sqlite_conn, mysql_conn, metadata, report_path)
            print(f"Validation report written to: {report_path}")
    finally:
        sqlite_conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate legacy SQLite data into MySQL for JD Matcher v2")
    parser.add_argument("--sqlite-path", default=None, help="Optional explicit path to the legacy SQLite database")
    parser.add_argument("--mysql-url", default=resolve_mysql_url(), help="Target MySQL SQLAlchemy URL")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    migrate(detect_sqlite_path(args.sqlite_path), args.mysql_url)
