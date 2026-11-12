"""Deterministic OpenPose (COCO-18) conditioning maps for full-body views.

A neutral standing skeleton is defined in 3D (units = fraction of image height),
rotated by yaw and projected orthographically. Face keypoints facing away from the
camera are hidden, which is how OpenPose encodes a back view. Pose guidance frames
the body; it does NOT guarantee body identity (see MOTEUR_GPU.md).
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

# x (right of image for the subject's left), y (down), z (towards camera)
NEUTRAL = [
    (0.0, 0.125, 0.045),    # 0 nose
    (0.0, 0.19, 0.0),       # 1 neck
    (-0.095, 0.20, 0.0),    # 2 R shoulder
    (-0.115, 0.33, 0.0),    # 3 R elbow
    (-0.125, 0.45, 0.01),   # 4 R wrist
    (0.095, 0.20, 0.0),     # 5 L shoulder
    (0.115, 0.33, 0.0),     # 6 L elbow
    (0.125, 0.45, 0.01),    # 7 L wrist
    (-0.055, 0.50, 0.0),    # 8 R hip
    (-0.055, 0.70, 0.01),   # 9 R knee
    (-0.055, 0.90, 0.0),    # 10 R ankle
    (0.055, 0.50, 0.0),     # 11 L hip
    (0.055, 0.70, 0.01),    # 12 L knee
    (0.055, 0.90, 0.0),     # 13 L ankle
    (-0.017, 0.108, 0.035), # 14 R eye
    (0.017, 0.108, 0.035),  # 15 L eye
    (-0.035, 0.115, 0.0),   # 16 R ear
    (0.035, 0.115, 0.0),    # 17 L ear
]
FACE_POINTS = {0, 14, 15, 16, 17}
LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12),
         (12, 13), (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
COLORS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0),
          (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255),
          (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]

# yaw in degrees: 0 = facing camera, 90 = subject's left profile, 180 = back
VIEW_YAW = {"pied_face": 0, "pied_trois_quarts": 40, "pied_profil": 90, "pied_dos": 180, "pied_profil_oppose": -90}


def keypoints(yaw_deg: float, width: int, height: int) -> list[tuple[float, float] | None]:
    t = math.radians(yaw_deg)
    pts: list[tuple[float, float] | None] = []
    for i, (x, y, z) in enumerate(NEUTRAL):
        xr = x * math.cos(t) + z * math.sin(t)
        zr = -x * math.sin(t) + z * math.cos(t)
        if i in FACE_POINTS and zr < -1e-3:
            pts.append(None)
            continue
        pts.append((width / 2 + xr * height, y * height))
    return pts


def pose_map(view: str, width: int = 768, height: int = 1344) -> Image.Image:
    if view not in VIEW_YAW:
        raise ValueError(f"pas de carte de pose pour {view}")
    pts = keypoints(VIEW_YAW[view], width, height)
    img = Image.new("RGB", (width, height), (0, 0, 0))
    d = ImageDraw.Draw(img)
    stick = max(4, height // 170)
    for idx, (a, b) in enumerate(LIMBS):
        if pts[a] is None or pts[b] is None:
            continue
        c = tuple(int(v * 0.6) for v in COLORS[idx])
        d.line([pts[a], pts[b]], fill=c, width=stick)
    r = max(3, height // 300)
    for i, p in enumerate(pts):
        if p is None:
            continue
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=COLORS[i])
    return img
