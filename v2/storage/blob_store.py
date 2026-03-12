from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from v2.storage.protocols import BlobReferenceStore


def _validate_name(name: str) -> str:
    path = Path(name)
    if path.name != name or name in {"", ".", ".."}:
        raise ValueError(f"invalid blob name: {name}")
    return name


class FileBlobStore(BlobReferenceStore):
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, name: str) -> str:
        safe_name = _validate_name(name)
        blob_id = uuid4().hex
        blob_dir = self._root / blob_id
        blob_dir.mkdir(parents=True, exist_ok=False)
        blob_path = blob_dir / safe_name
        blob_path.write_bytes(data)
        return str(Path(blob_id) / safe_name)

    def load(self, ref: str) -> bytes:
        ref_path = Path(ref)
        if ref_path.is_absolute() or ".." in ref_path.parts:
            raise ValueError(f"invalid blob ref: {ref}")
        return (self._root / ref_path).read_bytes()


class MemoryBlobStore(BlobReferenceStore):
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def save(self, data: bytes, name: str) -> str:
        safe_name = _validate_name(name)
        ref = str(Path(uuid4().hex) / safe_name)
        self._blobs[ref] = data
        return ref

    def load(self, ref: str) -> bytes:
        return self._blobs[ref]


__all__ = ["FileBlobStore", "MemoryBlobStore"]
