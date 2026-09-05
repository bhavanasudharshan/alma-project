"""Populate a local database with demo leads (C2).

Idempotent: reruns leave the same four leads rather than piling up duplicates. Refuses
to run outside ``ENVIRONMENT=local`` -- this writes fictional people into a leads
table, which must never happen against anything real.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "api"))

from app.core import deps  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.models import Lead, LeadEvent, LeadState  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.email.console import ConsoleEmailService  # noqa: E402
from app.services.lead_service import SYSTEM_ACTOR, generate_tracking_code  # noqa: E402
from app.services.storage.local import LocalDiskStorage, build_key  # noqa: E402

# Fictional people, all @example.com. No real person's details belong in seed data.
# (first, last, email, state, roster index to assign to — None leaves it unassigned)
DEMO_LEADS = [
    ("Ada", "Lovelace", "ada@example.com", LeadState.PENDING, None),
    ("Grace", "Hopper", "grace@example.com", LeadState.PENDING, 0),
    ("Katherine", "Johnson", "katherine@example.com", LeadState.REACHED_OUT, 1),
    ("Dorothy", "Vaughan", "dorothy@example.com", LeadState.QUALIFIED, 2),
]

# How each lead got where it is, so the audit trail and the status portal look real.
PATH_TO_STATE = {
    LeadState.PENDING: [],
    LeadState.REACHED_OUT: [LeadState.REACHED_OUT],
    LeadState.QUALIFIED: [LeadState.REACHED_OUT, LeadState.QUALIFIED],
}


def tiny_pdf(name: str) -> bytes:
    """A structurally valid one-page PDF, so the app's own validation would accept it."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R >>",
        (
            f"<< /Length 60 >>\nstream\nBT /F1 12 Tf 20 120 Td (Resume - {name}) Tj ET\nendstream"
        ).encode(),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    out += trailer.encode()
    return bytes(out)


def force_console_email() -> None:
    """Guarantee seeding can never send a real email (C2).

    Seeding writes rows directly and does not notify anyone today, but a developer
    with ``RESEND_API_KEY`` in their ``.env`` is one careless edit away from mailing
    four fictional people from a demo script. Pinning the adapter for the life of this
    process makes that impossible rather than merely unlikely.
    """
    deps.get_email_service.cache_clear()
    deps.get_email_service = lambda: ConsoleEmailService()  # type: ignore[assignment]


def main() -> int:
    force_console_email()
    settings = get_settings()

    if settings.environment != "local":
        print(
            f"Refusing to seed: ENVIRONMENT is {settings.environment!r}, not 'local'.\n"
            "This writes fictional leads and must never run against a real database.",
            file=sys.stderr,
        )
        return 1

    storage = LocalDiskStorage(root=settings.upload_path)
    created = 0

    with SessionLocal() as session:
        roster = settings.roster
        for first, last, email, target, attorney_index in DEMO_LEADS:
            existing = session.query(Lead).filter(Lead.email == email).one_or_none()
            if existing is not None:
                continue

            filename = f"{first.lower()}-{last.lower()}-resume.pdf"
            key = build_key(filename)
            import io

            storage.save(key, io.BytesIO(tiny_pdf(f"{first} {last}")), "application/pdf")

            lead = Lead(
                first_name=first,
                last_name=last,
                email=email,
                resume_key=key,
                resume_filename=filename,
                resume_content_type="application/pdf",
                state=target,
                tracking_code=generate_tracking_code(),
                # Spread across the roster so the "Mine" tab and the assignment column
                # have something to show; wraps when fewer attorneys are configured.
                assigned_to=(
                    str(roster[attorney_index % len(roster)].email)
                    if attorney_index is not None
                    else None
                ),
            )
            session.add(lead)
            session.flush()

            # Walk the same path a real lead would, so the trail is coherent.
            session.add(
                LeadEvent(
                    lead_id=lead.id, from_state=None, to_state=LeadState.PENDING, actor=SYSTEM_ACTOR
                )
            )
            previous = LeadState.PENDING
            for step in PATH_TO_STATE[target]:
                session.add(
                    LeadEvent(
                        lead_id=lead.id,
                        from_state=previous,
                        to_state=step,
                        actor=settings.attorney_email,
                    )
                )
                previous = step

            created += 1

        session.commit()

        total = session.query(Lead).count()
        by_state = {
            state.value: session.query(Lead).filter(Lead.state == state).count()
            for state in LeadState
        }

    if created:
        print(f"Seeded {created} demo lead(s).")
    else:
        print("Demo leads already present; nothing to do.")
    print(f"Leads in the database: {total}  ({', '.join(f'{k}={v}' for k, v in by_state.items())})")
    print(f"Attorneys on the roster: {', '.join(str(a.email) for a in get_settings().roster)}")
    print("Sign in at http://localhost:3000/login with the credentials in your .env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
