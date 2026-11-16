from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Invoice IQ"
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    DATABASE_URL: str = "sqlite:///./data/documind.db"

    # Authentication & Security
    SECRET_KEY: str = "invoice_iq_enterprise_jwt_secret_key_2026_dev_env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Filesystem Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    UPLOAD_DIR: Path = Path("./data/uploads")
    PROCESSED_PAGES_DIR: Path = Path("./data/processed_pages")
    ML_ARTIFACTS_DIR: Path = Path("./ml/artifacts")

    # Business & Model Thresholds
    CONFIDENCE_THRESHOLD: float = Field(default=0.80, ge=0.0, le=1.0)
    ANOMALY_CONTAMINATION: float = Field(default=0.05, gt=0.0, lt=0.5)
    MAX_UPLOAD_SIZE_MB: int = Field(default=15, gt=0, le=50)
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "png", "jpg", "jpeg"]

    @field_validator("UPLOAD_DIR", "PROCESSED_PAGES_DIR", "ML_ARTIFACTS_DIR", mode="after")
    @classmethod
    def resolve_and_create_dir(cls, v: Path) -> Path:
        resolved = v.resolve() if v.is_absolute() else (Path.cwd() / v).resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()

