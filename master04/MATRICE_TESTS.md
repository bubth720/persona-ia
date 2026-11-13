# MASTER-04 — matrice de tests avec preuves

Workflow `.github/workflows/master04-live.yml`, branche `master04/persona-live`. Les preuves sont dans les artefacts de chaque exécution (onglet Actions). Les seules données utilisées sont **fictives** : personnage généré par script, ou personne inventée produite par le moteur lors de MASTER-01 (run `43300222986`).

| # | Test | Environnement | Résultat | Preuve |
|---|---|---|---|---|
| L01 | Projet Godot : import et analyse de tous les scripts sans erreur | Linux CI | **PASS** | job « Phase 4 », étape *Import project* |
| L02 | Autotest intégré (15 contrôles) sans affichage : scène, squelette, animations, marche 0,93 m, état walk, course 4,2 m/s, arrêt (idle), rotation vers le déplacement, orbite et zoom caméra, lampe, changement de décor, import GLB depuis le disque, personnage importé qui se déplace, réglages sauvegardés | Linux CI | **15/15 PASS** | `selftest_headless.json` |
| L03 | Même autotest avec **rendu OpenGL réel** (xvfb, Mesa llvmpipe) + capture d'écran | Linux CI | **15/15 PASS** (capture comprise) | `selftest_render.json`, `persona_live_screenshot.png` |
| L04 | Exécutable **Linux exporté** : autotest | Linux CI | **15/15 PASS** (capture non testée sans affichage) | `selftest_export_linux.json` |
| L05 | Exécutable **Windows exporté** `PERSONA_LIVE.exe` : autotest sur une machine Windows | windows-latest (AMD EPYC, 4 cœurs, 16 Go, sans GPU) | **15/15 PASS** en mode sans affichage ; import depuis `characters\persona_demo.glb` livré à côté de l'exe | `selftest_windows.json` |
| L06 | Rendu graphique sur GPU Windows réel, fluidité | IdeaPad Gaming 3 | **NON TESTÉ** | à faire par toi : `PERSONA_LIVE.console.exe -- --selftest --report=rapport.json` |
| P01 | Moteur Python : banque de références, planches, worker, contrat HTTP, hors ligne, backend sd.cpp simulé | Linux + **Windows** | **PASS** (20 tests Linux ; Windows : mêmes tests, faux sd-cli Unix ignoré) | job « PC package », étape *Python engine tests on Windows* |
| P02 | Atelier web : import de 2 références, génération, 6 vues affichées, comparaison superposée, export JSON, 0 erreur JavaScript | Chromium local, moteur **de test** | **PASS** (moteur de test clairement signalé) | `evidence/atelier_pc_moteur_test_apercu.jpg` |
| P03 | Image **réellement nouvelle** par le moteur : 3 références fictives, 6 vues visage et 4 vues corps, réseau coupé | Linux CPU (MASTER-01) | **PASS** | run `43300222986`, `master02/evidence/` |
| P04 | Image nouvelle avec **`sd-cli.exe` sous Windows** + PhotoMaker v1, 3 références fictives, 512 px, 5 étapes | windows-latest (4 cœurs, 16 Go, sans GPU) | **PASS** : 404,5 s, RAM pic 4 945 Mo, SHA-256 `ef6a7f68…1f10`, absente des références | artefact `persona-windows-generation` (run `43452105793`) |
| B01 | Règles de classement des angles (points synthétiques) : face, trois-quarts, profil, dos, cadrage | Linux | **PASS** | `tests/test_master04.py` |
| B02 | Classement **MediaPipe** sur les 4 vues corps fictives générées | Linux CI | **3/4** (la vue de face a été classée trois-quarts, confiance 0,76) | `classification_check.json` |
| B03 | Couverture et parties manquantes ; proportions relatives bornées, taille marquée « non mesurée » | Linux CI | **PASS** | `body_analysis.json` |
| D01 | Personnage démo Blender : 18 os, 4 animations, GLB (148 Ko) + FBX | Blender 4.2.3 LTS headless | **PASS** | artefact `persona-demo-character` |
| D02 | Dossier personnage → modèle ajusté aux proportions → **chargé dans PERSONA LIVE exporté** et piloté | Linux CI | **15/15 PASS** (LIVE-INTEGRATED) | `selftest_integrated.json`, `evidence/live_integrated_fictive_ci_apercu.jpg` |
| H01 | Détection matérielle et profils (8 Go + 4 Go → léger ; 16 + 8 → standard ; 32 + 12 → avancé) | Linux + Windows | **PASS** | tests ; dry-run de l'installeur Windows |
| H02 | Exclusion : calcul IA lourd refusé tant que PERSONA LIVE est ouvert | Linux + Windows | **PASS** | `test_generation_refused_while_live_runs` |
| I01 | Installeur Windows `-DryRun` (diagnostic matériel, rapport JSON) ; atelier démarré sous Windows (page + `/v1/hardware`) | windows-latest | **PASS** | job « PC package », run `43452105793` |
| I02 | Installation complète (Python, modèles, Blender, lanceurs) sur le PC cible | IdeaPad Gaming 3 | **NON TESTÉ** | à faire par toi |
| F01 | Fidélité à une vraie personne (visage, corps, 3D) | — | **NON ÉVALUÉE** : aucune photo réelle utilisée (règle de confidentialité) | — |
