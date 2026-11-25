from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEV_JWT_SECRET = "neurolearn_insecure_dev_secret_change_in_production_key_32bytes"


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroLearn API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"  # "development", "staging", "production", "test"
    DEBUG: bool = True

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # JWT & Authentication configuration
    # In production, set JWT_SECRET via environment variable!
    # e.g.: python -c "import secrets; print(secrets.token_urlsafe(32))"
    JWT_SECRET: str = INSECURE_DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for development; recommend 60-120 in production

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            import json
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return [v]
            return v
        raise ValueError(v)

    # Database: SQLite fallback for zero-setup local dev, PostgreSQL ready for production
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./neurolearn.db"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env_lower = self.ENVIRONMENT.strip().lower()
        is_production = env_lower in ("production", "prod")

        if is_production:
            # 1. Debug mode MUST be disabled in production
            if self.DEBUG:
                raise ValueError(
                    "Invalid production configuration: DEBUG mode cannot be enabled in production environment."
                )

            # 2. JWT Secret MUST NOT be the default insecure dev secret
            if self.JWT_SECRET == INSECURE_DEV_JWT_SECRET:
                raise ValueError(
                    "Invalid production configuration: JWT_SECRET must be explicitly set and cannot use the development fallback key."
                )

            # 3. JWT Secret MUST have at least 32 bytes (entropy check)
            if len(self.JWT_SECRET.encode("utf-8")) < 32:
                raise ValueError(
                    "Invalid production configuration: JWT_SECRET must be at least 32 bytes in length for HS256 security."
                )

            # 4. CORS validation for production: wildcards not permitted with credentials
            for origin in self.BACKEND_CORS_ORIGINS:
                if origin.strip() == "*":
                    raise ValueError(
                        "Invalid production configuration: BACKEND_CORS_ORIGINS cannot contain wildcard '*' when credentials are enabled."
                    )
                if not (origin.startswith("http://") or origin.startswith("https://")):
                    raise ValueError(
                        f"Invalid production configuration: CORS origin '{origin}' must begin with http:// or https://"
                    )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
