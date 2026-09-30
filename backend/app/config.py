import os
from dataclasses import dataclass
from pathlib import Path


INSTANCE_DIR = Path(__file__).resolve().parents[1] / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'impact_ledger_v2.db'}")
    jwt_secret: str = os.getenv("JWT_SECRET", "local-development-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_minutes: int = int(os.getenv("JWT_MINUTES", "480"))
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin-demo")
    viewer_password: str = os.getenv("VIEWER_PASSWORD", "viewer-demo")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    anthropic_timeout: float = float(os.getenv("ANTHROPIC_TIMEOUT", "12"))
    k_anonymity_threshold: int = int(os.getenv("K_ANONYMITY_THRESHOLD", "3"))
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5173")


settings = Settings()
