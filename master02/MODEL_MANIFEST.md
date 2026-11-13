# Manifeste des modèles — moteur local du téléphone

Aucun poids n'est dans le dépôt Git. Les URL pointent vers des **révisions immuables** (commit Hugging Face) ; l'application vérifie taille et SHA-256 (`ModelStore.kt`).

| Rôle | Dépôt | Révision | Fichier | Taille (octets) | SHA-256 | Licence | Redistribution |
|---|---|---|---|---|---|---|---|
| Modèle de base SDXL (photo, peu d'étapes) | [SG161222/RealVisXL_V4.0_Lightning](https://huggingface.co/SG161222/RealVisXL_V4.0_Lightning) | `39b41eff57c9d10c62119590901d6771863b426d` | `RealVisXL_V4.0_Lightning.safetensors` | 6 939 220 250 | `d6a48d3e2025448f011c27f4667145286910696d744c50c8ba3c2fb31dc98ea1` | CreativeML OpenRAIL++-M | permise avec la licence et ses restrictions d'usage ; l'app télécharge depuis la source plutôt que de redistribuer |
| Décodeur (VAE) | [madebyollin/sdxl-vae-fp16-fix](https://huggingface.co/madebyollin/sdxl-vae-fp16-fix) | `207b116dae70ace3637169f1ddd2434b91b3a8cd` | `sdxl_vae.safetensors` | 334 641 162 | `235745af8d86bf4a4c1b5b4f529868b37019a10f7c0b2e79ad0abca3a22bc6e1` | MIT | permise |
| Identité (PhotoMaker v1, format sd.cpp) | [bssrdf/PhotoMaker](https://huggingface.co/bssrdf/PhotoMaker) | `1d7e19f85ce03bc409b77a874998e5defd50346f` | `photomaker-v1.safetensors` | 933 571 072 | `21b907eed072fa9fdbe7418384b50f448856d497f702114f4a43bd7d7ac7ee19` | Apache-2.0 | permise |
| SDXL quantifié q8_0 (produit **sur l'appareil**) | — | sd.cpp `e239e4b` | `sdxl_realvisxl4_lightning_q8_0.gguf` | 4 180 813 792 (CI) | CI x86 : `46272d34a83e09ae4c497119afc673bbbf5bf33eaab46d7e8b9a1a68065e4bb2` | dérivé de RealVisXL | non redistribué |

Les tokenizers et encodeurs de texte CLIP-L / CLIP-G sont **inclus** dans le fichier RealVisXL (format SDXL « single file ») ; PhotoMaker v1 contient son propre encodeur d'image (CLIP ViT-L) et sa fusion d'identité. Aucun autre fichier n'est nécessaire : pas d'InsightFace, pas de ControlNet.

Moteur : [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) commit `e239e4b0fd3de49834cec67031a44796ca465abc` (30/10/2026), licence **MIT**, compilé par la CI en `libsdcli.so` (arm64 dotprod+fp16, arm64 générique, x86_64 pour émulateurs).

Espace disque sur le téléphone : ≈ 8,2 Go à télécharger, 4,2 Go pour la quantification, puis ≈ 5,4 Go conservés après suppression de l'original. Coût : 0 €.
