from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class ParserAIResult(BaseModel):
    company: str = ""
    role_title: str = ""
    cluster: Literal["A", "B", "C1", "C2", "Other"]
    fit_score: int = Field(ge=0, le=100)
    cluster_reason: str
    must_have_keywords: list[str] = Field(default_factory=list, max_length=10)
    nice_to_have_keywords: list[str] = Field(default_factory=list, max_length=8)
    domain_keywords: list[str] = Field(default_factory=list, max_length=6)
    years_required: Literal["0", "1-3", "3-5", "5+"]
    top_gaps: list[str] = Field(
        default_factory=list,
        max_length=3,
        validation_alias=AliasChoices("top_gaps", "gap_keywords"),
    )
    screening_risks: list[str] = Field(default_factory=list, max_length=3)
    recommended_resume_version: Literal["V1", "V2", "V3"]
    resume_tweak_suggestions: list[str] = Field(default_factory=list, max_length=5)


class StrategistAIResult(BaseModel):
    cluster_summary: dict
    resume_variant: Literal["A_resume", "B_resume", "C1_resume", "C2_resume"]
    positioning_sentence: str
    keyword_additions: list[str] = Field(min_length=8, max_length=12)
    bullets: list[str] = Field(min_length=6, max_length=6)
    actionable_checklist: list[str] = Field(min_length=5, max_length=5)
    notes: list[str] = Field(default_factory=list, max_length=5)