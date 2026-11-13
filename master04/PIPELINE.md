# Chaîne PERSONA : PHOTO → BODY → 3D → LIVE

```
 photos autorisées ──► [1 PHOTO] atelier (worker + page locale)      ──► vues générées + manifestes (graines, paramètres, SHA-256)
        │               moteur sd.cpp + SDXL Lightning + PhotoMaker v1
        └──────────────► [2 BODY]  body.py (MediaPipe Pose, local)  ──► angles, cadrage, couverture, parties manquantes,
                                                                          proportions RELATIVES (bornées)
                                                   │
                         [3 3D]    character.py → Blender (headless) ──► model/<id>.glb + .fbx : squelette 18 os,
                                   make_character.py                      animations idle / walk / run / wave
                                                   │
                         persona_character.json  (dossier commun, empreintes seulement, pas de photo)
                                                   │
                         [4 LIVE]  PERSONA_LIVE.exe (Godot 4.3)       ──► F2 → dossier ou .glb → personnage jouable
```

## Interfaces d'échange (stables)

| Interface | Fichier / API | Produit par | Lu par |
|---|---|---|---|
| Contrat moteur photo | `POST /v1/jobs`, `PUT …/references/{sha}`, `GET …/outputs/{vue}`, `GET …/manifest` | worker | atelier web, app Android |
| Manifeste de planche | `manifest_face.json` / `manifest_body.json` | `boards.py` | atelier, dossier personnage |
| Analyse corporelle | `body_analysis.json` | `body.py` | `character.py` |
| Paramètres 3D | `proportions.json` : `height`, `shoulder_ratio`, `hip_ratio`, `leg_ratio`, `head_ratio` | `character.py` | `make_character.py` |
| Dossier personnage | `persona_character.json` (`schema: persona-character/1`) | `character.py` | PERSONA LIVE (`load_persona_folder`) |
| Modèle 3D | glTF binaire : `Skeleton3D` + `AnimationPlayer` (`idle`, `walk`, `run`) | Blender ou tout outil | PERSONA LIVE (import à l'exécution) |
| Matériel | `%APPDATA%\PERSONA\hardware_report.json` | `hardware.py` / installeur | worker, PERSONA LIVE |

Tout GLB respectant la dernière ligne (par exemple un personnage Mixamo exporté en glTF, si sa licence le permet) se charge dans LIVE. Les animations sont reconnues par leur nom (`idle`, `walk`, `run`) ; sans animation, un balancement procédural est appliqué et signalé.

## Ce que fait vraiment la phase 3

* **Fait :** un humanoïde riggé et animé, généré par script (CC0). Ses **proportions globales** (taille déclarée ou 1,75 m par défaut, épaules, hanches, jambes) sont ajustées aux estimations de la phase 2.
* **Ne fait pas :** reconstruire le visage, la morphologie fine, les cheveux, la peau ni les vêtements de la personne. Le niveau **LIVE-IDENTITY n'est pas atteint.**
* **Pistes suivantes, toutes gratuites :**
  1. photogrammétrie (COLMAP/Meshroom) depuis une séance multi-vues (`master03/PROTOCOLE_PHOTOS_3D.md`), puis retopologie et rig dans Blender ;
  2. MPFB (MakeHuman pour Blender, assets CC0) pour un corps humain réaliste paramétré par les proportions ;
  3. MetaHuman (`master03/`) si un PC compatible et les conditions Epic sont acceptés.
