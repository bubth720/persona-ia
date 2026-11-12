# PERSONA IA — MASTER 01

Exécution de « PERSONA IA MASTER 01 — Mission intégrale » (12 novembre 2026) sur la branche `ccr-8f135e00-hwmdvs`. `main` n'est pas modifiée. PERSONA-3D n'est pas modifié.

**Commencer par [`TABLEAU_DE_BORD.md`](TABLEAU_DE_BORD.md)** : statut PASS / PARTIEL / BLOQUÉ de chaque phase, avec les preuves.

| Dossier / fichier | Phase |
|---|---|
| `INVENTAIRE_RECUPERATION.md` | A — récupération M1–M3.1 |
| `MOTEUR_GPU.md`, `engine/requirements-gpu.lock`, `engine/colab/` | B — moteur GPU |
| `engine/persona_engine/refbank.py` | C — banque de références |
| `engine/persona_engine/backends/photomaker_v2.py`, `pose.py`, `run_boards.py`, `REVUE_HUMAINE.md` | D/E — planches visage et corps |
| `engine/persona_engine/boards.py` | F — assemblage, manifeste, anti-substitution |
| `engine/persona_engine/worker.py`, `contract.py`, `android/` | G — contrat moteur et application Android |
| `AUDIT_PERSONA3D.md` | H — PERSONA-3D |
| `PHASE_I_VIDEO_LIVE.md` | I — vidéo et PERSONA LIVE |
| `../.github/workflows/master01.yml` | CI : tests moteur, APK, émulateurs API 29/35 |

## Commandes

```bash
# Tests moteur (sans GPU, données synthétiques)
cd master01/engine && python -m unittest -v tests.test_master01

# Worker de TEST (non génératif) pour essayer l'app Android en local
python -m persona_engine.worker --backend test_pattern --port 8765   # jeton dans worker_token.txt

# Worker réel sur PC/GPU (environnement verrouillé Python 3.11 + clone PhotoMaker sur PYTHONPATH)
python -m persona_engine.worker --backend photomaker_v2 --host 127.0.0.1 --port 8765

# APK
cd master01/android && ./gradlew assembleDebug testDebugUnitTest
```

Le backend `test_pattern` existe uniquement pour tester la plomberie : chaque image porte « TEST — PAS UNE GÉNÉRATION », son manifeste porte `is_generation: false` et la planche est classée `layout_test_only`. Il ne peut jamais valider les phases D ou E.
