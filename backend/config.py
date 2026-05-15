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

    # Comma-separated list of allowed child names (case-insensitive).
    # Children enter by typing their name only; any name on this list creates
    # or recovers their user row. Edit via Railway env var to add/remove.
    ALLOWED_CHILDREN: str = "Samihan"

    @property
    def allowed_children_list(self) -> list[str]:
        return [n.strip() for n in self.ALLOWED_CHILDREN.split(",") if n.strip()]


settings = Settings()
