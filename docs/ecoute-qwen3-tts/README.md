# Jeu d'écoute — la voix d'Arthur

Les clips qui documentent les décisions **encore en vigueur**, et le choix qui attend une
oreille : les âges d'Arthur (lot 8).
Verdicts et mesures : [`../qwen3-tts.md`](../qwen3-tts.md).

    bash docs/ecoute-qwen3-tts/ecouter.sh      # tout, dans l'ordre
    bash docs/ecoute-qwen3-tts/ecouter.sh 1    # la voix en service
    bash docs/ecoute-qwen3-tts/ecouter.sh 2    # l'âge par le prompt, même timbre
    bash docs/ecoute-qwen3-tts/ecouter.sh 3    # A/B Chatterbox contre Qwen3-TTS
    bash docs/ecoute-qwen3-tts/ecouter.sh 4    # ⚠ les âges d'Arthur — À VALIDER

`ecouter.sh` utilise `afplay` (macOS). Ailleurs, n'importe quel lecteur fait l'affaire.

| dossier | contenu |
|---|---|
| `4-melanges/aiden_0-5-ryan_0-5.wav` | **le timbre en service**, validé à l'oreille |
| `7-age-par-prompt/` | l'âge par le prompt, timbre intact ([détail](7-age-par-prompt/README.md)) |
| `8-ages-par-prompt/` | **⚠ à valider** — les six stades, et la limite du prompt ([détail](8-ages-par-prompt/README.md)) |
| `3-ab/` | A = Chatterbox, B = Qwen3-TTS, sur 4 répliques identiques |
| `repere-chatterbox/` | les 7 clips Chatterbox qui servent d'étalon aux bancs |
| `5-tournoi-arthur/`, `6-ages-arthur/` | README et mesures seuls — clips supprimés |

## Ce qui a été supprimé, et pourquoi c'est sans perte

Le 2026-08-08, les **variantes écartées** ont été retirées : les 9 timbres du premier
balayage, les 7 du tournoi, les 5 stades produits par dilution du timbre, les prompts
perdants. De 9,8 Mo à 1,0 Mo.

Les **mesures** de tous ces essais restent — dans les README de chaque lot et dans les
rapports JSON (`rapport_tournoi.json`, `rapport_ages.json`, `rapport_prompt.json`,
`calibrage/*.json`). Ce sont elles qui portent les conclusions, pas les fichiers audio.
Et les clips eux-mêmes sont dans l'historique Git : `git log --diff-filter=D --name-only`
les retrouve, `git checkout <commit>^ -- <chemin>` les rend.

`repere-chatterbox/` est conservé pour une raison précise : sept des huit clips qui
servaient d'étalon aux bancs ont été **remplacés** dans `voices/arthur/` par le lot
Qwen3. Sans cette copie, `_repere_chatterbox` mesurerait du Qwen3 en croyant mesurer du
Chatterbox — une mesure fausse qui ne signale rien.

Le texte prononcé vient des timelines Dialogic du jeu — ce sont de vraies répliques, pas
des phrases de démonstration : un timbre qui tient sur « Bonjour, je suis une voix de
synthèse » ne dit rien de ce qu'il donnera sur « Je... je le sens. C'est comme une petite
flamme, tout au fond. »
