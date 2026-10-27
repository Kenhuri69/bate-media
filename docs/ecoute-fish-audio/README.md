# Jeu d'écoute — Fish Audio (S2-Pro, Drama-3) contre Qwen3-TTS

Banc du 2026-10-27 : les voix livrées d'Arthur et de Tessia, clonées par Fish Audio à partir
de leurs propres clips Qwen3-TTS. **Verdict d'oreille à rendre** — rien n'est branché en
production.

    afplay arthur/01_original_qwen_tts.ogg

| fichier | test |
|---|---|
| `01_original_qwen_tts` | la réplique livrée par Qwen3-TTS (exclue de la référence de clonage), -16 LUFS |
| `01_clone_fish_<modèle>` | la même réplique, voix clonée |
| `02_articulation_<modèle>` | phrase inédite : liaisons, « 14 juillet 1847, à 21 h 30 » |
| `03a/b/c_fish_<émotion>_<modèle>` | même réplique en `[whisper]`, `[angry tone]`, `[excited]` |
| `04_narration_longue_<modèle>` | cinq phrases d'affilée (Arthur : registre de narration) |

## Mesures (`resultats.json`)

| | S2-Pro 8 bits | Drama-3 4 bits | Qwen3-TTS |
|---|---|---|---|
| RTF (temps de calcul / durée) | 1,9-3,6 | 1,1-2,9 | **0,29** |
| pic mémoire | 10-13 Go | 28-29 Go | — |
| CER whisper | 0-4 % | 0-8 %, 34 % sur le murmure d'Arthur | 0-6 % |
| similarité à la référence, duel (Arthur / Tessia) | 0,984 / 0,973 | **0,991 / 0,977** | 0,997 / 0,974 |
| pire fenêtre de la narration | 0,956 / 0,863 | **0,984 / 0,966** | — |

Chaque clone ressemble plus à son personnage qu'à l'autre (témoin croisé) : l'empreinte est
bien utilisée. Le murmure de Drama-3 sur Arthur dégénère (21 s pour ~4 s de texte).

Outils : `voice-agent/training/{migrer_voix_fish,fishtts,test_qwen_to_fish_cloning}.py`.
