# M1 — état de récupération (2026-11-08)

Le bundle local PERSONA_IA_M1.bundle a été fourni. Son pointeur principal est `fc86f3d0187543b7d78b5b09ac2aa14cfffd4c74` (`refs/heads/codex/persona-m1-foundation`); il contient aussi un historique local initial distinct de `main` sur GitHub.

**Important : ce fichier est une fiche de récupération, pas une publication du code M1.** Les sources M1 ne sont pas encore poussées sur le dépôt distant. Ne pas lancer M2 avant restauration et vérification.

Procédure sur machine Git autorisée :

```bash
git clone PERSONA_IA_M1.bundle persona-ia-m1 -b codex/persona-m1-foundation
cd persona-ia-m1
git fsck --full
git rev-parse HEAD
git remote add github https://github.com/bubth720/persona-ia.git
git push github HEAD:refs/heads/codex/persona-m1-foundation
```

Le dernier `git push` nécessite authentification GitHub et autorisation du propriétaire. Il crée/met à jour uniquement la branche M1, pas `main`. Vérifier le nom de branche distant avant de pousser et ne pas utiliser `--force`. L'historique local initial du bundle et celui de GitHub `main` sont distincts : ne pas fusionner automatiquement.

Limites relevées dans le rapport Codex M1 : JPEG/PNG/WebP pris en charge, pas de HEIC/GIF/vidéo; tests physiques et thermiques non qualifiés. Les preuves M1 sont des résultats fournis par Codex, pas une reproduction indépendante de tests.

Voir `EXECUTION_CODEX.md` pour la suite.
