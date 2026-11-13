"""Phase 2 — PERSONA BODY : classement des angles, couverture, parties manquantes, proportions RELATIVES.

Détection de pose : MediaPipe Pose (Apache-2.0), exécuté localement (modèle inclus dans le paquet pip).
Sans MediaPipe, le classement reste « assisté » : vue « non_classe » à valider par l'humain.

Les proportions sont des ESTIMATIONS RELATIVES (rapports à la taille), à ±15 % au mieux, jamais des mesures.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from statistics import median

from PIL import Image, ImageOps

try:
    import mediapipe as mp  # type: ignore
    import numpy as np  # type: ignore
    HAVE_MP = True
except Exception:  # noqa: BLE001
    HAVE_MP = False

# Indices MediaPipe Pose (33 points)
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 2, 5, 7, 8
L_SH, R_SH, L_WR, R_WR, L_HIP, R_HIP = 11, 12, 15, 16, 23, 24
L_KNEE, R_KNEE, L_ANK, R_ANK, L_FOOT, R_FOOT = 25, 26, 27, 28, 31, 32

BODY_VIEWS = ["face", "trois_quarts", "profil", "dos"]
PART_POINTS = {"tete": [NOSE, L_EAR, R_EAR], "mains": [L_WR, R_WR], "genoux": [L_KNEE, R_KNEE], "pieds": [L_ANK, R_ANK, L_FOOT, R_FOOT]}


@dataclass
class PoseResult:
    file: str
    detected: bool
    view: str = "non_classe"          # face | trois_quarts | profil | dos | non_classe
    side: str = ""                    # gauche | droite (profil / trois-quarts)
    framing: str = "inconnu"          # plein_pied | plan_americain | buste | inconnu
    confidence: float = 0.0
    visible_parts: list = field(default_factory=list)
    ratios: dict = field(default_factory=dict)
    method: str = "mediapipe_pose" if HAVE_MP else "aucune (assisté)"
    note: str = ""


class PoseAnalyzer:
    def __init__(self):
        if not HAVE_MP:
            raise RuntimeError("MediaPipe absent : pip install mediapipe==0.10.14 (classement automatique) ou classement manuel")
        self.pose = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=False)

    def close(self):
        self.pose.close()

    def analyze(self, path: Path) -> PoseResult:
        with Image.open(path) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")
        w, h = img.size
        res = self.pose.process(np.asarray(img))
        if not res.pose_landmarks:
            return PoseResult(file=Path(path).name, detected=False, note="aucune personne détectée")
        lm = res.pose_landmarks.landmark
        return classify([(lm[i].x * w, lm[i].y * h, lm[i].z, lm[i].visibility) for i in range(33)], Path(path).name)


def classify(points: list[tuple[float, float, float, float]], name: str = "") -> PoseResult:
    """Règles géométriques sur 33 points (x px, y px, z relatif, visibilité). Testable sans MediaPipe."""
    x = lambda i: points[i][0]  # noqa: E731
    y = lambda i: points[i][1]  # noqa: E731
    v = lambda i: points[i][3]  # noqa: E731
    r = PoseResult(file=name, detected=True)
    sh_w = abs(x(L_SH) - x(R_SH))
    torso_h = abs((y(L_SH) + y(R_SH)) / 2 - (y(L_HIP) + y(R_HIP)) / 2) or 1.0
    ratio = sh_w / torso_h
    face_vis = median([v(NOSE), v(L_EYE), v(R_EYE)])
    # Sujet de face : son épaule gauche apparaît à droite de l'image (x_L > x_R) ; de dos : l'inverse.
    facing = x(L_SH) - x(R_SH)
    if ratio < 0.38:
        r.view = "profil"
        nose_dx = x(NOSE) - (x(L_SH) + x(R_SH)) / 2
        r.side = "gauche" if nose_dx < 0 else "droite"   # côté vers lequel regarde le sujet dans l'image
        r.confidence = round(min(1.0, (0.38 - ratio) / 0.2 + 0.5), 2)
    elif facing < 0 or face_vis < 0.35:
        r.view = "dos"
        r.confidence = round(min(1.0, 0.5 + abs(facing) / (torso_h + 1e-6) + (0.35 - face_vis if face_vis < 0.35 else 0)), 2)
    elif ratio < 0.68:
        r.view = "trois_quarts"
        r.side = "gauche" if x(NOSE) < (x(L_SH) + x(R_SH)) / 2 else "droite"
        r.confidence = round(0.5 + min(0.5, abs(ratio - 0.53) * 2), 2)
    else:
        r.view = "face"
        r.confidence = round(min(1.0, 0.5 + (ratio - 0.68)), 2)
    ank = max(v(L_ANK), v(R_ANK))
    knee = max(v(L_KNEE), v(R_KNEE))
    r.framing = "plein_pied" if ank > 0.5 else ("plan_americain" if knee > 0.5 else "buste")
    r.visible_parts = [p for p, idx in PART_POINTS.items() if max(v(i) for i in idx) > 0.5]
    if r.view == "face" and r.framing == "plein_pied":
        top = y(NOSE)
        bottom = (y(L_ANK) + y(R_ANK)) / 2
        H = (bottom - top) / 0.90 if bottom > top else 0      # nez ≈ 0,94 H ; chevilles ≈ 0,04 H
        if H > 50:
            r.ratios = {
                "shoulder_ratio": round(sh_w / H, 3),
                "hip_ratio": round(abs(x(L_HIP) - x(R_HIP)) / (0.75 * H), 3),
                "leg_ratio": round(((y(L_ANK) + y(R_ANK)) / 2 - (y(L_HIP) + y(R_HIP)) / 2) / H, 3),
            }
    return r


LIMITS = {"shoulder_ratio": (0.18, 0.32), "hip_ratio": (0.14, 0.26), "leg_ratio": (0.42, 0.53)}


def proportions(results: list[PoseResult], height_m: float | None = None) -> dict:
    """Médiane des rapports mesurés sur les vues de face en pied, bornée à des valeurs humaines plausibles."""
    vals: dict[str, list[float]] = {}
    for r in results:
        for k, val in r.ratios.items():
            vals.setdefault(k, []).append(val)
    out = {"status": "estimation_relative", "n_views": len([r for r in results if r.ratios]),
           "warning": "Rapports estimés depuis des photos 2D (perspective, vêtements, posture) : ±15 % au mieux, pas des mesures."}
    for k, (lo, hi) in LIMITS.items():
        if vals.get(k):
            m = median(vals[k])
            out[k] = round(min(hi, max(lo, m)), 3)
            out[k + "_raw"] = round(m, 3)
            if not lo <= m <= hi:
                out.setdefault("clamped", []).append(k)
    out["height"] = height_m if height_m else 1.75
    out["height_source"] = "déclarée par l'utilisateur" if height_m else "valeur par défaut (non mesurée)"
    return out


def coverage(results: list[PoseResult]) -> dict:
    views = {v: 0 for v in BODY_VIEWS}
    full_body = 0
    parts = {p: 0 for p in PART_POINTS}
    for r in results:
        if r.view in views:
            views[r.view] += 1
        if r.framing == "plein_pied":
            full_body += 1
        for p in r.visible_parts:
            parts[p] += 1
    missing_views = [v for v, n in views.items() if n == 0]
    missing_parts = [p for p, n in parts.items() if n == 0]
    if not any(r.view == "dos" and r.framing == "plein_pied" for r in results):
        missing_parts.append("dos en pied")
    return {"views": views, "full_body": full_body, "parts": parts, "missing_views": missing_views,
            "missing_parts": sorted(set(missing_parts)),
            "usable_for_reconstruction": views["face"] > 0 and full_body > 0,
            "note": "Les zones manquantes seront estimées par les modèles, jamais présentées comme exactes."}


def analyze_folder(folder: Path) -> dict:
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    results: list[PoseResult] = []
    if HAVE_MP:
        an = PoseAnalyzer()
        try:
            results = [an.analyze(f) for f in files]
        finally:
            an.close()
    else:
        results = [PoseResult(file=f.name, detected=False, note="MediaPipe absent : classement manuel requis") for f in files]
    return {"results": [asdict(r) for r in results], "coverage": coverage(results), "proportions": proportions(results)}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(analyze_folder(Path(sys.argv[1])), indent=2, ensure_ascii=False))
