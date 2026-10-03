"""IT-00-16 (ST-001, ADR 0008 part C): the dev object store supports what production uses:
multipart upload, presigned GET that expires, and delete; and it enforces authentication.

Runs against S3_ENDPOINT_URL when set (e.g. the Compose `objectstore` service), otherwise
starts a local SeaweedFS with scripts/dev-objectstore.sh. Real server, no mocks.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import boto3
import pytest
import requests
from botocore.client import Config
from botocore.exceptions import ClientError
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.integration

MiB = 1024 * 1024


@pytest.fixture(scope="module")
def s3_env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, str]]:
    if os.environ.get("S3_ENDPOINT_URL"):
        yield {k: v for k, v in os.environ.items() if k.startswith("S3_")}
        return
    state = tmp_path_factory.mktemp("objstore")
    env = {**os.environ, "RA_DEV_STATE": str(state)}
    script = str(SCRIPTS_DIR / "dev-objectstore.sh")
    res = subprocess.run(
        ["bash", script, "start"], capture_output=True, text=True, env=env, timeout=180, check=False
    )
    assert res.returncode == 0, res.stderr
    values = dict(re.findall(r"^export (S3_[A-Z_]+)=(\S+)$", res.stdout, re.M))
    try:
        yield values
    finally:
        subprocess.run(["bash", script, "stop"], env=env, timeout=60, check=False)


def client(env: dict[str, str], secret: str | None = None):
    return boto3.client(
        "s3",
        endpoint_url=env["S3_ENDPOINT_URL"],
        aws_access_key_id=env["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=secret or env["S3_SECRET_ACCESS_KEY"],
        region_name=env.get("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def key() -> str:
    return f"parity/{uuid.uuid4()}"


# ---------------------------------------------------------------- negative cases first
def test_wrong_secret_is_refused(s3_env: dict[str, str]) -> None:
    bad = client(s3_env, secret="definitely-wrong-secret")
    with pytest.raises(ClientError) as err:
        bad.put_object(Bucket=s3_env["S3_BUCKET_MEDIA"], Key=key(), Body=b"x")
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403


def test_presigned_get_expires(s3_env: dict[str, str]) -> None:
    s3, bucket, k = client(s3_env), s3_env["S3_BUCKET_MEDIA"], key()
    s3.put_object(Bucket=bucket, Key=k, Body=b"expiring")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": k}, ExpiresIn=2)
    assert requests.get(url, timeout=10).status_code == 200
    time.sleep(4)
    assert requests.get(url, timeout=10).status_code == 403


def test_tampered_presigned_url_is_refused(s3_env: dict[str, str]) -> None:
    s3, bucket, k = client(s3_env), s3_env["S3_BUCKET_MEDIA"], key()
    s3.put_object(Bucket=bucket, Key=k, Body=b"secret-ish")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": k}, ExpiresIn=60)
    other = k + "-other"
    s3.put_object(Bucket=bucket, Key=other, Body=b"other")
    assert requests.get(url.replace(k, other), timeout=10).status_code == 403


def test_deleted_object_is_gone(s3_env: dict[str, str]) -> None:
    s3, bucket, k = client(s3_env), s3_env["S3_BUCKET_MEDIA"], key()
    s3.put_object(Bucket=bucket, Key=k, Body=b"to delete")
    s3.delete_object(Bucket=bucket, Key=k)
    with pytest.raises(ClientError) as err:
        s3.head_object(Bucket=bucket, Key=k)
    assert err.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


# ---------------------------------------------------------------- positive cases
def test_multipart_upload_round_trips_byte_for_byte(s3_env: dict[str, str]) -> None:
    s3, bucket, k = client(s3_env), s3_env["S3_BUCKET_MEDIA"], key()
    parts_data = [os.urandom(5 * MiB), os.urandom(5 * MiB), os.urandom(1 * MiB)]
    mpu = s3.create_multipart_upload(Bucket=bucket, Key=k, ContentType="video/mp4")
    parts = []
    for n, data in enumerate(parts_data, start=1):
        etag = s3.upload_part(
            Bucket=bucket, Key=k, PartNumber=n, UploadId=mpu["UploadId"], Body=data
        )["ETag"]
        parts.append({"PartNumber": n, "ETag": etag})
    s3.complete_multipart_upload(
        Bucket=bucket, Key=k, UploadId=mpu["UploadId"], MultipartUpload={"Parts": parts}
    )
    body = s3.get_object(Bucket=bucket, Key=k)["Body"].read()
    assert hashlib.sha256(body).hexdigest() == hashlib.sha256(b"".join(parts_data)).hexdigest()


def test_aborted_multipart_upload_leaves_no_object(s3_env: dict[str, str]) -> None:
    s3, bucket, k = client(s3_env), s3_env["S3_BUCKET_MEDIA"], key()
    mpu = s3.create_multipart_upload(Bucket=bucket, Key=k)
    s3.upload_part(
        Bucket=bucket, Key=k, PartNumber=1, UploadId=mpu["UploadId"], Body=os.urandom(5 * MiB)
    )
    s3.abort_multipart_upload(Bucket=bucket, Key=k, UploadId=mpu["UploadId"])
    with pytest.raises(ClientError):
        s3.head_object(Bucket=bucket, Key=k)


def test_launcher_state_file_is_outside_git(tmp_path: Path) -> None:
    gitignore = (SCRIPTS_DIR.parent / ".gitignore").read_text()
    assert re.search(r"^/?\.local/?$", gitignore, re.M)
