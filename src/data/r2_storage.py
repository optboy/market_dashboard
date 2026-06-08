from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
from botocore.config import Config


R2_PREFIX = "market-dashboard"
MAX_UPLOAD_BYTES = int(os.getenv("R2_MAX_UPLOAD_BYTES", str(8 * 1024**3)))


def is_r2_configured() -> bool:
    return all(
        _setting(name)
        for name in [
            "R2_ENDPOINT_URL",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET_NAME",
        ]
    )


def upload_dataframe(df: pd.DataFrame, key: str) -> None:
    buffer = BytesIO()
    df.to_parquet(buffer, index=False)
    upload_bytes(buffer.getvalue(), key)


def download_dataframe(key: str) -> pd.DataFrame:
    response = _client().get_object(Bucket=_bucket(), Key=_full_key(key))
    return pd.read_parquet(BytesIO(response["Body"].read()))


def upload_file(path: Path, key: str) -> None:
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError(f"Refusing to upload {path}: file exceeds R2_MAX_UPLOAD_BYTES")
    _client().upload_file(str(path), _bucket(), _full_key(key))


def upload_bytes(payload: bytes, key: str) -> None:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Refusing to upload {key}: payload exceeds R2_MAX_UPLOAD_BYTES")
    _client().put_object(Bucket=_bucket(), Key=_full_key(key), Body=payload)


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_setting("R2_ENDPOINT_URL"),
        aws_access_key_id=_setting("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_setting("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _bucket() -> str:
    return str(_setting("R2_BUCKET_NAME"))


def _full_key(key: str) -> str:
    return f"{R2_PREFIX}/{key.lstrip('/')}"


def _setting(name: str) -> Any:
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None
