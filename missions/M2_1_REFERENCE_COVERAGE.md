# PERSONA-002.1 — Audit de couverture des références et import non trié

## Décision produit
Après M3 en cours, réaliser un lot M2.1 ciblé, sans attendre M4/M5. Cette mission est proposée et non exécutée. Ne pas interrompre la branche Codex M3; intégrer par branche distincte après réception/qualification de M3. Références : M2_UNSORTED_REFERENCE_IMPORT_REQUIREMENTS.md.

## Fonction principale : « Quelles photos me manquent ? »
- Inventorier automatiquement (si moteurs locaux qualifiés disponibles) ou via annotations assistées les vues disponibles : face, trois-quarts gauche/droit, profil gauche/droit, dos, visage rapproché, buste, plein pied, bras/mains visibles, expressions, coiffures, tenues, lumière.
- Produire un tableau de couverture par **usage** (portrait, plein pied, mouvement, vue de dos, scènes), sans prétendre qu'une photo de dos révèle les traits du visage.
- Distinguer « absent », « disponible », « incertain », « qualité insuffisante »; expliquer le diagnostic, exposer les références qui l'étayent et laisser l'utilisateur corriger.
- Proposer un nombre réduit de photos complémentaires, classées par gain attendu et coût d'acquisition : par exemple « 1 portrait de face net, lumière diffuse », « 1 profil droit », « 1 plein pied de dos », avec instructions simples de cadrage et distance. Aucun quota arbitraire ni garantie de fidélité parfaite.
- Grand angle, faible résolution, occlusion et perspectives déformées peuvent dégrader l'utilité pour certaines tâches sans entraîner rejet global.
- Ne pas réclamer de nouvelles images si le dossier répond déjà au besoin choisi; chaque recommandation est facultative.
- Les images doivent provenir de sources autorisées; ne pas demander d'images privées d'un tiers sans consentement.

## UX Android
- Écran « Couverture des références » : matrice angles × cadrages, couverture qualitative et confiance calibrée uniquement si validée; sinon indiquer « estimation non qualifiée ».
- Bouton « Voir les images utilisées » pour chaque catégorie.
- Liste « 3 prochaines photos les plus utiles » avec exemple de prise de vue textuel et possibilité « ignorer ».
- Réévaluation incrémentale à chaque nouvel import, sans modifier les originaux.
- Fonctionnement offline, limitation CPU/batterie, gestion de 10 à 1000+ photos et import de dossier non trié.

## Tests
Corpus de synthèse avec catégories présentes/manquantes, angles confondus, grand-angle, portrait/paysage, changements de coiffure/tenue et doublons. Vérifier que le moteur ne fabrique pas de vues absentes et ne confond pas absence d'image avec faible confiance. Tests d'interface et reprise d'import. Vérifier migrations M2/M3 et conservation des sauvegardes.

## Limites et acceptation
Sans modèle de vision local validé, fournir annotations manuelles et couverture calculée à partir de ces annotations; ne pas annoncer une reconnaissance automatique opérationnelle. M2.1 est complète seulement quand l'utilisateur peut importer en vrac, voir les manques justifiés et obtenir une liste de prises de vue utiles, avec tests et preuves.
