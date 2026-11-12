# Sélection des modèles — 100 % local, 100 % gratuit

Date : 2026-11-12. Règles imposées par le propriétaire du projet :

1. **100 % local** : tout tourne sur ses appareils, sans service cloud et sans Internet une fois installé.
2. **100 % gratuit** : ni abonnement, ni paiement, ni crédits.

Conséquences immédiates :

* **Google Colab est exclu** (calcul dans le cloud). Le notebook `engine/colab/` est conservé pour l'historique, mais il ne fait plus partie de la mission.
* Les modèles sous licence **non commerciale** restent acceptables : ils sont gratuits pour un usage personnel. Chacun est signalé ci-dessous, au cas où l'usage deviendrait commercial.
* Le téléphone qui pilote un PC du **même Wi-Fi** reste 100 % local : le réseau domestique n'est pas un cloud et ne passe pas par Internet.

## 1. Ce que tes appareils peuvent faire (vérifié)

| Appareil | Puce / mémoire | Génération d'images sur l'appareil | Rôle retenu |
|---|---|---|---|
| POCO X8 Pro | MediaTek Dimensity 8500 (NPU 880), 8 ou 12 Go de RAM | Possible en théorie (MediaTek annonce la prise en charge des diffusion transformers), mais **aucune application ouverte n'exploite ce NPU** aujourd'hui. Local Dream (gratuit, open source) n'accélère que les NPU Snapdragon ; sur cette puce il tourne en CPU/GPU, en SD1.5 basse résolution et **sans conservation d'identité**. | Bibliothèque de références, revue, export, pilotage du moteur PC |
| Redmi Pad SE | Snapdragon 680, 4 à 8 Go de RAM | Trop faible : son NPU est sous le minimum (Hexagon V68) exigé par Local Dream | Consultation des résultats |
| **PC avec carte NVIDIA** | à préciser | **Seule option réaliste** pour des portraits photoréalistes fidèles, entièrement hors ligne | Moteur de génération |

**Conclusion honnête : aucun modèle actuel ne produit sur un téléphone des planches photoréalistes fidèles à une personne réelle.** Il faut un PC (ou un Mac Apple Silicon, voir §5). L'application Android et le worker sont déjà prêts pour ce fonctionnement : jeton d'accès, HTTP refusé hors des adresses privées, aucun tunnel.

## 2. Images avec la même identité — classement selon la carte graphique

| Mémoire vidéo (VRAM) NVIDIA | 1er choix | Licence (gratuite) | Pourquoi | Alternative |
|---|---|---|---|---|
| **8 Go** | **PhotoMaker V2 + SDXL (RealVisXL V4) + ControlNet OpenPose** — déjà intégré (`backends/photomaker_v2.py`) | Code Apache-2.0 ; poids Apache-2.0 / OpenRAIL++ ; InsightFace **non commercial** | Le plus léger ; plusieurs références ; pose guidée pour le corps | PuLID-SDXL : meilleure similarité de visage selon l'article PuLID (InsightFace, non commercial) |
| **12 Go** | **FLUX.2 [klein] 4B** | **Apache-2.0** | Récent, rapide, jusqu'à 4 images de référence ; environ 13 Go en BF16, moins en FP8 | Qwen-Image-Edit-2511 en GGUF Q4 (≈ 12–13 Go, avec délestage vers la RAM) |
| **16 Go** | **Qwen-Image-Edit-2511** (GGUF Q5/Q6 ou FP8) | **Apache-2.0** | Meilleur modèle d'édition ouvert permissif ; cohérence de personnage améliorée ; plusieurs images en entrée → idéal pour « même personne, autre angle » | FLUX.2 [klein] 4B |
| **24 Go et plus** | **Qwen-Image-2.1** (7B + encodeur Qwen3-VL) | Qwen Research License : **non commerciale**, gratuite | Jusqu'à 10 références ; conservation explicite de l'identité des personnes | Qwen-Image-Edit-2511 en BF16 ; FLUX.2 [dev] seulement à partir de 32 Go (non commercial) |

Pour la **planche corporelle**, aucun de ces modèles ne garantit la morphologie : on garde le guidage de pose (`pose.py`, cartes face/profil/¾/dos), et le dos reste marqué « estimé ».

## 3. Vidéo (phase I) — local et gratuit

