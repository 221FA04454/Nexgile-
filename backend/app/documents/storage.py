"""Object storage abstraction. Local disk for development; S3-compatible for production."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import AppError

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    base = Path(name or "document").name
    cleaned = SAFE_NAME.sub("_", base)[:120]
    return cleaned or "document"


class StorageBackend(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> str: ...
    def get(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise AppError("BAD_REQUEST", "Invalid storage key.", 400)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def get(self, key: str) -> bytes:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise AppError("FORBIDDEN", "Invalid storage key.", 403)
        return path.read_bytes()


class S3Storage:
    """Production interface. Requires boto3 + bucket credentials — not invoked without config."""

    def __init__(self, bucket: str, endpoint: str = "", region: str = "us-east-1"):
        self.bucket = bucket
        self.endpoint = endpoint
        self.region = region

    def put(self, key: str, data: bytes, content_type: str) -> str:
        raise AppError(
            "SERVICE_UNAVAILABLE",
            "S3 object storage is configured but the provider client is not installed.",
            503,
        )

    def get(self, key: str) -> bytes:
        raise AppError("SERVICE_UNAVAILABLE", "S3 object storage is not available.", 503)


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.object_storage_backend == "s3":
        if not settings.s3_bucket:
            raise AppError("SERVICE_UNAVAILABLE", "S3_BUCKET is required for object storage.", 503)
        return S3Storage(settings.s3_bucket, settings.s3_endpoint, settings.s3_region)
    return LocalStorage(settings.upload_dir)


def validate_upload(filename: str, content_type: str, size: int) -> str:
    settings = get_settings()
    if size > settings.max_upload_bytes:
        raise AppError("BAD_REQUEST", "File exceeds the maximum upload size.", 400)
    if content_type not in ALLOWED_TYPES:
        raise AppError("BAD_REQUEST", "File type is not allowed.", 400)
    return f"{uuid.uuid4().hex}_{safe_filename(filename)}"
