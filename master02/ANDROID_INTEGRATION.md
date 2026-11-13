# Intégration Android (MASTER-02 §5)

```
UI (Activities Kotlin)
 ├─ ReferencesActivity ── Library (bibliothèque locale, journal, SHA-256, doublons, EXIF)
 ├─ ModelActivity ─────── ModelStore (paquet de modèles : téléchargement figé + SHA-256 + reprise, import, quantification)
 ├─ LocalGenerateActivity ┐
 └─ HistoryActivity ──────┤
                          LocalJobs (orchestrateur : 1 tâche à la fois, état observable, historique)
                          GenerationService (service au premier plan, wakelock, notification)
                          LocalEngine (adaptateur moteur : arguments, étapes, erreurs typées, annulation, mesure RSS)
                          libsdcli.so (stable-diffusion.cpp, natif ARM64, PROCESSUS SÉPARÉ)
```

* **Pourquoi un processus séparé plutôt que JNI** : un manque de mémoire ou un plantage du moteur ne tue pas l'application ; l'annulation (`kill -9`) libère toute la mémoire native ; aucune fuite JNI possible. Le binaire est livré comme bibliothèque native (`lib/arm64-v8a/libsdcli.so`), extrait dans `nativeLibraryDir` (`useLegacyPackaging`), seul emplacement exécutable autorisé par Android 10+.
* **Choix du binaire** : variante `dotprod+fp16` si `/proc/cpuinfo` annonce `asimddp` et `asimdhp` (Dimensity 8500), sinon variante générique armv8-a.
* **Contrat** : `LocalEngine.Request` (références, prompt, négatif, taille, pas, CFG, graine, force d'identité, threads) → `Event(stage, step, total)` → `Result(fichier, durée, pic RSS, journal, arguments)` ou `EngineError(kind)` parmi ENGINE_MISSING, MODEL_MISSING, OUT_OF_MEMORY, CANCELLED, NO_OUTPUT, FAILED.
* **Étapes affichées** : uniquement celles réellement émises par le moteur (chargement, préparation identité/texte, inférence **pas n/N**, décodage, enregistrement). Aucun pourcentage artificiel.
* **Cycle de vie** : la génération continue écran éteint (service au premier plan de type `specialUse`, wakelock partiel). Si l'application ou le service est tué, l'inférence en cours est perdue (pas de reprise au milieu, impossible avec ce runtime) ; modèles, références et historique restent intacts, et il suffit de relancer.
* **Mémoire et chaleur** : avertissement avant le lancement si RAM totale < 7,5 Go ou RAM libre < 5,5 Go ; statut thermique Android lu à chaque étape ; arrêt propre au niveau SEVERE.
* **Réseau** : la permission INTERNET sert seulement au téléchargement initial du paquet de modèles (et au mode PC optionnel). `LocalEngine` et `libsdcli.so` n'ouvrent aucune connexion. Les références sont copiées dans un dossier temporaire privé, supprimé après chaque génération.
* **Historique** : `files/history/<id>/result.png` + `meta.json` (description, prompt, graine, taille, pas, modèle et empreinte, identifiants courts des références (jamais les photos), durée, RSS, température, avis de ressemblance).