| VRAM | Choix | Licence | Remarque |
|---|---|---|---|
| 8–12 Go | **Wan 2.2 TI2V-5B** en GGUF | Apache-2.0 | Clips courts, lent ; image → vidéo |
| 24 Go | Wan 2.2 TI2V-5B natif (720p) | Apache-2.0 | Configuration de référence de l'éditeur |
| — | HunyuanVideo 1.5 | Tencent Hunyuan Community License | **À écarter en France** : cette licence exclut, à ma connaissance, l'Union européenne (à vérifier sur le texte de la licence) |

Les versions Wan plus récentes que la 2.2 citées dans la presse (Wan 2.6) ne sont disponibles **que par API payante** : exclues.

## 4. Logiciels d'exécution (gratuits, hors ligne)

* **Worker PERSONA** (`engine/persona_engine/worker.py`) avec diffusers : déjà en place, même API pour l'app Android.
* **ComfyUI** (GPL-3.0) : prend en charge nativement tous les modèles du §2 et §3 ; utile pour comparer les modèles avant d'en brancher un dans le worker.
* Après installation, le moteur force `HF_HUB_OFFLINE=1` : **aucun accès réseau pendant la génération** (voir `backends/photomaker_v2.py`). Le téléchargement des poids est une étape séparée et volontaire (`PERSONA_ALLOW_DOWNLOAD=1`).

## 5. Mac Apple Silicon

Des portages MLX existent (par exemple `qwen-image-edit-2511-mlx`). C'est faisable avec 32 Go de mémoire unifiée ou plus, mais nettement plus lent qu'une carte NVIDIA, et non intégré au worker pour l'instant.

## 6. Évaluation : ce qui reste à mesurer sur ton PC

Je n'ai pas pu exécuter ces modèles : cette session n'a pas de GPU et n'a pas accès à HuggingFace. Le classement ci-dessus repose sur les licences, les tailles publiées et les comparaisons publiées par les auteurs. **Ce n'est pas un essai réel.** Le protocole de choix final, sur ta machine :

1. Mêmes références autorisées, même graine, mêmes 6 vues visage et 4 vues corps pour chacun des deux meilleurs candidats de ta tranche de VRAM.
2. Relever : temps par image, VRAM de pointe (déjà enregistrée dans chaque manifeste), échecs.
3. Revue humaine côte à côte avec `REVUE_HUMAINE.md`. **Le modèle retenu est celui qui ressemble le plus selon toi**, pas celui qui a le meilleur score automatique.
4. Couper le Wi-Fi et la connexion du PC, puis relancer une génération : elle doit réussir. C'est la preuve du « 100 % local ».

## Sources

* POCO X8 Pro : [mi.com](https://www.mi.com/br/product/poco-x8-pro/specs/), [ProPakistani](https://propakistani.pk/2026/03/18/poco-x8-pro-series-brings-flagship-chip-for-the-first-time-with-dynamic-rgb-lighting/) ; Dimensity 8500 : [MediaTek](https://www.mediatek.com/products/smartphones/mediatek-dimensity-8500)
* Redmi Pad SE : [GSMArena](https://m.gsmarena.com/xiaomi_pad_se-12466.php)
* Local Dream : [GitHub xororz/local-dream](https://github.com/xororz/local-dream)
* FLUX.2 [klein] : [Black Forest Labs](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence), [VentureBeat](https://venturebeat.com/technology/black-forest-labs-launches-open-source-flux-2-klein-to-generate-ai-images-in)
* Qwen-Image-Edit-2511 : [Hugging Face](https://huggingface.co/Qwen/Qwen-Image-Edit-2511), [The Decoder](https://the-decoder.com/qwen-updates-image-editing-model-with-better-character-consistency/), [ComfyUI docs](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511), [Unsloth GGUF](https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF)
* Qwen-Image-2.1 : [GitHub QwenLM](https://github.com/QwenLM/Qwen-Image-2.1), [analyse licence](https://braindetox.kr/en/posts/qwen_image_2_1_unified_generation_2026.html), [VRAM](https://codersera.com/blog/how-to-run-qwen-image-2-1-locally-2026/)
* PuLID : [arXiv 2404.16022](https://arxiv.org/abs/2404.16022) ; InfiniteYou : [arXiv 2503.16418](https://arxiv.org/abs/2503.16418)
* Vidéo : [Wan 2.2 en local](https://localaimaster.com/blog/wan-video-generation-guide), [comparatif des licences](https://fuser.studio/articles/best-open-source-video-models)
