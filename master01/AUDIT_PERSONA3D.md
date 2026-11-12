# MASTER 01 — Phase H : audit de PERSONA-3D

Source auditée : `bubth720/PERSONA-3D@1a0ec537` (branche `persona3d/android-build-setup`). **Le dépôt PERSONA-3D n'a pas été modifié.**

## Inventaire

| Composant | Nature | État vérifié |
|---|---|---|
| Projet Godot 4.3 (GL Compatibility) dans `PERSONA3D_GitHub_Android_ready.zip` | viewer 3D, acteur procédural stylisé, import GLB | APK debug produite par la CI (run 13) ; **aucun test sur appareil** |
| `scripts/core/reference_library.gd` | catalogue de photos, empreintes, libellés de vue, vues manquantes | logique équivalente à la banque MASTER 01 |
| `scripts/core/character_manifest.gd` | manifeste JSON de personnage (schema_version 1) | réutilisable comme format d'échange |
| `extensions/photo_reference.gd` | visionneuse d'une photo (« not a 3D reconstruction ») | honnête, mais redondante avec l'écran Références Android |
| `tools/audit_avatar_package.py`, `prepare_avatar_blender.py` | audit / conversion GLB via Blender | pipeline auteur PC, hors V1 |
| `.github/workflows/android.yml` | export Godot → APK signée debug | modèle utile de CI Android |
| Tests Python (16) | contrats statiques | **16/16 passent** dans cette session |
| Licence | aucun fichier LICENSE | à ajouter par le propriétaire avant toute réutilisation publique |

Aucune reconstruction photo → 3D, aucun poids, aucune image privée dans le dépôt.

## Coût / bénéfice

| Élément | Classement | Raison |
|---|---|---|
| Format `character_manifest` | **réutilisable par adaptateur** | relier un profil PERSONA IA (empreintes des références, planches validées) à un futur GLB |
| Libellés de vues de `reference_library.gd` | **adaptable** | mêmes catégories que `contract.REFERENCE_VIEWS` ; une table de correspondance suffit |
| Viewer Godot + acteur procédural | **module facultatif, expérimental** | utile pour PERSONA LIVE (déplacement libre), pas pour le rendu photo |
| Workflow Android Godot | **référence** | la CI MASTER 01 suit la même logique (apksigner, aapt, SHA-256) |
| `photo_reference.gd` | **inutile** pour la V1 | doublon de l'écran Références |
| Intégration du moteur Godot dans l'APK PERSONA IA | **incompatible à ce stade** | ~24 Mo d'APK, pile de rendu différente, aucune valeur pour la génération photo |

## Décision et interface de module facultatif

* PERSONA IA est le point d'entrée unique. PERSONA-3D reste une **application séparée** (paquet `org.persona3d.prototype`) jusqu'à ce que PERSONA LIVE soit qualifié.
* Contrat de données commun proposé : export depuis PERSONA IA d'un `character_manifest` v1 dont `source_images` contient **les empreintes SHA-256** (jamais les photos) et des chemins de planches choisis par l'utilisateur. Migration réversible : c'est un fichier en plus, rien n'est déplacé.
* Aucune fusion d'historique Git. Une éventuelle intégration se fera sur une branche `integration/persona3d-module` avec tests de non-régression des tests photo (`master01/engine/tests`, tests JVM et émulateur).

**Gate H : PARTIEL** — audit fait, contrat défini, module 3D volontairement désactivé ; aucune régression possible de la V1 photo puisque rien n'est intégré dans son APK.
