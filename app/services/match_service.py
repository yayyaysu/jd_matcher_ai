from __future__ import annotations

import re

CLUSTER_SKILLS = {
    "backend engineer": {
        "core": ["python", "api", "sql", "mysql", "redis", "docker"],
        "support": ["fastapi", "flask", "django", "postgresql", "sqlalchemy", "microservices", "kubernetes"],
    },
    "data engineer": {
        "core": ["python", "sql", "etl", "airflow", "spark", "data pipeline"],
        "support": ["kafka", "dbt", "warehouse", "aws", "docker", "pyspark"],
    },
    "ml engineer": {
        "core": ["python", "machine learning", "pytorch", "tensorflow", "scikit-learn", "mlops"],
        "support": ["llm", "rag", "docker", "kubernetes", "api", "aws"],
    },
    "platform engineer": {
        "core": ["linux", "docker", "kubernetes", "terraform", "aws", "ci/cd"],
        "support": ["python", "monitoring", "networking", "observability", "redis", "bash"],
    },
    "fullstack engineer": {
        "core": ["javascript", "typescript", "react", "node.js", "api", "sql"],
        "support": ["next.js", "python", "docker", "redis", "css", "frontend"],
    },
}

KEYWORD_PATTERNS = {
    "python": [r"\bpython\b"],
    "fastapi": [r"\bfastapi\b"],
    "flask": [r"\bflask\b"],
    "django": [r"\bdjango\b"],
    "api": [r"\bapi\b", r"\brest(?:ful)?\b", r"\bapi design\b"],
    "sql": [r"\bsql\b"],
    "mysql": [r"\bmysql\b"],
    "postgresql": [r"\bpostgres(?:ql)?\b"],
    "redis": [r"\bredis\b", r"\bcaching\b", r"\bcache\b"],
    "docker": [r"\bdocker\b", r"\bcontainer(?:s|ized)?\b"],
    "sqlalchemy": [r"\bsqlalchemy\b"],
    "microservices": [r"\bmicroservices?\b"],
    "kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "etl": [r"\betl\b", r"\belt\b"],
    "airflow": [r"\bairflow\b"],
    "spark": [r"\bspark\b"],
    "pyspark": [r"\bpyspark\b"],
    "data pipeline": [r"\bdata pipelines?\b", r"\bpipeline orchestration\b"],
    "kafka": [r"\bkafka\b"],
    "dbt": [r"\bdbt\b"],
    "warehouse": [r"\bwarehouse\b", r"\bdata warehouse\b"],
    "aws": [r"\baws\b", r"\bamazon web services\b"],
    "machine learning": [r"\bmachine learning\b", r"\bml\b"],
    "pytorch": [r"\bpytorch\b"],
    "tensorflow": [r"\btensorflow\b"],
    "scikit-learn": [r"\bscikit-learn\b", r"\bsklearn\b"],
    "mlops": [r"\bmlops\b"],
    "llm": [r"\bllms?\b", r"\blarge language models?\b"],
    "rag": [r"\brag\b", r"\bretrieval augmented generation\b"],
    "linux": [r"\blinux\b"],
    "terraform": [r"\bterraform\b"],
    "ci/cd": [r"\bci/cd\b", r"\bcicd\b", r"\bcontinuous integration\b", r"\bcontinuous delivery\b"],
    "monitoring": [r"\bmonitoring\b", r"\bprometheus\b", r"\bgrafana\b"],
    "networking": [r"\bnetworking\b", r"\bnetwork\b"],
    "observability": [r"\bobservability\b", r"\btracing\b", r"\blogging\b"],
    "bash": [r"\bbash\b", r"\bshell scripting\b"],
    "javascript": [r"\bjavascript\b"],
    "typescript": [r"\btypescript\b"],
    "react": [r"\breact\b"],
    "node.js": [r"\bnode(?:\.js)?\b"],
    "next.js": [r"\bnext(?:\.js)?\b"],
    "css": [r"\bcss\b", r"\bhtml\b"],
    "frontend": [r"\bfrontend\b", r"\bfront-end\b", r"\bui\b"],
}

STOP_WORDS = {
    "with",
    "and",
    "the",
    "for",
    "you",
    "will",
    "have",
    "are",
    "our",
    "your",
    "from",
    "this",
    "that",
    "into",
    "experience",
    "years",
    "work",
    "team",
    "engineering",
}


def analyze_jd_text(jd_text: str) -> dict[str, object]:
    normalized_text = normalize_jd_text(jd_text)
    extracted_keywords = extract_keywords(normalized_text)

    best_cluster = "backend engineer"
    best_match: dict[str, object] | None = None
    for cluster_name, cluster_skills in CLUSTER_SKILLS.items():
        current_match = compute_match(extracted_keywords, cluster_skills)
        if best_match is None or float(current_match["score"]) > float(best_match["score"]):
            best_cluster = cluster_name
            best_match = current_match

    assert best_match is not None
    return {
        "normalized_text": normalized_text,
        "extracted_keywords": extracted_keywords,
        "cluster": best_cluster,
        "score": best_match["score"],
        "matched_keywords": best_match["matched_keywords"],
        "missing_keywords": best_match["missing_keywords"],
    }


def normalize_jd_text(jd_text: str) -> str:
    text = jd_text.replace("\r", " ").replace("\n", " ").lower()
    text = re.sub(r"[^a-z0-9\+\.#/\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(normalized_text: str) -> list[str]:
    extracted: list[str] = []
    for keyword, patterns in KEYWORD_PATTERNS.items():
        if any(re.search(pattern, normalized_text) for pattern in patterns):
            extracted.append(keyword)

    tokens = re.findall(r"[a-z][a-z0-9\-\+\.]{1,30}", normalized_text)
    for token in tokens:
        if token in STOP_WORDS or token in extracted:
            continue
        extracted.append(token)

    return extracted[:40]


def compute_match(extracted_keywords: list[str], cluster_skills: dict[str, list[str]]) -> dict[str, object]:
    extracted_set = {keyword.lower() for keyword in extracted_keywords}
    core_skills = cluster_skills["core"]
    support_skills = cluster_skills["support"]

    matched_core = [keyword for keyword in core_skills if keyword.lower() in extracted_set]
    matched_support = [keyword for keyword in support_skills if keyword.lower() in extracted_set]
    missing_core = [keyword for keyword in core_skills if keyword.lower() not in extracted_set]
    missing_support = [keyword for keyword in support_skills if keyword.lower() not in extracted_set]

    core_score = len(matched_core) / len(core_skills) if core_skills else 0
    support_score = len(matched_support) / len(support_skills) if support_skills else 0
    score = round((core_score * 0.7 + support_score * 0.3) * 100, 2)

    return {
        "score": score,
        "matched_keywords": matched_core + matched_support,
        "missing_keywords": (missing_core + missing_support)[:8],
    }
