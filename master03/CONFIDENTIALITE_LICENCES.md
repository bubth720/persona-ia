# Confidentialité et licences — MetaHuman

| Élément | Licence / coût | Réseau |
|---|---|---|
| Unreal Engine | gratuit (redevance seulement au-delà de 1 M$ de revenus) | compte Epic, téléchargement initial |
| MetaHuman (Creator, Mesh to MetaHuman, Animator) | inclus dans la licence Unreal Engine, gratuit sous 1 M$ de revenus (metahuman.com/license) | données Core téléchargées ; **certaines étapes (identité, conform, rig) peuvent utiliser des services Epic : à vérifier en coupant le réseau sur la version installée** |
| COLMAP | BSD | local |
| Meshroom / AliceVision | MPL-2.0 | local |
| Blender | GPL | local |

* **Avant toute étape qui contacterait Epic** : expliquer quelles données partent (maillage ? textures ? photos ?), recueillir un consentement spécifique, journaliser. Ne jamais envoyer les photos brutes si l'étape n'en a pas besoin.
* **Aucune publication automatique** de photos, maillages ou textures, ni sur GitHub ni ailleurs.
* **Entraînement IA** : l'ancien contrat MetaHuman l'interdisait. Epic a annoncé fin octobre 2026 une révision permettant aux licenciés de le choisir. Relire le texte en vigueur avant toute utilisation des rendus MetaHuman avec un modèle d'IA (par exemple pour nourrir PERSONA IA).
* **Règle du projet** : tant qu'une étape exige les services Epic, la voie MetaHuman est « gratuite » mais **pas 100 % hors ligne**. La photogrammétrie locale (voie A, étapes 1 à 3) l'est.

Sources : [MetaHuman — exigences matérielles (Epic)](https://dev.epicgames.com/documentation/metahuman/metahuman-hardware-requirements-in-unreal-engine), [From Mesh (Epic)](https://dev.epicgames.com/documentation/en-us/metahuman/from-mesh), [Guide de migration MetaHuman Creator (Epic)](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-migration-guide-in-unreal-engine), [Licence MetaHuman](https://www.metahuman.com/license), [Révision EULA et IA (Epic)](https://unrealengine.com/ue-devs-can-now-choose-to-train-ai-models-on-their-projects), [Fermeture de l'app web (guide tiers)](https://www.strayspark.studio/blog/metahuman-2026-web-app-shutdown-migration-guide).
