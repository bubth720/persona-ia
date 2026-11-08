# Règles contractuelles PERSONA IA
- Source de vérité: mission 1 livrée localement sous commit fc86f3d0187543b7d78b5b09ac2aa14cfffd4c74, branche codex/persona-m1-foundation, actuellement absente du GitHub distant. Avant toute implémentation, demander/importer le bundle PERSONA_IA_M1.bundle et vérifier son SHA, ses tests, son schéma de données et ses contrats. Ne jamais prétendre que M1 est déjà publiée.
- Dépôt autorisé: bubth720/persona-ia seulement. Ne toucher à aucun autre projet. Pas de fusion main, suppression, publication de données personnelles, installation sur appareils, téléchargement de modèles lourds ou déploiement sans accord explicite.
- Branche de travail dédiée par mission; PR brouillon seulement si explicitement autorisée; livrer patch/bundle, code, APK de test si compilé, tests, preuves, SHA256 et limites.
- Android d'abord pour bibliothèque et pilotage; calcul photo/vidéo lourd sur PC local ultérieur; pas de cloud ni crédits obligatoires; sécurité, consentement, confidentialité, contrôle des ressources.
- Priorité: fidélité photoréaliste aux références, non avatar 3D. Ne pas inclure la fonctionnalité « détection des références douteuses ». Conserver toutefois l'intégrité technique des imports, l'évitement de mélanges accidentels de personnages et les validations manuelles.
- Ne jamais inventer les résultats de tests, les capacités matérielles, les modèles compatibles ou les garanties de ressemblance.

# PERSONA-003 — PERSONA PHOTO
## But
Créer de nouvelles images photoréalistes fidèles aux références, via un moteur LOCAL PC réellement disponible et compatible; Android reste le client de pilotage. Aucune garantie de ressemblance parfaite.
## Prérequis
M1 et M2 validées; manifests Identity Master versionnés; matériel PC local décrit (OS, GPU/VRAM, RAM, stockage), licences et poids modèles acceptés. Si aucun PC compatible, livrer uniquement les contrats, la préparation des jobs et un mode de démonstration clairement étiqueté NON GÉNÉRATIF; ne pas déclarer la mission terminée.
## Architecture
Android: écran « Nouvelle photo », personnage, profil, variante, pose, cadrage, lumière, décor, graine, nombre de variantes, aperçu, statut, résultats. PC worker séparé avec API LAN authentifiée et chiffrée, liste blanche d'appareils, pairing explicite, gestion de jobs asynchrones, idempotence, pause/annulation, stockage local et expiration des transferts. Définir version de protocole, schémas JSON, migrations et codes d'erreur.
## Travaux
1. Évaluer plusieurs pipelines open-source image à références multiples selon licences, poids, VRAM, fidélité, reproductibilité, capacité offline; consigner benchmark et choix. Aucune dépendance cloud.
2. Génération guidée par Identity Master + références contextuelles; ne jamais transférer toutes les 300 images sans justification; préserver provenance, consentement et variantes.
3. Paramètres: prompt positif/négatif, seed, ratio, résolution, style photoréaliste, intensité de référence, variante d'apparence, caméra, éclairage et contrôles de pose seulement si réellement supportés.
4. Générer petites prévisualisations avant rendu haute résolution, avec devis de mémoire/temps et limites matérielles. Éviter surchauffe et saturation disque.
5. Contrôle de cohérence: comparateur côte-à-côte avec références, détection d'écarts possible seulement si qualifiée, annotations utilisateur, historique des rejets, nouvelles itérations; ne pas afficher de score de « fidélité » sans validation méthodologique.
6. Sauvegarder prompts, modèles et versions, hashes, paramètres, références exactes, seed, résultat, date, licence et métadonnées; pouvoir reproduire si matériel/moteur le permettent.
7. Export PNG/JPEG et manifeste, galerie de versions, restauration après coupure réseau, téléchargement intégral ou miniature suivant choix.
8. Sécurité: aucun serveur exposé sur internet, pas de journal de photos en clair, protections contre traversal, limites taille requêtes, auth, TLS local ou canal équivalent justifié, suppression des caches.
## Tests
- Générer réellement au moins 3 scènes distinctes sur matériel cible déclaré, avec personnage consenti et plusieurs coiffures; rapport qualitatif et limites sans inventer une fidélité parfaite.
- Contrôler job annulé, PC éteint, coupure LAN, stockage plein, modèle manquant, mauvais token, relecture de job, compatibilité versions, conservation du profil M2.
- Benchmarks résolution/VRAM/durée et conformité licences; tests Android et worker.
## Définition de terminé
Un vrai rendu photo inédit, produit localement par moteur documenté, visible sur Android, avec métadonnées et reprise, tests et preuves. Sans machine compatible: statut « infrastructure prête, génération non qualifiée ».
