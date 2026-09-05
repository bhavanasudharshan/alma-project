"""Local-disk storage: the P0 default, so the app runs with no Docker and no cloud ($1)."""

import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_MAX_FILENAME_LEN = 120


def sanitise_filename(filename: str) -> str:
    """Reduce an untrusted filename to a flat, safe basename (S2).

    Strips any directory component, replaces everything outside a conservative
    allow-list, and collapses leading dots so ``../../etc/passwd`` and ``.bashrc``
    cannot escape or hide.
    """
    # Normalise Windows separators first: Path() does not treat "\\" as one on POSIX.
    base = Path(filename.replace("\\", "/")).name
    cleaned = _UNSAFE_CHARS.sub("_", base).lstrip(".")
    cleaned = cleaned[:_MAX_FILENAME_LEN]
    return cleaned or "resume"


def display_filename(filename: str) -> str:
    """Return a flat, printable filename safe to echo back in a response header.

    Distinct from :func:`sanitise_filename`, which produces an ASCII-only *storage
    key*. Here the goal is presentation: strip every directory component and control
    character so a name like ``../../etc/passwd.pdf`` cannot escape a download
    directory, while preserving Unicode so ``résumé señor.pdf`` survives intact for
    the attorney (C1). The caller still percent-encodes it per RFC 5987.
    """
    base = Path(filename.replace("\\", "/")).name
    cleaned = "".join(ch for ch in base if ch.isprintable() and ch not in "/\\").lstrip(".")
    return cleaned[:_MAX_FILENAME_LEN] or "resume"


def build_key(filename: str) -> str:
    """Return a collision-free storage key: ``<uuid>/<sanitised filename>``."""
    return f"{uuid.uuid4()}/{sanitise_filename(filename)}"


class LocalDiskStorage:
    """:class:`~app.services.storage.base.FileStorage` backed by a directory tree."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Map ``key`` to an absolute path, refusing anything outside the root (S2)."""
        candidate = (self._root / key).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(f"Refusing to access a path outside the storage root: {key!r}")
        return candidate

    def save(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        """Stream ``fileobj`` to disk without buffering it whole in memory (P1)."""
        destination = self._resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            shutil.copyfileobj(fileobj, handle)

    def open(self, key: str) -> BinaryIO:
        """Open the stored object for reading."""
        return self._resolve(key).open("rb")

    def delete(self, key: str) -> None:
        """Delete the stored object, ignoring an already-absent key."""
        self._resolve(key).unlink(missing_ok=True)
