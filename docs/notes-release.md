# Pack de voix 0.3.0 — première version : Arthur, chapitres 0 à 5

**72 répliques, une seule voix.** Ce pack ne contient plus que ce qui a été produit et
validé : Arthur sur le prologue et ses premiers chapitres, en Qwen3-TTS.

Les 1570 répliques Chatterbox des trente autres personnages sont retirées. Elles restent
téléchargeables dans la [v0.2.0](https://github.com/Kenhuri69/bate-media/releases/tag/v0.2.0)
pour qui les veut, mais elles ne sont plus la ligne du projet : la voix repart d'Arthur,
personnage par personnage, avec le moteur et la méthode qui ont fait leurs preuves ici.

## Contenu

| stade | répliques | voix |
|---|---|---|
| prologue (ch0-1, King Grey) | 26 | `aiden:0.5+ryan:0.5`, ~120 Hz |
| toddler (ch2-5) — répliques parlées | 7 | même timbre + prompt d'âge, ~164 Hz |
| toddler (ch2-5) — narration | 39 | même timbre, ~122 Hz |

**Un seul timbre pour Arthur, à tous les âges.** L'âge se joue par un prompt de style, pas
en modifiant la voix : une première version diluait le timbre validé dans une composante
plus aiguë pour atteindre la hauteur d'un enfant, au prix de n'en garder que 20 % — ce
n'était plus le même personnage. Mesuré, le prompt seul fait aussi bien que cette dilution
à dose modérée (164 Hz contre 162) en gardant le timbre entier.

**La narration ne suit pas l'âge** : une seule voix de narrateur. Arthur parle jeune et
raconte d'une voix posée.

## Qualité

Les 72 clips ont passé un contrôle d'énergie spectrale : 8 clips défectueux détectés,
8 récupérés, 0 défaut résiduel. Ce contrôle a été ajouté parce que le garde-fou existant
ne voyait pas ces cas — durée, niveau et voisement plausibles, mais énergie à la mauvaise
hauteur. Il ne s'appuie pas sur la F0, qui se trompe d'octave quand le fondamental est
faible.

## Installer

    python3 tools/verify_pack.py bate-media-voices-0.3.0.tar.zst
    python3 tools/install_pack.py bate-media-voices-0.3.0.tar.zst --jeu ~/workspace/bate

Rien ici n'est nécessaire pour jouer : une voix absente laisse le dialogue continuer en
silence (`AudioManager.ResolveClip` rend `null`). Les chapitres 6 et suivants, et tous les
autres personnages, sont donc simplement muets. Voir
[`docs/integration-dialogic.md`](integration-dialogic.md).

## Suite

Arthur au-delà du chapitre 5 : les stades enfant (ch6-30), adolescent (ch31-42) et
académie (ch43-97) ont des prompts d'âge rédigés mais **non mesurés**. Les autres
personnages sont à reprendre depuis leurs textes, qui sont conservés
(`voice-agent/training/forge/*/lines.json`).
