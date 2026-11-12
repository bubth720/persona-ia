# MASTER 01 — Phase I : vidéo et PERSONA LIVE

## Statut : **NON RÉALISÉ — consigné comme non réalisable avec les contraintes actuelles**

Prérequis du plan (§13) : Phases D/E qualifiées et socle Android validé. Aucune image photoréaliste inédite n'existe encore (Gate B bloquée faute de GPU dans cette session). Démarrer la vidéo maintenant violerait la règle « aucun travail avant Gate D/E ».

## I1. Vidéo photoréaliste — plan prêt à exécuter après Gate D/E

* Entrée : une vue **acceptée** d'une planche (manifeste + SHA-256).
* Candidats à comparer sur GPU ≥ 24 Go (une T4 15 Go est trop juste pour la plupart) : image-vers-vidéo ouvert (familles Wan 2.x I2V, HunyuanVideo-I2V, LTX-Video) — licences à vérifier modèle par modèle.
* Mesures : stabilité du visage image par image (même aide automatique que les planches, jamais un score de fidélité), mains, vêtements, arrière-plan, clignements.
* Les plans `VideoPlan` et `provenance_record` de `independent/m4_m6` servent déjà de manifeste.
* T13 : une vidéo n'est comptée que si elle est générée ; une animation d'image (panoramique, morphing) est étiquetée « démonstration d'animation ».

## I2. PERSONA LIVE — faisabilité

* 5 décors maximum, sélection d'avatar, déplacement libre.
* Le seul composant existant qui bouge librement est l'acteur procédural **stylisé** de PERSONA-3D (Godot) : il démontre le contrôleur de déplacement, pas le photoréalisme.
* Architecture : contrôleur d'interaction (entrées tactiles → trajectoire) séparé du moteur de rendu ; le rendu peut être 3D (Godot) ou vidéo générée par segments. Compromis : photoréalisme ↔ latence ↔ calcul distant.
* Livrable futur : prototype derrière un indicateur « expérimental », jamais présenté comme terminé sans déplacement libre démontré (T14).
