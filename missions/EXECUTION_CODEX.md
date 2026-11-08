# PERSONA IA — Procédure Codex et livraison

## État confirmé
- Dépôt GitHub distant: main contient uniquement l'initialisation; la livraison M1 est locale.
- Livraison M1 annoncée: commit `fc86f3d0187543b7d78b5b09ac2aa14cfffd4c74`, branche `codex/persona-m1-foundation`, archive `PERSONA_IA_M1.bundle`, APK 0.1.0 debug. Aucun résultat de test indépendant sur appareil n'est encore établi.
- Les missions 2, 3 et 4 sont définies dans ce dossier. Leurs prérequis sont obligatoires.
- Les PDF existent séparément et devront être ajoutés sous `missions/pdf/` après transfert binaire contrôlé. Ne pas considérer les PDF comme publiés tant que GitHub ne les montre pas.

## Ordre d'exécution
1. Préserver le dossier original M1 et vérifier les SHA-256 fournis.
2. Restaurer le bundle Git M1 sur une branche distincte sans remplacer `main`. Vérifier le commit et exécuter les tests.
3. Qualifier l'APK M1 sur appareil de test uniquement avec données fictives, sauvegarde et restauration.
4. Mission 2: `M2_IDENTITY_MASTER.md`. Faire valider les résultats.
5. Mission 3: `M3_PERSONA_PHOTO.md`. Nécessite un PC local compatible pour un vrai rendu photo; sinon résultat partiel.
6. Mission 4: `M4_PERSONA_VIDEO.md`. Nécessite PC local compatible et M3 validée.
7. Ne fusionner ni déployer sans approbation explicite.

## Commandes Codex prêtes à l'emploi
**Mission 2** : « Exécute uniquement PERSONA-002 depuis la branche docs/persona-roadmap-m2-m4, fichier missions/M2_IDENTITY_MASTER.md. Vérifie d'abord M1 et le bundle local. Produis branche isolée, code, tests, artefacts, rapport et preuves. Ne touche pas aux autres projets et ne fusionne rien. »

**Mission 3** : « Exécute uniquement PERSONA-003 depuis missions/M3_PERSONA_PHOTO.md. Vérifie M1 et M2, les licences, le matériel PC et les tests avant de commencer. Ne revendique pas de génération photoréaliste sans rendu réel. Aucun merge ni installation personnelle. »

**Mission 4** : « Exécute uniquement PERSONA-004 depuis missions/M4_PERSONA_VIDEO.md. Vérifie M1-M3 et la compatibilité PC. Fournis vrais MP4, métriques et limites, ou signale explicitement le statut partiel. Aucun merge ni installation personnelle. »

## Conditions de livraison obligatoires
- Branche distincte et SHA du commit final.
- Liste des fichiers modifiés, tests exécutés et résultats bruts.
- APK/artefacts vérifiables, SHA-256, instructions d'installation et de retour arrière.
- Rapport des limites et des tests non exécutés.
- Confirmation explicite qu'aucun autre dépôt ni `main` n'a été modifié.

## Principes permanents
Android en priorité pour pilotage et bibliothèque, calcul lourd local sur PC plus tard. Pas de cloud imposé. Priorité à la fidélité photoréaliste. Le modèle 3D reste hors périmètre. La fonctionnalité « détection des références douteuses » est exclue. Préserver les originaux et la vie privée.
