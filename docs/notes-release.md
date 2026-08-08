# Pack de voix 0.2.0 — la voix d'Arthur passe à Qwen3-TTS sur ses premiers chapitres

1642 répliques, 31 voix. **72 répliques d'Arthur régénérées** avec Qwen3-TTS ; les 1570
autres sont inchangées depuis la 0.1.0 (Chatterbox).

## Ce qui change

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

**La narration ne suit pas l'âge** : une seule voix de narrateur sur tout le jeu. Arthur
parle jeune et raconte d'une voix posée.

## Qualité

Les 72 clips ont passé un contrôle d'énergie spectrale : 8 clips défectueux ont été
détectés et régénérés, 8 récupérés. Le lot est à 0 défaut résiduel.

Ce contrôle a été ajouté parce que le garde-fou existant ne voyait pas ces cas : les clips
avaient une durée, un niveau et un taux de voisement plausibles, mais leur énergie n'était
pas à la bonne hauteur. Il ne s'appuie pas sur la F0, qui se trompe d'octave quand le
fondamental est faible.

## Installer

    python3 tools/verify_pack.py bate-media-voices-0.2.0.tar.zst
    python3 tools/install_pack.py bate-media-voices-0.2.0.tar.zst --jeu ~/workspace/bate

Rien ici n'est nécessaire pour jouer : une voix absente laisse le dialogue continuer en
silence (`AudioManager.ResolveClip` rend `null`). Voir
[`docs/integration-dialogic.md`](integration-dialogic.md).

## Reste à faire

Trois stades d'Arthur ne sont pas encore traités : enfant (ch6-30), adolescent (ch31-42),
académie (ch43-97). Leurs prompts d'âge sont rédigés mais **non mesurés** — ils restent en
Chatterbox dans ce pack.
