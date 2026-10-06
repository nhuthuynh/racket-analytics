"""S3-compatible object store adapter (ST-001/ST-008; ADR 0008 part C, ADR 0011).

The only module that talks S3. Callers pass server-generated keys only (``ObjectKeyPolicy``).
Presigned URLs are bearer secrets: never log them (NFR-055, NFR-069).
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from racket.platform.settings import MissingSettingError, Settings

PRESIGN_MAX_SECONDS = 15 * 60  # NFR-055


@dataclass(frozen=True)
class S3Config:
    bucket: str
    endpoint_url: str | None
    access_key_id: str | None
    secret_access_key: str | None
    region: str

    @classmethod
    def from_env(cls) -> S3Config:
        bucket = os.environ.get("S3_BUCKET_MEDIA", "").strip()
        if not bucket:
            raise MissingSettingError(["S3_BUCKET_MEDIA"])
        return cls(
            bucket=bucket,
            endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
            access_key_id=os.environ.get("S3_ACCESS_KEY_ID") or None,
            secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY") or None,
            region=os.environ.get("S3_REGION") or "us-east-1",
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> S3Config:
        return cls(
            bucket=settings.s3_bucket_media,
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            region=settings.s3_region,
        )


class ObjectStore:
    def __init__(self, config: S3Config) -> None:
        self.bucket = config.bucket
        self._key_id, self._secret = config.access_key_id, config.secret_access_key
        self._region = config.region
        self._signers: dict[str, Any] = {}
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name=config.region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=60,
            ),
        )

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> ObjectStore:
        config = S3Config.from_env() if settings is None else S3Config.from_settings(settings)
        return cls(config)

    # ------------------------------------------------------------ objects
    def list_keys(self, prefix: str = "") -> Iterator[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                yield str(item["Key"])

    def get_bytes(self, key: str) -> bytes:
        return bytes(self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read())

    def put_bytes(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def size_of(self, key: str) -> int | None:
        try:
            head = self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return int(head["ContentLength"])

    def presigned_get(
        self,
        key: str,
        ttl_seconds: int = PRESIGN_MAX_SECONDS,
        *,
        public_endpoint: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """A GET link for ``key``. With ``public_endpoint`` the link is signed for the host the
        browser uses (the https origin's media route, SRE-MEDIA), so the signature matches what
        the store receives through the proxy. With ``content_type`` the store answers with that
        ``Content-Type`` (signed ``response-content-type``), whatever the object was stored
        with (QA-RV1-05). Bearer secret: never log it (NFR-069)."""
        ttl = max(1, min(ttl_seconds, PRESIGN_MAX_SECONDS))
        client = self._client if public_endpoint is None else self._signer(public_endpoint)
        params = {"Bucket": self.bucket, "Key": key}
        if content_type is not None:
            params["ResponseContentType"] = content_type
        return str(client.generate_presigned_url("get_object", Params=params, ExpiresIn=ttl))

    def _signer(self, endpoint: str) -> Any:
        """A client that only signs (no request is sent), for the public endpoint."""
        if endpoint not in self._signers:
            self._signers[endpoint] = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=self._key_id,
                aws_secret_access_key=self._secret,
                region_name=self._region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._signers[endpoint]

    def ping(self) -> None:
        self._client.head_bucket(Bucket=self.bucket)

    # ------------------------------------------------------------ multipart
    def create_multipart(self, key: str, *, content_type: str | None = None) -> str:
        extra = {} if content_type is None else {"ContentType": content_type}
        response = self._client.create_multipart_upload(Bucket=self.bucket, Key=key, **extra)
        return str(response["UploadId"])

    def upload_part(self, key: str, upload_id: str, number: int, data: bytes) -> str:
        response = self._client.upload_part(
            Bucket=self.bucket, Key=key, UploadId=upload_id, PartNumber=number, Body=data
        )
        return str(response["ETag"])

    def complete_multipart(
        self, key: str, upload_id: str, parts: Sequence[tuple[int, str]]
    ) -> None:
        self._client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": [{"PartNumber": n, "ETag": e} for n, e in parts]},
        )

    def abort_multipart(self, key: str, upload_id: str) -> None:
        self._client.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)


def is_missing_upload(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") in ("NoSuchUpload", "404")
