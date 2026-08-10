# Lot 9 — casting de Tessia : quatre candidates, à trancher à l'oreille

**Rien n'est décidé ici.** Ce lot existe pour être écouté ; la mesure ne fait qu'écarter, elle
ne choisit pas. C'est la convention de la forge depuis le premier timbre d'Arthur.

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 5
```

## Pourquoi ces quatre-là, et pas d'autres

CustomVoice compte neuf timbres premium, dont **exactement quatre féminins** : `serena`,
`vivian`, `ono_anna`, `sohee`. Les quatre sont ici. Il n'y a pas de cinquième voix de femme à
essayer — le choix contraint du modèle est épuisé.

Ce sont des timbres **purs**, pas des mélanges. Un mélange peut battre un timbre pur (c'est le
cas pour Arthur, `aiden:0.5+ryan:0.5`), mais une audition doit d'abord porter sur des voix
entières : valider `serena:0.6+vivian:0.4` avant d'avoir entendu `serena` reviendrait à choisir
une formule plutôt qu'une voix. Si aucune des quatre ne convient telle quelle, les mélanges
sont l'étape d'après.

## Ce que chaque candidate doit porter

Tessia traverse **deux âges** sur les ch0-60, et l'échantillon les couvre tous les deux — c'est
la même voix qui devra tenir les deux, donc c'est sur les deux qu'elle se juge :

| âge | chapitres | ce qu'elle y est |
|---|---|---|
| enfant | ch10-18 | cinq ans, captive puis chez les elfes — « Tessia Eralith. Et j'ai eu cinq ans. » |
| adolescente | ch44-60 | à l'académie de Xyrus, elle préside et explique |

Huit répliques, les plus longues de chaque âge. Longues à dessein : la F0 médiane d'un clip de
deux secondes repose sur trop peu de trames voisées pour valoir une mesure — piège déjà payé sur
les âges d'Arthur, où deux clips courts sortaient 50 à 80 Hz au-dessus des quatre longs du même
lot. Et ce sont de **vraies répliques du jeu**, pas des phrases de démonstration.

**Aucun prompt d'âge n'est appliqué.** On écoute le timbre, pas sa déclinaison : ce sont deux
questions, et les mêler ferait juger une voix sur un réglage. (Sur Arthur, la déclinaison par
âge sépare bien la voix parlée de la narration mais ne distingue pas les stades entre eux —
voir le lot 8. Le problème reste donc ouvert, raison de plus pour ne pas le mêler à celui-ci.)

## Mesures — et elles ne se mettent pas d'accord

Deux grandeurs, parce qu'aucune ne suffit. La **F0** vise le fondamental mais se trompe d'octave
quand l'énergie basse est faible (elle a produit un verdict entièrement faux sur les voix
d'Arthur, voir le lot 8) ; le **barycentre** ne peut pas se tromper d'octave mais mesure aussi
la brillance, donc il bouge avec le texte prononcé. Ici la F0 est crédible — l'énergie sous
150 Hz est de 0,0 à 0,1 %, cohérent avec un fondamental à 210-255 Hz — mais les deux classements
divergent, et il faut le dire plutôt que choisir celui qui arrange.

| timbre | F0 | plage F0 | barycentre | enfant → ado (barycentre) | écart |
|---|---|---|---|---|---|
| `sohee` | 210 Hz | **13 Hz** | 363 Hz | 343 → 365 Hz | +23 Hz |
| `serena` | 229 Hz | 65 Hz | 364 Hz | 335 → 410 Hz | **+75 Hz** |
| `vivian` | 240 Hz | 58 Hz | 338 Hz | 313 → 384 Hz | **+71 Hz** |
| `ono_anna` | 255 Hz | 69 Hz | 354 Hz | 360 → 348 Hz | **−11 Hz** |

**Le désaccord porte sur la stabilité, qui est le critère décisif.** À la F0, `sohee` domine
d'un facteur cinq (13 Hz de plage contre 58-69) et `ono_anna` est le plus dispersé. Au
barycentre, c'est l'inverse : `ono_anna` est le seul à ne pas bouger entre les deux âges (−11 Hz)
quand `serena` et `vivian` sautent de 71 à 75 Hz.

Ce que les deux disent quand même :

* **`serena` et `vivian` changent nettement de voix entre l'enfant et l'adolescente.** Les deux
  grandeurs le voient (écart d'âge 28 et 10 Hz en F0, 75 et 71 au barycentre). Or aucun prompt
  d'âge n'a été donné : c'est le TEXTE qui les fait bouger. Une voix qui change de registre selon
  ce qu'elle dit fera entendre deux personnes là où le récit n'en a qu'une.
* **`sohee` et `ono_anna` sont les deux candidates stables**, chacune selon une grandeur
  différente. C'est entre elles deux que l'écoute a le plus de chances de trancher.

Et le biais à garder en tête, quel que soit le critère : **la stabilité récompense la voix la
plus plate.** `sohee` est peut-être régulière parce qu'elle joue moins. Un lot dispersé ne fait
pas entendre un personnage mais plusieurs ; un lot trop plat n'en fait entendre aucun. Seule
l'oreille arbitre entre les deux — c'est pour ça que ce dossier existe.

## Après l'écoute

Le timbre retenu se note dans un `choice.json` de forge, comme celui d'Arthur, et sert à
produire les 112 répliques de Tessia sur les ch0-60 :

```bash
../.venv-mlx/bin/python ../voice-agent/training/qwen3tts.py \
    --lines ~/workspace/voice-agent/training/forge/bate-tessia/lines.json \
    --speaker <timbre retenu> --out-dir voices/tessia --format ogg
```

Mesures brutes : [`rapport_casting.json`](rapport_casting.json). Production :
[`../../tools/tessia_casting.py`](../../tools/tessia_casting.py).
