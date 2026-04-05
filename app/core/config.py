from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str

    # EMQX
    emqx_host: str = "localhost"
    emqx_port: int = 1883
    emqx_username: str = "admin"
    emqx_password: str = "public"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080

    # FastAPI
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    fastapi_workers: int = 4

    # Batch processing
    batch_size: int = 50
    batch_timeout: int = 6

    # MQTT subscription (optional, for direct mode)
    mqtt_tls_enable: bool = True
    mqtt_client_id: str = "fastapi_backend"
    enable_mqtt_subscription: bool = False

    # Metrics
    enable_metrics: bool = True

    # 日志
    log_level: str = "INFO"
    log_file: str = "/var/log/fastapi/app.log"

    class Config:
        env_file = ".env"


settings = Settings()
