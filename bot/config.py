"""Configuration management for the sentiment bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    DISCORD_TOKEN: str = os.environ.get("DISCORD_BOT_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    DATABASE_PATH: str = os.environ.get("DATABASE_PATH", "sentiment.db")
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"
    MAX_TOKENS: int = 1000
    SUMMARY_HOUR: int = 8
    SUMMARY_TIMEZONE: str = "America/New_York"
    MONITORED_APPS: list[str] = ["cora", "spiral", "sparkle", "monologue"]
    MONITORED_CHANNEL_IDS: set[str] = {
        "1019678288618205294",
        "821856844137758730",
        "797477569195671592",
        "1389667062569242644",
        "1395804083801165895",
        "1393267393928630473",
        "1395804228336750672",
        "1395804148825329777",
        "1466104194644836620",
    }

    @classmethod
    def validate(cls) -> None:
        errors = []
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_BOT_TOKEN environment variable is required")
        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY environment variable is required")
        if errors:
            raise ValueError("\n".join(errors))

    @classmethod
    def get_database_path(cls) -> Path:
        db_path = Path(cls.DATABASE_PATH)
        if not db_path.is_absolute():
            db_path = Path(__file__).parent.parent / db_path
        return db_path
