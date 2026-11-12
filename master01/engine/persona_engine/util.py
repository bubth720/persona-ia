"""Shared helpers: hashing, atomic writes, perceptual hash. Stdlib + Pillow only."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def atomic_write_json(path: Path, data) -> None:
    atomic_write_bytes(path, json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except FileNotFoundError:
        return default


def dhash(img: Image.Image, size: int = 16) -> int:
    """Difference hash on an orientation-corrected greyscale thumbnail (help only, not identity)."""
    g = ImageOps.exif_transpose(img).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.tobytes())
    bits = 0
    for y in range(size):
        row = px[y * (size + 1):(y + 1) * (size + 1)]
        for x in range(size):
            bits = (bits << 1) | (1 if row[x] > row[x + 1] else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
