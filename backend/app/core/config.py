from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_debug: bool = True
    app_url: str = "http://localhost:8080"
    secret_key: str = "change-me"
    csrf_secret_key: str = "change-me"

    postgres_user: str = "plombir"
    postgres_password: str = "change-me"
    postgres_db: str = "plombirclub"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str = "postgresql+asyncpg://plombir:change-me@postgres:5432/plombirclub"
    database_url_sync: str = "postgresql://plombir:change-me@postgres:5432/plombirclub"

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_access_cookie_name: str = "access_token"
    jwt_refresh_cookie_name: str = "refresh_token"
    csrf_cookie_name: str = "csrf_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    login_rate_limit: int = 5
    login_rate_window_seconds: int = 15 * 60
    forgot_password_rate_limit: int = 3
    forgot_password_rate_window_seconds: int = 60 * 60
    code_send_rate_limit: int = 1
    code_send_rate_window_seconds: int = 60
    verify_code_max_attempts: int = 5
    verification_code_ttl_seconds: int = 5 * 60

    smtp_host: str = "smtp.mail.ru"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    sms_api_url: str = ""
    sms_api_key: str = ""
    sms_sender_name: str = "PlombirClub"

    upload_dir: str = "/uploads"
    user_document_max_mb: int = 20
    material_max_mb: int = 100

    backup_dir: str = "/backups"
    backup_retain_count: int = 7
    backup_script_path: str = "/scripts/backup.sh"

    @property
    def user_document_max_bytes(self) -> int:
        return self.user_document_max_mb * 1024 * 1024

    @property
    def material_max_bytes(self) -> int:
        return self.material_max_mb * 1024 * 1024


settings = Settings()
