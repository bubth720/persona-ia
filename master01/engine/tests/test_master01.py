"""MASTER 01 acceptance tests that can run without GPU (synthetic data only).

T01 import 10/300/1000 · T02 interrupted import · T03 consent · T07 regenerate one view ·
T08 boards + hashes · T09 worker stop mid-job · anti-substitution · HTTP auth.
"""
from __future__ import annotations

import json
import os
import random
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from persona_engine.refbank import RefBank, ConsentError  # noqa: E402
from persona_engine.boards import assemble, verify_manifest, BoardError  # noqa: E402
from persona_engine.backends.test_pattern import TestPatternBackend  # noqa: E402
from persona_engine.worker import JobManager, serve  # noqa: E402
from persona_engine.util import sha256_file, dhash  # noqa: E402
from persona_engine.pose import pose_map, keypoints  # noqa: E402
from persona_engine.contract import FACE_VIEWS, BODY_VIEWS  # noqa: E402


def synth_images(folder: Path, n: int, seed: int = 0, size=(96, 128), dup_every: int = 0) -> list[Path]:
    """Synthetic, rights-free test images (random blocks), optional exact duplicates."""
    folder.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(seed)
    paths = []
    for i in range(n):
        p = folder / f"img_{i:05d}.{['jpg', 'png', 'webp'][i % 3]}"
        if dup_every and i and i % dup_every == 0:
            prev = paths[i - 1]
            p = p.with_suffix(prev.suffix)
            p.write_bytes(prev.read_bytes())
        else:
            im = Image.new("RGB", size, tuple(rnd.randrange(256) for _ in range(3)))
            for _ in range(6):
                x, y = rnd.randrange(size[0]), rnd.randrange(size[1])
                im.paste(tuple(rnd.randrange(256) for _ in range(3)), (x, y, min(size[0], x + 30), min(size[1], y + 30)))
            if p.suffix == ".jpg" and i % 7 == 0:
                exif = Image.Exif()
                exif[0x0112] = 6
                im.save(p, exif=exif, quality=90)
            else:
                im.save(p)
        paths.append(p)
    return paths


class T01Import(unittest.TestCase):
    def test_10_300_1000_no_loss_no_silent_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for n in (10, 300, 1000):
                src = synth_images(d / f"src{n}", n, seed=n, dup_every=50)
                before = {p: sha256_file(p) for p in src}
                bank = RefBank(d / f"bank{n}")
                rep = bank.import_paths(src, authorized=True, consent_note="corpus synthétique")
                self.assertEqual(rep["errors"], [])
                n_unique = len(set(before.values()))
                self.assertEqual(len(rep["imported"]), n_unique)
                self.assertEqual(len(rep["imported"]) + len(rep["duplicates"]), n)   # nothing silent
                self.assertEqual(len(bank.records), n_unique)
                for p, h in before.items():                                          # originals untouched
                    self.assertEqual(sha256_file(p), h)
                    self.assertEqual(sha256_file(bank.path(h)), h)                    # byte-exact copy
                rotated = [r for r in bank.records.values() if r.orientation == 6]
                self.assertTrue(rotated and all(r.width == 128 and r.height == 96 for r in rotated))
                # re-import = all duplicates, nothing added
                rep2 = bank.import_paths(src, authorized=True, consent_note="x")
                self.assertEqual(len(rep2["imported"]), 0)
                self.assertEqual(len(RefBank(d / f"bank{n}").records), n_unique)      # survives reopen


