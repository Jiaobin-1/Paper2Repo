from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _resolve_backend_path(value: str) -> Path:
    path_str = str(value)
    for prefix in ("sqlite:///", "sqlite://", "sqlite:/"):
        if path_str.startswith(prefix):
            path_str = path_str[len(prefix):]
            break
    path = Path(path_str)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_model_options: str = ""

    database_url: str = "sqlite:///./data/paper2repo.db"
    upload_dir: str = "./storage/uploads"
    report_dir: str = "./storage/reports"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        return _resolve_backend_path(self.database_url)

    @property
    def upload_path(self) -> Path:
        return _resolve_backend_path(self.upload_dir)

    @property
    def report_path(self) -> Path:
        return _resolve_backend_path(self.report_dir)

    @property
    def available_openai_models(self) -> list[str]:
        models: list[str] = []
        for raw_model in self.openai_model_options.split(","):
            model = raw_model.strip()
            if model and model not in models:
                models.append(model)
        default_model = self.openai_model.strip()
        if default_model and default_model not in models:
            models.insert(0, default_model)
        return models or ["gpt-4o-mini"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
