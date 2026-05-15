from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = Path(__file__).parents[3] / ".env"


class DatabaseConfig(BaseSettings):
    db_url: str


class StorageConfig(BaseSettings):
    storage_type: Literal["local", "s3"] = "s3"
    storage_local_path: str = "storage"  # Only used when storage_type="local"

    # S3/MinIO (Only used when storage_type="s3")
    s3_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket_name: str = "file-manager"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_address_style: Literal["auto", "virtual", "path"] = "path"
    s3_use_iam: bool = False


class SigningConfig(BaseSettings):
    secret_key: str = ""  # Generate via: openssl rand -base64 42
    files_base_url: str = "http://localhost:8000"  # Base URL for signed file URLs
    files_access_timeout: int | None = None  # Seconds, None means never expire


class ValidationConfig(BaseSettings):
    # FileValidator defaults; file_manager deps do not automatically construct a validator from them.
    extension_blacklist: list[str] = []  # Blocked file extensions, e.g. [".exe", ".bat"]
    max_file_size_mb: int = 15
    max_image_size_mb: int = 10
    max_video_size_mb: int = 100
    max_audio_size_mb: int = 50


class FileManagerConfig(DatabaseConfig, StorageConfig, SigningConfig, ValidationConfig):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")


settings = FileManagerConfig()
