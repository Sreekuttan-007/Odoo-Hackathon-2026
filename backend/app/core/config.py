from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "supersecretkeythatshouldbechangedinproduction"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DATABASE_URL: str = "sqlite:///./payloom.db"

    # Optional — the AI layer (PayTrace AI Narrator, Phase 7B; Payloom
    # Intelligence, Phase 10). Entirely optional: when ANTHROPIC_API_KEY is
    # unset every AI endpoint returns `available: False` and every
    # deterministic system (payroll engine, PayTrace, Preflight, Simulator)
    # is completely unaffected. See app/services/payroll_narrator.py and
    # app/services/intelligence.py.
    AI_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()
