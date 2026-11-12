"""NON-GENERATIVE backend used only to test the plumbing (worker, Android, boards).

Every image it writes is stamped "TEST — PAS UNE GÉNÉRATION" and its manifest
carries ``is_generation: false``; boards built from it are marked layout_test_only
and can never count as a Gate D/E success.
"""
from __future__ import annotations

import random
import time
from pathlib import Path

from PIL import Image, ImageDraw

from ..contract import VIEW_LABELS
from ..pose import pose_map, VIEW_YAW
from ..boards import _font
from .base import Backend, GenerationResult


class TestPatternBackend(Backend):
    name = "test_pattern"
    is_generation = False

    def __init__(self, delay_s: float = 0.0, fail_views: set[str] | None = None):
        self.delay_s = delay_s
        self.fail_views = set(fail_views or ())

    def generate(self, *, kind, view, references, seed, params, out_path: Path) -> GenerationResult:
        t0 = time.time()
        if view in self.fail_views:
            raise RuntimeError(f"échec simulé pour {view}")
        if self.delay_s:
            time.sleep(self.delay_s)
        w, h = (512, 512) if kind == "face" else (512, 896)
        rnd = random.Random(seed)
        if view in VIEW_YAW:
            img = pose_map(view, w, h)
        else:
            img = Image.new("RGB", (w, h), tuple(rnd.randint(40, 90) for _ in range(3)))
        d = ImageDraw.Draw(img)
        for i in range(0, w + h, 24):
            d.line([(i, 0), (0, i)], fill=(70, 70, 70), width=1)
        d.rectangle([0, h // 2 - 28, w, h // 2 + 28], fill=(200, 0, 0))
        d.text((10, h // 2 - 22), "TEST — PAS UNE GÉNÉRATION", fill=(255, 255, 255), font=_font(22))
        d.text((10, h // 2 + 2), f"{VIEW_LABELS.get(view, view)} · seed {seed}", fill=(255, 255, 255), font=_font(16))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG")
        return GenerationResult(path=out_path, engine=self.name, model="none", model_version="0",
                                licence="n/a", is_generation=False, seed=seed, prompt="", negative_prompt="",
                                params=dict(params), duration_s=round(time.time() - t0, 3), hardware="cpu",
                                warnings=["Image de test non générative : ne compte pas comme génération."])
