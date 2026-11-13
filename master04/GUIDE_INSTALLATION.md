# PERSONA sur PC Windows — guide simple

Tout est gratuit et fonctionne sur ton ordinateur. Aucune photo n'est envoyée sur Internet. Les seuls téléchargements (modèles d'IA, Blender) se font une fois, avec ton accord.

## A. Essayer tout de suite PERSONA LIVE (2 minutes, rien à installer)

1. Sur GitHub : **Actions → « MASTER04 - PERSONA LIVE » → dernière exécution verte → Artifacts → `PERSONA_LIVE-windows`**. Télécharge et dézippe.
2. Double-clique **`PERSONA_LIVE.exe`**. Si Windows SmartScreen avertit (l'exécutable n'est pas signé), clique « Informations complémentaires » puis « Exécuter quand même ».
3. Commandes :

| Touche | Action |
|---|---|
| Z Q S D (ou W A S D) / flèches | se déplacer |
| Maj | courir |
| E | interagir (lampe, ballon) |
| clic droit + souris, ou J L I K | tourner la caméra |
| molette ou + / − | zoom |
| C | caméra libre (Z Q S D déplacent la caméra) |
| N | décor suivant (Studio, Jardin) |
| F2 | importer un personnage (fichier `.glb` ou dossier PERSONA) |
| F3 | profil graphique léger / standard / avancé |
| F12 ou P | capture d'écran (dossier `%APPDATA%\PERSONA\screenshots`) |
| F1 ou H | aide |

Les réglages sont sauvegardés dans `%APPDATA%\PERSONA\persona_live.cfg`. Le dossier `characters` livré à côté contient le personnage de démonstration (`persona_demo.glb` et `.fbx`, licence CC0), qui sert aussi d'exemple d'import.

**Test automatique** (si tu veux vérifier ta machine) : dans une invite de commande ouverte dans ce dossier, lance
`PERSONA_LIVE.console.exe -- --selftest --report=rapport.json`, puis envoie-moi `rapport.json`.

## B. Installer l'atelier photo et la chaîne 3D (paquet `PERSONA_PC-windows-package`)

1. Télécharge l'artefact **`PERSONA_PC-windows-package`**, dézippe-le (par exemple dans `C:\PERSONA`).
2. **Diagnostic sans rien installer** : clic droit sur le menu Démarrer → *Terminal*, puis :
   `powershell -ExecutionPolicy Bypass -File C:\PERSONA\install\Installer-PERSONA.ps1 -DryRun`
   Cela affiche ton processeur, ta RAM, ta carte graphique, ta VRAM et le profil choisi. Le rapport est dans `%APPDATA%\PERSONA\hardware_report.json`.
3. **Installation** : même commande **sans** `-DryRun`. Le script demande ton accord pour :
   * Python 3.11 (via winget, gratuit) si absent ;
   * les modèles d'IA (≈ 8,2 Go, révisions figées, SHA-256 vérifiés) ;
   * Blender 4.2 LTS portable (≈ 350 Mo) pour la chaîne 3D.
4. Lanceurs créés :
   * **`PERSONA Atelier.cmd`** ouvre l'atelier photographique dans ton navigateur (adresse locale `127.0.0.1`) : importer des photos, générer face / profils / trois-quarts, comparer, valider, exporter ;
   * **`PERSONA Dossier personnage.cmd`** analyse un dossier de photos (angles, couverture, parties manquantes), crée le dossier du personnage et un modèle 3D riggé ajusté aux proportions estimées. Charge ensuite ce dossier dans PERSONA LIVE avec **F2**.

**Règle mémoire** : ne lance pas une génération IA pendant que PERSONA LIVE est ouvert. L'atelier refuse de démarrer un calcul lourd tant que LIVE tourne.

## C. Ce qu'il faut savoir sur ton IdeaPad Gaming 3 (caractéristiques supposées, à confirmer avec le diagnostic)

* i5-10300H, 8 Go de RAM, GTX 1650 4 Go → **profil léger**.
* PERSONA LIVE : rendu simplifié (pas d'ombres, résolution 75 %), adapté à cette machine.
* Génération photo : sur le **processeur** avec le modèle quantifié q4_K, en 640 px et 5 étapes. Compte **plusieurs minutes par image**. L'accélération par la GTX 1650 n'est pas encore livrée : le binaire fourni est la version processeur AVX2.
* 8 Go de RAM est juste : ferme le navigateur et les autres applications pendant une génération.
