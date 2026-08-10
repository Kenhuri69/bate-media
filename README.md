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

Le jeu d'écoute de `docs/ecoute-qwen3-tts/` (1 Mo) est la seule exception à la règle : il
garde les clips qui documentent une décision **encore en vigueur** — la voix en service,
l'A/B qui a fait changer de moteur, l'étalon de mesure. Les candidats de casting et les
clips d'audit en faisaient partie jusqu'au 2026-08-08 ; ils ont été retirés, les décisions
qu'ils justifiaient vivant dans `voice-agent/training/forge/*/choice.json`.

## Utilisation

Récupérer un pack publié et l'installer dans le jeu :

    python3 tools/verify_pack.py dist/bate-media-voices-<version>.tar.zst
    python3 tools/install_pack.py dist/bate-media-voices-<version>.tar.zst \
        --jeu ~/workspace/bate

Assembler un pack depuis les voix produites localement :

    python3 tools/sync_from_forge.py            # récupère les sorties de voice-agent forge
    python3 tools/build_pack.py --version 0.1.0

## Production des voix

Les voix sont créées avec la pipeline `voice-agent forge` (dépôt `voice-agent`, 100 % local).
Depuis la 0.3.0, le moteur est **Qwen3-TTS** : un timbre premium — ou un mélange pondéré de
plusieurs — choisi à l'écoute, et une émotion donnée par une phrase en français attachée à
chaque réplique. Verdict et mesures : [`docs/qwen3-tts.md`](docs/qwen3-tts.md).

Ce que la 0.4.0 contient — **Arthur et le narrateur, chapitres 0 à 60, 4401 répliques** — est
ce qui a été produit et validé avec cette méthode. Les 1570 répliques Chatterbox des trente
autres personnages, livrées jusqu'à la 0.2.0, ne sont plus distribuées : elles restent
téléchargeables dans cette version-là, et leurs textes sources sont conservés pour être
reproduits (`voice-agent/training/forge/*/lines.json`).

**Un clip est nommé par le TEXTE qu'il dit**, pas par sa place :
`<rôle>_<empreinte>` (`narrator_c03132187d`). Une réplique déplacée garde sa voix ; une réplique
réécrite perd la sienne et se tait, au lieu de décaler silencieusement toutes les suivantes. La
règle est partagée avec le jeu et vérifiable : `python3 tools/empreinte.py --selftest` rejoue les
vecteurs que `bate` publie.

Aucune voix ne reproduit celle d'une personne réelle : chaque timbre est synthétisé depuis
une **description écrite** ou choisi parmi les timbres premium du modèle, jamais cloné d'un
enregistrement humain.

## Statut juridique

Voir [`NOTICE.md`](NOTICE.md). En résumé : travail de fan, non commercial, dérivé de
*The Beginning After The End* de TurtleMe. Les **outils** de ce dépôt sont sous licence MIT
(`LICENSE-TOOLS`) ; les **contenus** ne sont pas sous licence libre et ne peuvent pas l'être.
