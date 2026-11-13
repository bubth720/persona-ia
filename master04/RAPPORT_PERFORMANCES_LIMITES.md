# MASTER-04 — performances et limites

## Mesures réelles (machines CI, aucune ne correspond au PC cible)

| Mesure | Valeur | Machine |
|---|---|---|
| Génération photo, `sd-cli.exe` Windows, SDXL Lightning q8_0 + PhotoMaker v1, 512 px, 5 étapes | **404,5 s**, RAM pic **4 945 Mo** | windows-latest, AMD EPYC 4 cœurs, 16 Go, sans GPU |
| Génération photo Linux, 768 px, 6 étapes | 737–774 s par image, RAM pic 5 392 Mo | ubuntu, 4 vCPU (MASTER-01) |
| Quantification q8_0 sous Windows | 119 s | windows-latest |
| Téléchargement des 3 modèles (8,2 Go) | ≈ 9 min | réseau GitHub |
| PERSONA LIVE, rendu logiciel (Mesa llvmpipe, sans GPU), profil léger | ≈ 39 images/s affichées dans l'interface | ubuntu + xvfb |
| PERSONA LIVE : démarrage puis 15 contrôles d'autotest | ≈ 6 s (sans affichage) | Windows et Linux |
| Exécutable Windows | 84 Mo (`PERSONA_LIVE.exe`, paquet intégré), et 185 Ko pour le lanceur console | — |
| Personnage démo | GLB 148 Ko, FBX 473 Ko, 18 os, 4 animations | Blender 4.2.3 LTS |
| Analyse corporelle MediaPipe | 10 images en environ 20 s | ubuntu CPU |

## Estimation pour l'IdeaPad Gaming 3 (i5-10300H, 8 Go, GTX 1650 4 Go) — **non mesurée**

* **PERSONA LIVE** : la GTX 1650 dépasse de loin le rendu logiciel mesuré. Avec le profil léger (pas d'ombres, 75 % de résolution), une animation fluide est attendue ; **à confirmer avec l'autotest sur la machine.**
* **Génération photo** : 4 cœurs / 8 threads, comparable aux machines CI. Compte de l'ordre de **6 à 15 minutes par portrait** en 512–640 px.
* **Mémoire** : le pic mesuré (4,9–5,4 Go en q8_0) laisse très peu de marge sur 8 Go avec Windows. L'installeur choisit donc **q4_K** en profil léger. Cette variante est **non validée** : qualité et mémoire restent à mesurer.
* L'accélération GPU de la génération (CUDA ou Vulkan) **n'est pas livrée** : seul le binaire processeur AVX2 est compilé et testé.

## Limites (honnêtes)

1. **LIVE-IDENTITY non atteint.** Le modèle 3D est un mannequin générique dont seules les proportions globales sont ajustées. Il ne reproduit ni le visage ni le corps de la personne.
2. **Proportions** : estimations relatives à partir de photos 2D (±15 % au mieux). La taille vaut 1,75 m par défaut tant qu'elle n'est pas déclarée.
3. **Classement automatique des angles** : 3 vues sur 4 correctes sur l'essai fictif (une vue de face classée trois-quarts). Il reste **assisté** : chaque vue doit être validée par un humain.
4. **Fidélité photo** : PhotoMaker v1 donne une ressemblance approximative. Elle n'a jamais été évaluée sur une vraie personne, faute de photos réelles utilisées.
5. **PERSONA LIVE** : décors procéduraux simples (2 sur 5 emplacements), une seule interaction par objet, et des animations du mannequin rudimentaires. Un personnage importé doit fournir ses propres animations `idle` / `walk` / `run`, sinon un balancement procédural est appliqué.
6. **Exécutable non signé** : Windows SmartScreen affichera un avertissement.
7. **MetaHuman** (facultatif) : non intégré. Voir `master03/`.
