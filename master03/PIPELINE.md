# Pipeline de reconstruction — deux voies à comparer

```
Bibliothèque PERSONA IA → sélection des vues + consentement → prétraitement local
  → (A) reconstruction multi-vues → maillage texturé → Mesh to MetaHuman
  → (B) MetaHuman de base ajusté à la main d'après les références
→ textures / cheveux / corps → rig et animation → rendus 360° + exports → galerie PERSONA IA
```

## Voie A : photogrammétrie puis Mesh to MetaHuman (la plus fidèle si les photos le permettent)

| Étape | Outil (gratuit) | Local ? | Automatisable |
|---|---|---|---|
| 1. 40 à 80 photos nettes autour de la tête, lumière diffuse, expression neutre, yeux ouverts | téléphone + `PROTOCOLE_PHOTOS_3D.md` | oui | non |
| 2. Reconstruction multi-vues → maillage + texture | **COLMAP** (BSD) puis maillage, ou **Meshroom / AliceVision** (MPL-2.0) | oui, GPU NVIDIA conseillé | oui (lignes de commande) |
| 3. Nettoyage : garder tête + cou, fermer les trous, réduire, export **OBJ ou FBX** avec texture albédo, yeux ouverts, sclère visible | **Blender** (GPL) | oui | partiellement (script Python Blender) |
| 4. Import dans Unreal → **MetaHuman Identity** → *From Mesh* → choisir le cadrage neutre → **Identity Solve** | Unreal + plugin MetaHuman | à vérifier (voir confidentialité) | non : clics guidés |
| 5. **Conform** / création du MetaHuman depuis l'identité, puis ajustements dans MetaHuman Creator (peau, yeux, cheveux, corps) | MetaHuman Creator (éditeur) | à vérifier | non |
| 6. Assemblage, rig, export | Unreal | à vérifier | partiel |

Exigences Epic pour l'entrée de Mesh to MetaHuman : FBX ou OBJ, topologie libre, texture d'albédo de peau (ou matériaux de sclère séparés), **yeux ouverts avec le blanc des yeux visible**.

Limite honnête : avec des **photos ordinaires** (peu de vues, éclairages différents), la photogrammétrie échoue ou produit un maillage bruité. Il faut une **séance de prise de vue dédiée**.

## Voie B : ajustement guidé d'un MetaHuman de base

Partir d'un preset proche, puis ajuster forme du visage, yeux, nez, bouche, mâchoire, peau et coiffure en comparant côte à côte avec les références (face, profil, trois-quarts). Possible avec **une seule photo**, mais le résultat est une **approximation artistique** : la forme du crâne, des oreilles et du corps n'est pas déduite. À signaler comme telle.

## Choix

À faire sur PC après Q1 : essayer A sur un jeu de photos **fictif ou autorisé** et B sur les mêmes références, puis retenir la voie qui ressemble le plus selon la revue humaine (face, profil, trois-quarts, neutre et sourire, éclairage comparable). Aucun bouton « photo → clone 3D parfait » n'existe.

## Animation (Q4)

Rig MetaHuman natif : rotation de la tête, clignement, sourire et parole (MetaHuman Animator depuis une vidéo de téléphone, ou animation manuelle), plus une animation corporelle simple. Scène de démonstration : caméra orbitale, rotation 360°, lumière réglable. Le déplacement libre et les 5 décors sont reportés.

## Android

**Aucun MetaHuman complet en temps réel sur le POCO n'est promis.** Piste ultérieure : rendus vidéo 360° consultables dans la galerie PERSONA IA, puis, après mesure, un maillage allégé exporté vers le viewer Godot de PERSONA-3D, si la licence l'autorise.
