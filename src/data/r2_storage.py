from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import boto3
import botocore.auth
import botocore.exceptions
import pandas as pd
from botocore.config import Config


R2_PREFIX = "market-dashboard"
MAX_UPLOAD_BYTES = int(os.getenv("R2_MAX_UPLOAD_BYTES", str(8 * 1024**3)))
_R2_TIME_OFFSET: timedelta | None = None


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
            if _is_request_time_skew_error(exc):
                _refresh_r2_time_offset(exc)
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
    time_offset = _r2_time_offset()
    if time_offset is None:
        return
    botocore.auth.get_current_datetime = _corrected_current_datetime


def _corrected_current_datetime(remove_tzinfo: bool = True):
    if _R2_TIME_OFFSET is None:
        return datetime.now(timezone.utc).replace(tzinfo=None if remove_tzinfo else timezone.utc)
    corrected = datetime.now(timezone.utc) + _R2_TIME_OFFSET
    return corrected.replace(tzinfo=None) if remove_tzinfo else corrected


def _r2_time_offset() -> timedelta | None:
    global _R2_TIME_OFFSET
    if _R2_TIME_OFFSET is not None:
        return _R2_TIME_OFFSET

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

    _R2_TIME_OFFSET = _offset_from_date_header(date_header)
    return _R2_TIME_OFFSET


def _refresh_r2_time_offset(exc: Exception | None = None) -> None:
    global _R2_TIME_OFFSET
    date_header = _date_header_from_exception(exc) if exc else None
    if not date_header:
        _R2_TIME_OFFSET = None
        _r2_time_offset()
        return
    _R2_TIME_OFFSET = _offset_from_date_header(date_header)


def _offset_from_date_header(date_header: str) -> timedelta:
    parsed = parsedate_to_datetime(date_header)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc) - datetime.now(timezone.utc)


def _date_header_from_exception(exc: Exception | None) -> str | None:
    if not isinstance(exc, botocore.exceptions.ClientError):
        return None
    headers = exc.response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
    return headers.get("date") or headers.get("Date")


def _is_request_time_skew_error(exc: Exception) -> bool:
    if not isinstance(exc, botocore.exceptions.ClientError):
        return False
    return exc.response.get("Error", {}).get("Code") == "RequestTimeTooSkewed"


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
