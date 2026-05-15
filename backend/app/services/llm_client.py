from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Generator
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import get_settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)
logger = logging.getLogger(__name__)


class LLMClient:
    _client: OpenAI | None = None
    _client_key: tuple[str, str, float] | None = None

    def __init__(self, model_name: str | None = None) -> None:
        self.settings = get_settings()
        self.model_name = model_name or self.settings.openai_model
        self.last_call_meta: dict[str, object] = {}

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    def client(self) -> OpenAI:
        if not self.is_configured():
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        client_key = (
            self.settings.openai_api_key,
            self.settings.openai_base_url,
            self.settings.openai_timeout_seconds,
        )
        if LLMClient._client is None or LLMClient._client_key != client_key:
            LLMClient._client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                timeout=self.settings.openai_timeout_seconds,
            )
            LLMClient._client_key = client_key
        return LLMClient._client

    def structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[SchemaT],
        temperature: float = 0.2,
    ) -> SchemaT:
        attempts = 0
        errors: list[str] = []
        if self._supports_responses_api():
            attempts += 1
            try:
                return self._structured_output_responses(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema_model=schema_model,
                    temperature=temperature,
                    attempts=attempts,
                )
            except Exception as exc:
                errors.append(f"responses_structured: {exc}")
                if _is_timeout_error(exc):
                    self._record_structured_failure("responses_structured", schema_model, attempts, errors, timed_out=True)
                    raise
                logger.warning("Responses structured output failed; falling back to Chat Completions", exc_info=True)

            attempts += 1
            try:
                return self._structured_output_chat_schema(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema_model=schema_model,
                    temperature=temperature,
                    attempts=attempts,
                )
            except Exception as exc:
                errors.append(f"chat_structured: {exc}")
                if _is_timeout_error(exc):
                    self._record_structured_failure("chat_structured", schema_model, attempts, errors, timed_out=True)
                    raise
                logger.warning("Chat structured output failed; falling back to JSON mode", exc_info=True)

        attempts += 1
        try:
            return self._structured_output_json_legacy(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema_model=schema_model,
                temperature=temperature,
                attempts=attempts,
            )
        except Exception as exc:
            errors.append(f"chat_json_legacy: {exc}")
            self._record_structured_failure("chat_json_legacy", schema_model, attempts, errors, timed_out=_is_timeout_error(exc))
            raise

    def _structured_output_responses(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[SchemaT],
        temperature: float,
        attempts: int,
    ) -> SchemaT:
        start = time.perf_counter()
        response = self.client().responses.create(
            model=self.model_name,
            instructions=system_prompt,
            input=user_prompt,
            temperature=temperature,
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(schema_model),
                    "schema": schema_model.model_json_schema(),
                    "strict": True,
                }
            },
        )
        content = _response_output_text(response)
        result = schema_model.model_validate(_load_json_object(content))
        self._record_call("responses_structured", schema_model, response, start, attempts)
        return result

    def _structured_output_chat_schema(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[SchemaT],
        temperature: float,
        attempts: int,
    ) -> SchemaT:
        start = time.perf_counter()
        response = self.client().chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            store=False,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": _schema_name(schema_model),
                    "schema": schema_model.model_json_schema(),
                    "strict": True,
                },
            },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if not response.choices:
            raise RuntimeError("LLM returned an empty response with no choices.")
        message = response.choices[0].message
        if getattr(message, "refusal", None):
            raise RuntimeError(f"LLM refused structured output: {message.refusal}")
        content = message.content or "{}"
        result = schema_model.model_validate(_load_json_object(content))
        self._record_call("chat_structured", schema_model, response, start, attempts)
        return result

    def _structured_output_json_legacy(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[SchemaT],
        temperature: float,
        attempts: int,
    ) -> SchemaT:
        start = time.perf_counter()
        schema = json.dumps(schema_model.model_json_schema(), ensure_ascii=False)
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{user_prompt}\n\n"
                        f"JSON schema:\n{schema}\n\n"
                        "Return only one JSON object matching this schema."
                    ),
                },
            ],
        }
        if self._is_official_openai_base_url():
            kwargs["store"] = False
        response = self.client().chat.completions.create(**kwargs)  # type: ignore[call-overload]
        if not response.choices:
            raise RuntimeError("LLM returned an empty response with no choices.")
        content = response.choices[0].message.content or "{}"
        result = schema_model.model_validate(_load_json_object(content))
        self._record_call("chat_json_legacy", schema_model, response, start, attempts)
        return result

    def chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> str:
        full_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "temperature": temperature,
            "messages": full_messages,  # type: ignore[arg-type]
        }
        if self._is_official_openai_base_url():
            kwargs["store"] = False
        response = self.client().chat.completions.create(**kwargs)  # type: ignore[call-overload]
        if not response.choices:
            raise RuntimeError("LLM returned an empty response with no choices.")
        return response.choices[0].message.content or ""

    def chat_stream(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> Generator[str, None, None]:
        full_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "temperature": temperature,
            "messages": full_messages,  # type: ignore[arg-type]
            "stream": True,
        }
        if self._is_official_openai_base_url():
            kwargs["store"] = False
        stream = self.client().chat.completions.create(**kwargs)  # type: ignore[call-overload]
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _supports_responses_api(self) -> bool:
        return self._is_official_openai_base_url() and hasattr(self.client(), "responses")

    def _is_official_openai_base_url(self) -> bool:
        return str(self.settings.openai_base_url).rstrip("/") == "https://api.openai.com/v1"

    def _record_call(
        self,
        mode: str,
        schema_model: type[BaseModel],
        response,
        start: float,
        attempts: int,
    ) -> None:
        self.last_call_meta = {
            "mode": mode,
            "model": self.model_name,
            "schema": schema_model.__name__,
            "attempts": attempts,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "usage": _usage_dict(getattr(response, "usage", None)),
        }
        logger.info("LLM structured call completed", extra={"llm_call": self.last_call_meta})

    def _record_structured_failure(
        self,
        mode: str,
        schema_model: type[BaseModel],
        attempts: int,
        errors: list[str],
        *,
        timed_out: bool = False,
    ) -> None:
        self.last_call_meta = {
            "mode": mode,
            "model": self.model_name,
            "schema": schema_model.__name__,
            "attempts": attempts,
            "errors": errors,
            "timed_out": timed_out,
        }


def _schema_name(schema_model: type[BaseModel]) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", schema_model.__name__)[:64] or "StructuredOutput"


def _response_output_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(text)
    if parts:
        return "\n".join(parts)
    raise RuntimeError("LLM returned an empty response.")


def _usage_dict(usage) -> dict | None:
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return dict(getattr(usage, "__dict__", {}))


def _is_timeout_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    return isinstance(exc, TimeoutError) or "timeout" in name or "timed out" in message or "read timed out" in message


def _load_json_object(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        json_object = _extract_json_object(cleaned)
        if not json_object:
            raise
        value = json.loads(json_object)
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object.")
    return value


def _extract_json_object(content: str) -> str | None:
    for start, char in enumerate(content):
        if char != "{":
            continue
        candidate = _balanced_json_from(content, start)
        if not candidate:
            continue
        try:
            json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return candidate
    return None


def _balanced_json_from(content: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]

    return None
