from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "supersecretkeythatshouldbechangedinproduction"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DATABASE_URL: str = "sqlite:///./payloom.db"

    # Optional — PayTrace AI Narrator (Phase 7B). Entirely optional: when
    # unset, the narrator endpoint returns `available: False` and the
    # deterministic PayTrace is unaffected. See app/services/payroll_narrator.py.
    ANTHROPIC_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()
