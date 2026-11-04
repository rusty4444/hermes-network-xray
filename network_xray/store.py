"""Explicit-root, private, atomic probe persistence; no profile/global path."""

from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import stat
import threading
import uuid

from .bundles import _unique_object, overall, valid_id, validate_bundle
from .collector import MAX_BUNDLE_BYTES

MAX_RECORDS = 1000
HISTORY_LIMIT = 100
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _directory_fd(path):
    """Walk with no-follow dirfds so even ancestor swaps cannot redirect writes."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            if component in (".", ".."):
                raise ValueError("Store path cannot contain traversal")
            try:
                os.mkdir(component, mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


class Store:
    def __init__(self, root):
        self.root = Path(root).absolute()
        if self.root == Path(self.root.anchor):
            raise ValueError("A dedicated store directory is required")
        with _LOCKS_GUARD:
            self._lock = _LOCKS.setdefault(str(self.root), threading.RLock())
        with self._directory() as descriptor:
            os.fchmod(descriptor, 0o700)

    @contextmanager
    def _directory(self):
        try:
            descriptor = _directory_fd(self.root)
        except OSError:
            raise ValueError("Store directory is unavailable or unsafe") from None
        try:
            yield descriptor
        finally:
            os.close(descriptor)

    def _read(self, descriptor, identifier):
        valid_id(identifier)
        try:
            file_descriptor = os.open(
                f"{identifier}.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
            )
        except FileNotFoundError:
            raise KeyError("Probe not found") from None
        except OSError:
            raise ValueError("Unsafe probe file") from None
        with os.fdopen(file_descriptor, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_size > MAX_BUNDLE_BYTES + 256
            ):
                raise ValueError("Unsafe or oversized probe file")
            raw = handle.read(MAX_BUNDLE_BYTES + 257)
        try:
            record = json.loads(raw, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError("Invalid stored record") from None
        if (
            type(record) is not dict
            or set(record) != {"probe", "origin"}
            or record["origin"] not in ("local", "imported")
        ):
            raise ValueError("Invalid stored record")
        probe = validate_bundle(record["probe"])
        if probe["id"] != identifier:
            raise ValueError("Stored probe ID mismatch")
        return {"probe": probe, "origin": record["origin"]}

    def save_probe(self, bundle, origin):
        probe = validate_bundle(bundle)
        if origin not in ("local", "imported"):
            raise ValueError("Origin must be local or imported")
        record = {"probe": probe, "origin": origin}
        with self._lock, self._directory() as descriptor:
            try:
                existing = self._read(descriptor, probe["id"])
            except KeyError:
                existing = None
            if existing is not None:
                if existing["probe"] != probe:
                    raise ValueError("Probe ID collision with different content")
                return existing
            if len(self._names(descriptor)) >= MAX_RECORDS:
                raise ValueError("Store limit reached (1000 records); no data deleted")
            self._write(descriptor, record)
            return record

    def _write(self, descriptor, record):
        temporary = f".{uuid.uuid4()}.tmp"
        raw = json.dumps(
            record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
        file_descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=descriptor,
        )
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            # Atomic create, not replace: a concurrent external writer cannot be clobbered.
            os.link(
                temporary,
                f"{record['probe']['id']}.json",
                src_dir_fd=descriptor,
                dst_dir_fd=descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            raise ValueError("Concurrent probe ID collision") from None
        finally:
            os.unlink(temporary, dir_fd=descriptor)
        os.fsync(descriptor)

    @staticmethod
    def _names(descriptor):
        names = [name for name in os.listdir(descriptor) if name.endswith(".json")]
        if len(names) > MAX_RECORDS:
            raise ValueError("Store exceeds record cap")
        return names

    def get_probe(self, identifier):
        valid_id(identifier)
        with self._lock, self._directory() as descriptor:
            return self._read(descriptor, identifier)

    def list_probes(self):
        with self._lock, self._directory() as descriptor:
            records = [self._read(descriptor, name[:-5]) for name in self._names(descriptor)]
        records.sort(
            key=lambda record: (
                datetime.fromisoformat(record["probe"]["captured_at"].replace("Z", "+00:00")),
                record["probe"]["id"],
            ),
            reverse=True,
        )
        return {
            "probes": [
                {
                    "id": record["probe"]["id"],
                    "label": record["probe"]["vantage"]["label"],
                    "url": record["probe"]["target"]["url"],
                    "captured_at": record["probe"]["captured_at"],
                    "overall": overall(record["probe"]),
                    "origin": record["origin"],
                }
                for record in records[:HISTORY_LIMIT]
            ]
        }
