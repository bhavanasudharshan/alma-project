"""The storage port. Swapping local disk for S3 is a new implementation, nothing else (E2)."""

from typing import BinaryIO, Protocol


class FileStorage(Protocol):
    """Binary blob store keyed by an opaque string."""

    def save(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        """Persist ``fileobj`` under ``key``, overwriting any existing object."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Return a readable binary stream for ``key``.

        :raises FileNotFoundError: if the key does not exist.
        """
        ...

    def delete(self, key: str) -> None:
        """Remove ``key``. Deleting a missing key is not an error."""
        ...
