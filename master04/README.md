# MASTER-04 — PERSONA : photographie → reconstruction → personnage interactif

Branche **`master04/persona-live`** (issue de `ccr-8f135e00-hwmdvs` à `e160c8d`). `main`, JARVIS et les autres projets ne sont pas modifiés.

## Décision

| Niveau | Statut | Preuve |
|---|---|---|
| **LIVE-DEMO** — scène interactive et personnage générique | **ATTEINT** | exécutable Windows : 15/15 autotests sur machine Windows ; rendu OpenGL réel avec capture (Linux) |
| **LIVE-INTEGRATED** — import d'un personnage personnalisé et liaison avec les dossiers PERSONA | **ATTEINT** | chaîne CI : images générées par le moteur (fictives) → analyse corporelle → dossier PERSONA → modèle Blender riggé → chargé et piloté dans l'exécutable exporté (15/15) |
| **LIVE-IDENTITY** — personnage reconstruit fidèle à la personne | **NON ATTEINT** | pas de reconstruction du visage ou du corps ; aucune fidélité évaluée |

Restent à faire **sur ton PC** : l'autotest avec rendu sur GPU réel et l'installation complète (voir `GUIDE_INSTALLATION.md`).

## Livrables

| # | Livrable | Où |
|---|---|---|
| 1 | Exécutable Windows PERSONA LIVE | artefact Actions `PERSONA_LIVE-windows` (+ `characters/` démo) |
| 2 | Sources et projet 3D | `master04/live/` (Godot 4.3), `master04/pipeline/blender/make_character.py` |
| 3 | Atelier photographique PC | `master01/engine/persona_engine/ui/` + worker ; paquet `PERSONA_PC-windows-package` |
| 4 | Pipeline de reconstruction | `PIPELINE.md`, `persona_engine/body.py`, `persona_engine/character.py` |
| 5 | Personnage de démonstration libre (CC0) | artefact `persona-demo-character` (GLB + FBX), régénérable par script |
| 6 | Scène interactive | PERSONA LIVE (décors Studio et Jardin, registre de 5 emplacements) |
| 7 | Guide d'installation | `GUIDE_INSTALLATION.md`, `install/Installer-PERSONA.ps1` |
| 8 | Rapport de performances et limites | `RAPPORT_PERFORMANCES_LIMITES.md` |
| 9 | Matrice de tests avec preuves | `MATRICE_TESTS.md`, `evidence/` (fictif uniquement) |
| 10 | Branche et commits | `master04/persona-live` ; CI `.github/workflows/master04-live.yml` |
