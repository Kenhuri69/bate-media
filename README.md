# bate-media — pack de voix et de médias d'immersion pour BATE

Dépôt **public** des contenus d'immersion du jeu [BATE](https://github.com/Kenhuri69/bate) :
voix des personnages, vidéos, animations.

**Rien ici n'est nécessaire pour jouer.** Le jeu fonctionne sans ce pack : les dialogues
s'affichent, l'histoire avance. Ces médias ajoutent l'immersion — une voix sur chaque
réplique, des cinématiques, des animations d'ambiance. Cette séparation est délibérée :

- le dépôt du jeu reste léger et se clone vite ;
- un pack lourd se versionne et se télécharge indépendamment du code ;
- une absence de média ne casse jamais une partie, elle la rend seulement plus sobre.

## Ce que contient le dépôt, et ce qu'il ne contient pas

Le dépôt lui-même reste **léger** : manifestes, outils, documentation. Les fichiers audio et
vidéo sont distribués comme **artefacts de Release**, pas versionnés dans l'arborescence.

C'est un choix technique, pas de la paresse : versionner des milliers de binaires dans Git
(même via LFS) rend le dépôt pénible à cloner, coûteux en quota, et fragile — ce projet a
déjà rencontré un LFS mal initialisé qui a écrit des pointeurs là où on attendait des blobs.
Un pack immuable, horodaté et vérifiable par somme de contrôle règle le problème.

    voices/<personnage>/     # présent en local, ignoré par Git (voir .gitignore)
    video/  animation/       # idem
    manifest.json            # index versionné : ce que le pack DOIT contenir
    tools/                   # assemblage, vérification, installation
    docs/                    # production des voix, intégration Dialogic

## Utilisation

Récupérer un pack publié et l'installer dans le jeu :

    python3 tools/verify_pack.py dist/bate-media-voices-<version>.tar.zst
    python3 tools/install_pack.py dist/bate-media-voices-<version>.tar.zst \
        --jeu ~/workspace/bate

Assembler un pack depuis les voix produites localement :

    python3 tools/sync_from_forge.py            # récupère les sorties de voice-agent forge
    python3 tools/build_pack.py --version 0.1.0

## Production des voix

Les voix sont créées avec la pipeline `voice-agent forge` (dépôt `voice-agent`, 100 % local) :
une description en français → candidats Parler-TTS → validation à l'écoute → clonage
Chatterbox de la voix retenue sur chaque réplique. Détail dans
[`docs/pipeline-voix.md`](docs/pipeline-voix.md).

Aucune voix ne reproduit celle d'une personne réelle : chaque timbre est synthétisé depuis
une **description écrite**, pas cloné d'un enregistrement humain.

## Statut juridique

Voir [`NOTICE.md`](NOTICE.md). En résumé : travail de fan, non commercial, dérivé de
*The Beginning After The End* de TurtleMe. Les **outils** de ce dépôt sont sous licence MIT
(`LICENSE-TOOLS`) ; les **contenus** ne sont pas sous licence libre et ne peuvent pas l'être.
