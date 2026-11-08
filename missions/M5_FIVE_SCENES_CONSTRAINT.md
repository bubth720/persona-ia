# PERSONA LIVE — limite de cinq décors

## Décision utilisateur
Cinq environnements interactifs maximum dans la première version. Privilégier qualité photoréaliste, continuité et interactions crédibles plutôt qu'un monde ouvert.

## Conception
- Registre de 1 à 5 scènes versionnées (SceneId, image/background, variantes lumière, zones marchables, obstacles, profondeur approximative, points d'interaction, points d'entrée/sortie).
- Chaque scène définit son propre repère, les limites de déplacement et les animations/poses disponibles; ne pas supposer qu'une image fixe fournit automatiquement un modèle 3D navigable.
- Préparer les transitions entre scènes, sans imposer une caméra libre à 360° ni inventer les faces cachées.
- Interactions graduelles : déplacement, arrêt, orientation, approche d'un meuble, puis s'asseoir si la pose a été réellement créée et validée.
- Les cinq décors sont un **plafond**, non une obligation de tous les réaliser avant le premier prototype; commencer avec un seul décor fonctionnel.
- Favoriser assets photoréalistes contrôlés et caches de vues; la génération vidéo/pose asynchrone M3/M4 enrichit ensuite les interactions.
- Ne pas ajouter de représentation 3D visible artificielle; toute reconstruction cachée doit être discutée avant implémentation.

## Tests
Vérifier zones marchables, obstacles, clics hors scène, changements de scène, déformations visuelles, performances Android et compatibilité portrait/paysage. Aucun « déplacement libre total » revendiqué si angles et poses sont limités.

## Statut
Spécification seulement; aucune implémentation. À traiter lors de M5 après M2.1 et qualification M3/M4.
