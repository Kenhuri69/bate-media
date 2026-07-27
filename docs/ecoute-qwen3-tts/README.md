# Jeu d'écoute — Qwen3-TTS pour la voix d'Arthur

Les clips qui ont servi à trancher entre Chatterbox (le moteur en service) et Qwen3-TTS,
et à choisir le timbre d'Arthur. Verdict et mesures : [`../qwen3-tts.md`](../qwen3-tts.md).

Ils sont versionnés à titre de **pièces justificatives** : les chiffres du verdict (cohésion
de timbre, ambitus par registre) ne remplacent pas l'oreille, et un choix de voix qu'on ne
peut plus réécouter n'est pas un choix vérifiable. Les voix de production, elles, ne sont
pas dans le dépôt — elles sont distribuées en Release (voir le README racine).

    bash docs/ecoute-qwen3-tts/ecouter.sh      # tout, dans l'ordre
    bash docs/ecoute-qwen3-tts/ecouter.sh 1    # timbres premium
    bash docs/ecoute-qwen3-tts/ecouter.sh 2    # registres de jeu
    bash docs/ecoute-qwen3-tts/ecouter.sh 3    # A/B contre Chatterbox
    bash docs/ecoute-qwen3-tts/ecouter.sh 4    # mélanges de timbres

`ecouter.sh` utilise `afplay` (macOS). Ailleurs, n'importe quel lecteur fait l'affaire.

| dossier | contenu |
|---|---|
| `1-timbres/` | les 9 timbres premium sur une même réplique d'Arthur |
| `2-registres/` | les 7 registres de jeu sur `aiden` |
| `3-ab/` | A = Chatterbox en service, B = Qwen3-TTS, sur 4 répliques identiques |
| `4-melanges/` | mélanges pondérés de timbres, + les 7 registres sur le meilleur |
| `rapport.json`, `rapport_speakers.json` | mesures brutes du banc (`tools/bench_qwen3tts.py`) |

Le texte prononcé vient des timelines Dialogic du jeu — ce sont de vraies répliques, pas
des phrases de démonstration : un timbre qui tient sur « Bonjour, je suis une voix de
synthèse » ne dit rien de ce qu'il donnera sur « Je... je le sens. C'est comme une petite
flamme, tout au fond. »
