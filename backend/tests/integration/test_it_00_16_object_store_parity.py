"""IT-00-16 (object store parity, ST-001; ADR 0008 part C): the dev/CI S3-compatible store
supports what production uses: multipart upload, presigned GET that expires, delete.

Talks S3 directly with boto3 so it tests the store, not our adapter. Configuration:
S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_MEDIA, S3_REGION
(the names in infra/env.example and scripts/dev-objectstore.sh).
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.slow

PART = 5 * 1024 * 1024  # S3 minimum part size (except the last part)


@pytest.fixture(scope="module")
def s3() -> tuple[Any, str]:
    import boto3
    from botocore.config import Config

    endpoint = os.environ.get("S3_ENDPOINT_URL")
    if not endpoint:
        pytest.fail(
            "S3_ENDPOINT_URL is not set; start the Compose object store or "
            "scripts/dev-objectstore.sh (see docs/sprints/00/test-plan-status.md)",
            pytrace=False,
        )
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY", "test"),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = os.environ.get("S3_BUCKET_MEDIA", "racket-media")
    try:
        client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=bucket)
    return client, bucket


def test_multipart_upload_round_trips(s3: tuple[Any, str]) -> None:
    client, bucket = s3
    key = f"parity/{uuid.uuid4()}"
    data = os.urandom(PART) + os.urandom(1024)

    mpu = client.create_multipart_upload(Bucket=bucket, Key=key)
    parts = []
    for number, chunk in enumerate([data[:PART], data[PART:]], start=1):
        r = client.upload_part(
            Bucket=bucket, Key=key, PartNumber=number, UploadId=mpu["UploadId"], Body=chunk
        )
        parts.append({"PartNumber": number, "ETag": r["ETag"]})
    client.complete_multipart_upload(
        Bucket=bucket, Key=key, UploadId=mpu["UploadId"], MultipartUpload={"Parts": parts}
    )

    body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    assert hashlib.sha256(body).digest() == hashlib.sha256(data).digest()


def test_presigned_get_works_then_expires(s3: tuple[Any, str]) -> None:
    client, bucket = s3
    key = f"parity/{uuid.uuid4()}"
    client.put_object(Bucket=bucket, Key=key, Body=b"hello")
    url = client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=2
    )

    assert httpx.get(url).content == b"hello"
    time.sleep(3.5)
    assert httpx.get(url).status_code == 403


def test_tampered_presigned_url_is_refused(s3: tuple[Any, str]) -> None:
    client, bucket = s3
    key = f"parity/{uuid.uuid4()}"
    client.put_object(Bucket=bucket, Key=key, Body=b"secret")
    url = client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=60
    )

    assert httpx.get(url.replace(key, key + "x")).status_code == 403


def test_delete_removes_the_object(s3: tuple[Any, str]) -> None:
    client, bucket = s3
    key = f"parity/{uuid.uuid4()}"
    client.put_object(Bucket=bucket, Key=key, Body=b"bye")

    client.delete_object(Bucket=bucket, Key=key)

    with pytest.raises(client.exceptions.ClientError) as err:
        client.head_object(Bucket=bucket, Key=key)
    assert err.value.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound")
