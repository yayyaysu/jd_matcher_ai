from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "JD Matcher v2 API"
    app_version: str = "0.1.0"

    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "jd_user"
    mysql_password: str = "jd_password"
    mysql_database: str = "jd_matcher"

    redis_url: str = "redis://redis:6379/0"

    cache_ttl_seconds: int = 3600
    analysis_version: int = 1

    openai_api_key: str = ""
    parser_model: str = "gpt-4.1-mini"
    strategist_model: str = "gpt-4.1-mini"

    resume_path: str = "resume.txt"
    outputs_dir: str = "data/outputs"

    @property
    def database_url(self) -> str:
        override = os.getenv("DATABASE_URL", "").strip()
        if override:
            return override
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def prompt_dir(self) -> Path:
        return self.project_root / "app" / "prompts"

    @property
    def outputs_path(self) -> Path:
        path = Path(self.outputs_dir)
        if not path.is_absolute():
            path = self.project_root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_output_path(self, filename: str) -> Path:
        return self.outputs_path / filename

    @property
    def resolved_resume_path(self) -> Path:
        configured = Path(self.resume_path)
        candidates: list[Path] = []
        if configured.is_absolute():
            candidates.append(configured)
        else:
            candidates.extend(
                [
                    self.project_root / configured,
                    self.project_root.parent / "jd-matcher" / configured,
                    Path("/legacy/jd-matcher") / configured,
                ]
            )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[0]

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
