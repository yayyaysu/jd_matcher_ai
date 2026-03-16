from __future__ import annotations

PARSER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "company": {"type": "string"},
        "role_title": {"type": "string"},
        "cluster": {
            "type": "string",
            "enum": ["A", "B", "C1", "C2", "Other"],
        },
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "cluster_reason": {"type": "string"},
        "must_have_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 10,
        },
        "nice_to_have_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
        "domain_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
        "years_required": {
            "type": "string",
            "enum": ["0", "1-3", "3-5", "5+"],
        },
        "top_gaps": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "screening_risks": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "recommended_resume_version": {
            "type": "string",
            "enum": ["V1", "V2", "V3"],
        },
        "resume_tweak_suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
    },
    "required": [
        "company",
        "role_title",
        "cluster",
        "fit_score",
        "cluster_reason",
        "must_have_keywords",
        "nice_to_have_keywords",
        "domain_keywords",
        "years_required",
        "top_gaps",
        "screening_risks",
        "recommended_resume_version",
        "resume_tweak_suggestions",
    ],
}

CLUSTER_SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "top_must_haves": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "keyword": {"type": "string"},
                    "count": {"type": "integer", "minimum": 1},
                },
                "required": ["keyword", "count"],
            },
            "maxItems": 15,
        },
        "top_domains": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "keyword": {"type": "string"},
                    "count": {"type": "integer", "minimum": 1},
                },
                "required": ["keyword", "count"],
            },
            "maxItems": 10,
        },
        "top_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "keyword": {"type": "string"},
                    "count": {"type": "integer", "minimum": 1},
                },
                "required": ["keyword", "count"],
            },
            "maxItems": 8,
        },
    },
    "required": ["top_must_haves", "top_domains", "top_gaps"],
}

STRATEGIST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "cluster_summary": CLUSTER_SUMMARY_SCHEMA,
        "resume_variant": {
            "type": "string",
            "enum": ["A_resume", "B_resume", "C1_resume", "C2_resume"],
        },
        "positioning_sentence": {"type": "string"},
        "keyword_additions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 8,
            "maxItems": 12,
        },
        "bullets": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 6,
            "maxItems": 6,
        },
        "actionable_checklist": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5,
        },
        "notes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 0,
            "maxItems": 5,
        },
    },
    "required": [
        "cluster_summary",
        "resume_variant",
        "positioning_sentence",
        "keyword_additions",
        "bullets",
        "actionable_checklist",
        "notes",
    ],
}