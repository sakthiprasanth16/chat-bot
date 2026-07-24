"""
Centralized configuration, loaded from environment variables (.env file).
Using pydantic-settings so every value is validated once at startup instead
of being read ad-hoc with os.environ across the codebase.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Gemini ---
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"

    # --- MongoDB Atlas ---
    mongodb_uri: str
    mongodb_db_name: str = "chatbot_v1"

    # --- App ---
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    # --- Guardrails (Phase 4) ---
    # Toggle for the local regex/keyword jailbreak pre-check that runs
    # before a message is sent to Gemini. Hardened system prompt + Gemini
    # safety_settings stay on regardless of this flag.
    enable_jailbreak_precheck: bool = True

    # --- Rolling summarization ---
    # Once (summary + raw messages) exceeds this many tokens, the older
    # portion gets folded into the rolling summary via a Gemini call.
    summary_token_threshold: int = 3000
    # How many of the most recent raw messages to always keep verbatim
    # (never summarized) — these plus the summary form the Gemini prompt.
    keep_recent_messages: int = 3
    # Target length instruction given to Gemini for each summary pass.
    summary_target_words: int = 150

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Single shared instance imported across the app.
settings = Settings()
