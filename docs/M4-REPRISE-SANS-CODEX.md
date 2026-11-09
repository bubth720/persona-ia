# PERSONA IA — Reprise autonome et plan M4

Date : 2026-11-09

## État vérifié
- Dépôt GitHub accessible : `bubth720/persona-ia`.
- Branches distantes visibles : `main` et `docs/persona-roadmap-m2-m4`.
- Le README de `main` ne contient que `# persona-ia`.
- Les branches locales Codex `codex/persona-m3-persona-photo`, `codex/persona-m21-reference-coverage` et `codex/persona-m31-android-local-generation` ne sont pas publiées dans ce dépôt.
- Aucun APK ou code Android M3.1 n'a été retrouvé sur les branches distantes. Il est impossible de modifier en sécurité le projet Android réel avant récupération de ses sources.

## Rapports fournis par l'utilisateur (non vérifiés sur GitHub)
- M3 : APK 0.3.0, compagnon PC, génération réelle non qualifiée.
- M2.1 : APK 0.3.1, couverture des références, reconnaissance automatique non qualifiée.
- M3.1 : 79 tests JVM, 19 tests Python, 7/8 tests Android ; aucun modèle téléchargé, POCO non testé.

## Ordre de reprise sans crédits Codex
1. Récupérer l'archive sources/bundle Git de la livraison M3.1 et la sauvegarder sans modification.
2. Vérifier les signatures, licences, scripts Gradle, fichiers de test et historique Git ; inventorier les différences M3/M3.1.
3. Importer dans une branche isolée `dev/persona-m4-recovery` sans toucher `main`, après contrôle des secrets et médias personnels.
4. Corriger le test Android défaillant et qualifier le diagnostic matériel (expiration à 15 secondes).
5. Ajouter un catalogue de modèles explicite : identifiant, URL officielle, version, licence, empreinte SHA-256, taille, RAM estimée, moteur compatible.
6. Implémenter un gestionnaire de téléchargement avec consentement, reprise, vérification SHA-256, estimation du stockage libre et suppression sécurisée des fichiers temporaires.
7. Intégrer un moteur de génération réel compatible Android ARM64, avec mesure des ressources et arrêt thermique. Ne pas annoncer de génération réussie sans image produite.
8. Préparer les interfaces photo/vidéo, sans simuler une génération réelle ; séparer les critères de qualification photo et vidéo.
9. Tests de non-régression sur bibliothèque et restauration ; aucun effacement de données.
10. Fournir APK, rapports et limites après compilation et qualification.

## Critères de validation
- PHOTO LOCAL : image effectivement générée hors ligne sur appareil Android compatible, avec logs, temps, RAM, température et consommation.
- VIDEO : vidéo réellement produite et exportée en MP4, distincte de la simple lecture d'images.
- Aucun merge sur `main`, aucune modification d'autres dépôts, aucun téléchargement de poids non identifiés.

## Blocage
Les sources Codex M3.1 ne sont pas accessibles depuis les branches GitHub actuellement visibles. La prochaine action utile est de récupérer la livraison « sources, bundle Git » depuis le lien Codex ou de publier sa branche distante.
