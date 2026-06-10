from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://quest:quest@localhost:5432/quest"
    ANTHROPIC_API_KEY: str = "sk-ant-PLACEHOLDER"
    JWT_SECRET: str = "1123"
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    JWT_ALG: str = "HS256"
    JWT_EXPIRY_DAYS: int = 7

    PARENT_EMAIL: str = "parent@quest-academy.app"
    PARENT_PASSWORD: str = "changeme123"
    PARENT_NAME: str = "Dad"
    CHILD_NAME: str = "Samihan"
    CHILD_EMAIL: str = "child@quest-academy.app"

    # Comma-separated allowlist. Each entry is `Name` or `Name:year_level`,
    # e.g. "Samihan:3,Anvi:4". year_level drives the difficulty floor so an
    # older sibling never gets baby-easy questions. Bare name defaults to
    # Year 3 for backward compatibility.
    ALLOWED_CHILDREN: str = "Samihan"

    @property
    def allowed_children_list(self) -> list[str]:
        return [name for name, _ in self.allowed_children_dict.items()]

    @property
    def allowed_children_dict(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for entry in self.ALLOWED_CHILDREN.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                name, raw = entry.split(":", 1)
                try:
                    out[name.strip()] = int(raw.strip())
                except ValueError:
                    out[name.strip()] = 3
            else:
                out[entry] = 3
        return out


settings = Settings()
