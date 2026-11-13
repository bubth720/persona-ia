"""Backend stable-diffusion.cpp (sd-cli) : SDXL + PhotoMaker v1, 100 % local sur processeur.

Pensé pour le POCO X8 Pro (Termux, arm64, CPU) et pour tout PC sans dépendance Python lourde.
* Aucun réseau : sd-cli ne lit que des fichiers locaux.
* PhotoMaker v1 lit directement un dossier d'images de référence (pas d'InsightFace).
* Les vues corps n'ont pas de contrôle de pose ici (prompt seul) : signalé dans chaque manifeste.

Configuration (variables d'environnement ou arguments) :
  PERSONA_SDCPP_BIN      chemin de sd-cli
  PERSONA_SDCPP_MODEL    modèle SDXL (.safetensors ou .gguf quantifié, p. ex. q8_0)
  PERSONA_SDCPP_VAE      VAE SDXL fp16-fix (optionnel mais recommandé)
  PERSONA_SDCPP_PM       photomaker-v1.safetensors (format converti pour sd.cpp)
"""
from __future__ import annotations

import os
import platform
try:
    import resource  # Unix
except ImportError:  # Windows
    resource = None
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ..prompts import VIEW_PROMPTS, STYLE, NEGATIVE
from ..util import sha256_file
from .base import Backend, GenerationResult

SDCPP_COMMIT = "e239e4b0fd3de49834cec67031a44796ca465abc"   # épinglé (2026-10-30)

# Lightning : 4 à 8 pas, CFG basse. Valeurs de départ à ajuster après revue humaine.
DEFAULTS = {"steps": 6, "cfg": 1.8, "sampler": "euler", "scheduler": "sgm_uniform", "pm_style_strength": 20,
            "face_size": (768, 768), "body_size": (576, 1024)}


