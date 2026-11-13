# Installation (futur PC, uniquement avec ton accord explicite)

## Matrice matériel

| | Minimum réaliste | Recommandé par Epic (MetaHuman Creator / Animator) |
|---|---|---|
| Système | Windows 10/11 64 bits (seule plateforme au flux complet Identity/Performance) | idem |
| Processeur | 8 cœurs | 16 cœurs physiques performants |
| RAM | 32 Go | 32 Go et plus |
| Carte graphique | 8 Go de VRAM, compatible DirectX 12 | NVIDIA RTX 3070 / AMD RX 6800 XT, 8 Go et plus |
| Disque | SSD, 200 Go libres (moteur ≈ 60–100 Go + données MetaHuman + projets) | NVMe 1 To |

Un PC choisi pour PERSONA (§ `master01/SELECTION_MODELES_LOCAUX.md`) avec une **RTX 16 Go** couvre à la fois la génération photo locale et MetaHuman.

## Contrôle avant tout téléchargement (5 min)

1. `dxdiag` → version Windows, carte graphique, VRAM, pilote.
2. Gestionnaire des tâches → RAM, cœurs.
3. Explorateur → espace libre sur le SSD.
Consigner ces valeurs dans `master03/evidence/materiel.md` (sans données personnelles).

## Étapes

1. Créer un compte Epic Games (gratuit), installer **Epic Games Launcher**.
2. Installer **Unreal Engine** : version stable courante (5.8 à la date de rédaction ; MetaHuman Creator in-editor requiert 5.7 ou plus).
3. Créer un projet vierge, **Edit → Plugins** : activer **MetaHuman Creator** (et **MetaHuman Animator** seulement si l'animation faciale par vidéo est utilisée ; **Depth Processing** seulement pour les captures avec profondeur). Redémarrer.
4. Laisser le plugin télécharger les **MetaHuman Creator Core Data** (téléchargement initial).
5. Test Q1 : créer un MetaHuman **fictif** depuis un preset, le modifier, l'assembler, l'enregistrer, rouvrir le projet. Captures + version + temps + RAM/VRAM → `evidence/`.
6. Avant toute photo réelle : lire `CONFIDENTIALITE_LICENCES.md` et noter si une étape a demandé une connexion (le vérifier en coupant le réseau).

Ancien MetaHuman Creator dans le navigateur : fermé le 5 novembre 2026 selon un guide tiers. On utilise uniquement le plugin dans l'éditeur.
