"""The demo seed script must never send email, and never run outside local (C2)."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = REPO_ROOT / "scripts" / "seed.py"

# A key shaped like a real one. If the guard fails, the adapter selection changes --
# nothing here ever contacts a provider.
FAKE_RESEND_KEY = "re_fake_key_that_must_never_be_used"


def run_seed(tmp_path, **env_overrides) -> subprocess.CompletedProcess:
    """Run the seed script in its own process, against a throwaway database."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'seed.db'}",
        "UPLOAD_DIR": str(tmp_path / "uploads"),
        "ENVIRONMENT": "local",
        **env_overrides,
    }
    return subprocess.run(
        [sys.executable, str(SEED)],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )


def prepare_schema(tmp_path) -> None:
    from sqlalchemy import create_engine

    from app.db.base import Base
    from app.db.models import Lead  # noqa: F401  (registers the tables)

    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}")
    Base.metadata.create_all(engine)
    engine.dispose()


def test_seeding_pins_the_console_adapter_even_with_a_provider_key() -> None:
    """C2: a developer with RESEND_API_KEY set must not mail four fictional people.

    The guard replaces the adapter factory for the life of the process, so any future
    code path that reaches for the email service gets the one that only logs.
    """
    sys.path.insert(0, str(REPO_ROOT / "api"))
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

    from app.core import deps
    from app.services.email.console import ConsoleEmailService

    original = deps.get_email_service
    try:
        import seed

        seed.force_console_email()
        assert isinstance(deps.get_email_service(), ConsoleEmailService)
    finally:
        deps.get_email_service = original
        deps.get_email_service.cache_clear()


def test_seed_creates_the_demo_leads(tmp_path) -> None:
    """Four fictional leads spread across the pipeline."""
    prepare_schema(tmp_path)

    result = run_seed(tmp_path, RESEND_API_KEY=FAKE_RESEND_KEY)

    assert result.returncode == 0, result.stderr
    assert "Seeded 4 demo lead(s)" in result.stdout
    assert "PENDING=2" in result.stdout
    assert "REACHED_OUT=1" in result.stdout
    assert "QUALIFIED=1" in result.stdout


def test_seed_is_idempotent(tmp_path) -> None:
    """Running it twice leaves four leads, not eight."""
    prepare_schema(tmp_path)

    run_seed(tmp_path)
    second = run_seed(tmp_path)

    assert second.returncode == 0, second.stderr
    assert "already present" in second.stdout
    assert "Leads in the database: 4" in second.stdout


def test_seed_refuses_outside_local(tmp_path) -> None:
    """It writes fictional people; it must never touch a real database."""
    prepare_schema(tmp_path)

    result = run_seed(tmp_path, ENVIRONMENT="production")

    assert result.returncode == 1
    assert "Refusing to seed" in result.stderr


def test_seeded_data_is_entirely_fictional() -> None:
    """Privacy: no real person's details belong in a fixture that ships in the repo."""
    import re

    source = SEED.read_text()
    emails = set(re.findall(r"[\w.+-]+@[\w.-]+\.\w+", source))

    assert emails, "expected the demo addresses to be found"
    assert all(address.endswith("@example.com") for address in emails), emails
