# Premier rendu sur le POCO X8 Pro — 100 % local, 100 % gratuit

But : générer les planches visage et corps **sur le téléphone**, sans Internet une fois installé, et les piloter depuis l'application PERSONA IA.

| Brique | Rôle | Licence |
|---|---|---|
| [Termux](https://f-droid.org/packages/com.termux/) (via F-Droid) | Terminal Linux sur Android | GPL-3.0, gratuit |
| stable-diffusion.cpp `e239e4b` (binaire `sd-cli` compilé par la CI) | Moteur de génération sur processeur | MIT |
| RealVisXL V4.0 Lightning, quantifié q8_0 | Modèle photo SDXL en peu d'étapes | CreativeML OpenRAIL++-M |
| sdxl-vae-fp16-fix | Décodeur d'image | MIT |
| PhotoMaker v1 (format sd.cpp) | Ressemblance à partir de photos de référence, sans InsightFace | Apache-2.0 |
| Worker PERSONA (Python) | Même API que le futur PC : l'app ne change pas | ce dépôt |

**Ce qu'il faut savoir avant de commencer**

* Tout tourne sur le processeur du téléphone (la puce graphique Mali n'est pas prise en charge de façon fiable). Il faut compter **plusieurs minutes par image** ; les durées exactes seront mesurées sur ton POCO (étape 6).
* Il faut la version **12 Go de RAM** de préférence. Avec 8 Go, la génération peut échouer faute de mémoire.
* Environ **6 Go** d'espace pour les modèles.
* La qualité et la ressemblance seront **inférieures** à ce que donnera un PC (PhotoMaker v1, peu d'étapes, résolution réduite). C'est un premier rendu, pas le rendu final.
* Pour la planche corps, il n'y a pas de guidage de pose sur le téléphone : le cadrage vient du texte seul, et le dos reste marqué « estimé ».

## 1. Installer Termux (une fois)

Installe **F-Droid**, puis **Termux** depuis F-Droid. La version du Play Store est obsolète.

```sh
pkg update && pkg upgrade -y
pkg install -y python python-pillow git
termux-setup-storage          # accès au dossier Téléchargements
```

## 2. Récupérer le moteur et le code (une fois, avec Internet)

1. Sur GitHub, ouvre **Actions → « MASTER01 - POCO local engine »**, dernière exécution réussie. Télécharge l'artefact **`poco-sd-cli-arm64`** (il faut être connecté à ton compte).
2. Dézippe-le dans `Téléchargements/poco-sd-cli-arm64/`, puis :

```sh
mkdir -p ~/persona/bin && cd ~/persona
cp ~/storage/downloads/poco-sd-cli-arm64/sd-cli-arm64-dotprod bin/sd-cli
cp ~/storage/downloads/poco-sd-cli-arm64/SHA256SUMS.txt bin/
(cd bin && sha256sum sd-cli)   # doit correspondre à la ligne « dotprod » de SHA256SUMS.txt
chmod +x bin/sd-cli && ./bin/sd-cli --help | head -3
git clone -b ccr-8f135e00-hwmdvs https://github.com/bubth720/persona-ia.git
```

Si `sd-cli` affiche « Illegal instruction », prends `sd-cli-arm64-generic` (plus lent, mais compatible avec tous les processeurs).

## 3. Télécharger les modèles (une fois, avec Internet)

```sh
pip install huggingface_hub==0.26.5
python persona-ia/master01/poco/fetch_models.py ~/persona/models
SRC=$(python -c "import json;print(json.load(open('/data/data/com.termux/files/home/persona/models/models.lock.json'))['sdxl']['local_path'])")
./bin/sd-cli -M convert -m "$SRC" -o models/sdxl_q8_0.gguf --type q8_0 && rm "$SRC"
```

`models.lock.json` enregistre la révision et l'empreinte SHA-256 de chaque fichier. Compare-les avec ceux de l'exécution CI (`proof/models.lock.json`) : ils doivent être identiques.

## 4. Passer en mode avion

À partir d'ici, **plus aucune connexion n'est nécessaire**. Active le mode avion : c'est la preuve du « 100 % local ».

```sh
cat > ~/persona/env.sh <<'EOF'
export PERSONA_SDCPP_BIN=~/persona/bin/sd-cli
export PERSONA_SDCPP_MODEL=~/persona/models/sdxl_q8_0.gguf
export PERSONA_SDCPP_VAE=~/persona/models/vae/sdxl_vae.safetensors
export PERSONA_SDCPP_PM=~/persona/models/photomaker/photomaker-v1.safetensors
export PYTHONPATH=~/persona/persona-ia/master01/engine
EOF
```

## 5a. Premier essai sans photo personnelle (personne fictive)

```sh
. ~/persona/env.sh
termux-wake-lock    # empêche la mise en veille de tuer le calcul
python -m persona_engine.run_boards --backend sdcpp --demo-synthetic --subject woman --kinds face --out ~/persona/demo
```

Les planches se trouvent dans `~/persona/demo/worker/jobs/*/board/`.

## 5b. Depuis l'application PERSONA IA, avec tes vraies photos autorisées

Dans Termux :

```sh
. ~/persona/env.sh
termux-wake-lock
python -m persona_engine.worker --backend sdcpp --host 127.0.0.1 --port 8765 --root ~/persona/worker
cat worker_token.txt        # jeton à copier dans l'app
```

Dans PERSONA IA :
1. **Réglages** : moteur `http://127.0.0.1:8765`, colle le jeton, coche le consentement (les photos ne quittent pas le téléphone), puis « Enregistrer et tester ».
2. **Références** : importe tes photos et classe-en au moins 2 à 4 de face ou de trois-quarts, nettes.
3. **Générer une planche**, puis **Résultats** : accepte, rejette ou régénère chaque vue, puis exporte.

## 6. À me renvoyer pour la suite

* Le contenu de `run_summary.json` (durée et RAM de pointe par vue).
* Ton avis sur la ressemblance, à l'aide de `master01/REVUE_HUMAINE.md`.
* Si possible, la température ressentie et la batterie consommée.

## Limites honnêtes

* PhotoMaker v1 ressemble moins que les modèles prévus pour le PC (voir `SELECTION_MODELES_LOCAUX.md`).
* Pas de génération de vidéo sur le téléphone.
* Termux reste une étape technique. L'intégration du moteur directement dans l'APK est l'étape suivante, une fois ce premier rendu validé.
