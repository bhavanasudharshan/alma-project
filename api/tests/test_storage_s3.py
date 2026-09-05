"""S3 adapter round trip against moto, so no AWS account is needed (E2/M2)."""

import io

import boto3
import pytest
from moto import mock_aws

from app.core.config import Settings
from app.services.storage.s3 import S3Storage

BUCKET = "alma-resumes-test"


@pytest.fixture
def s3_settings() -> Settings:
    return Settings(
        s3_bucket=BUCKET,
        s3_region="us-east-1",
        s3_access_key_id="testing",
        s3_secret_access_key="testing",
    )


@mock_aws
def test_ensure_bucket_creates_a_missing_bucket(s3_settings: Settings) -> None:
    """MinIO starts empty, so startup must be able to create the bucket."""
    storage = S3Storage(s3_settings)

    storage.ensure_bucket()

    buckets = boto3.client("s3", region_name="us-east-1").list_buckets()["Buckets"]
    assert [b["Name"] for b in buckets] == [BUCKET]


@mock_aws
def test_ensure_bucket_is_idempotent(s3_settings: Settings) -> None:
    """Restarting the app twice must not fail on an existing bucket."""
    storage = S3Storage(s3_settings)
    storage.ensure_bucket()

    storage.ensure_bucket()  # must not raise


@mock_aws
def test_save_open_delete_round_trip(s3_settings: Settings) -> None:
    """The S3 adapter satisfies the same contract as local disk (E2)."""
    storage = S3Storage(s3_settings)
    storage.ensure_bucket()
    key = "abc/cv.pdf"

    storage.save(key, io.BytesIO(b"%PDF-1.4 resume"), "application/pdf")
    assert storage.open(key).read() == b"%PDF-1.4 resume"

    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.open(key)


@mock_aws
def test_open_missing_key_raises_file_not_found(s3_settings: Settings) -> None:
    """A missing object surfaces the same error the local adapter raises.

    The service layer maps FileNotFoundError to a 404; if this adapter leaked a
    botocore ClientError instead, that path would become a 500.
    """
    storage = S3Storage(s3_settings)
    storage.ensure_bucket()

    with pytest.raises(FileNotFoundError):
        storage.open("nope/missing.pdf")


@mock_aws
def test_presigned_url_is_produced(s3_settings: Settings) -> None:
    """Presigning is available on S3 and time-limited."""
    storage = S3Storage(s3_settings)
    storage.ensure_bucket()
    storage.save("abc/cv.pdf", io.BytesIO(b"%PDF"), "application/pdf")

    url = storage.presigned_url("abc/cv.pdf", expires=120)

    assert url is not None
    assert BUCKET in url
    assert "X-Amz-Expires=120" in url


def test_local_storage_has_no_presigned_url(tmp_path) -> None:
    """The local adapter returns None, so callers must keep the proxy route (E2)."""
    from app.services.storage.local import LocalDiskStorage

    assert LocalDiskStorage(root=tmp_path).presigned_url("any/key") is None
