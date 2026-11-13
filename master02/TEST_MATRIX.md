# Matrice de qualification Q01–Q09 (13/11/2026)

Exécution de référence : GitHub Actions run `43407275278`, commit `0114cba`.

| Test | Statut | Preuve | Ce qui manque |
|---|---|---|---|
| **Q01 Build APK** | **PASS** | `app-debug.apk` SHA-256 `0b893433c3417045a93d55913251b3386a5805510f09faf8b5f13b4968776fa4`, `ia.persona.app` 2.0.0-master02, minSdk 29 / target 35, ABI `arm64-v8a` + `x86_64`, signature debug vérifiée (apksigner), journal Gradle dans l'artefact `persona-ia-master01-debug-apk`. Moteur natif : `lib/arm64-v8a/libsdcli.so` (dotprod+fp16), `libsdcli_generic.so` (armv8-a), `lib/x86_64/libsdcli.so` (émulateurs), allégés (`llvm-strip`) | signature de release (hors V1) |
| **Q02 Émulateur API 29/35** | **PASS** | 5/5 tests instrumentés sur chaque API, 0 ignoré : écrans (dont Génération locale, Modèle, Historique), 300 imports, parcours via le moteur de test, **le moteur natif embarqué s'exécute depuis l'APK** (`NativeEngineTest.embeddedEngineExecutes`), **modèle corrompu → erreur typée et aucune image** (`corruptModelGivesTypedError`) ; JVM : étapes, pas n/N, OOM, échec, sortie absente, **annulation effective**, téléchargement **coupé puis repris** (Range) + SHA-256, import corrompu refusé | inférence SDXL complète sur émulateur (4 Go de modèle, non tentée) |
| **Q03 Moteur réel** | **PASS (Linux CPU)** | run `43300222986` : 13 images nouvelles (3 références fictives + 6 vues visage + 4 vues corps), même moteur et même commit sd.cpp, modèle q8_0 SHA `46272d34…`, ≈ 12,5–13 min/image sur 4 vCPU, RSS de pointe 5,39 Go, seeds et prompts dans les manifestes — `evidence/` | **inférence dans l'APK sur ARM64 réel : non encore exécutée** |
| **Q04 Hors ligne** | **PASS (Linux)** / **à faire (POCO)** | génération CI dans un espace de noms **sans réseau** (`unshare -n`) ; le moteur Android n'ouvre aucune connexion (processus natif à fichiers locaux uniquement) | mode avion sur le POCO |
| **Q05 Autonomie** | **PASS (conception + émulateur)** | aucun Termux, Python ou serveur : `libsdcli.so` lancé par l'app elle-même | confirmation sur le POCO |
| **Q06 Résilience** | **PARTIEL** | annulation (JVM), modèle corrompu (émulateur), reprise de téléchargement, refus d'import corrompu, contrôles RAM/espace/chaleur avant et pendant | arrêt de l'app pendant l'inférence, stockage plein réel, mesuré sur le POCO |
| **Q07 POCO physique** | **NON FAIT** | pas d'accès à l'appareil ; aucune installation sur un téléphone personnel sans ton accord | à faire avec `DEVICE_TEST_GUIDE.md` |
| **Q08 Confidentialité** | **PASS** | CI : sujets fictifs uniquement ; aucune photo personnelle, aucune empreinte faciale ; références copiées en temporaire privé puis supprimées ; historique sans les originaux ; trafic réseau limité au téléchargement des 3 fichiers de modèle | — |
| **Q09 Qualité F01–F07** | **PARTIEL** | planches fictives Linux (identité plausible, défauts notés dans `ENGINE_DECISION.md`) | F01–F07 avec tes références sur le POCO, ton avis visuel |
