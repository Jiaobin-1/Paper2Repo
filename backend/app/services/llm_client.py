from __future__ import annotations

import json
import re
from collections.abc import Generator
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import get_settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMClient:
    _client: OpenAI | None = None

    def __init__(self, model_name: str | None = None) -> None:
        self.settings = get_settings()
        self.model_name = model_name or self.settings.openai_model

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    def client(self) -> OpenAI:
        if not self.is_configured():
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if LLMClient._client is None:
            LLMClient._client = OpenAI(api_key=self.settings.openai_api_key, base_url=self.settings.openai_base_url)
        return LLMClient._client

    def structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[SchemaT],
        temperature: float = 0.2,
    ) -> SchemaT:
        schema = json.dumps(schema_model.model_json_schema(), ensure_ascii=False)
        response = self.client().chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
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
        )
        if not response.choices:
            raise RuntimeError("LLM returned an empty response with no choices.")
        content = response.choices[0].message.content or "{}"
        return schema_model.model_validate(_load_json_object(content))

    def chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> str:
        full_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)
        response = self.client().chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=full_messages,  # type: ignore[arg-type]
        )
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
        stream = self.client().chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=full_messages,  # type: ignore[arg-type]
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


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
