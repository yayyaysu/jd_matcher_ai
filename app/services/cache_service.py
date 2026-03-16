from __future__ import annotations

import hashlib
import json
from typing import Any

from app.cache.redis_client import get_redis_client
from app.core.config import settings


class CacheService:
    async def get_json(self, key: str) -> dict[str, Any] | None:
        cached = await get_redis_client().get(key)
        if not cached:
            return None
        return json.loads(cached)

    async def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
        await get_redis_client().set(key, json.dumps(payload, ensure_ascii=False), ex=ttl)

    async def get_analysis(self, jd_text: str) -> dict | None:
        key = self._build_key(jd_text)
        return await self.get_json(key)

    async def set_analysis(self, jd_text: str, payload: dict) -> None:
        key = self._build_key(jd_text)
        await self.set_json(key, payload)

    @staticmethod
    def build_parser_key(job_id: str, resume_hash: str, analysis_version: int) -> str:
        return f"parser:{job_id}:{analysis_version}:{resume_hash}"

    @staticmethod
    def build_strategy_key(
        cluster: str,
        resume_hash: str,
        analysis_version: int,
        cluster_input_hash: str,
        filter_company: str | None,
        filter_min_score: int | None,
    ) -> str:
        company_token = (filter_company or "*").strip().lower() or "*"
        min_score_token = "*" if filter_min_score is None else str(filter_min_score)
        return (
            f"strategy:{cluster}:{analysis_version}:{resume_hash}:"
            f"{company_token}:{min_score_token}:{cluster_input_hash}"
        )

    @staticmethod
    def _build_key(jd_text: str) -> str:
        digest = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
        return f"jd_analysis:{digest}"
