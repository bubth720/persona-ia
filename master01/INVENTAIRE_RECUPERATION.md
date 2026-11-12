# MASTER 01 — Phase A : inventaire de récupération

Date : 2026-11-12. Fait depuis une session cloud ayant accès en lecture à `bubth720/persona-ia` et `bubth720/PERSONA-3D` uniquement (pas de Google Drive, pas de pièces jointes de projet autres que le PDF MASTER 01).

## A1. Ce qui existe sur GitHub (vérifié)

### bubth720/persona-ia

| Réf | SHA | Date | Contenu |
|---|---|---|---|
| `main` | `0a935da03b351e9634c8efffd2978588d42a3e17` | 2026-11-07 | `README.md` seul (« # persona-ia ») |
| `docs/persona-roadmap-m2-m4` | `6146570b2352301d4981238a7da5775d22f6ec5a` | 2026-11-09 | 18 commits : missions M2–M5, fiches de statut M1/M2, `tools/validate_model_manifest.py` (+5 tests), `independent/m4_m6/persona_components/core.py` (+9 tests) |
| Tags / releases / PR | — | — | aucun |
| Workflows Actions | — | — | aucun avant MASTER 01 |
| Issue #1 | ouverte | 2026-11-11 | « P0 — GEN-01 » : même objectif que MASTER 01, interdit de déclarer PASS sans génération réelle |

Branches recherchées et **absentes** du distant : `codex/persona-m1-foundation`, `feat/m2-identity-foundation`, `codex/persona-m21-reference-coverage`, `codex/persona-m3-persona-photo`, `codex/persona-m31-android-local-generation`. La recherche de code GitHub ne trouve aucune occurrence non plus.

### bubth720/PERSONA-3D

| Réf | SHA | Contenu |
|---|---|---|
| `main` | `d651369ea29ddaa57e3c935826aad736dcd149cf` | `README.md` seul |
| `persona3d/android-build-setup` | `1a0ec537e74398554dcefd776c37c780501f91a5` | `.github/workflows/android.yml`, `PERSONA3D_GitHub_Android_ready.zip` (SHA-256 `c97300012788514fcdda4422ec18d687dbfc0e2d0be1b9249e54ceafb2940810`, 29 036 o), `extensions/photo_reference.gd` (SHA-256 `d7036cde…22ad`) |
| Actions | 13 exécutions, la dernière (n° 13, run `42682631038`) réussie | artefact `PERSONA3D-debug-build` (23,9 Mo, digest `sha256:55753f64…c7a8`, expire 2027-02-07) : APK Godot **PERSONA 3D**, pas une APK PERSONA IA |

## A1. Ce qui est rapporté mais introuvable

| Livraison | Preuve disponible | Statut |
|---|---|---|
| M1 (bundle `PERSONA_IA_M1.bundle`, commit `fc86f3d0…`, APK 0.1.0) | fiche `missions/M1_RECOVERY_STATUS.md` | **introuvable** : bundle jamais poussé |
| M2 (`feat/m2-identity-foundation`, commit `4bdbb951…`, prototype Python) | fiche `missions/M2_LOCAL_DEVELOPMENT_STATUS.md` | **introuvable** |
| M2.1 (APK 0.3.1), M3 (APK 0.3.0 + compagnon PC), M3.1 (79 tests JVM) | comptes rendus cités dans `docs/M4-REPRISE-SANS-CODEX.md` | **introuvables** : ni sources, ni APK, ni artefact CI |

Aucun bundle, ZIP, APK ou compagnon PC n'a été trouvé dans les fichiers disponibles de cette session. Aucun binaire inconnu n'a été exécuté.

## Contrôles effectués sur les candidats trouvés

* Le ZIP PERSONA-3D a été extrait dans un dossier isolé : 30 fichiers sources Godot/Python/docs, aucune image, aucun secret, aucun binaire. Ses 16 tests Python passent (`pytest -q tests`).
* Le workflow PERSONA-3D génère une clé de signature **debug** jetable dans le runner (mot de passe `android` public) : acceptable pour du debug, interdit pour une release.
* Les composants Python de `docs/persona-roadmap-m2-m4` : 5 + 9 tests passent (le second jeu exige `PYTHONPATH=independent/m4_m6`, la commande du README échoue sans).

## A2. Décision : **PASS PARTIEL** (repli)

M1 à M3.1 ne sont pas récupérables depuis les sources accessibles. Conformément au plan de secours (§14), le constat est figé ici et seule une **base V1 minimale** a été construite, sur la branche `ccr-8f135e00-hwmdvs` partie de `docs/persona-roadmap-m2-m4` (historique conservé, `main` non modifiée). Elle ne prétend pas restaurer M3/M3.1.

Pour récupérer quand même M1–M3.1 : déposer les bundles Git (`*.bundle`) ou les ZIP de sources Codex dans une session, puis :

```bash
git bundle verify PERSONA_IA_M1.bundle
git clone PERSONA_IA_M1.bundle m1 -b codex/persona-m1-foundation && cd m1 && git fsck --full
git push https://github.com/bubth720/persona-ia HEAD:refs/heads/recovery/m1   # jamais main, jamais --force
```

Ensuite, comparer M3.1 et la base MASTER 01 (le contrat moteur `master01/engine/persona_engine/contract.py` est fait pour qu'on puisse brancher un client Android existant dessus).
