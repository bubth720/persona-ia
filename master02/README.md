# MASTER-02 — PERSONA IA V1 (Android autonome, génération locale)

Branche `ccr-8f135e00-hwmdvs` · base MASTER01 `4a19d8a` · `main` intacte · aucun autre dépôt modifié.

| Document | Contenu |
|---|---|
| [`RESULTS.md`](RESULTS.md) | **Décision GO-V1 / CANDIDATE-V1 / NO-GO**, exigences satisfaites et non satisfaites |
| [`TEST_MATRIX.md`](TEST_MATRIX.md) | Q01–Q09 avec preuves |
| [`ENGINE_DECISION.md`](ENGINE_DECISION.md) | Choix du moteur, mesures, alternatives écartées |
| [`MODEL_MANIFEST.md`](MODEL_MANIFEST.md) | Modèles : révisions immuables, SHA-256, licences, tailles |
| [`ANDROID_INTEGRATION.md`](ANDROID_INTEGRATION.md) | Architecture : moteur natif en processus séparé, service, contrat |
| [`DEVICE_TEST_GUIDE.md`](DEVICE_TEST_GUIDE.md) | Guide en 5 étapes sans terminal + fiche de test POCO |
| `evidence/` | Aperçus des planches **fictives** générées par la CI (aucune donnée personnelle) |

Code : `master01/android/app/src/main/java/ia/persona/app/engine/` (`LocalEngine`, `ModelStore`, `LocalJobs`, `GenerationService`) et `ui/` (`ModelActivity`, `LocalGenerateActivity`, `HistoryActivity`). Build : `.github/workflows/master01.yml` (jobs `native` → `apk` → `emulator`).
