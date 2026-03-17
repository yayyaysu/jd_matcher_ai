from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from openai import OpenAI
from openai._exceptions import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from app.core.config import settings
from app.utils.retry import retry


class OpenAIClient:
    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = (api_key or settings.openai_api_key).strip()
        if not resolved_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        self._client = OpenAI(api_key=resolved_key)
        self._token_log_file = settings.logs_path / "openai_usage.txt"
        self._token_log_file.parent.mkdir(parents=True, exist_ok=True)

    @retry(
        exceptions=(RateLimitError, APIError, APIConnectionError, APITimeoutError, InternalServerError),
        max_attempts=4,
        base_delay=1.5,
    )
    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
        schema_name: str,
        pipeline_type: str,
        max_output_tokens: int = 800,
    ) -> dict[str, Any]:
        response = self._client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
            max_output_tokens=max_output_tokens,
        )
        self._record_token_usage(response, pipeline_type, model)

        parsed = self._extract_parsed_from_response(response)
        if parsed is not None:
            return parsed

        output_text = response.output_text or self._extract_text_from_response(response)
        if not output_text:
            raise RuntimeError("Empty response from OpenAI")

        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            cleaned = self._sanitize_json_text(output_text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                snippet = cleaned[:200].replace("\n", " ")
                raise RuntimeError(f"Failed to parse JSON from OpenAI response. Snippet: {snippet}") from exc

    @staticmethod
    def _extract_text_from_response(response: Any) -> str:
        try:
            for item in getattr(response, "output", []) or []:
                for content in getattr(item, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        return text
        except Exception:
            return ""
        return ""

    @staticmethod
    def _extract_parsed_from_response(response: Any) -> dict[str, Any] | None:
        try:
            for item in getattr(response, "output", []) or []:
                for content in getattr(item, "content", []) or []:
                    parsed = getattr(content, "parsed", None)
                    if isinstance(parsed, dict):
                        return parsed
        except Exception:
            return None
        return None

    def _record_token_usage(self, response: Any, pipeline_type: str, model: str) -> None:
        try:
            usage = getattr(response, "usage", None)
            if usage is None:
                return
            input_tokens = getattr(usage, "input_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} {pipeline_type} {model} {input_tokens} {output_tokens} {total_tokens}\n"
            with self._token_log_file.open("a", encoding="utf-8") as handle:
                handle.write(log_entry)
        except Exception:
            pass

    @staticmethod
    def _sanitize_json_text(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]
        return cleaned