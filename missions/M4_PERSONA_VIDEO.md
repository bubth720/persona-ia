# Règles contractuelles PERSONA IA
- Source de vérité: mission 1 livrée localement sous commit fc86f3d0187543b7d78b5b09ac2aa14cfffd4c74, branche codex/persona-m1-foundation, actuellement absente du GitHub distant. Avant toute implémentation, demander/importer le bundle PERSONA_IA_M1.bundle et vérifier son SHA, ses tests, son schéma de données et ses contrats. Ne jamais prétendre que M1 est déjà publiée.
- Dépôt autorisé: bubth720/persona-ia seulement. Ne toucher à aucun autre projet. Pas de fusion main, suppression, publication de données personnelles, installation sur appareils, téléchargement de modèles lourds ou déploiement sans accord explicite.
- Branche de travail dédiée par mission; PR brouillon seulement si explicitement autorisée; livrer patch/bundle, code, APK de test si compilé, tests, preuves, SHA256 et limites.
- Android d'abord pour bibliothèque et pilotage; calcul photo/vidéo lourd sur PC local ultérieur; pas de cloud ni crédits obligatoires; sécurité, consentement, confidentialité, contrôle des ressources.
- Priorité: fidélité photoréaliste aux références, non avatar 3D. Ne pas inclure la fonctionnalité « détection des références douteuses ». Conserver toutefois l'intégrité technique des imports, l'évitement de mélanges accidentels de personnages et les validations manuelles.
- Ne jamais inventer les résultats de tests, les capacités matérielles, les modèles compatibles ou les garanties de ressemblance.

# PERSONA-004 — PERSONA VIDEO
## But
Créer de courtes vidéos photoréalistes à partir d'une image validée de M3, en préservant autant que possible l'identité. Calcul sur PC local compatible; Android prépare, suit et consulte.
## Prérequis
M1-M3 qualifiées; modèle vidéo choisi avec licence compatible et mesures réelles GPU/VRAM, stockage, latence; ne pas annoncer de rendu vidéo si le modèle ne tourne pas effectivement.
## Travaux
1. Évaluer moteurs image-vers-vidéo locaux disponibles: limites durée/résolution/fps, VRAM, poids, codecs, licence, compatibilité hardware; sélectionner selon benchmark.
2. UI storyboard: personnage, image de départ validée, prompt de mouvement, caméra, durée, format, seed, prévisualisation et export; gérer contraintes et refus explicites de paramètres non supportés.
3. API worker VideoJob versionnée, file d'attente, progression réelle, journaux sans données sensibles, reprise/annulation, timeout, nettoyage des caches, quotas disque et GPU.
4. Générer courts clips tests, conserver identité, coiffure et costume entre images dans les limites du moteur; évaluer dérive visuelle, clignotement, anatomie et cohérence temporelle; proposer régénération ciblée quand possible.
5. Encoder MP4/H.264 ou codec compatible appareil, piste audio absente clairement signalée, métadonnées et provenance; galerie Android et export via SAF.
6. Préserver M1-M3, tests de migration/restauration, aucun impact autres dépôts; télémétrie opt-in seulement, aucune communication cloud.
7. Protections: authentification LAN, chiffrement transfert, gestion des médias privés, autorisation d'usage de ressemblances réelles, restrictions de créations intimes non consenties et usurpation trompeuse.
## Tests
- Au moins 3 clips image-vers-vidéo réels sur PC qualifié, scènes et mouvements différents, avec preuves reproductibles.
- Mesurer VRAM, durée, fps, résolution, stockage, taux d'échec et limites; vérifier interruptions réseau, espace plein, annulation, corruption MP4, conservation des projets et sauvegardes.
- Revue manuelle de cohérence d'identité avec références; aucun score de fidélité non étayé.
## Définition de terminé
Génération vidéo locale réellement exécutée, MP4 lisible Android, provenance, paramètres et reprise. Si PC absent, livraison partielle documentée, pas de déclaration de mission terminée.
