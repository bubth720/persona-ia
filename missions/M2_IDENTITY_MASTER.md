# Règles contractuelles PERSONA IA
- Source de vérité: mission 1 livrée localement sous commit fc86f3d0187543b7d78b5b09ac2aa14cfffd4c74, branche codex/persona-m1-foundation, actuellement absente du GitHub distant. Avant toute implémentation, demander/importer le bundle PERSONA_IA_M1.bundle et vérifier son SHA, ses tests, son schéma de données et ses contrats. Ne jamais prétendre que M1 est déjà publiée.
- Dépôt autorisé: bubth720/persona-ia seulement. Ne toucher à aucun autre projet. Pas de fusion main, suppression, publication de données personnelles, installation sur appareils, téléchargement de modèles lourds ou déploiement sans accord explicite.
- Branche de travail dédiée par mission; PR brouillon seulement si explicitement autorisée; livrer patch/bundle, code, APK de test si compilé, tests, preuves, SHA256 et limites.
- Android d'abord pour bibliothèque et pilotage; calcul photo/vidéo lourd sur PC local ultérieur; pas de cloud ni crédits obligatoires; sécurité, consentement, confidentialité, contrôle des ressources.
- Priorité: fidélité photoréaliste aux références, non avatar 3D. Ne pas inclure la fonctionnalité « détection des références douteuses ». Conserver toutefois l'intégrité technique des imports, l'évitement de mélanges accidentels de personnages et les validations manuelles.
- Ne jamais inventer les résultats de tests, les capacités matérielles, les modèles compatibles ou les garanties de ressemblance.

# PERSONA-002 — IDENTITY MASTER
## But
Transformer 10 à 300+ photos d'un personnage en bibliothèque d'identité structurée, traçable et réutilisable. Pas de promesse de génération photo inédite à cette étape.
## Prérequis
Reconstituer M1 à partir du bundle local; audit Room/SQLite, SAF, sauvegardes chiffrées, permissions et compatibilité Android API26+. Capturer baseline tests et APK. Si bundle absent, arrêter et demander livraison.
## Travaux
1. Concevoir entités versionnées Person, SourceMedia, FaceObservation, AppearanceVariant, ReferenceSet, IdentityProfile, IdentityRevision, ManualOverride, ImportJob et ExportManifest; migrations réversibles, contraintes FK, identifiants stables et suppression explicite.
2. Pipeline local d'import: copie atomique, hash SHA-256, EXIF et orientation, miniatures, formats HEIC/JPEG/PNG/WebP selon décodeurs Android; éviter OOM avec décodage échantillonné; pagination, WorkManager, reprise après interruption et annulation sans perte.
3. Indexer manuellement ou avec modèles locaux légers et optionnels les angles (face/profil/3-4), expressions, cheveux, vêtements, plans (visage/buste/corps), éclairage, netteté et résolution. Tout résultat automatique est modifiable; marquer « inconnu » plutôt qu'inventer.
4. Distinguer traits stables (forme visage, proportions observables) et variantes (coiffure, couleur cheveux, tenue, maquillage, lumière). Ne pas inférer des mesures exactes depuis une photo.
5. Construire un Identity Master multi-références: vue frontale + profil + 3/4 + expression neutre quand disponibles, sélection déterministe documentée, origine et justification de chaque référence. Ne pas « moyenner » les visages; garder provenance.
6. Générer une planche de contact à partir des VRAIES photos, avec étiquettes d'origine, angles et variantes; exporter PNG/PDF facultatif; toute vue synthétique future doit être clairement identifiée.
7. Sélecteur de références contextuel: portrait, corps entier, expression, coiffure, cadrage; score explicable, filtres, sélection manuelle verrouillable.
8. UX Android: fiche personnage, galerie virtualisée, filtres, annotations, sélection maître, historique de modifications, aperçu de planche, export manifeste JSON documenté.
9. Préparer API d'abstraction IdentityProvider/ReferenceSelector/GenerationRequestBuilder sans appeler un faux générateur. Données personnelles locales, chiffrement existant conservé, aucun upload.
## Tests d'acceptation
- Corpus de 10, 100, 300 et 1000 médias synthétiques/consentis; import, interruption/reprise, doublons, EXIF, formats non décodables, suppression/restore; zéro perte de fichiers.
- Changer une coiffure ne crée pas un nouvel Identity Master; le profil stable reste inchangé sauf validation utilisateur.
- Planche exportée: références réelles, provenance vérifiable, aucune invention de vue.
- Navigation téléphone/tablette, rotations, contraintes RAM/stockage, restauration chiffrée, tests JVM/instrumentation quand possible.
- Rapports chiffrés de temps, mémoire et stockage avec environnement exact; absence de mesure = « non qualifié ».
## Définition de terminé
APK installable de test + démonstration import -> classification -> validation -> planche -> export -> restauration; tests et documentation reproductibles. Pas de moteur de génération revendiqué.
