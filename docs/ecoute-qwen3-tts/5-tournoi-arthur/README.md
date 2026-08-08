# Lot 5 — quel timbre pour Arthur (balayage du 2026-08-08)

Sept timbres Qwen3-TTS CustomVoice, **les huit mêmes répliques réelles** d'Arthur pour
chacun, registres et graines de production. Produit par `tools/tournoi_timbre_arthur.py`,
mesures dans `rapport_tournoi.json`.

Les lots 1 à 4 avaient tranché le moteur et sorti deux têtes de série qui ne gagnaient pas
sur le même critère : `aiden:0.7+serena:0.3` la stabilité, `aiden:0.8+vivian:0.2` la
hauteur. La question restante n'était donc pas « lequel des deux » mais **quelle dose** —
d'où un balayage à sept points sur les deux axes, et non un duel.

## Verdict mesuré

| dossier | F0 médian | plage F0 | verdict |
|---|---|---|---|
| `aiden-0-5_serena-0-5` | **183 Hz** | **41 Hz** | **retenu** |
| `aiden-0-7_serena-0-3` | 172 Hz | 62 Hz | trop grave, trop dispersé |
| `aiden-0-9_vivian-0-1` | 153 Hz | 78 Hz | écarté |
| `aiden` | 147 Hz | 95 Hz | écarté |
| `aiden-0-8_vivian-0-2` | 189 Hz | 105 Hz | change d'âge selon la réplique |
| `aiden-0-6_serena-0-3_vivian-0-1` | 172 Hz | 119 Hz | écarté |
| `aiden-0-7_vivian-0-3` | 195 Hz | 158 Hz | change d'âge selon la réplique |

Repère : l'Arthur Chatterbox en service tient **173–211 Hz, plage 38 Hz**.

**La plage compte plus que la médiane.** `aiden:0.7+vivian:0.3` affiche 195 Hz, pile dans
la cible — mais c'est la moyenne d'une voix qui va de 138 à 296 Hz d'une réplique à
l'autre. La cohésion MFCC, elle, ne sépare rien : sept candidats en un dixième, et elle
favorise le timbre qui varie le moins *à l'intérieur* d'une réplique — donc le plus plat.

## Écouter

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 5     # la même réplique sur les 7 timbres
bash docs/ecoute-qwen3-tts/ecouter.sh 5b    # les 8 répliques du timbre retenu
```

Le lot 5 joue **la même réplique enchaînée sur les sept timbres** : c'est la comparaison
qui se fait à l'oreille. Le lot 5b fait l'inverse — un seul timbre sur les huit répliques,
pour entendre s'il reste le même personnage entre un « Prêt. » et une narration de 14 s.

Deux choses à vérifier, que la mesure ne dit pas :

1. **Est-ce Arthur ?** 183 Hz est la hauteur d'un garçon de seize ans, mais la hauteur ne
   fait pas l'âge — le grain et la façon d'attaquer les mots comptent autant.
2. **Joue-t-il assez ?** Le timbre retenu a le plus petit ambitus du lot (3,6 demi-tons
   contre 5,1–5,8). Il est stable en partie parce qu'il est plat. Si les répliques émues
   sonnent récitées, c'est ce compromis-là qu'il faut refuser — et alors `+serena:0.3`
   (5,1 st, mais 62 Hz de plage) redevient discutable.