class SdCppBackend(Backend):
    name = "sdcpp_photomaker_v1"
    is_generation = True

    def __init__(self, binary: str | None = None, model: str | None = None, vae: str | None = None,
                 photomaker: str | None = None, threads: int | None = None, **overrides):
        self.binary = binary or os.environ.get("PERSONA_SDCPP_BIN", "sd-cli")
        self.model = model or os.environ.get("PERSONA_SDCPP_MODEL", "")
        self.vae = vae or os.environ.get("PERSONA_SDCPP_VAE", "")
        self.photomaker = photomaker or os.environ.get("PERSONA_SDCPP_PM", "")
        self.threads = threads or int(os.environ.get("PERSONA_SDCPP_THREADS", "0")) or (os.cpu_count() or 4)
        self.cfg = DEFAULTS | overrides
        missing = [k for k, v in (("modèle", self.model), ("photomaker", self.photomaker)) if not v or not Path(v).is_file()]
        if not shutil.which(self.binary) and not Path(self.binary).is_file():
            missing.append("sd-cli")
        if missing:
            raise FileNotFoundError("fichiers locaux manquants : " + ", ".join(missing))
        self._model_sha = None

    def describe(self) -> dict:
        return {"name": self.name, "is_generation": True, "runtime": f"stable-diffusion.cpp@{SDCPP_COMMIT[:7]}",
                "model": Path(self.model).name, "threads": self.threads}

    def command(self, *, prompt: str, negative: str, seed: int, width: int, height: int, out: Path,
                id_dir: Path | None, steps: int, cfg: float) -> list[str]:
        cmd = [self.binary, "-m", self.model, "-p", prompt, "-n", negative, "--seed", str(seed),
               "-W", str(width), "-H", str(height), "--steps", str(steps), "--cfg-scale", str(cfg),
               "--sampling-method", self.cfg["sampler"], "--scheduler", self.cfg["scheduler"],
               "--threads", str(self.threads), "--vae-tiling", "-o", str(out)]
        if self.vae:
            cmd += ["--vae", self.vae]
        if id_dir is not None:
            cmd += ["--photo-maker", self.photomaker, "--pm-id-images-dir", str(id_dir),
                    "--pm-style-strength", str(self.cfg["pm_style_strength"])]
        return cmd

    def run(self, cmd: list[str], log_path: Path) -> tuple[float, float]:
        """Exécute sd-cli ; mesure la RAM de pointe (getrusage sous Unix, psutil peak_wset sous Windows)."""
        before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if resource else 0
        t0 = time.time()
        peak_mb = 0.0
        with open(log_path, "w") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            try:
                import psutil  # optionnel
                ps = psutil.Process(proc.pid)
            except Exception:  # noqa: BLE001
                ps = None
            while proc.poll() is None:
                if ps is not None:
                    try:
                        mi = ps.memory_info()
                        peak_mb = max(peak_mb, getattr(mi, "peak_wset", mi.rss) / 2**20)
                    except Exception:  # noqa: BLE001
                        pass
                time.sleep(0.5)
                if time.time() - t0 > 3 * 3600:
                    proc.kill()
                    raise RuntimeError("sd-cli : délai dépassé (3 h)")
        dt = time.time() - t0
        if resource:
            peak_mb = max(peak_mb, max(before, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024)
        if proc.returncode != 0:
            tail = Path(log_path).read_text(errors="replace")[-1500:]
            raise RuntimeError(f"sd-cli a échoué (code {proc.returncode}) : {tail}")
        return dt, peak_mb

    def generate(self, *, kind, view, references, seed, params, out_path: Path,
                 use_photomaker: bool = True) -> GenerationResult:
        if use_photomaker and not references:
            raise RuntimeError("Aucune référence autorisée fournie.")
        subject = params.get("subject_class", "woman")          # sd.cpp : man, woman, girl, boy
        trigger = f"{subject} img" if use_photomaker else f"fictitious adult {subject}"
        appearance = params.get("appearance", "")
        prompt = ", ".join(x for x in (f"a photo of a {trigger}", VIEW_PROMPTS[view], appearance, STYLE) if x)
        negative = params.get("negative_prompt", NEGATIVE)
        w, h = self.cfg["face_size"] if kind == "face" else self.cfg["body_size"]
        w, h = int(params.get("width", w)), int(params.get("height", h))
        steps, cfg = int(params.get("steps", self.cfg["steps"])), float(params.get("guidance", self.cfg["cfg"]))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pm-ids-") as tmp:
            id_dir = None
            if use_photomaker:
                id_dir = Path(tmp)
                for i, ref in enumerate(references[:4]):
                    # sd.cpp lit les extensions usuelles ; les références du worker sont stockées en .img
                    shutil.copyfile(ref, id_dir / f"ref{i}.png" if _is_png(ref) else id_dir / f"ref{i}.jpg")
            cmd = self.command(prompt=prompt, negative=negative, seed=seed, width=w, height=h, out=out_path,
                               id_dir=id_dir, steps=steps, cfg=cfg)
            dt, peak_mb = self.run(cmd, out_path.with_suffix(".log"))
        if self._model_sha is None and os.environ.get("PERSONA_HASH_MODELS") == "1":
            self._model_sha = sha256_file(Path(self.model))
        warnings = []
        if kind == "body":
            warnings.append("Pas de contrôle de pose dans ce backend : cadrage obtenu par le prompt seul.")
            warnings.append("PhotoMaker conditionne le visage : morphologie du corps non garantie.")
        if view == "pied_dos":
            warnings.append("Vue de dos : estimation du modèle, non documentée par les références.")
        if not use_photomaker:
            warnings.append("Image sans référence (personne fictive) : sert uniquement de référence de démonstration.")
        return GenerationResult(
            path=out_path, engine=self.name,
            model=f"{Path(self.model).name} + {Path(self.photomaker).name if use_photomaker else '—'}",
            model_version=f"stable-diffusion.cpp@{SDCPP_COMMIT[:7]}" + (f" model_sha256={self._model_sha}" if self._model_sha else ""),
            licence="sd.cpp MIT ; PhotoMaker Apache-2.0 ; RealVisXL CreativeML OpenRAIL++-M",
            is_generation=True, seed=seed, prompt=prompt, negative_prompt=negative,
            params={"steps": steps, "cfg_scale": cfg, "width": w, "height": h, "sampler": self.cfg["sampler"],
                    "scheduler": self.cfg["scheduler"], "pm_style_strength": self.cfg["pm_style_strength"],
                    "photomaker": use_photomaker, "n_references": min(len(references), 4) if use_photomaker else 0,
                    "threads": self.threads},
            duration_s=round(dt, 1), peak_vram_mb=None,
            hardware=f"CPU {platform.machine()} ×{self.threads} · RAM pic {peak_mb:.0f} Mo · {platform.system()}",
            warnings=warnings)


def _is_png(p: Path) -> bool:
    with open(p, "rb") as f:
        return f.read(4) == b"\x89PNG"