class T02Interruption(unittest.TestCase):
    def test_interrupt_then_resume(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = synth_images(d / "src", 120, seed=3)
            bank = RefBank(d / "bank")
            rep = bank.import_paths(src, authorized=True, consent_note="t", stop_after=37)
            self.assertTrue(rep.get("interrupted"))
            self.assertEqual(len(bank.records), 37)
            bank.annotate(rep["imported"][0], view="face", region="visage", validated=True)
            # simulate crash: file copied but not journaled + torn journal line + temp file
            orphan_src = src[50]
            sha = sha256_file(orphan_src)
            (d / "bank" / "originals" / sha[:2]).mkdir(parents=True, exist_ok=True)
            (d / "bank" / "originals" / sha[:2] / f"{sha}{orphan_src.suffix}").write_bytes(orphan_src.read_bytes())
            (d / "bank" / "originals" / sha[:2] / ".tmp-partial.png").write_bytes(b"\x89PNG partial")
            with open(d / "bank" / "journal.jsonl", "a") as f:
                f.write('{"op": "import", "rec')
            bank2 = RefBank(d / "bank")
            self.assertEqual(bank2.recovered, [sha])
            self.assertFalse(bank2.records[sha].authorized)                # recovered = to be re-confirmed
            self.assertEqual(bank2.records[rep["imported"][0]].view, "face")  # metadata kept
            rep2 = bank2.import_paths(src, authorized=True, consent_note="t")
            self.assertEqual(len(bank2.records), 120)
            self.assertEqual(len(rep2["duplicates"]), 38)
            self.assertEqual(rep2["errors"], [])
            self.assertTrue(bank2.undo_last_annotation())
            self.assertEqual(RefBank(d / "bank").records[rep["imported"][0]].view, "non_classe")


class T03Consent(unittest.TestCase):
    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = synth_images(d / "src", 5)
            bank = RefBank(d / "bank")
            with self.assertRaises(ConsentError):
                bank.import_paths(src, authorized=False, consent_note="")
            self.assertEqual(len(bank.records), 0)
            bank.import_paths(src, authorized=True, consent_note="ok")
            shas = list(bank.records)
            with self.assertRaises(ConsentError):
                bank.select_for_engine(shas, remote=True, remote_consent=False)
            self.assertEqual(len(bank.select_for_engine(shas, remote=False, remote_consent=False)), 5)
            mgr = JobManager(d / "w", TestPatternBackend())
            try:
                with self.assertRaises(PermissionError):
                    mgr.create({"kind": "face"})
                job = mgr.create({"kind": "face", "consent_declared": True})
                data = src[0].read_bytes()
                with self.assertRaises(PermissionError):
                    mgr.add_reference(job["id"], sha256_file(src[0]), data, consent=False)
            finally:
                mgr.shutdown()

    def test_coverage_never_invents(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            bank = RefBank(d / "bank")
            bank.import_paths(synth_images(d / "s", 4), authorized=True, consent_note="ok")
            cov = bank.coverage()
            self.assertEqual(cov["non_valides"], 4)
            self.assertIn("dos", cov["manquantes"])
            s = next(iter(bank.records))
            bank.annotate(s, view="face", validated=True)
            self.assertEqual(bank.coverage()["par_vue"]["face"], 1)


def _job_with_refs(mgr, kind, refs):
    job = mgr.create({"kind": kind, "consent_declared": True, "seed": 42, "profile": "synthétique"})
    for p in refs:
        mgr.add_reference(job["id"], sha256_file(p), p.read_bytes(), consent=True)
    return job


class T07T08Boards(unittest.TestCase):
    def test_face_and_body_boards_regenerate_one_view(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            refs = synth_images(d / "r", 3, size=(256, 256))
            mgr = JobManager(d / "w", TestPatternBackend())
            try:
                for kind, n in (("face", 6), ("body", 4)):
                    job = _job_with_refs(mgr, kind, refs)
                    mgr.start(job["id"])
                    job = mgr.wait(job["id"])
                    self.assertEqual(job["state"], "succeeded")
                    m = mgr.manifest(job["id"])
                    self.assertEqual(len(m["views"]), n)
                    self.assertEqual(m["status"], "layout_test_only")          # test backend can't pass Gate D/E
                    mpath = d / "w" / "jobs" / job["id"] / "board" / f"manifest_{kind}.json"
                    self.assertEqual(verify_manifest(mpath), [])
                    if kind == "body":
                        self.assertIn("pied_dos", m["estimated_regions"])
                    # T07: reject one view, regenerate it only
                    views = list(job["views"])
                    keep = {v: job["views"][v]["provenance"]["sha256"] for v in views[1:]}
                    mgr.review(job["id"], views[0], False, "trait du nez faux")
                    mgr.review(job["id"], views[1], True, "ok")
                    old_seed = job["views"][views[0]]["seed"]
                    mgr.regenerate(job["id"], views[0])
                    job = mgr.wait(job["id"])
                    self.assertEqual(job["views"][views[0]]["state"], "done")
                    self.assertNotEqual(job["views"][views[0]]["seed"], old_seed)
                    self.assertEqual(job["views"][views[1]]["state"], "accepted")
                    for v, h in keep.items():
                        self.assertEqual(job["views"][v]["provenance"]["sha256"], h)
                    self.assertEqual(job["views"][views[0]]["attempts"], 2)
            finally:
                mgr.shutdown()

    def test_substitution_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            refs = synth_images(d / "r", 6, size=(600, 600))
            ref_sha = {sha256_file(p) for p in refs}
            ref_dh = {sha256_file(p): dhash(Image.open(p)) for p in refs}
            # cropped / re-encoded copy of a reference passed off as "generated"
            crop = d / "crop.png"
            Image.open(refs[0]).crop((10, 10, 590, 590)).resize((600, 600)).save(crop)
            views = {v: {"path": refs[i] if i else crop, "is_generation": True} for i, v in enumerate(FACE_VIEWS)}
            with self.assertRaises(BoardError):
                assemble("face", views, d / "out", title="x", consent_declared=True,
                         reference_sha=ref_sha, reference_dhash=ref_dh)
            with self.assertRaises(BoardError):
                assemble("face", views, d / "out", title="x", consent_declared=False,
                         reference_sha=ref_sha, reference_dhash=ref_dh)


class T09WorkerStop(unittest.TestCase):
    def test_stop_mid_job_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            refs = synth_images(d / "r", 2, size=(256, 256))
            mgr = JobManager(d / "w", TestPatternBackend(delay_s=0.3))
            job = _job_with_refs(mgr, "face", refs)
            mgr.start(job["id"])
            while sum(v["state"] == "done" for v in mgr.load(job["id"])["views"].values()) < 2:
                time.sleep(0.05)
            # brutal stop: kill the loop and pretend the process died while a view was running
            mgr.stop.set()
            mgr.thread.join(timeout=5)
            j = mgr.load(job["id"])
            j["state"] = "running"
            for v in j["views"].values():
                if v["state"] == "pending":
                    v["state"] = "running"
                    break
            mgr.save(j)
            done_before = {v: s["provenance"]["sha256"] for v, s in j["views"].items() if s["state"] == "done"}
            mgr2 = JobManager(d / "w", TestPatternBackend())
            try:
                j2 = mgr2.wait(job["id"])
                self.assertEqual(j2["state"], "succeeded")
                for v, h in done_before.items():
                    self.assertEqual(j2["views"][v]["provenance"]["sha256"], h)   # not redone
                self.assertTrue(any("reprise" in e["event"] for e in j2["events"]))
            finally:
                mgr2.shutdown()

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            refs = synth_images(d / "r", 1, size=(256, 256))
            mgr = JobManager(d / "w", TestPatternBackend(delay_s=0.2))
            try:
                job = _job_with_refs(mgr, "face", refs)
                mgr.start(job["id"])
                time.sleep(0.3)
                mgr.cancel(job["id"])
                time.sleep(0.5)
                j = mgr.load(job["id"])
                self.assertEqual(j["state"], "cancelled")
                self.assertTrue(any(v["state"] == "pending" for v in j["views"].values()))
                mgr.start(job["id"])
                self.assertEqual(mgr.wait(job["id"])["state"], "succeeded")
            finally:
                mgr.shutdown()


class HttpContract(unittest.TestCase):
    def test_http_flow_and_auth(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ref = synth_images(d / "r", 1, size=(256, 256))[0]
            httpd, mgr, token = serve(d / "w", "test_pattern", port=0)
            import threading
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{httpd.server_address[1]}"

            def call(method, path, body=None, headers=None, auth=True):
                h = {"Authorization": f"Bearer {token}"} if auth else {}
                h.update(headers or {})
                req = urllib.request.Request(base + path, data=body, method=method, headers=h)
                try:
                    with urllib.request.urlopen(req, timeout=10) as r:
                        return r.status, r.read()
                except urllib.error.HTTPError as e:
                    return e.code, e.read()
            try:
                self.assertEqual(call("GET", "/v1/health", auth=False)[0], 401)
                code, b = call("POST", "/v1/jobs", json.dumps({"kind": "body", "consent_declared": True}).encode())
                self.assertEqual(code, 201)
                jid = json.loads(b)["id"]
                sha = sha256_file(ref)
                self.assertEqual(call("PUT", f"/v1/jobs/{jid}/references/{sha}", ref.read_bytes())[0], 403)
                self.assertEqual(call("PUT", f"/v1/jobs/{jid}/references/{'0' * 64}", ref.read_bytes(),
                                      {"X-Consent": "granted"})[0], 400)
                self.assertEqual(call("PUT", f"/v1/jobs/{jid}/references/{sha}", ref.read_bytes(),
                                      {"X-Consent": "granted"})[0], 200)
                call("POST", f"/v1/jobs/{jid}/start")
                mgr.wait(jid)
                code, png = call("GET", f"/v1/jobs/{jid}/outputs/pied_face")
                self.assertEqual(code, 200)
                self.assertTrue(png.startswith(b"\x89PNG"))
                self.assertEqual(call("GET", f"/v1/jobs/{jid}/board.png")[0], 200)
                m = json.loads(call("GET", f"/v1/jobs/{jid}/manifest")[1])
                self.assertEqual(m["kind"], "body")
                self.assertEqual(call("GET", "/v1/jobs/../../etc")[0], 404)
                self.assertEqual(call("DELETE", f"/v1/jobs/{jid}")[0], 200)
                self.assertEqual(call("GET", f"/v1/jobs/{jid}")[0], 404)
            finally:
                httpd.shutdown()
                mgr.shutdown()


class PoseMaps(unittest.TestCase):
    def test_back_view_hides_face(self):
        self.assertIsNone(keypoints(180, 768, 1344)[0])
        self.assertIsNotNone(keypoints(0, 768, 1344)[0])
        for v in BODY_VIEWS:
            im = pose_map(v)
            self.assertEqual(im.size, (768, 1344))
            self.assertGreater(len(set(im.tobytes())), 5)


FAKE_SDCLI = """#!/usr/bin/env python3
import sys, json, os
from PIL import Image
a = sys.argv[1:]
out = a[a.index("-o") + 1]
if "--pm-id-images-dir" in a:
    d = a[a.index("--pm-id-images-dir") + 1]
    n = len([f for f in os.listdir(d) if f.endswith((".png", ".jpg"))])
    assert n >= 1, "no id images"
if os.environ.get("FAKE_FAIL"):
    print("boom"); sys.exit(3)
w, h = int(a[a.index("-W") + 1]), int(a[a.index("-H") + 1])
Image.effect_noise((w, h), 60).convert("RGB").save(out)
open(out + ".args.json", "w").write(json.dumps(a))
"""


class SdCppBackendTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.bin = self.d / "sd-cli"
        self.bin.write_text(FAKE_SDCLI.replace("/usr/bin/env python3", sys.executable))
        self.bin.chmod(0o755)
        for f in ("model.gguf", "pm.safetensors"):
            (self.d / f).write_bytes(b"x")

    def backend(self):
        from persona_engine.backends.sdcpp import SdCppBackend
        return SdCppBackend(binary=str(self.bin), model=str(self.d / "model.gguf"),
                            photomaker=str(self.d / "pm.safetensors"), threads=2)

    def test_missing_files_refused(self):
        from persona_engine.backends.sdcpp import SdCppBackend
        with self.assertRaises(FileNotFoundError):
            SdCppBackend(binary=str(self.bin), model=str(self.d / "absent.gguf"), photomaker=str(self.d / "pm.safetensors"))

    def test_face_and_body_jobs_through_worker(self):
        refs = synth_images(self.d / "r", 2, size=(256, 256))
        mgr = JobManager(self.d / "w", self.backend())
        try:
            for kind, n in (("face", 6), ("body", 4)):
                job = _job_with_refs(mgr, kind, refs)
                mgr.start(job["id"])
                job = mgr.wait(job["id"], timeout=60)
                self.assertEqual(job["state"], "succeeded", job["events"][-3:])
                m = mgr.manifest(job["id"])
                self.assertEqual(m["status"], "candidate_for_human_review")   # vraie génération (moteur simulé ici)
                self.assertEqual(len(m["views"]), n)
                v0 = next(iter(job["views"].values()))
                args = json.loads(Path(str(mgr._jdir(job["id"]) / "out" / f"{next(iter(job['views']))}.png") + ".args.json").read_text())
                self.assertIn("--photo-maker", args)
                self.assertIn(" img,", args[args.index("-p") + 1])
                self.assertIn("RAM pic", v0["provenance"]["hardware"])
                if kind == "body":
                    self.assertTrue(any("pose" in w for w in v0["provenance"]["warnings"]))
        finally:
            mgr.shutdown()

    def test_synthetic_reference_without_photomaker_and_failure(self):
        b = self.backend()
        r = b.generate(kind="face", view="face", references=[], seed=1, params={}, out_path=self.d / "s.png",
                       use_photomaker=False)
        args = json.loads((self.d / "s.png.args.json").read_text())
        self.assertNotIn("--photo-maker", args)
        self.assertIn("fictitious", r.prompt)
        os.environ["FAKE_FAIL"] = "1"
        try:
            with self.assertRaises(RuntimeError):
                b.generate(kind="face", view="face", references=[self.d / "s.png"], seed=1, params={},
                           out_path=self.d / "f.png")
        finally:
            os.environ.pop("FAKE_FAIL")


class OfflinePolicy(unittest.TestCase):
    def test_offline_enforced_unless_explicit(self):
        import os
        from persona_engine import offline
        saved = {k: os.environ.pop(k, None) for k in offline.OFFLINE_VARS + ("PERSONA_ALLOW_DOWNLOAD",)}
        try:
            self.assertTrue(offline.enforce_offline())
            self.assertTrue(all(os.environ[v] == "1" for v in offline.OFFLINE_VARS))
            for v in offline.OFFLINE_VARS:
                os.environ.pop(v)
            os.environ["PERSONA_ALLOW_DOWNLOAD"] = "1"
            self.assertFalse(offline.enforce_offline())
            self.assertNotIn("HF_HUB_OFFLINE", os.environ)
            os.environ.pop("PERSONA_ALLOW_DOWNLOAD")
            with self.assertRaises(SystemExit):
                offline.prefetch()
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main(verbosity=2)
