from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NIBGPT"
    app_version: str = "1.0.0"
    app_env: str = "development"

    database_host: str
    database_port: int = 5432
    database_name: str
    database_user: str
    database_password: str

    secret_key: str
    access_token_expire_minutes: int = 60

    data_source_encryption_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.database_user}:"
            f"{self.database_password}@{self.database_host}:"
            f"{self.database_port}/{self.database_name}"
        )


settings = Settings()
