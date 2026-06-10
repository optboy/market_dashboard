from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import boto3
import botocore.auth
import pandas as pd
from botocore.config import Config


R2_PREFIX = "market-dashboard"
MAX_UPLOAD_BYTES = int(os.getenv("R2_MAX_UPLOAD_BYTES", str(8 * 1024**3)))
_R2_SERVER_DATETIME = None


def is_r2_configured() -> bool:
    return not missing_r2_settings()


def missing_r2_settings() -> list[str]:
    return [
        name
        for name in [
            "R2_ENDPOINT_URL",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET_NAME",
        ]
        if not _setting(name)
    ]


def upload_dataframe(df: pd.DataFrame, key: str) -> None:
    buffer = BytesIO()
    df.to_parquet(buffer, index=False)
    upload_bytes(buffer.getvalue(), key)


def download_dataframe(key: str, attempts: int = 3) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = _client().get_object(Bucket=_bucket(), Key=_full_key(key))
            return pd.read_parquet(BytesIO(response["Body"].read()))
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(0.5 * attempt)
    raise RuntimeError(f"Failed to download R2 object {_full_key(key)} after {attempts} attempts: {last_error}")


def upload_file(path: Path, key: str) -> None:
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError(f"Refusing to upload {path}: file exceeds R2_MAX_UPLOAD_BYTES")
    _client().upload_file(str(path), _bucket(), _full_key(key))


def upload_bytes(payload: bytes, key: str) -> None:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Refusing to upload {key}: payload exceeds R2_MAX_UPLOAD_BYTES")
    _client().put_object(Bucket=_bucket(), Key=_full_key(key), Body=payload)


def _client():
    _patch_botocore_time()
    return boto3.client(
        "s3",
        endpoint_url=_setting("R2_ENDPOINT_URL"),
        aws_access_key_id=_setting("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_setting("R2_SECRET_ACCESS_KEY"),
        config=Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
        region_name="auto",
    )


def _bucket() -> str:
    return str(_setting("R2_BUCKET_NAME"))


def _full_key(key: str) -> str:
    return f"{R2_PREFIX}/{key.lstrip('/')}"


def _patch_botocore_time() -> None:
    server_datetime = _r2_server_datetime()
    if server_datetime is None:
        return
    botocore.auth.get_current_datetime = lambda: server_datetime


def _r2_server_datetime():
    global _R2_SERVER_DATETIME
    if _R2_SERVER_DATETIME is not None:
        return _R2_SERVER_DATETIME

    urls = [
        _setting("R2_ENDPOINT_URL"),
        "https://api.cloudflare.com/client/v4",
        "https://www.cloudflare.com",
    ]
    date_header = None
    for url in urls:
        if not url:
            continue
        date_header = _date_header_from_url(str(url))
        if date_header:
            break

    if not date_header:
        return None

    parsed = parsedate_to_datetime(date_header)
    _R2_SERVER_DATETIME = parsed.replace(tzinfo=None)
    return _R2_SERVER_DATETIME


def _date_header_from_url(url: str) -> str | None:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.headers.get("Date")
    except urllib.error.HTTPError as exc:
        return exc.headers.get("Date")
    except Exception:
        return None


def _setting(name: str) -> Any:
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None
