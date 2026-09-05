from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "supersecretkeythatshouldbechangedinproduction"
    CORS_ORIGINS: str = "http://localhost:5173"
    DATABASE_URL: str = "sqlite:///./payloom.db"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()
