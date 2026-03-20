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
        payload, _ = self.generate_json_with_metadata(
            model=model,
            system_prompt=system_prompt,
            user_content=user_content,
            schema=schema,
            schema_name=schema_name,
            pipeline_type=pipeline_type,
            max_output_tokens=max_output_tokens,
        )
        return payload

    @retry(
        exceptions=(RateLimitError, APIError, APIConnectionError, APITimeoutError, InternalServerError),
        max_attempts=4,
        base_delay=1.5,
    )
    def generate_json_with_metadata(
        self,
        *,
        model: str,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
        schema_name: str,
        pipeline_type: str,
        max_output_tokens: int = 800,
    ) -> tuple[dict[str, Any], dict[str, int]]:
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
        token_usage = self._extract_token_usage(response)
        self._record_token_usage(token_usage, pipeline_type, model)

        parsed = self._extract_parsed_from_response(response)
        if parsed is not None:
            return parsed, token_usage

        output_text = response.output_text or self._extract_text_from_response(response)
        if not output_text:
            raise RuntimeError("Empty response from OpenAI")

        try:
            return json.loads(output_text), token_usage
        except json.JSONDecodeError:
            cleaned = self._sanitize_json_text(output_text)
            try:
                return json.loads(cleaned), token_usage
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

    def _record_token_usage(self, token_usage: dict[str, int], pipeline_type: str, model: str) -> None:
        try:
            input_tokens = token_usage["input_tokens"]
            output_tokens = token_usage["output_tokens"]
            total_tokens = token_usage["total_tokens"]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} {pipeline_type} {model} {input_tokens} {output_tokens} {total_tokens}\n"
            with self._token_log_file.open("a", encoding="utf-8") as handle:
                handle.write(log_entry)
        except Exception:
            pass

    @staticmethod
    def _extract_token_usage(response: Any) -> dict[str, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

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