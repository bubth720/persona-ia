"""Détection matérielle PC et profils PERSONA (léger / standard / avancé). Windows, Linux, macOS.

Écrit hardware_report.json dans le dossier de données PERSONA (lu aussi par PERSONA LIVE).
Aucune donnée n'est envoyée nulle part.

  python -m persona_engine.hardware [--json]
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .util import now_iso


def data_dir() -> Path:
    """Même dossier que PERSONA LIVE (Godot, custom_user_dir_name="PERSONA")."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "PERSONA"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run(cmd: list[str], timeout: int = 20) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def ram_gb() -> tuple[float, float]:
    """(total, disponible) en Go."""
    try:
        import psutil  # optionnel
        vm = psutil.virtual_memory()
        return vm.total / 2**30, vm.available / 2**30
    except ImportError:
        pass
    if sys.platform == "win32":
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullTotalPhys / 2**30, m.ullAvailPhys / 2**30
    try:
        info = dict(l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines() if ":" in l)
        kb = lambda k: float(info[k].split()[0])  # noqa: E731
        return kb("MemTotal") / 2**20, kb("MemAvailable") / 2**20
    except Exception:  # noqa: BLE001
        return -1.0, -1.0


def gpus() -> list[dict]:
    out = []
    smi = shutil.which("nvidia-smi")
    if smi:
        q = _run([smi, "--query-gpu=name,memory.total,driver_version,compute_cap", "--format=csv,noheader,nounits"])
        for line in q.splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 3:
                out.append({"name": parts[0], "vram_gb": round(float(parts[1]) / 1024, 1), "driver": parts[2],
                            "compute_cap": parts[3] if len(parts) > 3 else "", "vendor": "NVIDIA", "cuda": True})
    if not out and sys.platform == "win32":
        q = _run(["powershell", "-NoProfile", "-Command",
                  "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json"])
        try:
            data = json.loads(q) if q else []
            for g in data if isinstance(data, list) else [data]:
                ram = g.get("AdapterRAM") or 0
                out.append({"name": g.get("Name", ""), "vram_gb": round(ram / 2**30, 1) if ram > 0 else -1,
                            "driver": g.get("DriverVersion", ""), "vendor": "", "cuda": False,
                            "note": "AdapterRAM plafonné à 4 Go par Windows : VRAM réelle possiblement supérieure"})
        except json.JSONDecodeError:
            pass
    if not out and sys.platform.startswith("linux"):
        for line in _run(["sh", "-c", "lspci 2>/dev/null | grep -Ei 'vga|3d'"]).splitlines():
            out.append({"name": line.split(":", 2)[-1].strip(), "vram_gb": -1, "vendor": "", "cuda": False})
    return out


def vulkan_available() -> bool:
    return bool(shutil.which("vulkaninfo")) or (sys.platform == "win32" and Path(os.environ.get("SystemRoot", "C:/Windows"), "System32", "vulkan-1.dll").exists())


def choose_profile(ram_total: float, vram: float) -> str:
    if ram_total >= 28 and vram >= 10:
        return "avance"
    if ram_total >= 14 and vram >= 6:
        return "standard"
    return "leger"


# Réglages de génération par profil : jamais un modèle plus gros que la mémoire disponible.
GENERATION = {
    "leger": {"sd_backend": "sd.cpp CPU (ou Vulkan/CUDA si ≥ 4 Go VRAM, encodeur texte et VAE sur CPU)",
              "model_quant": "q4_K", "resolution": 640, "steps": 5, "threads": "cœurs physiques",
              "min_free_ram_gb": 3.5, "note": "génération ~ plusieurs minutes/image ; fermer PERSONA LIVE pendant le calcul"},
    "standard": {"sd_backend": "sd.cpp CUDA/Vulkan", "model_quant": "q8_0", "resolution": 768, "steps": 6,
                 "min_free_ram_gb": 5.5, "note": "ou PhotoMaker V2 (diffusers) si ≥ 8 Go VRAM"},
    "avance": {"sd_backend": "diffusers CUDA (PhotoMaker V2 / modèles de master01/SELECTION_MODELES_LOCAUX.md)",
               "model_quant": "fp16", "resolution": 1024, "steps": 30, "min_free_ram_gb": 8.0, "note": ""},
}


def detect() -> dict:
    total, avail = ram_gb()
    g = gpus()
    vram = max([x.get("vram_gb", -1) for x in g] or [-1])
    disk = shutil.disk_usage(data_dir())
    prof = choose_profile(total, vram)
    return {
        "generated_at": now_iso(),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python": platform.python_version(),
        "cpu": {"name": platform.processor() or _run(["sh", "-c", "grep -m1 'model name' /proc/cpuinfo | cut -d: -f2"]).strip(),
                "logical_cores": os.cpu_count(), "machine": platform.machine()},
        "ram_gb": {"total": round(total, 1), "available": round(avail, 1)},
        "gpu": {"list": g, "vram_gb": vram, "cuda": any(x.get("cuda") for x in g), "vulkan": vulkan_available()},
        "disk_free_gb": round(disk.free / 2**30, 1),
        "profile": prof,
        "generation": GENERATION[prof],
        "rules": ["ne jamais charger un modèle plus gros que la mémoire disponible",
                  "ne pas lancer simultanément un traitement IA lourd et PERSONA LIVE"],
    }


def write_report() -> Path:
    rep = detect()
    p = data_dir() / "hardware_report.json"
    p.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------- exclusion IA lourde / moteur 3D
def live_running() -> bool:
    lock = data_dir() / "persona_live.lock"
    if not lock.exists():
        return False
    try:
        pid = int(lock.read_text().strip())
    except ValueError:
        return False
    if sys.platform == "win32":
        return str(pid) in _run(["tasklist", "/FI", f"PID eq {pid}", "/NH"])
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    path = write_report()
    rep = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(rep, indent=2, ensure_ascii=False) if "--json" in sys.argv else
          f"Profil {rep['profile']} · RAM {rep['ram_gb']['total']} Go · VRAM {rep['gpu']['vram_gb']} Go · rapport : {path}")
