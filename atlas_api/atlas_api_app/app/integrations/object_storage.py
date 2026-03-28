"""S3-compatible object storage (MinIO, AWS S3) for Atlas."""

from __future__ import annotations

from typing import Any

import boto3

from app.core.config import get_settings


def get_s3_client() -> Any:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
    )


def check_s3_health() -> None:
    """Raises if the configured bucket is not reachable."""
    s = get_settings()
    client = get_s3_client()
    client.head_bucket(Bucket=s.s3_bucket)
