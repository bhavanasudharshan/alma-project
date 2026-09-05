"""S3-compatible object storage (P1), used for both AWS S3 and MinIO.

Selected by configuration alone -- no service or router changes (M4/E2). Resumes stay
in a private bucket and are never given a public URL (C1); the authenticated proxy
route remains the path the UI uses, with presigned URLs available as an optimisation.
"""

import logging
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings

logger = logging.getLogger(__name__)


class S3Storage:
    """:class:`~app.services.storage.base.FileStorage` backed by an S3 API."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            # Path style keeps MinIO working without per-bucket DNS.
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        """Create the bucket when missing. Called once at startup for local MinIO."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status not in (403, 404):
                raise

        try:
            self._client.create_bucket(Bucket=self._bucket)
            logger.info("Created object storage bucket %s", self._bucket)
        except ClientError as exc:
            # A concurrent worker winning the race is not an error.
            if exc.response.get("Error", {}).get("Code") not in (
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            ):
                raise

    def save(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        """Upload the stream. boto3 chunks it, so nothing is buffered whole (P1)."""
        self._client.upload_fileobj(
            fileobj,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def open(self, key: str) -> BinaryIO:
        """Open the object for reading.

        :raises FileNotFoundError: to match the local adapter, so the service layer
            never has to know which backend it is talking to.
        """
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise FileNotFoundError(key) from exc
            raise
        return response["Body"]

    def delete(self, key: str) -> None:
        """Remove the object. S3 delete is already idempotent."""
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_url(self, key: str, expires: int = 300) -> str | None:
        """A short-lived GET URL, or ``None`` if signing fails.

        Failing soft matters: the caller falls back to the proxy route, so a signing
        problem degrades performance rather than breaking downloads (A1).
        """
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        except ClientError:
            logger.exception("Could not presign %s", key)
            return None
