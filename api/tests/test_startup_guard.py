"""Startup refuses placeholder credentials outside local development (S4)."""

import pytest

from app.core.config import DEV_ATTORNEY_PASSWORD, DEV_JWT_SECRET, Settings
from app.main import InsecureConfiguration, create_app


def test_local_boots_with_placeholder_credentials(tmp_path) -> None:
    """The zero-config reviewer run must keep working ($1)."""
    settings = Settings(
        environment="local",
        database_url=f"sqlite:///{tmp_path / 'x.db'}",
        upload_dir=str(tmp_path),
    )

    assert create_app(settings) is not None


@pytest.mark.parametrize("environment", ["staging", "production", "ci"])
def test_non_local_refuses_to_start_with_placeholders(tmp_path, environment: str) -> None:
    """A warning is not enough: known credentials mean the app is unauthenticated.

    Failing at boot is the only outcome that cannot be scrolled past in a log.
    """
    settings = Settings(
        environment=environment,
        database_url=f"sqlite:///{tmp_path / 'x.db'}",
        upload_dir=str(tmp_path),
        jwt_secret_key=DEV_JWT_SECRET,
        attorney_password=DEV_ATTORNEY_PASSWORD,
    )

    with pytest.raises(InsecureConfiguration) as excinfo:
        create_app(settings)

    assert "JWT_SECRET_KEY" in str(excinfo.value)
    assert "ATTORNEY_PASSWORD" in str(excinfo.value)


def test_non_local_starts_once_real_secrets_are_set(tmp_path) -> None:
    """The guard blocks placeholders, not deployment."""
    settings = Settings(
        environment="production",
        database_url=f"sqlite:///{tmp_path / 'x.db'}",
        upload_dir=str(tmp_path),
        jwt_secret_key="a-real-secret-of-adequate-length-0123456789",
        attorney_password="a-real-password",
    )

    assert create_app(settings) is not None


def test_partial_placeholders_are_named_individually(tmp_path) -> None:
    """The error says which values are still placeholders, not just that some are."""
    settings = Settings(
        environment="production",
        database_url=f"sqlite:///{tmp_path / 'x.db'}",
        upload_dir=str(tmp_path),
        jwt_secret_key="a-real-secret-of-adequate-length-0123456789",
        attorney_password=DEV_ATTORNEY_PASSWORD,
    )

    with pytest.raises(InsecureConfiguration) as excinfo:
        create_app(settings)

    assert "ATTORNEY_PASSWORD" in str(excinfo.value)
    assert "JWT_SECRET_KEY" not in str(excinfo.value)
