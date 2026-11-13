# Guide utilisateur et qualification sur le POCO X8 Pro (5 étapes, sans terminal)

> L'installation sur ton téléphone se fait **par toi** ; je n'installe rien sur un appareil personnel.

1. **Installer l'APK** : télécharge l'artefact `persona-ia-master01-debug-apk` de la dernière exécution verte de « MASTER01 - engine tests, Android APK, emulators » (onglet Actions), vérifie le SHA-256 indiqué dans `apk_sha256.txt`, puis installe `app-debug.apk` (autoriser les sources inconnues pour ton gestionnaire de fichiers). Une ancienne version 1.0 peut être mise à jour directement.
2. **Installer le modèle** (une fois, en Wi-Fi, ≈ 8,2 Go) : Accueil → *Modèle local* → *Vérifier le moteur natif* (doit afficher « Moteur OK ») → *1. Télécharger* → *2. Préparer le modèle* (quantification, quelques minutes). L'état doit passer à **PRÊT**.
3. **Mode avion** : active-le. Tout ce qui suit doit fonctionner sans réseau.
4. **Références** : Accueil → *Importer des photos* (coche la déclaration d'autorisation) → choisis 2 à 4 photos nettes de face ou de trois-quarts → classe-les.
5. **Générer** : Accueil → *Générer sur le téléphone* → choisis les références, écris une description, profil *Standard*, puis *Générer*. Laisse le téléphone branché ; compte plusieurs minutes. Le résultat s'ouvre dans l'*Historique* : *Ressemble / Ne ressemble pas*, *Exporter*, *Partager*.

## Fiche de qualification à me renvoyer (Q07, sans photo personnelle)

| Mesure | Valeur |
|---|---|
| RAM du POCO (8 / 12 Go), Android, espace libre | |
| « Vérifier le moteur natif » : texte affiché | |
| Durée de la préparation (quantification) ; l'empreinte est-elle « identique à la CI » ? | |
| 1ʳᵉ génération (à froid) : durée et « RAM pic » affichées dans l'historique | |
| 2ᵉ génération (à chaud) : durée, RAM pic | |
| 3ᵉ : lancer, annuler pendant l'inférence, relancer → stable ? | |
| Mode avion actif pendant tout le test ? | oui / non |
| Température : avertissement affiché ? arrêt ? | |
| Cas F01 à F07 (portrait, trois-quarts, expression, décor, tenue, plan élargi, même graine deux fois) : réussite technique ? ressemblance (ton avis) ? | |

Descriptions conseillées (anglais) : F01 `head and shoulders portrait, looking at the camera` · F02 `three-quarter view portrait, window light` · F03 `laughing, head and shoulders` · F04 `standing in a park, autumn, portrait` · F05 `wearing a navy suit, portrait` · F06 `full body, standing on a street` · F07 F01 deux fois avec la même graine.
