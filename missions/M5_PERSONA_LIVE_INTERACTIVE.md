# PERSONA-005 — PERSONA LIVE : contrôle interactif photoréaliste (spécification exploratoire)

## Vision utilisateur
Retrouver la liberté d'interaction gestuelle d'un personnage type Clumsy Ninja (déplacement, manipulation et réactions), tout en préservant une apparence photoréaliste issue de références consenties. L'utilisateur refuse un **rendu 3D visuellement artificiel**; ne pas imposer un avatar 3D stylisé ni promettre une animation libre photoréaliste parfaite sur Android.

## Position dans la feuille de route
M1 bibliothèque, M2 Identity Master, M3 photo, M4 vidéo; M5 LIVE à prototyper seulement après qualification de M2/M3, et idéalement M4. Ne pas détourner M2-M4 de leur périmètre ni annoncer M5 comme développée.

## Hypothèses techniques à comparer par prototypes mesurés
A. 2D/2.5D photoréaliste: calques découpés, squelette 2D, déformations par maillage, points d'ancrage, IK, interpolation et réactions procédurales. Faible latence, mais rotations fortes et occlusions limitées.
B. Animation pilotée par pose / landmarks: suivi des gestes utilisateur et conditionnement d'un moteur image/vidéo local; fidélité potentiellement supérieure mais latence et ressources plus élevées, pas forcément temps réel.
C. Hybride: interaction immédiate en 2D/2.5D sur Android, calcul asynchrone de nouveaux angles et gestes par PC local puis intégration contrôlée dans une bibliothèque de mouvements. Indiquer clairement les transitions et limites.
D. Représentation volumétrique/3D cachée, uniquement si l'utilisateur l'autorise explicitement après démonstration comparative; ne jamais la présenter comme imposée. L'apparence finale resterait photoréaliste.

## Expériences initiales (sans modifier M1-M4)
- Écran prototype isolé: glisser le personnage dans le cadre, faire pivoter légèrement la tête, modifier posture du buste, déclencher retour à une pose de repos; tous les gestes doivent être réversibles et respecter les limites anatomiques.
- Interaction multitouch et glisser-déposer, gestion des zones de prise et des collisions simples, animation d'inertie et interpolation.
- Réactions procédurales (regard, respiration, équilibre) sans scripts fixes obligatoires.
- Utiliser uniquement images de test consenties ou synthétiques, sans publication des médias.
- Comparer latence, FPS, mémoire, batterie, échauffement et qualité visuelle sur téléphone et tablette cibles.
- Mesurer déformations de visage, mains, cheveux, occultations et changements d'angle; signaler les artefacts, ne pas inventer de réalisme.
- Mode dégradé et arrêt immédiat de l'animation en cas de pression thermique/mémoire.

## Critères de décision
L'utilisateur choisit après prototype visuel : interaction réactive mais liberté de pose limitée, ou liberté de mouvement accrue avec rendu plus lent sur PC. Un compromis peut combiner les deux.

## Contraintes de projet
Aucune fusion main, aucune installation ni changement des autres dépôts sans accord. Pas de cloud imposé, confidentialité et provenance. La mission reste une étude/prototype, pas un engagement de temps réel photoréaliste intégral.

## Décision utilisateur — 2026-11-08 : priorité déplacement libre dans une scène
**Priorité P0 :** cliquer/toucher une destination et y faire évoluer le personnage avec marche, orientation, arrêt, retour, évitement simple d'obstacles et transitions crédibles. Contrôle tactile direct des membres hors périmètre initial.

### Prototype P0 à réaliser en premier
1. Une scène fixe avec sol et zones marchables explicitement définies, repère de coordonnées, obstacles et points d'interaction (chaise, porte), sans inventer la profondeur depuis une image unique.
2. Toucher une destination -> calcul d'itinéraire 2D sur la scène (grille/navmesh simplifié), déplacement progressif, changement d'orientation, arrêt précis et annulation par nouveau toucher.
3. Personnage photoréaliste 2D/2.5D composé de vues/poses réellement disponibles, transitions entre cycles de marche et repos, gestion du changement d'échelle et des occultations selon la profondeur de scène. Signaler clairement les angles non couverts; ne pas créer de faux mouvement libre 360°.
4. Pour les vues ou mouvements manquants, préparer des demandes asynchrones au moteur local de génération (M3/M4) et un cache de variantes validées. Ne pas bloquer l'interface en attendant la génération.
5. Réactions contextuelles sobres : regard vers la destination, posture de repos, respiration; interaction avec chaise seulement si animation et alignement de scène qualifiés.
6. Profiling sur appareil : FPS, latence tactile, mémoire, stockage, batterie et dégradation thermique; pas de seuil « réussi » sans mesure sur matériel cible.

### Critères d'acceptation P0
- Départ, destination, trajet, interruption et nouvelle destination fonctionnent sans lancer manuellement une animation nommée.
- Le personnage reste dans les zones marchables et évite les obstacles définis.
- Les changements de direction ne provoquent pas de rupture visuelle majeure sur les angles effectivement pris en charge; angles non pris en charge explicitement limités.
- Une démonstration vidéo et des métriques vérifiables montrent la fluidité sur un appareil réel, ou le statut demeure non qualifié.
- Aucune dépendance à un avatar 3D rendu visible; aucune promesse de mouvement photoréaliste libre intégral en temps réel.

### Développement par étapes
P0 navigation tactile et locomotion; P1 interactions avec décor; P2 génération asynchrone de nouvelles poses et scènes; P3 éventuelle extension de liberté après mesures et validation utilisateur. Toute représentation géométrique cachée ou reconstruction 3D demande accord explicite avant implémentation.
