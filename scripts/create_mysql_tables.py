from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import Base
from app.db import models as db_models  # noqa: F401


def resolve_mysql_url() -> str:
    override = os.getenv("DATABASE_URL", "").strip()
    if override:
        return override

    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "jd_user")
    password = os.getenv("MYSQL_PASSWORD", "jd_password")
    database = os.getenv("MYSQL_DATABASE", "jd_matcher")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def create_mysql_tables(mysql_url: str | None = None) -> list[str]:
    engine = create_engine(mysql_url or resolve_mysql_url(), pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    return sorted(inspector.get_table_names())


if __name__ == "__main__":
    tables = create_mysql_tables()
    print("Created or verified tables:")
    for table_name in tables:
        print(f"- {table_name}")