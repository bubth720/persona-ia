# Décision moteur (MASTER-02 §4)

## Chaîne retenue : stable-diffusion.cpp + RealVisXL V4.0 Lightning (q8_0) + VAE fp16-fix + PhotoMaker v1

**Conservée** parce qu'elle satisfait les critères et qu'elle est la seule chaîne à identité testée réellement :

| Critère | Mesure / preuve |
|---|---|
| Génération réelle | 3 références fictives + 6 vues visage + 4 vues corps générées le 12/11/2026, run CI `43300222986`, **réseau coupé** (`unshare -n`) — `evidence/ci_cpu_*` |
| Compatibilité PhotoMaker v1 ↔ base | **vérifiée en pratique** sur RealVisXL V4 Lightning (SDXL) : identité plausible et cohérente entre vues (voir limites) |
| Mémoire | pic RSS **5,39 Go** (q8_0, 768×768 / 576×1024, VAE en tuiles), 4 threads x86 |
| Temps | **≈ 12,5–13 min par image** sur 4 vCPU x86 (6 pas) ; sur le POCO : **à mesurer** (Q07) |
| Disque | 4,18 Go (q8_0) + 0,33 + 0,93 Go |
| ABI Android | binaire statique arm64-v8a (NDK, android-28) compilé ; exécution sur émulateur x86_64 via la même chaîne de build |
| Coût | 0 € ; licences MIT / Apache-2.0 / OpenRAIL++-M |
| Réseau à l'inférence | aucun |

## Alternatives écartées (pour le téléphone)

| Candidat | Raison |
|---|---|
| PhotoMaker V2 | exige des embeddings InsightFace calculés en Python (`face_detect.py`) : pas portable dans l'APK sans un second runtime ; modèles InsightFace non commerciaux |
| Qwen-Image-Edit-2511, FLUX.2 klein, Qwen-Image-2.1 | 8 à 20 Go de poids + encodeur de 5 à 9 Go : au-delà du budget mémoire du POCO (12 Go partagés) → **profil PC futur** |
| SD 1.5 + IP-Adapter FaceID | dépend aussi d'InsightFace ; qualité photo inférieure |
| Accélération GPU Mali (Vulkan) / NPU MediaTek | aucun support démontré pour cette chaîne (crashs Vulkan Mali rapportés) → **CPU uniquement**, rien n'est promis |
| Local Dream | NPU Snapdragon seulement ; pas d'identité |

## Paramètres conservateurs

Lightning : 6 pas (profil standard, 768 px) ou 5 pas (prudent, 640 px), CFG 1,8, `euler` + `sgm_uniform`, VAE en tuiles, génération séquentielle, threads limités (4 en prudent). PhotoMaker : force de style 10 / 20 / 35. Ce réglage agit réellement : c'est le paramètre `--pm-style-strength` du moteur.

## Limites observées (revue visuelle sur aperçus, personne fictive)

* Visage plausible et photoréaliste ; identité **à peu près** stable, mais la longueur de cheveux varie d'une vue à l'autre, et la vue « trois-quarts droit » est presque de face.
* Corps : silhouette et tenue cohérentes ; la vue « dos » est un trois-quarts arrière avec le visage tourné ; les mains sont souvent cachées dans les poches.
* Pas de guidage de pose (pas de ControlNet dans cette chaîne).
* Avec PhotoMaker v1, la ressemblance d'une **vraie** personne est moins bonne qu'avec les modèles PC. C'est à évaluer sur le POCO avec tes photos (F01–F07).
