"""Environment diagnostics for a reviewer whose setup is not working.

Reports tool versions, configuration presence, database reachability and which
adapters the current environment selects -- using the same properties ``core/deps.py``
selects on, so this can never disagree with the running app (M4).
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "api"))

OK = "  \033[32mok\033[0m  "
BAD = "  \033[31mxx\033[0m  "
WARN = "  \033[33m??\033[0m  "


def line(marker: str, label: str, value: str) -> None:
    print(f"{marker}{label:<22} {value}")


def tool_version(command: str, *args: str) -> str | None:
    if shutil.which(command) is None:
        return None
    try:
        result = subprocess.run(
            [command, *args], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else None


def check_tools() -> bool:
    print("\nTools")
    ok = True
    for command, args, hint in [
        ("uv", ("--version",), "curl -LsSf https://astral.sh/uv/install.sh | sh"),
        ("node", ("--version",), "https://nodejs.org (v20 or newer)"),
        ("pnpm", ("--version",), "corepack enable && corepack prepare pnpm@9 --activate"),
    ]:
        version = tool_version(command, *args)
        if version:
            line(OK, command, version)
        else:
            line(BAD, command, f"not found — install: {hint}")
            ok = False

    docker = tool_version("docker", "--version")
    line(
        OK if docker else WARN,
        "docker",
        docker or "not found (optional: only for the pg/s3 profiles)",
    )
    return ok


def check_config() -> bool:
    print("\nConfiguration")
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        line(OK, ".env", str(env_file.relative_to(REPO_ROOT)))
    else:
        line(BAD, ".env", "missing — run: make setup (or cp .env.example .env)")
        return False
    return True


def check_app() -> bool:
    """Import the real settings so this reports what the app would actually do."""
    print("\nSelected adapters")
    try:
        from app.core.config import get_settings
    except Exception as exc:  # noqa: BLE001
        line(BAD, "api package", f"could not import settings ({exc}) — run: make install")
        return False

    settings = get_settings()
    engine = "Postgres" if settings.database_url.startswith("postgresql") else "SQLite"

    line(OK, "environment", settings.environment)
    line(OK, "attorney roster", f"{len(settings.roster)} account(s)")
    line(OK, "database", f"{engine}")
    line(OK, "file storage", "S3 / MinIO" if settings.uses_s3 else "local disk")
    line(OK, "email", "Resend" if settings.uses_resend else "console (logged, not sent)")
    line(OK, "rate limiting", "on" if settings.rate_limit_enabled else "off")

    insecure = settings.insecure_defaults()
    if insecure:
        line(BAD, "credentials", f"placeholders in use outside local: {', '.join(insecure)}")
        return False
    if settings.environment == "local":
        line(WARN, "credentials", "placeholder values (fine locally, never deploy them)")

    print("\nDatabase")
    try:
        from sqlalchemy import text

        from app.db.session import engine as db_engine

        with db_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        # Render the target without the absolute path: this output gets pasted into
        # issues and transcripts, and a home directory is personal information.
        url = db_engine.url
        target = (
            f"sqlite: {Path(url.database).name}"
            if url.drivername.startswith("sqlite") and url.database
            else f"{url.drivername}: {url.host or ''}/{url.database or ''}"
        )
        line(OK, "connection", target)
    except Exception as exc:  # noqa: BLE001
        line(BAD, "connection", f"unreachable ({type(exc).__name__}) — run: make migrate")
        return False

    try:
        from app.db.models import Lead

        with db_engine.connect() as connection:
            query = text(f"SELECT count(*) FROM {Lead.__tablename__}")
            count = connection.execute(query).scalar()
        line(OK, "leads table", f"{count} rows")
    except Exception:  # noqa: BLE001
        line(BAD, "leads table", "missing — run: make migrate")
        return False

    return check_assignments(settings, db_engine)


def check_assignments(settings, db_engine) -> bool:
    """Warn when leads are owned by someone the roster no longer knows (FR10).

    ``leads.assigned_to`` holds an email, not a foreign key, because the roster lives
    in configuration. Removing an attorney from ``ATTORNEYS`` therefore leaves their
    leads pointing at an address that no longer resolves to a name -- the assignment is
    still a true historical fact, but nobody is picking that work up. Surface it rather
    than let it sit silently.
    """
    from sqlalchemy import text as sql

    known = {str(attorney.email).lower() for attorney in settings.roster}

    with db_engine.connect() as connection:
        rows = connection.execute(
            sql(
                "SELECT assigned_to, count(*) FROM leads "
                "WHERE assigned_to IS NOT NULL GROUP BY assigned_to"
            )
        ).all()

    orphaned = [(email, count) for email, count in rows if (email or "").lower() not in known]
    if not orphaned:
        assigned = sum(count for _, count in rows)
        line(OK, "assignments", f"{assigned} assigned to roster attorneys")
        return True

    total = sum(count for _, count in orphaned)
    line(WARN, "assignments", f"{total} lead(s) assigned to {len(orphaned)} unknown attorney(s)")
    for email, count in orphaned:
        print(f"        {email} ({count} lead(s)) is not in ATTORNEYS — reassign or restore")
    # A warning, not a failure: the data is consistent, the roster simply moved on.
    return True


def main() -> int:
    print("\n\033[1malma doctor\033[0m")
    healthy = all([check_tools(), check_config(), check_app()])

    print()
    if healthy:
        print("Everything looks healthy. Start it with: make dev\n")
        return 0
    print("Some checks failed — see the hints above.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
