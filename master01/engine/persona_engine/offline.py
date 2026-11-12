"""Règle « 100 % local » : la génération ne doit jamais accéder au réseau.

Les poids sont téléchargés une seule fois, volontairement, avec PERSONA_ALLOW_DOWNLOAD=1
(par exemple : ``PERSONA_ALLOW_DOWNLOAD=1 python -m persona_engine.offline --prefetch``).
Ensuite, HuggingFace/diffusers/transformers sont forcés en mode hors ligne : un modèle
absent du cache provoque une erreur explicite au lieu d'un téléchargement silencieux.
"""
from __future__ import annotations

import argparse
import os

OFFLINE_VARS = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "DIFFUSERS_OFFLINE")


def download_allowed() -> bool:
    return os.environ.get("PERSONA_ALLOW_DOWNLOAD") == "1"


def enforce_offline() -> bool:
    """Active le mode hors ligne sauf si le téléchargement est explicitement autorisé."""
    if download_allowed():
        return False
    for v in OFFLINE_VARS:
        os.environ[v] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("DO_NOT_TRACK", "1")
    return True


def prefetch() -> None:
    """Télécharge une fois les poids du backend PhotoMaker V2 (étape d'installation)."""
    if not download_allowed():
        raise SystemExit("Téléchargement refusé : relancer avec PERSONA_ALLOW_DOWNLOAD=1")
    from huggingface_hub import hf_hub_download, snapshot_download
    from .backends.photomaker_v2 import BASE_MODEL, PM_REPO, PM_FILE, POSE_CONTROLNET
    print(hf_hub_download(PM_REPO, PM_FILE))
    for repo in (BASE_MODEL, POSE_CONTROLNET):
        print(snapshot_download(repo, allow_patterns=["*.json", "*.txt", "*fp16*.safetensors",
                                                     "*.safetensors" if repo == POSE_CONTROLNET else "*fp16*"]))
    print("Poids en cache. Les générations suivantes fonctionnent sans Internet.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefetch", action="store_true")
    if ap.parse_args().prefetch:
        prefetch()
