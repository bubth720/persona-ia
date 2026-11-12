"""Téléchargement UNIQUE des poids (étape d'installation, avec Internet), puis tout est local.

Écrit models.lock.json : dépôt, révision, fichier, taille, SHA-256 — pour vérifier hors ligne ensuite.
Usage : python fetch_models.py DEST_DIR
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

MODELS = [
    # (rôle, dépôt, fichier exact ou None = choisir le .safetensors racine le plus léger)
    ("sdxl", "SG161222/RealVisXL_V4.0_Lightning", None),
    ("vae", "madebyollin/sdxl-vae-fp16-fix", "sdxl_vae.safetensors"),
    ("photomaker", "bssrdf/PhotoMaker", "photomaker-v1.safetensors"),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main(dest: str) -> None:
    api = HfApi()
    out = Path(dest)
    out.mkdir(parents=True, exist_ok=True)
    lock = {}
    for role, repo, filename in MODELS:
        info = api.model_info(repo, files_metadata=True)
        if filename is None:
            cands = [s for s in info.siblings if s.rfilename.endswith(".safetensors") and "/" not in s.rfilename
                     and (s.size or 0) > 2**30]
            filename = min(cands, key=lambda s: s.size).rfilename
        path = Path(hf_hub_download(repo, filename, revision=info.sha, local_dir=out / role))
        lock[role] = {"repo": repo, "revision": info.sha, "file": filename, "size": path.stat().st_size,
                      "sha256": sha256(path), "license": getattr(info.card_data, "license", None) if info.card_data else None,
                      "local_path": str(path)}
        print(role, json.dumps(lock[role]), flush=True)
    (out / "models.lock.json").write_text(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
