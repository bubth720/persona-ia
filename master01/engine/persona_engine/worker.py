"""Engine worker: persistent jobs + authenticated HTTP API (see contract.py).

* One generation job at a time (VRAM rule for a 15 GB T4).
* Job state is written atomically after every transition; on restart, views left
  ``running`` go back to ``pending`` and the job is re-queued (T09), finished views
  are kept.
* A single view can be rejected and regenerated without touching the others (T07).
* Binds 127.0.0.1 by default; every call requires the Bearer token. No public tunnel.
* Uploaded references stay in the job folder (regeneration needs them) and are erased by DELETE /v1/jobs/{id}.
"""
from __future__ import annotations

from .offline import enforce_offline

enforce_offline()   # avant tout import de huggingface_hub / diffusers (lus à l'import)

import argparse
import hmac
import json
import re
import secrets
import shutil
import threading
import time
import traceback
import uuid
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .backends import get_backend
from .boards import assemble, BoardError
from .contract import views_for, VIEW_STATES
from .util import atomic_write_json, read_json, now_iso, sha256_bytes, sha256_file, dhash

MAX_REF_BYTES = 40 * 2**20


def _live_running() -> bool:
    try:
        from .hardware import live_running
        return live_running()
    except Exception:  # noqa: BLE001
        return False
MAX_REFS = 64


