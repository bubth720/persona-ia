"""Dossier de personnage PERSONA : interface commune des phases PHOTO → BODY → 3D → LIVE.

  <données PERSONA>/characters/<id>/
    persona_character.json   manifeste (lu par PERSONA LIVE : F2 → dossier)
    body_analysis.json       phase 2 : angles, couverture, proportions relatives
    proportions.json         paramètres transmis à Blender
    model/<id>.glb|.fbx      phase 3 : personnage riggé (démo ajustée en proportions)
    boards/                  phase 1 : planches générées (si disponibles)

Les photos restent dans la banque privée (refbank) : le manifeste ne contient que leurs empreintes.

  python -m persona_engine.character build --name "Alex" --refs DOSSIER --consent "..." [--height 1.72]
         [--blender CHEMIN_BLENDER] [--out DOSSIER]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from . import body
from .hardware import data_dir
from .refbank import RefBank
from .util import now_iso, atomic_write_json, sha256_file

SCHEMA = "persona-character/1"
def _blender_script() -> Path:
    here = Path(__file__).resolve()
    for c in (os.environ.get("PERSONA_BLENDER_SCRIPT", ""),
              here.parents[3] / "master04" / "pipeline" / "blender" / "make_character.py",   # dépôt
              here.parents[2] / "pipeline" / "blender" / "make_character.py"):              # paquet PERSONA_PC
        if c and Path(c).is_file():
            return Path(c)
    return Path("make_character.py")


BLENDER_SCRIPT = _blender_script()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "personnage"


def build(name: str, refs: Path, consent: str, out_root: Path | None = None, height: float | None = None,
          blender: str | None = None, boards: list[Path] | None = None) -> Path:
    if not consent.strip():
        raise PermissionError("Déclaration de consentement requise (personne adulte, usage autorisé).")
    cid = slug(name)
    root = (out_root or data_dir() / "characters") / cid
    (root / "model").mkdir(parents=True, exist_ok=True)
    bank = RefBank(data_dir() / "refbank")
    files = sorted(p for p in Path(refs).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    rep = bank.import_paths(files, authorized=True, consent_note=consent)
    sha_by_name = {Path(f).name: sha256_file(f) for f in files}

    analysis = body.analyze_folder(Path(refs))
    prop = body.proportions([body.PoseResult(**{k: v for k, v in r.items()}) for r in analysis["results"]], height)
    analysis["proportions"] = prop
    atomic_write_json(root / "body_analysis.json", analysis)
    atomic_write_json(root / "proportions.json", {"proportions": prop})

    references = []
    for r in analysis["results"]:
        sha = sha_by_name.get(r["file"], "")
        references.append({"sha256": sha, "view_auto": r["view"], "side": r["side"], "framing": r["framing"],
                           "confidence": r["confidence"], "view_validated": None, "method": r["method"]})
        if sha and r["view"] != "non_classe" and sha in bank.records:
            mapped = {"face": "face", "dos": "dos", "profil": "profil_gauche" if r["side"] == "gauche" else "profil_droit",
                      "trois_quarts": "trois_quarts_gauche" if r["side"] == "gauche" else "trois_quarts_droit"}[r["view"]]
            if r["framing"] == "plein_pied" and r["view"] in ("face",):
                mapped = "plein_pied"
            bank.annotate(sha, view=mapped, region="corps" if r["framing"] != "buste" else "visage", validated=False)

    model = {"file": "", "source": "", "identity_status": "aucun modèle"}
    if blender and BLENDER_SCRIPT.exists():
        log = root / "model" / "blender.log"
        with open(log, "w") as lf:
            proc = subprocess.run([blender, "-b", "--factory-startup", "--python", str(BLENDER_SCRIPT), "--",
                                   "--out", str(root / "model"), "--params", str(root / "proportions.json"), "--name", cid],
                                  stdout=lf, stderr=subprocess.STDOUT, timeout=600)
        if proc.returncode == 0 and (root / "model" / f"{cid}.glb").exists():
            meta = json.loads((root / "model" / f"{cid}.json").read_text(encoding="utf-8"))
            model = {"file": f"model/{cid}.glb", "fbx": f"model/{cid}.fbx", "source": "mannequin PERSONA ajusté aux proportions estimées",
                     "identity_status": meta["identity_status"], "rig": {"bones": len(meta["bones"]), "animations": meta["animations"]},
                     "sha256": sha256_file(root / "model" / f"{cid}.glb")}
        else:
            model["identity_status"] = f"échec Blender (voir {log.name})"

    for b in boards or []:
        (root / "boards").mkdir(exist_ok=True)
        shutil.copy2(b, root / "boards" / Path(b).name)

    manifest = {
        "schema": SCHEMA, "id": cid, "display_name": name, "created_at": now_iso(),
        "consent": {"declared": True, "note": consent},
        "references": references, "import_report": {k: len(v) if isinstance(v, list) else v for k, v in rep.items()},
        "coverage": analysis["coverage"], "proportions": prop, "model": model,
        "boards": sorted(p.name for p in (root / "boards").glob("*")) if (root / "boards").exists() else [],
        "levels": {"LIVE-DEMO": "personnage générique", "LIVE-INTEGRATED": "dossier chargeable dans PERSONA LIVE",
                   "LIVE-IDENTITY": "non atteint : aucune reconstruction fidèle du visage/corps validée"},
        "warnings": ["Les proportions sont des estimations relatives, pas des mesures.",
                     "Le modèle 3D est un mannequin générique ajusté en proportions : il ne reproduit pas la personne."],
    }
    atomic_write_json(root / "persona_character.json", manifest)
    return root


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--name", required=True)
    b.add_argument("--refs", required=True)
    b.add_argument("--consent", required=True)
    b.add_argument("--height", type=float, default=None)
    b.add_argument("--blender", default=shutil.which("blender"))
    b.add_argument("--out", default=None)
    b.add_argument("--boards", nargs="*", default=[])
    a = ap.parse_args(argv)
    root = build(a.name, Path(a.refs), a.consent, Path(a.out) if a.out else None, a.height, a.blender, [Path(x) for x in a.boards])
    m = json.loads((root / "persona_character.json").read_text(encoding="utf-8"))
    print(json.dumps({"folder": str(root), "coverage": m["coverage"], "proportions": m["proportions"], "model": m["model"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
