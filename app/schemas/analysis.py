from __future__ import annotations

from pydantic import BaseModel, Field


class JDAnalysisRequest(BaseModel):
    jd_text: str = Field(..., min_length=20, description="Raw job description text")

    model_config = {
        "json_schema_extra": {
            "example": {
                "jd_text": "We need a backend engineer with Python, FastAPI, MySQL, Redis, Docker and API design skills.",
            }
        }
    }


class JDAnalysisResponse(BaseModel):
    cluster: str
    score: float = Field(..., ge=0, le=100)
    matched_keywords: list[str]
    missing_keywords: list[str]
    cache_hit: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "cluster": "backend engineer",
                "score": 72.5,
                "matched_keywords": ["python", "fastapi", "redis", "mysql"],
                "missing_keywords": ["kubernetes", "microservices"],
                "cache_hit": False,
            }
        }
    }
