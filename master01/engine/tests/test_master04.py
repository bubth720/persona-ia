"""MASTER-04 : phase 2 (classement, couverture, proportions), matériel, exclusion IA / PERSONA LIVE."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_engine import body, hardware  # noqa: E402
from persona_engine.backends.test_pattern import TestPatternBackend  # noqa: E402
from persona_engine.worker import JobManager  # noqa: E402


def skeleton(view: str, H: float = 1000.0, cx: float = 500.0, feet: bool = True) -> list:
    """33 points synthétiques d'un adulte debout (y vers le bas), selon la vue."""
    pts = [(cx, 0.0, 0.0, 0.1)] * 33
    half_sh = 0.10 * H
    half_hip = 0.07 * H
    k = {"face": 1.0, "trois_quarts": 0.6, "profil": 0.15, "dos": -1.0}[view]
    face_vis = 0.95 if view != "dos" else 0.1
    def s(i, x, y, vis=0.95):
        pts[i] = (x, y, 0.0, vis)
    nose_x = cx + (0 if view in ("face", "dos") else -0.04 * H)
    s(body.NOSE, nose_x, 0.06 * H, face_vis)
    s(body.L_EYE, cx + 0.02 * H * k, 0.05 * H, face_vis)
    s(body.R_EYE, cx - 0.02 * H * k, 0.05 * H, face_vis)
    s(body.L_EAR, cx + 0.04 * H * k, 0.06 * H)
    s(body.R_EAR, cx - 0.04 * H * k, 0.06 * H)
    s(body.L_SH, cx + half_sh * k, 0.18 * H)
    s(body.R_SH, cx - half_sh * k, 0.18 * H)
    s(body.L_WR, cx + half_sh * k * 1.1, 0.48 * H)
    s(body.R_WR, cx - half_sh * k * 1.1, 0.48 * H)
    s(body.L_HIP, cx + half_hip * k, 0.47 * H)
    s(body.R_HIP, cx - half_hip * k, 0.47 * H)
    s(body.L_KNEE, cx + half_hip * k, 0.72 * H)
    s(body.R_KNEE, cx - half_hip * k, 0.72 * H)
    fv = 0.95 if feet else 0.05
    s(body.L_ANK, cx + half_hip * k, 0.96 * H, fv)
    s(body.R_ANK, cx - half_hip * k, 0.96 * H, fv)
    s(body.L_FOOT, cx + half_hip * k, 0.99 * H, fv)
    s(body.R_FOOT, cx - half_hip * k, 0.99 * H, fv)
    return pts


class Phase2Classification(unittest.TestCase):
    def test_views(self):
        for v in ("face", "trois_quarts", "profil", "dos"):
            r = body.classify(skeleton(v), v)
            self.assertEqual(r.view, v, f"{v} -> {r.view} ({r})")
            self.assertEqual(r.framing, "plein_pied")
        self.assertEqual(body.classify(skeleton("face", feet=False)).framing, "plan_americain")

    def test_coverage_and_missing(self):
        res = [body.classify(skeleton("face")), body.classify(skeleton("profil", feet=False))]
        cov = body.coverage(res)
        self.assertIn("dos", cov["missing_views"])
        self.assertIn("dos en pied", cov["missing_parts"])
        self.assertTrue(cov["usable_for_reconstruction"])

    def test_proportions_relative_and_bounded(self):
        res = [body.classify(skeleton("face"))]
        p = body.proportions(res)
        self.assertEqual(p["status"], "estimation_relative")
        for k, (lo, hi) in body.LIMITS.items():
            self.assertTrue(lo <= p[k] <= hi, (k, p[k]))
        self.assertEqual(p["height_source"], "valeur par défaut (non mesurée)")
        self.assertEqual(body.proportions(res, 1.68)["height"], 1.68)

    def test_no_mediapipe_means_assisted(self):
        with tempfile.TemporaryDirectory() as d:
            from PIL import Image
            Image.new("RGB", (64, 64)).save(Path(d) / "a.png")
            out = body.analyze_folder(Path(d))
            if not body.HAVE_MP:
                self.assertEqual(out["results"][0]["view"], "non_classe")
                self.assertFalse(out["coverage"]["usable_for_reconstruction"])


class HardwareAndExclusion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["XDG_DATA_HOME"] = self.tmp
        os.environ["APPDATA"] = self.tmp

    def test_detect_and_profiles(self):
        rep = hardware.detect()
        self.assertGreater(rep["cpu"]["logical_cores"], 0)
        self.assertIn(rep["profile"], ("leger", "standard", "avance"))
        self.assertEqual(hardware.choose_profile(8, 4), "leger")       # IdeaPad Gaming 3 supposé
        self.assertEqual(hardware.choose_profile(16, 8), "standard")
        self.assertEqual(hardware.choose_profile(32, 12), "avance")
        p = hardware.write_report()
        self.assertTrue(json.loads(p.read_text())["generation"]["min_free_ram_gb"] > 0)

    def test_generation_refused_while_live_runs(self):
        (hardware.data_dir() / "persona_live.lock").write_text(str(os.getpid()))   # processus vivant
        self.assertTrue(hardware.live_running())

        class GenBackend(TestPatternBackend):
            is_generation = True
        mgr = JobManager(Path(self.tmp) / "w", GenBackend())
        try:
            job = mgr.create({"kind": "face", "consent_declared": True})
            from PIL import Image
            import io, hashlib
            buf = io.BytesIO(); Image.new("RGB", (64, 64), (9, 9, 9)).save(buf, "PNG"); data = buf.getvalue()
            mgr.add_reference(job["id"], hashlib.sha256(data).hexdigest(), data, consent=True)
            mgr.start(job["id"])
            j = mgr.wait(job["id"], timeout=10)
            self.assertEqual(j["state"], "failed")
            self.assertTrue(any("PERSONA LIVE" in e.get("detail", "") for e in j["events"]))
        finally:
            mgr.shutdown()
        (hardware.data_dir() / "persona_live.lock").write_text("999999999")       # PID mort
        self.assertFalse(hardware.live_running())


if __name__ == "__main__":
    unittest.main(verbosity=2)
