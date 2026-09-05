from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "supersecretkeythatshouldbechangedinproduction"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DATABASE_URL: str = "sqlite:///./payloom.db"

    # Optional — the AI layer (PayTrace AI Narrator, Phase 7B; Payloom
    # Intelligence, Phase 10). Entirely optional: when the active provider's
    # key is unset every AI endpoint returns `available: False` and every
    # deterministic system (payroll engine, PayTrace, Preflight, Simulator)
    # is completely unaffected. See app/services/ai_provider.py.
    # One provider at a time — AI_PROVIDER selects it ("gemini" | "anthropic").
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()
