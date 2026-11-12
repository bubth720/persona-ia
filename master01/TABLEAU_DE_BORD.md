# MASTER 01 — tableau de bord final

Date : 2026-11-12 · Branche `ccr-8f135e00-hwmdvs` (partie de `docs/persona-roadmap-m2-m4@6146570`) · `main` intacte · PERSONA-3D intact.

## Verdict global

**V1 PHOTO : NO-GO pour l'instant.** Aucune image photoréaliste inédite n'a été générée : la session d'exécution n'avait ni GPU ni accès à HuggingFace. Tout ce qui précède et suit la génération est construit et testé ; la génération elle-même attend une exécution du notebook sur un GPU autorisé (Colab T4 ou PC).

**MASTER 01 : non complet.** Ne pas annoncer « terminé ».

## Phases

| Phase | Statut | Preuves | Prochaine action |
|---|---|---|---|
| A — Récupération M1–M3.1 | **PARTIEL** (repli) | `INVENTAIRE_RECUPERATION.md` : SHA de toutes les branches, M1–M3.1 introuvables sur GitHub, base minimale reconstruite | Fournir les bundles/ZIP Codex s'ils existent encore |
| B — Moteur GPU | **BLOQUÉ** (pas de GPU ni de HuggingFace ici) | `MOTEUR_GPU.md` ; lock Python 3.11 résolu ; cause de l'échec Colab identifiée (torch sans roue cp313) ; notebook prêt | Exécuter `engine/colab/PERSONA_MASTER01_GEN.ipynb` sur T4, cellules 1 à 5 |
| C — Banque de références | **PASS** (sur données synthétiques) | T01 (10/300/1000), T02, T03 en Python ; mêmes garanties en Kotlin (tests JVM + 300 imports sur émulateur) | Vérifier avec un vrai lot de photos sur téléphone |
| D — Planche faciale | **BLOQUÉ** (dépend de B) | Pipeline 6 vues + revue + régénération testés avec le backend de test non génératif | Génération réelle puis `REVUE_HUMAINE.md` |
| E — Planche corporelle | **BLOQUÉ** (dépend de B) | Cartes OpenPose face/profil/¾/dos ; dos marqué « estimé » | Idem ; si le corps n'est pas tenu, essayer un 2e pipeline |
| F — Assemblage et traçabilité | **PASS** (mécanisme) | Planches PNG + vues + manifeste SHA-256 ; rejet des substitutions (copie exacte et recadrage) ; planche de test classée `layout_test_only` | Revérifier sur de vraies générations |
| G — Android | **PARTIEL** | APK compilée et signée debug par la CI ; tests JVM 4/4 ; émulateurs API 29 et 35 : 3/3 tests (écrans, 300 imports, parcours complet contre le worker de test, prouvé par la trace du worker — run `43296162862`) | Parcours réel avec le moteur GPU ; appareils physiques **seulement avec votre accord** |
| H — PERSONA-3D | **PARTIEL** | `AUDIT_PERSONA3D.md` ; 16/16 tests PERSONA-3D ; module 3D isolé, rien intégré dans l'APK photo | Après la V1 photo |
| I — Vidéo / LIVE | **NON RÉALISÉ** (consigné) | `PHASE_I_VIDEO_LIVE.md` | Après Gate D/E |

## APK

| | |
|---|---|
| Exécution CI | run `43294928373` (commit `be65bdb`), job `apk` |
| Artefact | `persona-ia-master01-debug-apk` (Actions → run → Artifacts) |
| SHA-256 de `app-debug.apk` | `1e3080fd28af0a63985f7e69a588361575048e681aeda0564a45580cdd912f57` |
| Paquet / version | `ia.persona.app` 1.0.0-master01 (code 100), minSdk 29, targetSdk 35, permission INTERNET uniquement |
| Signature | clé **debug** Android standard : installable pour test, ne pas publier |

Chaque nouveau commit reconstruit l'APK ; son SHA-256 est dans `apk_sha256.txt` de l'artefact.

## Tests d'acceptation (§15)

| Test | Résultat |
|---|---|
| T01 import 10 / 300 / 1000 | PASS (Python : 1000 avec 19 doublons tous signalés ; Kotlin JVM : 1000 ; émulateur : 300) |
| T02 coupure puis reprise | PASS (orphelin récupéré, fichier partiel supprimé, ligne de journal tronquée ignorée, annotations conservées) — a révélé et corrigé un vrai bug Android |
| T03 refus sans autorisation / sans consentement de transfert | PASS |
| T04 poids chargés + image inédite | **NON EXÉCUTÉ** (pas de GPU) |
| T05 six vues faciales + revue humaine | **NON EXÉCUTÉ** |
| T06 quatre vues corps | **NON EXÉCUTÉ** |
| T07 rejeter puis régénérer une vue | PASS (les autres vues gardent leur empreinte ; Python + émulateur) |
| T08 deux planches + images + empreintes | PASS en mise en page de test (`verify_manifest`) |
| T09 arrêt du worker en plein job | PASS (vues terminées non refaites, reprise journalisée) ; annulation puis reprise PASS |
| T10 APK compilée, installée, parcours | PASS sur émulateur avec le worker **de test** ; parcours avec génération réelle non fait |
| T11 API 29 / 35 | PASS émulateurs ; appareils physiques non testés (pas d'accès, pas d'autorisation) ; mesures batterie/température non faites |
| T12 intégration 3D sans régression | non applicable (rien intégré) |
| T13 / T14 | non réalisés |

## Anomalies et limites

* Aucun moteur local sur téléphone : la génération dépend d'un PC ou d'un GPU distant, ce qui est affiché dans l'app.
* La liaison Android ↔ Colab n'est pas activée par défaut (pas de tunnel public). Pour le parcours Android complet, lancer le worker sur un PC du réseau local, ou ouvrir vous-même un tunnel privé authentifié.
* Les modèles InsightFace utilisés par PhotoMaker V2 sont réservés à un usage non commercial.
* Le classement des vues est manuel ; aucune reconnaissance automatique n'est revendiquée.
* Le stockage privé Android s'appuie sur le chiffrement de fichiers du système ; pas de chiffrement applicatif supplémentaire.

## Dépenses

0 € : session cloud et GitHub Actions (minutes gratuites). Coût GPU à venir : Colab gratuit possible, environ 30 à 60 min de T4 pour la démo.