class JobManager:
    def __init__(self, root: Path, backend):
        self.root = Path(root)
        self.jobs_dir = self.root / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend
        self.lock = threading.RLock()
        self.cancel_flags: dict[str, threading.Event] = {}
        self.queue: list[str] = []
        self.wake = threading.Event()
        self.stop = threading.Event()
        self._recover()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    # ------------------------------------------------------------ storage
    def _jdir(self, jid: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", jid):
            raise KeyError(jid)
        return self.jobs_dir / jid

    def load(self, jid: str) -> dict:
        j = read_json(self._jdir(jid) / "job.json")
        if j is None:
            raise KeyError(jid)
        return j

    def save(self, job: dict) -> None:
        job["updated_at"] = now_iso()
        if job.get("_last_logged") != job["state"]:
            job["_last_logged"] = job["state"]
            print(f"{job['updated_at']} job {job['id'][:8]} {job['kind']} -> {job['state']}", flush=True)
        atomic_write_json(self._jdir(job["id"]) / "job.json", job)

    def _recover(self) -> None:
        for p in sorted(self.jobs_dir.glob("*/job.json")):
            job = read_json(p)
            if job is None:
                continue
            changed = False
            for v in job["views"].values():
                if v["state"] == "running":
                    v["state"], changed = "pending", True
            if job["state"] in ("running", "queued"):
                job["state"] = "queued"
                job.setdefault("events", []).append({"at": now_iso(), "event": "reprise après arrêt du worker"})
                self.queue.append(job["id"])
                changed = True
            if changed:
                self.save(job)

    # ------------------------------------------------------------ API ops
    def create(self, spec: dict) -> dict:
        kind = spec.get("kind")
        views = views_for(kind, spec.get("extra_views"))
        if spec.get("views"):
            views = [v for v in views if v in spec["views"]]
        if not spec.get("consent_declared"):
            raise PermissionError("consent_declared requis (usage des photographies et de la ressemblance autorisé)")
        jid = uuid.uuid4().hex
        seed = int(spec.get("seed", secrets.randbelow(2**31)))
        job = {"id": jid, "kind": kind, "state": "created", "created_at": now_iso(), "seed": seed,
               "profile": spec.get("profile", "default"), "params": spec.get("params", {}),
               "backend": self.backend.describe(), "references": [],
               "views": {v: {"state": "pending", "seed": seed + i, "attempts": 0} for i, v in enumerate(views)},
               "events": [{"at": now_iso(), "event": "créé"}]}
        self._jdir(jid).mkdir(parents=True)
        self.save(job)
        return job

    def add_reference(self, jid: str, sha: str, data: bytes, consent: bool) -> dict:
        if not consent:
            raise PermissionError("X-Consent: granted requis pour chaque référence")
        if sha256_bytes(data) != sha:
            raise ValueError("empreinte SHA-256 ne correspond pas au contenu")
        with self.lock:
            job = self.load(jid)
            if job["state"] not in ("created",):
                raise ValueError("références uniquement avant le démarrage")
            if len(job["references"]) >= MAX_REFS:
                raise ValueError("trop de références")
            from io import BytesIO
            from PIL import Image
            with Image.open(BytesIO(data)) as im:
                im.verify()
            refdir = self._jdir(jid) / "refs"
            refdir.mkdir(exist_ok=True)
            (refdir / f"{sha}.img").write_bytes(data)
            if sha not in job["references"]:
                job["references"].append(sha)
            self.save(job)
            return job

    def start(self, jid: str) -> dict:
        with self.lock:
            job = self.load(jid)
            if not job["references"] and self.backend.is_generation:
                raise ValueError("aucune référence autorisée")
            if job["state"] in ("created", "failed", "cancelled", "succeeded"):
                job["state"] = "queued"
                job["events"].append({"at": now_iso(), "event": "mis en file"})
                self.save(job)
                self.queue.append(jid)
                self.wake.set()
            return job

    def cancel(self, jid: str) -> dict:
        with self.lock:
            job = self.load(jid)
            self.cancel_flags.setdefault(jid, threading.Event()).set()
            if jid in self.queue:
                self.queue.remove(jid)
            if job["state"] in ("created", "queued", "running"):
                job["state"] = "cancelled"
                for v in job["views"].values():
                    if v["state"] in ("pending", "running"):
                        v["state"] = "pending"
                job["events"].append({"at": now_iso(), "event": "annulé"})
                self.save(job)
            return job

    def review(self, jid: str, view: str, accepted: bool, note: str = "") -> dict:
        with self.lock:
            job = self.load(jid)
            v = job["views"][view]
            if v["state"] not in ("done", "accepted", "rejected"):
                raise ValueError("vue non terminée")
            v["state"] = "accepted" if accepted else "rejected"
            v["review"] = {"accepted": accepted, "note": note, "at": now_iso()}
            self.save(job)
            return job

    def regenerate(self, jid: str, view: str, seed: int | None = None) -> dict:
        with self.lock:
            job = self.load(jid)
            v = job["views"][view]
            if v["state"] == "running":
                raise ValueError("vue en cours")
            v["state"] = "pending"
            v["seed"] = int(seed) if seed is not None else v["seed"] + 1000
            v.pop("review", None)
            job["events"].append({"at": now_iso(), "event": f"régénération {view}"})
            self.save(job)
        self.cancel_flags.pop(jid, None)
        return self.start(jid)

    def output_path(self, jid: str, view: str) -> Path:
        job = self.load(jid)
        if view not in job["views"] or job["views"][view]["state"] not in ("done", "accepted", "rejected"):
            raise KeyError(view)
        return self._jdir(jid) / "out" / f"{view}.png"

    def manifest(self, jid: str) -> dict:
        job = self.load(jid)
        m = read_json(self._jdir(jid) / "board" / f"manifest_{job['kind']}.json")
        return m if m is not None else {"status": "absent", "job": job}

    # ------------------------------------------------------------ execution
    def _loop(self) -> None:
        while not self.stop.is_set():
            jid = None
            with self.lock:
                if self.queue:
                    jid = self.queue.pop(0)
            if jid is None:
                self.wake.wait(0.2)
                self.wake.clear()
                continue
            try:
                self._run(jid)
            except Exception:  # noqa: BLE001
                with self.lock:
                    job = self.load(jid)
                    job["state"] = "failed"
                    job["events"].append({"at": now_iso(), "event": "erreur", "detail": traceback.format_exc()[-2000:]})
                    self.save(job)

    def _run(self, jid: str) -> None:
        flag = self.cancel_flags.setdefault(jid, threading.Event())
        flag.clear()
        with self.lock:
            job = self.load(jid)
            if job["state"] != "queued":
                return
            if self.backend.is_generation and _live_running():
                job["state"] = "failed"
                job["events"].append({"at": now_iso(), "event": "refusé",
                                      "detail": "PERSONA LIVE est ouvert : fermez-le avant un calcul IA lourd (exclusion mémoire)."})
                self.save(job)
                return
            job["state"] = "running"
            self.save(job)
        refs = [self._jdir(jid) / "refs" / f"{s}.img" for s in job["references"]]
        for view, vstate in job["views"].items():
            if vstate["state"] != "pending":
                continue
            if flag.is_set():
                return
            with self.lock:
                job = self.load(jid)
                job["views"][view]["state"] = "running"
                job["views"][view]["attempts"] += 1
                self.save(job)
            out = self._jdir(jid) / "out" / f"{view}.png"
            try:
                res = self.backend.generate(kind=job["kind"], view=view, references=refs, seed=vstate["seed"],
                                            params=job["params"], out_path=out)
                prov = asdict(res) | {"path": out.name, "sha256": sha256_file(out), "at": now_iso()}
                new_state, err = "done", None
            except Exception as exc:  # noqa: BLE001
                prov, new_state, err = None, "failed", str(exc)
            with self.lock:
                job = self.load(jid)
                if job["state"] == "cancelled":
                    job["views"][view]["state"] = "pending"
                    self.save(job)
                    return
                job["views"][view]["state"] = new_state
                if prov:
                    job["views"][view]["provenance"] = prov
                if err:
                    job["views"][view]["error"] = err
                self.save(job)
        board_error = self._build_board(jid)       # board first, then the terminal state (no race)
        with self.lock:
            job = self.load(jid)
            states = {v["state"] for v in job["views"].values()}
            job["state"] = "failed" if ("failed" in states or board_error) else "succeeded"
            if board_error:
                job["events"].append({"at": now_iso(), "event": "planche refusée", "detail": board_error})
            job["events"].append({"at": now_iso(), "event": job["state"]})
            self.save(job)
        # Uploaded references stay in the job folder while views may still be regenerated (T07);
        # DELETE /v1/jobs/{id} erases them. Policy documented in MOTEUR_GPU.md.

    def _build_board(self, jid: str) -> str | None:
        job = self.load(jid)
        done = {v: s for v, s in job["views"].items() if s["state"] in ("done", "accepted", "rejected")}
        if not done:
            return None
        refs = {s: self._jdir(jid) / "refs" / f"{s}.img" for s in job["references"]}
        from PIL import Image
        ref_dh = {}
        for s, p in refs.items():
            with Image.open(p) as im:
                ref_dh[s] = dhash(im)
        views = {v: {"path": self._jdir(jid) / "out" / f"{v}.png", "is_generation": s["provenance"]["is_generation"],
                     "provenance": s["provenance"], "review": s.get("review")} for v, s in done.items()}
        try:
            assemble(job["kind"], views, self._jdir(jid) / "board", title=f"PERSONA IA — {job['profile']}",
                     consent_declared=True, reference_sha=set(refs), reference_dhash=ref_dh,
                     extra={"job_id": jid, "backend": job["backend"]})
        except BoardError as exc:
            return str(exc)
        return None

    def rebuild_board(self, jid: str) -> dict:
        self._build_board(jid)
        return self.manifest(jid)

    def list_jobs(self) -> list[dict]:
        out = []
        for p in self.jobs_dir.glob("*/job.json"):
            j = read_json(p)
            if j:
                out.append({k: j.get(k) for k in ("id", "kind", "state", "created_at", "seed", "profile")})
        return sorted(out, key=lambda j: j["created_at"] or "", reverse=True)

    def delete(self, jid: str) -> None:
        self.cancel(jid)
        shutil.rmtree(self._jdir(jid))

    def wait(self, jid: str, timeout: float = 30) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout:
            job = self.load(jid)
            if job["state"] in ("succeeded", "failed", "cancelled") and jid not in self.queue:
                return job
            time.sleep(0.05)
        raise TimeoutError(jid)

    def shutdown(self) -> None:
        self.stop.set()
        self.wake.set()
        self.thread.join(timeout=5)


# ---------------------------------------------------------------- HTTP layer
def make_handler(mgr: JobManager, token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PersonaEngine/1"

        def log_message(self, fmt, *args):  # no request logging of paths with ids to stdout
            pass

        def _auth(self) -> bool:
            got = self.headers.get("Authorization", "")
            if not hmac.compare_digest(got.encode(), f"Bearer {token}".encode()):
                self._json(401, {"error": "non autorisé"})
                return False
            return True

        def _json(self, code: int, obj) -> None:
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> bytes:
            n = int(self.headers.get("Content-Length", "0"))
            if n > MAX_REF_BYTES:
                raise ValueError("corps trop volumineux")
            return self.rfile.read(n) if n else b""

        def _route(self, method: str):
            parts = [p for p in self.path.split("?")[0].split("/") if p]
            if method == "GET" and parts in ([], ["ui"]):
                # Page de l'atelier : statique, sans données ; l'API reste protégée par le jeton.
                body = (Path(__file__).parent / "ui" / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' blob: data:")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if not self._auth():
                return
            try:
                if parts == ["v1", "health"]:
                    return self._json(200, {"ok": True, "backend": mgr.backend.describe()})
                if parts == ["v1", "hardware"]:
                    from .hardware import detect
                    return self._json(200, detect())
                if parts[:2] != ["v1", "jobs"]:
                    return self._json(404, {"error": "inconnu"})
                if method == "POST" and len(parts) == 2:
                    return self._json(201, mgr.create(json.loads(self._body() or b"{}")))
                if method == "GET" and len(parts) == 2:
                    return self._json(200, {"jobs": mgr.list_jobs()})
                jid = parts[2]
                rest = parts[3:]
                if method == "GET" and not rest:
                    return self._json(200, mgr.load(jid))
                if method == "DELETE" and not rest:
                    mgr.delete(jid)
                    return self._json(200, {"deleted": jid})
                if method == "PUT" and len(rest) == 2 and rest[0] == "references":
                    consent = self.headers.get("X-Consent", "") == "granted"
                    return self._json(200, mgr.add_reference(jid, rest[1], self._body(), consent))
                if method == "POST" and rest == ["start"]:
                    return self._json(200, mgr.start(jid))
                if method == "POST" and rest == ["cancel"]:
                    return self._json(200, mgr.cancel(jid))
                if method == "GET" and rest == ["manifest"]:
                    return self._json(200, mgr.manifest(jid))
                if method == "POST" and rest == ["board"]:
                    return self._json(200, mgr.rebuild_board(jid))
                if method == "GET" and len(rest) == 2 and rest[0] == "outputs":
                    data = mgr.output_path(jid, rest[1]).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if method == "GET" and rest == ["board.png"]:
                    job = mgr.load(jid)
                    name = "planche_faciale.png" if job["kind"] == "face" else "planche_corporelle.png"
                    data = (mgr._jdir(jid) / "board" / name).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if method == "POST" and len(rest) == 3 and rest[0] == "views":
                    b = json.loads(self._body() or b"{}")
                    if rest[2] == "review":
                        return self._json(200, mgr.review(jid, rest[1], bool(b.get("accepted")), str(b.get("note", ""))))
                    if rest[2] == "regenerate":
                        return self._json(200, mgr.regenerate(jid, rest[1], b.get("seed")))
                return self._json(404, {"error": "route inconnue"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except (KeyError, FileNotFoundError):
                return self._json(404, {"error": "introuvable"})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

        def do_PUT(self):
            self._route("PUT")

        def do_DELETE(self):
            self._route("DELETE")

    return Handler


def serve(root: Path, backend_name: str, host: str = "127.0.0.1", port: int = 8765, token: str | None = None,
          token_file: Path | None = None, backend_kwargs: dict | None = None):
    token = token or secrets.token_urlsafe(32)
    if token_file:
        Path(token_file).write_text(token)
        Path(token_file).chmod(0o600)
    mgr = JobManager(root, get_backend(backend_name, **(backend_kwargs or {})))
    httpd = ThreadingHTTPServer((host, port), make_handler(mgr, token))
    return httpd, mgr, token


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="PERSONA IA engine worker")
    ap.add_argument("--root", default="persona_worker_data")
    ap.add_argument("--backend", default="photomaker_v2", choices=["photomaker_v2", "sdcpp", "test_pattern"])
    ap.add_argument("--host", default="127.0.0.1",
                    help="0.0.0.0 uniquement sur LAN privé de confiance, jamais exposé publiquement")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token-file", default="worker_token.txt")
    ap.add_argument("--token", default=None, help="jeton imposé (tests CI); sinon aléatoire")
    ap.add_argument("--open-ui", action="store_true", help="ouvrir l'atelier dans le navigateur")
    a = ap.parse_args(argv)
    httpd, mgr, token = serve(Path(a.root), a.backend, a.host, a.port, a.token, Path(a.token_file))
    print(f"PERSONA engine on {a.host}:{httpd.server_address[1]} backend={a.backend} token-file={a.token_file}",
          flush=True)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/#token={token}"
    print(f"Atelier : {url}", flush=True)
    if a.open_ui:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    finally:
        mgr.shutdown()


if __name__ == "__main__":
    main()
