# MASTER-02 — Résultat et décision

## Décision : **CANDIDATE-V1, avec réserve**

**L'APK intègre réellement le moteur** : le binaire natif stable-diffusion.cpp est embarqué, s'exécute depuis l'application sur Android 10 et 15, et ne dépend ni de Termux, ni d'un PC, ni du cloud. **Ce moteur a produit de vraies images**, mais sur Linux CPU, réseau coupé, pas encore sur ARM64 Android.

**Réserve explicite :** aucune inférence complète n'a encore été exécutée **à l'intérieur de l'APK sur un téléphone**. La première aura lieu sur ton POCO (Q07). Le statut **GO-V1** ne sera attribué qu'après réception de la fiche de test (`DEVICE_TEST_GUIDE.md`) : image produite, mode avion, durée, RAM, température, avis sur la ressemblance.

## Exigences

| Exigence (cahier des charges) | Statut |
|---|---|
| Une seule application, aucune ligne de commande, ni PC, ni Termux pour générer | **satisfait** (installation du modèle guidée dans l'app) |
| Image nouvelle à partir de références autorisées | **satisfait sur Linux** ; **à confirmer sur le POCO** |
| Hors ligne après installation, aucun envoi de photos ou de prompts | **satisfait** par conception et en CI ; mode avion POCO à confirmer |
| 0 € de logiciel, modèle, API ou abonnement | **satisfait** (MIT, Apache-2.0, OpenRAIL++-M) |
| Étapes observables sans pourcentage inventé ; annulation effective ; pas de double lancement | **satisfait** |
| Contrôle RAM, espace, chaleur ; erreurs typées compréhensibles | **satisfait** (à mesurer en réel) |
| Paquet de modèles séparé : SHA-256, espace, reprise, licence | **satisfait** |
| Historique, export PNG, partage, suppression, avis de ressemblance | **satisfait** |
| Fidélité au visage | **non qualifiée** : PhotoMaker v1 donne une identité plausible mais imparfaite sur sujet fictif |
| Filtres de bibliothèque par apparence ou cadrage ; HEIC/RAW | **non fait** (HEIC/RAW non pris en charge, signalé) |
| Pose corporelle avancée, vidéo | hors périmètre V1 |

## Chiffres clés

* APK : SHA-256 `0b893433c3417045a93d55913251b3386a5805510f09faf8b5f13b4968776fa4` (commit `0114cba`, run `43407275278`).
* Modèles : 8,2 Go à télécharger une fois, 5,4 Go conservés.
* Linux 4 vCPU : 12,5–13 min/image en 768 px, 6 pas, RSS 5,39 Go. **POCO : inconnu.** Il pourrait être plus lent ou plus rapide (8 cœurs A725 contre 4 vCPU x86).

## Risques restants

1. **Mémoire** : 5,4 Go de pointe. Sur un POCO de 12 Go cela devrait passer ; sur 8 Go c'est incertain, et le profil Prudent réduit seulement la taille de l'image.
2. **Durée et chaleur** : plusieurs minutes de calcul à 100 % du processeur. Le système peut brider la fréquence ; l'app s'arrête au niveau thermique SEVERE.
3. **Ressemblance** : limitée par PhotoMaker v1 ; une meilleure fidélité passera par le futur PC (`master01/SELECTION_MODELES_LOCAUX.md`).
