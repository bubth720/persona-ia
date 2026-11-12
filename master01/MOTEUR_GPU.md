# MASTER 01 — Phase B : moteur de génération

## État : **BLOQUÉ dans cette session**, prêt à exécuter sur GPU

Cette session cloud n'a **ni GPU** (`nvidia-smi` absent ; 4 vCPU, 15 Go RAM) **ni accès à HuggingFace ou aux dépôts GitHub tiers** (réponses réseau 000/403). Aucune image n'a donc été générée ici. Gate B n'est **pas** atteinte : tant qu'aucune image n'existe avec son journal, aucun PASS n'est déclaré.

Ce qui est livré pour que la génération ait lieu dès qu'un GPU est disponible :

| Élément | Fichier |
|---|---|
| Environnement verrouillé (302 paquets épinglés, Python 3.11) | `engine/requirements-gpu.lock` (source `requirements-gpu.in`) |
| Notebook Colab T4 de bout en bout (capture d'environnement, test d'import, chargement des poids, démo, mode réel, revue, export) | `engine/colab/PERSONA_MASTER01_GEN.ipynb` |
| Backend PhotoMaker V2 + SDXL (+ ControlNet OpenPose pour le corps) | `engine/persona_engine/backends/photomaker_v2.py` |
| Cartes de pose déterministes (face, profil, trois-quarts, dos) | `engine/persona_engine/pose.py` |
| Capture `nvidia-smi`/torch/CUDA/VRAM/disque/`pip freeze`/commit PhotoMaker | `engine/persona_engine/env_capture.py` |
| Pilote planches visage + corps | `engine/persona_engine/run_boards.py` |
| Worker HTTP authentifié (même API pour Colab ou futur PC) | `engine/persona_engine/worker.py` |

## B1. Diagnostic de l'échec Colab rapporté (`import photomaker` échoue sur diffusers)

Vérifié par résolution de dépendances (`uv pip compile`) :
* la pile verrouillée **se résout pour Python 3.11** ;
* **elle ne se résout pas pour Python 3.13** : `torch==2.3.1 has no wheels with a matching Python ABI tag`.

Les mises à jour successives de `diffusers` sur le Python 3.13 de Colab mélangent des versions incompatibles avec le code PhotoMaker (épinglé autour de diffusers 0.29). Correctif : ne plus toucher au Python système de Colab, créer un **venv Python 3.11 avec `uv`** et installer uniquement le fichier verrouillé (cellule 2 du notebook).

Points de vigilance non vérifiables ici : `insightface==0.7.3` n'est distribué qu'en source (compilation de ~2 min sur Colab) ; `onnxruntime-gpu==1.18.1` de PyPI cible CUDA 11.8 et peut se replier sur le CPU pour la détection de visage (lent mais correct).

## B2. Candidats

| Candidat | Usage | Licence code / poids (à reconfirmer sur la carte du modèle au téléchargement) | Décision |
|---|---|---|---|
| **PhotoMaker V2** (TencentARC) + **RealVisXL V4.0** (SDXL) | identité faciale à partir de plusieurs références | code Apache-2.0 ; `photomaker-v2.bin` Apache-2.0 ; RealVisXL CreativeML OpenRAIL++-M | 1er candidat |
| InsightFace `buffalo_l` / `antelopev2` (requis par PhotoMaker V2 pour les embeddings d'identité) | détection + embedding | code MIT ; **modèles pré-entraînés réservés à la recherche non commerciale** | acceptable pour usage personnel non commercial uniquement |
| ControlNet OpenPose SDXL (`xinsir/controlnet-openpose-sdxl-1.0`) | cadrage et angle du corps | Apache-2.0 | nécessaire pour la planche corps ; ne garantit pas l'identité du corps |
| PuLID-SDXL / InstantID | alternative d'identité | Apache-2.0 (code) ; InstantID dépend aussi d'InsightFace | à essayer seulement si PhotoMaker est instable sur les mêmes références |
| Backend PC local | même API (`worker.py`) | — | plus tard, sans changer l'app Android |

Règles appliquées dans le code : FP16, `enable_model_cpu_offload()`, tuilage VAE, **une seule pipeline lourde chargée à la fois** (le passage visage → corps libère la précédente), un job à la fois. Le worker écoute `127.0.0.1` par défaut, exige un jeton, n'ouvre ni Gradio ni tunnel.

## Ce qu'il reste à mesurer (à remplir après l'exécution Colab)

| Mesure | Valeur |
|---|---|
| GPU / VRAM / Python / torch / CUDA | `persona_out/env_capture.json` |
| Commit PhotoMaker | `photomaker_commit.txt` |
| SHA-256 de `photomaker-v2.bin` | cellule 4 |
| Temps par image, VRAM de pointe | `run_summary.json`, champ `provenance` de chaque vue |
| Coût GPU | Colab gratuit/Pro : noter les unités de calcul consommées |

**Gate B — PASS** seulement quand `run_summary.json` montre au moins une vue `done` avec `is_generation: true` et que l'image a été regardée.

## Politique de suppression des fichiers temporaires

Les références envoyées au worker restent dans `jobs/<id>/refs/` tant que des vues peuvent être régénérées ; `DELETE /v1/jobs/<id>` (bouton à prévoir dans l'app) les efface. Le zip d'export du notebook exclut `refs/` et `refbank/originals/`.
