"""Engine contract shared by the Python worker and the Android client.

The Android app only knows this contract; any backend (Colab T4, future local PC)
can be swapped without touching the screens.

HTTP API (all calls require ``Authorization: Bearer <token>``; worker binds 127.0.0.1
by default and never opens a public tunnel by itself):

  createJob                  POST /v1/jobs                              body: JobSpec JSON
  uploadAuthorizedReferences PUT  /v1/jobs/{id}/references/{sha256}     body: image bytes,
                                                                        header X-Consent: granted
  startJob                   POST /v1/jobs/{id}/start
  getStatus                  GET  /v1/jobs/{id}
  cancelJob                  POST /v1/jobs/{id}/cancel
  fetchOutputs               GET  /v1/jobs/{id}/outputs/{view}         -> PNG
  fetchManifest              GET  /v1/jobs/{id}/manifest               -> JSON
  reviewView                 POST /v1/jobs/{id}/views/{view}/review     body {"accepted": bool, "note": str}
  regenerateView             POST /v1/jobs/{id}/views/{view}/regenerate body {"seed": int?}
  health                     GET  /v1/health                            (backend + is_generation flag)
"""
from __future__ import annotations

FACE_VIEWS = ["face", "profil_gauche", "profil_droit", "trois_quarts_gauche", "trois_quarts_droit", "expression"]
BODY_VIEWS = ["pied_face", "pied_profil", "pied_trois_quarts", "pied_dos"]
OPTIONAL_BODY_VIEWS = ["pied_profil_oppose"]

VIEW_LABELS = {
    "face": "Face",
    "profil_gauche": "Profil gauche",
    "profil_droit": "Profil droit",
    "trois_quarts_gauche": "Trois-quarts gauche",
    "trois_quarts_droit": "Trois-quarts droit",
    "expression": "Expression alternative",
    "pied_face": "Plein pied — face",
    "pied_profil": "Plein pied — profil",
    "pied_trois_quarts": "Plein pied — trois-quarts",
    "pied_dos": "Plein pied — dos (estimé)",
    "pied_profil_oppose": "Plein pied — profil opposé",
}

# Reference-bank view classes (Phase C). "non_classe" until a human validates.
REFERENCE_VIEWS = ["face", "profil_gauche", "profil_droit", "trois_quarts_gauche", "trois_quarts_droit",
                   "dos", "plan_americain", "plein_pied", "non_classe"]

# Views whose content is never observable from usual photo sets: always flagged "estimé".
ALWAYS_ESTIMATED = {"pied_dos": ["dos complet", "arrière de la tête", "dos des mains"]}

JOB_STATES = ["created", "queued", "running", "succeeded", "failed", "cancelled"]
VIEW_STATES = ["pending", "running", "done", "failed", "rejected", "accepted"]

KINDS = {"face": FACE_VIEWS, "body": BODY_VIEWS}


def views_for(kind: str, extra: list[str] | None = None) -> list[str]:
    if kind not in KINDS:
        raise ValueError(f"kind inconnu: {kind}")
    views = list(KINDS[kind])
    for v in extra or []:
        if v in OPTIONAL_BODY_VIEWS and kind == "body" and v not in views:
            views.append(v)
    return views
