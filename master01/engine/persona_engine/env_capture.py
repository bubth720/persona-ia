"""Phase B1 — capture the GPU environment (nvidia-smi, python, torch, CUDA, disk, pip freeze, PhotoMaker commit)."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .util import now_iso, atomic_write_json


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"indisponible: {exc}"


def capture(photomaker_dir: str | None = None) -> dict:
    info = {"captured_at": now_iso(), "python": sys.version, "executable": sys.executable,
            "platform": platform.platform(), "nvidia_smi": _run(["nvidia-smi"]),
            "disk_free_gb": round(shutil.disk_usage("/").free / 2**30, 1),
            "pip_freeze": _run([sys.executable, "-m", "pip", "freeze"]).splitlines()}
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = torch.version.cuda
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            info["gpu"] = p.name
            info["vram_gb"] = round(p.total_memory / 2**30, 2)
    except Exception as exc:  # noqa: BLE001
        info["torch"] = f"import impossible: {exc}"
    if photomaker_dir:
        info["photomaker_commit"] = _run(["git", "-C", photomaker_dir, "rev-parse", "HEAD"])
    return info


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "env_capture.json")
    data = capture(sys.argv[2] if len(sys.argv) > 2 else None)
    atomic_write_json(out, data)
    print(json.dumps({k: v for k, v in data.items() if k != "pip_freeze"}, indent=2, ensure_ascii=False))
