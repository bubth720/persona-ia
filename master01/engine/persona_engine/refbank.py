"""Phase C — reference bank.

Guarantees:
* originals are copied byte-for-byte into a private store and never modified;
* exact duplicates are detected by SHA-256 and reported (never silently dropped);
* every committed import is appended (fsync) to an append-only journal, so an
  interrupted import can be resumed and the index rebuilt;
* files copied but not yet journaled at crash time are recovered at reopen;
* no import without declared authorisation; no export to a remote engine
  without explicit consent;
* view classification is manual (``non_classe`` by default); annotations are
  journaled and can be undone.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

from PIL import Image, ExifTags

from .contract import REFERENCE_VIEWS, FACE_VIEWS, BODY_VIEWS
from .util import sha256_file, now_iso, atomic_write_json, dhash, _fsync_dir

SUPPORTED = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
_ORIENTATION_TAG = next(k for k, v in ExifTags.TAGS.items() if v == "Orientation")


class ConsentError(PermissionError):
    pass


@dataclass
class RefRecord:
    sha256: str
    ext: str
    size: int
    width: int
    height: int
    orientation: int
    dhash: str
    source_name: str          # base name only, never an absolute path
    imported_at: str
    authorized: bool
    consent_note: str
    view: str = "non_classe"
    region: str = "inconnu"   # visage | corps | inconnu
    tags: dict = field(default_factory=dict)   # coiffure, tenue, époque, lumière, maquillage…
    validated: bool = False


class RefBank:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.originals = self.root / "originals"
        self.journal = self.root / "journal.jsonl"
        self.index_path = self.root / "index.json"
        self.originals.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, RefRecord] = {}
        self.annotations: list[dict] = []
        self._replay()
        self.recovered = self._recover_orphans()

    # ------------------------------------------------------------------ journal
    def _append(self, entry: dict) -> None:
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        with open(self.journal, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def _replay(self) -> None:
        if not self.journal.exists():
            return
        with open(self.journal, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                except json.JSONDecodeError:
                    continue  # torn last line after a crash: ignored, file is recovered below
                self._apply(e)

    def _apply(self, e: dict) -> None:
        op = e["op"]
        if op == "import":
            self.records[e["record"]["sha256"]] = RefRecord(**e["record"])
        elif op == "annotate":
            rec = self.records[e["sha256"]]
            self.annotations.append(e)
            for k, v in e["new"].items():
                setattr(rec, k, v)
        elif op == "undo":
            target = self.annotations.pop()
            rec = self.records[target["sha256"]]
            for k, v in target["old"].items():
                setattr(rec, k, v)

    def _recover_orphans(self) -> list[str]:
        recovered = []
        for p in sorted(self.originals.glob("*/*")):
            if p.name.startswith(".tmp-"):
                p.unlink(missing_ok=True)          # partial copy: original source still intact
                continue
            sha = p.stem
            if sha in self.records:
                continue
            if sha256_file(p) != sha:             # corrupt / torn copy: drop, source untouched
                p.unlink()
                continue
            rec = self._describe(p, sha, source_name="(récupéré après interruption)",
                                 authorized=False, consent_note="à reconfirmer")
            self._append({"op": "import", "at": now_iso(), "record": asdict(rec)})
            self.records[sha] = rec
            recovered.append(sha)
        return recovered

    def save_index(self) -> None:
        atomic_write_json(self.index_path, {"generated_at": now_iso(),
                                            "records": [asdict(r) for r in self.records.values()]})

    # ------------------------------------------------------------------ import
    def _path_for(self, sha: str, ext: str) -> Path:
        return self.originals / sha[:2] / f"{sha}{ext}"

    def _describe(self, path: Path, sha: str, source_name: str, authorized: bool, consent_note: str) -> RefRecord:
        with Image.open(path) as im:
            im.load()
            orientation = int(im.getexif().get(_ORIENTATION_TAG, 1))
            w, h = im.size
            if orientation in (5, 6, 7, 8):
                w, h = h, w
            dh = f"{dhash(im):064x}"
        return RefRecord(sha256=sha, ext=path.suffix.lower(), size=path.stat().st_size, width=w, height=h,
                         orientation=orientation, dhash=dh, source_name=source_name, imported_at=now_iso(),
                         authorized=authorized, consent_note=consent_note)

    def import_paths(self, paths: Iterable[Path], *, authorized: bool, consent_note: str,
                     stop_after: int | None = None) -> dict:
        """Import files. ``stop_after`` simulates an interruption (tests T02)."""
        if not authorized:
            raise ConsentError("Import refusé : usage des photographies non déclaré comme autorisé.")
        report = {"imported": [], "duplicates": [], "errors": [], "skipped_already_present": []}
        count = 0
        for src in paths:
            src = Path(src)
            ext = src.suffix.lower()
            if ext not in SUPPORTED:
                report["errors"].append({"file": src.name, "error": "format non pris en charge"})
                continue
            try:
                sha = sha256_file(src)
                if sha in self.records:
                    report["duplicates"].append({"file": src.name, "sha256": sha,
                                                 "same_as": self.records[sha].source_name})
                    continue
                with Image.open(src) as im:
                    im.verify()
                dest = self._path_for(sha, ext)
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.parent / f".tmp-{sha}{ext}"
                shutil.copyfile(src, tmp)
                with open(tmp, "r+b") as f:      # écriture requise par fsync sous Windows
                    os.fsync(f.fileno())
                if sha256_file(tmp) != sha:
                    tmp.unlink()
                    raise IOError("copie corrompue")
                os.replace(tmp, dest)
                _fsync_dir(dest.parent)
                rec = self._describe(dest, sha, src.name, authorized, consent_note)
                self._append({"op": "import", "at": now_iso(), "record": asdict(rec)})
                self.records[sha] = rec
                report["imported"].append(sha)
            except Exception as exc:  # noqa: BLE001 — reported, never silent
                report["errors"].append({"file": src.name, "error": str(exc)})
            count += 1
            if stop_after is not None and count >= stop_after:
                report["interrupted"] = True
                break
        self.save_index()
        return report

    # ------------------------------------------------------------- annotations
    def annotate(self, sha: str, **fields) -> None:
        rec = self.records[sha]
        allowed = {"view", "region", "tags", "validated"}
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"champs non annotables: {bad}")
        if "view" in fields and fields["view"] not in REFERENCE_VIEWS:
            raise ValueError(f"vue inconnue: {fields['view']}")
        old = {k: getattr(rec, k) for k in fields}
        e = {"op": "annotate", "at": now_iso(), "sha256": sha, "old": old, "new": fields}
        self._append(e)
        self._apply(e)

    def undo_last_annotation(self) -> bool:
        if not self.annotations:
            return False
        e = {"op": "undo", "at": now_iso()}
        self._append(e)
        self._apply(e)
        return True

    def confirm_consent(self, sha: str, note: str) -> None:
        rec = self.records[sha]
        e = {"op": "annotate", "at": now_iso(), "sha256": sha,
             "old": {"authorized": rec.authorized, "consent_note": rec.consent_note},
             "new": {"authorized": True, "consent_note": note}}
        self._append(e)
        self._apply(e)

    # ---------------------------------------------------------------- queries
    def coverage(self) -> dict:
        """Coverage diagnosis from *human-validated* labels only. Never invents views."""
        counts = {v: 0 for v in REFERENCE_VIEWS}
        unvalidated = 0
        for r in self.records.values():
            if r.validated:
                counts[r.view] += 1
            else:
                unvalidated += 1
        face_needed = {v: counts.get(v, 0) for v in FACE_VIEWS if v != "expression"}
        body_needed = {"plein_pied": counts["plein_pied"], "dos": counts["dos"]}
        missing = [v for v, n in {**face_needed, **body_needed}.items() if n == 0]
        weak = [v for v, n in {**face_needed, **body_needed}.items() if 0 < n < 3]
        return {"total": len(self.records), "non_valides": unvalidated, "par_vue": counts,
                "manquantes": missing, "insuffisantes_moins_de_3": weak,
                "avertissement": "Les vues manquantes ne seront jamais inventées ; elles seront marquées « estimé » dans les planches."}

    def path(self, sha: str) -> Path:
        r = self.records[sha]
        return self._path_for(sha, r.ext)

    def select_for_engine(self, shas: list[str], *, remote: bool, remote_consent: bool) -> list[Path]:
        """T03: refuses unauthorised references and any remote transfer without explicit consent."""
        if remote and not remote_consent:
            raise ConsentError("Transfert vers un moteur distant refusé : consentement explicite absent.")
        out = []
        for s in shas:
            r = self.records[s]
            if not r.authorized:
                raise ConsentError(f"Référence {s[:12]} non autorisée.")
            out.append(self.path(s))
        return out

    def dhashes(self) -> dict[str, int]:
        return {s: int(r.dhash, 16) for s, r in self.records.items()}
