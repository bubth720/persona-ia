# MASTER-03 — PERSONA 3D STUDIO (MetaHuman)

Date : 2026-11-13 · Branche `ccr-8f135e00-hwmdvs` · `main`, JARVIS et STUDIO IA non modifiés · PERSONA-3D non modifié.

## Statut : **NO-GO d'exécution aujourd'hui : préparation seulement (Q0 PARTIEL)**

Le propriétaire du projet **n'a pas de PC**. MetaHuman Creator, Mesh to MetaHuman et MetaHuman Animator ne fonctionnent que dans Unreal Engine sur un PC (Windows recommandé pour le flux complet). **Rien n'a été installé, reconstruit ni animé.** Conformément au §13 du cahier des charges, seul l'environnement est préparé, sans prétendre avoir fait les étapes Unreal.

| Étape | Statut | Preuve / raison |
|---|---|---|
| Q0 audit, matériel, licences | **PARTIEL** | ce dossier ; audit PERSONA-3D déjà fait (`master01/AUDIT_PERSONA3D.md`) |
| Q1 Unreal + MetaHuman, personnage fictif éditable | **BLOQUÉ** | aucun PC |
| Q2 maillage 3D issu de références, inspection 360° | **BLOQUÉ** | aucun PC ; jeu de photos multi-vues à constituer |
| Q3 ajustement MetaHuman + comparaison | **BLOQUÉ** | dépend de Q1/Q2 |
| Q4 personnage animé | **BLOQUÉ** | dépend de Q3 |
| Q5 exports | **BLOQUÉ** | dépend de Q4 |
| Q6 test sur PC utilisateur / viewer Android | **BLOQUÉ** | aucun PC ; aucun viewer Android promis |

Ce qui peut avancer **dès maintenant sur le téléphone** : constituer et classer le jeu de photos (bibliothèque PERSONA IA, rapport de couverture). Voir `PROTOCOLE_PHOTOS_3D.md`.

## Contenu

* `INSTALLATION.md` : matériel requis, installation pas à pas (à faire **avec ton accord** sur ton futur PC).
* `PIPELINE.md` : les deux voies comparées (A photogrammétrie → Mesh to MetaHuman ; B ajustement guidé), étapes réelles, ce qui est automatisable.
* `PROTOCOLE_PHOTOS_3D.md` : prises de vue, consentement, couverture, préparation sans GitHub.
* `CONFIDENTIALITE_LICENCES.md` : local ou cloud Epic, licences, contradiction avec la règle « 100 % local ».

## Point de conflit à trancher

La règle du projet est **100 % local, 100 % gratuit**. MetaHuman est gratuit (licence Unreal, sous 1 M$ de revenus), mais son usage exige un compte Epic, un téléchargement initial des données MetaHuman, et **certaines étapes peuvent faire appel aux services Epic** : la documentation n'est pas claire sur le traitement local ou distant de l'identité. Tant que ce point n'est pas vérifié sur la version installée, **MetaHuman ne peut pas être qualifié « 100 % hors ligne »**. La voie A jusqu'au maillage (COLMAP / Meshroom) reste, elle, entièrement locale.
