from __future__ import annotations

import json
import re
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import get_settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    def client(self) -> OpenAI:
        if not self.is_configured():
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        return OpenAI(api_key=self.settings.openai_api_key, base_url=self.settings.openai_base_url)

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
            model=self.settings.openai_model,
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
        content = response.choices[0].message.content or "{}"
        return schema_model.model_validate(_load_json_object(content))


def _load_json_object(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object.")
    return value
