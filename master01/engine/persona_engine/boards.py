"""Phase F — board assembly, provenance manifest and anti-substitution checks."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .contract import VIEW_LABELS, KINDS, ALWAYS_ESTIMATED
from .util import sha256_file, dhash, hamming, now_iso, atomic_write_json

MIN_SIDE = {"face": 512, "body": 512}
SUBSTITUTION_DHASH_MAX = 18      # out of 256 bits; below => near-copy/crop of a reference
MANIFEST_VERSION = "master01-board/1"


class BoardError(ValueError):
    pass


def _font(size: int):
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def check_outputs(kind: str, views: dict[str, dict], reference_sha: set[str], reference_dhash: dict[str, int]) -> dict:
    """Verify view count, resolution and that no reference was substituted for an output."""
    required = KINDS[kind]
    problems, per_view = [], {}
    for v in required:
        if v not in views:
            problems.append(f"vue manquante: {v}")
    for v, info in views.items():
        p = Path(info["path"])
        sha = sha256_file(p)
        with Image.open(p) as im:
            im.load()
            w, h = im.size
            dh = dhash(im)
        nearest = min(((hamming(dh, d), s) for s, d in reference_dhash.items()), default=(256, None))
        issues = []
        if sha in reference_sha:
            issues.append("IDENTIQUE à une référence (substitution)")
        elif nearest[0] <= SUBSTITUTION_DHASH_MAX:
            issues.append(f"quasi-copie d'une référence (dHash {nearest[0]}/256, {str(nearest[1])[:12]})")
        if min(w, h) < MIN_SIDE[kind]:
            issues.append(f"résolution insuffisante {w}x{h}")
        if not info.get("is_generation"):
            issues.append("image non générative (backend de test)")
        per_view[v] = {"sha256": sha, "width": w, "height": h, "nearest_reference_dhash": nearest[0], "issues": issues}
        problems += [f"{v}: {i}" for i in issues]
    return {"ok": not problems, "problems": problems, "views": per_view}


def assemble(kind: str, views: dict[str, dict], out_dir: Path, *, title: str, consent_declared: bool,
             reference_sha: set[str], reference_dhash: dict[str, int], extra: dict | None = None) -> dict:
    """Build the board PNG, copy individual images and write the provenance manifest.

    ``views[v]`` = {"path", "is_generation", "provenance": {...}, "review": {...}}
    Returns the manifest. A board from non-generative images is written but stamped and
    marked ``layout_test_only`` — it can never pass Gate D/E.
    """
    if not consent_declared:
        raise BoardError("Consentement non déclaré : planche refusée.")
    order = [v for v in KINDS[kind] if v in views] + [v for v in views if v not in KINDS[kind]]
    check = check_outputs(kind, views, reference_sha, reference_dhash)
    substitution = any("substitution" in p or "quasi-copie" in p for p in check["problems"])
    if substitution:
        raise BoardError("Substitution d'une image source détectée : " + "; ".join(check["problems"]))
    all_generated = all(views[v].get("is_generation") for v in order)
    status = "candidate_for_human_review" if (check["ok"] and all_generated) else (
        "layout_test_only" if not all_generated else "incomplete")

    out_dir = Path(out_dir)
    (out_dir / "views").mkdir(parents=True, exist_ok=True)
    tiles = []
    for v in order:
        with Image.open(views[v]["path"]) as im:
            tiles.append((v, ImageOps.exif_transpose(im).convert("RGB")))
    cell_w = 512 if kind == "face" else 448
    cell_h = 512 if kind == "face" else 784
    cols = 3 if kind == "face" else len(tiles)
    rows = -(-len(tiles) // cols)
    margin, label_h, head_h, foot_h = 24, 44, 90, 70
    W = margin + cols * (cell_w + margin)
    H = head_h + rows * (cell_h + label_h + margin) + foot_h
    board = Image.new("RGB", (W, H), (245, 245, 243))
    d = ImageDraw.Draw(board)
    d.text((margin, 22), title, fill=(20, 20, 20), font=_font(34))
    d.text((margin, 62), f"{'Planche faciale' if kind == 'face' else 'Planche corporelle'} · {now_iso()} · statut: {status}",
           fill=(90, 90, 90), font=_font(18))
    for i, (v, im) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = margin + c * (cell_w + margin)
        y = head_h + r * (cell_h + label_h + margin)
        fitted = ImageOps.contain(im, (cell_w, cell_h), Image.LANCZOS)
        board.paste(fitted, (x + (cell_w - fitted.width) // 2, y + (cell_h - fitted.height) // 2))
        label = VIEW_LABELS.get(v, v)
        review = views[v].get("review") or {}
        if review.get("accepted") is True:
            label += "  ✓ validée"
        elif review.get("accepted") is False:
            label += "  ✗ rejetée"
        d.text((x, y + cell_h + 8), label, fill=(30, 30, 30), font=_font(20))
        dst = out_dir / "views" / f"{kind}_{v}.png"
        im.save(dst, "PNG")
    foot = "Régions non photographiées = estimation du modèle. Pas de fidélité anatomique démontrée."
    if status == "layout_test_only":
        foot = "MISE EN PAGE DE TEST — AUCUNE IMAGE GÉNÉRÉE. " + foot
        d.rectangle([0, head_h - 6, W, head_h - 2], fill=(200, 0, 0))
    d.text((margin, H - foot_h + 20), foot, fill=(150, 20, 20), font=_font(18))
    board_path = out_dir / f"planche_{'faciale' if kind == 'face' else 'corporelle'}.png"
    board.save(board_path, "PNG", optimize=True)

    estimated = {v: ALWAYS_ESTIMATED[v] for v in order if v in ALWAYS_ESTIMATED}
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "created_at": now_iso(),
        "kind": kind,
        "status": status,
        "consent_declared": True,
        "reference_sha256": sorted(reference_sha),        # fingerprints only, never the photos
        "board": {"file": board_path.name, "sha256": sha256_file(board_path), "size": list(board.size)},
        "views": {v: {"file": f"views/{kind}_{v}.png", "sha256": sha256_file(out_dir / "views" / f"{kind}_{v}.png"),
                      "is_generation": bool(views[v].get("is_generation")),
                      "provenance": views[v].get("provenance", {}), "review": views[v].get("review"),
                      "checks": check["views"][v]} for v in order},
        "estimated_regions": estimated,
        "checks": {"ok": check["ok"], "problems": check["problems"]},
        "warnings": ["Une vue du dos ou un détail jamais photographié est une estimation du modèle.",
                     "Mesures automatiques = aide uniquement ; la fidélité est décidée par revue humaine."],
    } | (extra or {})
    atomic_write_json(out_dir / f"manifest_{kind}.json", manifest)
    return manifest


def verify_manifest(manifest_path: Path) -> list[str]:
    """Re-check every file hash referenced by a manifest (T08)."""
    m = json.loads(Path(manifest_path).read_text("utf-8"))
    base = Path(manifest_path).parent
    errs = []
    if sha256_file(base / m["board"]["file"]) != m["board"]["sha256"]:
        errs.append("empreinte planche invalide")
    for v, info in m["views"].items():
        p = base / info["file"]
        if not p.exists():
            errs.append(f"{v}: fichier manquant")
        elif sha256_file(p) != info["sha256"]:
            errs.append(f"{v}: empreinte invalide")
    if set(m["views"]) < set(KINDS[m["kind"]]):
        errs.append("nombre de vues insuffisant")
    return errs
