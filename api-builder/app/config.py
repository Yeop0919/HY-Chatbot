import logging
import re
import os
from typing import Literal, List, Annotated, Any, Union, Dict

from pydantic import AnyUrl, BeforeValidator, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> Union[List[str], str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list) or isinstance(v, str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # Environment: local, staging, production
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    PORT: int = 8000
    SERVICE_NAME: str = "공지 챗봇 API"
    SERVICE_CODE: str = "notice-chatbot"
    MAJOR_VERSION: str = "v1"
    STATUS: str = "dev"

    # Request Server URL
    SERVER_URL: str = ""  # FastAPI SERVER URL 설정이 필요할 경우, 해당 변수로 설정

    # LOG
    LEVEL: str = "INFO"
    JSON_LOG: bool = False
    LOGURU_FORMAT: str = "<green>{time:YY-MM-DD HH:mm:ss.SSS}</green> | " \
                         "<level>{level: <8}</level> | " \
                         "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> " \
                         "- {process} {thread} {extra[request_id]} <level>{message}</level>"

    # LOG SAVE CONFIG
    SAVE: bool = True
    LOG_SAVE_PATH: str = "./logs"
    ROTATION: str = "00:00"
    RETENTION: str = "10 days"
    COMPRESSION: str = "zip"

    @field_validator('LEVEL')
    def validate_log_level(cls, v):
        if v.upper() not in 'CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET'.split('|'):
            raise ValueError(f"로그레벨 `LEVEL` 은 'CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET' 만 가능. LEVEL={v}")
        return v

    @field_validator('SERVER_URL')
    def valid_server_url(cls, v):
        server_url_regex = r'^https?:\/\/(www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+(\/[a-zA-Z0-9-._~:/?#[\]@!$&\'()*+,;=]*)?$'
        pattern = re.compile(server_url_regex)
        if v:
            if bool(pattern.match(v)):
                return v
            else:
                raise ValueError(f"URL Validation Error (regex {pattern=}), current url={v}")
        else:
            return None

    @computed_field  # type: ignore[misc]
    @property
    def log_level(self) -> Any:  # real return type: numeric value (int)
        return logging.getLevelName(self.LEVEL)

    @computed_field  # type: ignore[misc]
    @property
    def servers(self) -> Union[List[Dict[str, str]], None]:
        if self.SERVER_URL:
            return [{"url": f"{self.SERVER_URL}", "description": f"{self.ENVIRONMENT.capitalize()} Server"}]
        else:
            return None

    @computed_field  # type: ignore[misc]
    @property
    def root_path_in_servers(self) -> bool:
        if self.SERVER_URL:
            return False
        else:
            return True

    # Backend
    BACKEND_CORS_ORIGINS: Annotated[Union[List[AnyUrl], str], BeforeValidator(parse_cors)] = ["http://localhost:8001", "http://localhost:3000", "http://localhost:8000"]

    # Service Config
    X_TOKEN: str = "wisenut"
    
    ELASTIC_CLOUD_URL: str = os.getenv("ELASTIC_CLOUD_URL", "https://e398b41cb31146b5adaa38c2c530b10f.us-central1.gcp.cloud.es.io:443")
    ELASTIC_API_KEY: str = os.getenv("ELASTIC_API_KEY", "b2NlM0NKVUJzb3VEVGw3SEV4WUs6RzRjeUlYeEpTM20yY28tbFZCc0ZNQQ==")
    PORT: int = int(os.getenv("PORT", 8000))
    
    ELASTIC_CLOUD_ID: str = os.getenv("ELASTIC_CLOUD_ID","64fb5a48137c4e20bf19c9ce2d24b372:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGUzOThiNDFjYjMxMTQ2YjVhZGFhMzhjMmM1MzBiMTBmJDBhZDNjZDEwMjgyMzQ5ZGVhNmU4NmY5YTNhYjFjM2M564fb5a48137c4e20bf19c9ce2d24b372:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGUzOThiNDFjYjMxMTQ2YjVhZGFhMzhjMmM1MzBiMTBmJDBhZDNjZDEwMjgyMzQ5ZGVhNmU4NmY5YTNhYjFjM2M5")
    ELASTIC_USERNAME: str = os.getenv("ELASTIC_USERNAME","new_admin")
    ELASTIC_PASSWORD: str = os.getenv("ELASTIC_PASSWORD", "NewSecurePassword123!")


settings = Settings()  # type: ignore
print(settings.json())
