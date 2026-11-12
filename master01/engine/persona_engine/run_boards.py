"""Phase B/D/E/F driver: generate the face (6 views) and body (4 views) boards with a real backend.

Modes
  --demo-synthetic : creates a FICTITIOUS person with the base SDXL model (no reference),
                     then uses those images as references. Proves the pipeline (Gate B) without
                     any personal data. Never counts as identity fidelity (Gate D/E).
  --refs DIR       : authorised references of the consenting adult, read from a private folder
                     (e.g. mounted Drive). Requires --consent "<declaration>". Nothing is uploaded
                     anywhere by this script; outputs stay in --out.

Example (Colab, inside the Python 3.11 venv):
  python -m persona_engine.run_boards --demo-synthetic --out /content/persona_out
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .backends import get_backend
from .refbank import RefBank
from .util import sha256_file
from .worker import JobManager


def make_synthetic_person(out_dir: Path, seed: int, subject: str) -> list[Path]:
    import torch
    from diffusers import StableDiffusionXLPipeline
    from .backends.photomaker_v2 import BASE_MODEL, STYLE, NEGATIVE
    pipe = StableDiffusionXLPipeline.from_pretrained(BASE_MODEL, torch_dtype=torch.float16, variant="fp16",
                                                     use_safetensors=True)
    pipe.enable_model_cpu_offload()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, pose in enumerate(["frontal head and shoulders portrait", "three-quarter head portrait",
                              "frontal portrait, slight smile"]):
        g = torch.Generator("cuda").manual_seed(seed + i)
        im = pipe(prompt=f"photo of a fictitious adult {subject}, short brown hair, {pose}, {STYLE}",
                  negative_prompt=NEGATIVE, num_inference_steps=30, generator=g, width=1024, height=1024).images[0]
        p = out_dir / f"synthetic_ref_{i}.png"
        im.save(p)
        paths.append(p)
    del pipe
    torch.cuda.empty_cache()
    return paths


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo-synthetic", action="store_true")
    g.add_argument("--refs")
    ap.add_argument("--consent", default="")
    ap.add_argument("--subject", default="person", help="man / woman / person")
    ap.add_argument("--appearance", default="plain fitted grey t-shirt, dark jeans, white sneakers")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--kinds", default="face,body")
    ap.add_argument("--steps", type=int, default=40)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.demo_synthetic:
        refs = make_synthetic_person(out / "synthetic_refs", a.seed, a.subject)
        consent = "personne fictive générée (mode démonstration, aucune donnée personnelle)"
    else:
        if not a.consent.strip():
            raise SystemExit("--consent requis : déclaration d'autorisation de la personne représentée")
        bank = RefBank(out / "refbank")
        files = sorted(p for p in Path(a.refs).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
        print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in
                          bank.import_paths(files, authorized=True, consent_note=a.consent).items()}))
        refs = bank.select_for_engine(list(bank.records), remote=False, remote_consent=False)
        consent = a.consent
    backend = get_backend("photomaker_v2", steps=a.steps)
    mgr = JobManager(out / "worker", backend)
    summary = {"mode": "demo_synthetic" if a.demo_synthetic else "authorised_references", "consent": consent,
               "references_sha256": [sha256_file(p) for p in refs], "jobs": {}}
    try:
        for kind in a.kinds.split(","):
            job = mgr.create({"kind": kind, "consent_declared": True, "seed": a.seed, "profile": kind,
                              "params": {"subject_class": a.subject, "appearance": a.appearance}})
            for p in refs:
                mgr.add_reference(job["id"], sha256_file(p), p.read_bytes(), consent=True)
            t0 = time.time()
            mgr.start(job["id"])
            job = mgr.wait(job["id"], timeout=6 * 3600)
            summary["jobs"][kind] = {"id": job["id"], "state": job["state"], "seconds": round(time.time() - t0),
                                     "board_dir": str(out / "worker" / "jobs" / job["id"] / "board"),
                                     "views": {v: {"state": s["state"], "error": s.get("error"),
                                                   "duration_s": (s.get("provenance") or {}).get("duration_s"),
                                                   "peak_vram_mb": (s.get("provenance") or {}).get("peak_vram_mb")}
                                               for v, s in job["views"].items()}}
            print(json.dumps(summary["jobs"][kind], indent=2, ensure_ascii=False), flush=True)
    finally:
        mgr.shutdown()
        backend.close()
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
