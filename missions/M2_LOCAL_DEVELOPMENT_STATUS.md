# M2 — développement local réel (2026-11-08)

Un prototype fonctionnel M2 a été développé directement à partir de la livraison M1, sur une branche Git **locale distincte** `feat/m2-identity-foundation`. Commit `4bdbb951a748fd64bf91c1ea157007e91426710e`.

## Fonctionnel dans le prototype Python local
- Lecture d'un manifeste JSON de références explicitement annotées par l'utilisateur.
- Filtrage des médias sans consentement.
- Sélection déterministe de références favorisant la diversité des angles, le cadrage et une coiffure demandée.
- Export d'un manifeste de sélection avec SHA-256 et provenance sans chemin absolu.
- Planche de contact PNG à partir de pixels des vraies images, sans génération de nouveaux angles.
- 5 tests unitaires réussis et contrôle statique M1 `scripts/check_repository.py` réussi (131 fichiers vérifiés).

## Limites
**Ceci n'est pas M2 terminée.** Le prototype est un outil compagnon Python hors Android : pas d'écran Compose, pas de liaison au coffre chiffré Room de M1, pas de reconnaissance faciale ni de génération photo/vidéo. Aucun build Android ni essai sur appareil physique dans cette livraison.

## Livraison
Bundle Git local `PERSONA_IA_M2_FOUNDATION.bundle` (historique M1+commit M2) et ZIP téléchargeables depuis la conversation. Les sources de ce commit **ne sont pas encore sur GitHub** : cette fiche n'est pas une publication du code.

Pour reprendre : `git clone PERSONA_IA_M2_FOUNDATION.bundle persona-m2 -b feat/m2-identity-foundation`. Exécuter `python -m unittest discover -s tests/identity_master -v` (Pillow requis). Ne pas fusionner sur `main` sans autorisation.
