# PERSONA IA — Import d'une bibliothèque de références hétérogène
## Décision utilisateur (2026-11-08)
Le corpus de référence de l'avatar JARVIS est volumineux et **entièrement non trié**. Images paysage/portrait, grand angle, selfie, plans éloignés, décors variés, coiffures, maquillages, tenues, angles, éclairages et expressions variables. Ne jamais imposer un quota de vues ni demander de ranger les photos manuellement. L'application doit accepter un dossier unique et en dériver un classement progressif. Les originaux sont conservés sans modification.

## Exigences produit
1. Import récursif d'un dossier choisi par l'utilisateur via Storage Access Framework Android, avec permission persistante quand accordée; gestion du refus, fichiers illisibles, formats non supportés, interruption/reprise, doublons SHA et milliers d'images, sans OOM.
2. Décoder orientation EXIF, dimensions, ratio, taille, métadonnées disponibles, et produire miniatures non destructives. Un paysage n'est pas un critère de rejet.
3. Repérer automatiquement le cadrage, la netteté, les visages et la personne principale **uniquement si un modèle local approprié est disponible et qualifié**. Sinon afficher « non analysé » et permettre correction manuelle. Ne pas prétendre à une détection existante dans M2.
4. Séparer identité stable, apparences changeantes (cheveux, maquillage, tenue), conditions de prise de vue (grand-angle/perspective, lumière, fond) et qualité technique. Un changement d'apparence ne doit pas créer un nouvel individu.
5. Pour images avec plusieurs personnes, demander une confirmation explicite de la personne cible; ne pas fusionner automatiquement des identités. Cette validation de l'identité ne doit pas être présentée comme « détection des références douteuses », fonctionnalité exclue à la demande utilisateur.
6. Attribuer des rôles contextuels aux références : visage, profil, silhouette, coiffure, vêtements, expression, décor. Une image peut avoir plusieurs rôles; les portraits moins déformés sont privilégiés pour la géométrie du visage sans exclure les autres.
7. Sélectionner une planche maîtresse diverse, explicable, éditable; marquer angles manquants plutôt que les inventer. Ne pas imposer « 10 face + 10 profil ».
8. Préserver provenance et empreintes SHA; aucun upload cloud ni GitHub de photos personnelles, aucun déplacement/suppression d'originaux sans consentement.
9. Proposer import par lots, progression, pauses et erreurs récupérables; permettre d'ajouter de nouvelles photos sans refaire tout l'index.
10. Créer un jeu de test synthétique avec formats/cadrages/variantes mélangés et un jeu de validation consenti, sans diffusion des médias.

## État et impact
M2 0.2.0 livrée localement selon rapport Codex : cheveux/vêtements manuels ou balises, HEIC non supporté, reconnaissance sur portraits réels non qualifiée. Cette note est une **demande d'évolution**, pas une fonctionnalité implémentée. Codex M3 en cours : éviter d'interrompre ou de modifier sa branche; examiner ce document à la fin de M3 et planifier un lot distinct M2.1 si nécessaire. Prioriser compatibilité avec M3, pas de changement de schéma sans migration et tests.
