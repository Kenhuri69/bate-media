# Lot 6 — la voix d'Arthur par âge (2026-08-08)

Arthur est le seul rôle de BATE qui traverse quatre âges en parlant : trois ans au
chapitre 2, quinze à l'académie. Une voix unique sur tout le jeu ferait dire « Papa,
comment on sait qu'on a réussi ? » par un homme de trente ans.

Base : **`aiden:0.5+ryan:0.5`**, le timbre validé à l'oreille. Il sort à ~131 Hz, le plus
grave des mélanges essayés — c'est l'ancrage adulte, et les stades jeunes se construisent
en montant depuis lui. Les stades sont ceux du jeu
(`bate/tools/assets/character_plan.json`), pas un découpage inventé ici : la voix et le
sprite du même personnage doivent changer aux mêmes chapitres.

Produit par `tools/voix_age_arthur.py`, chaque stade sur **ses propres** répliques.

## État réel, stade par stade

| stade | mélange | F0 | cible | plage | état |
|---|---|---|---|---|---|
| `prologue` (King Grey, ch0-1) | `aiden:0.5+ryan:0.5` | 131 Hz | 132 | 37 | ✅ |
| `s02_toddler` (3 ans, ch2-5) | `+serena:0.8` | 245 Hz | 270 | 37 | ✅ |
| `s03_child` (6 ans, ch6-30) | `+ono_anna:0.45` | 226 Hz | 240 | 63 | ⚠️ |
| `s04_teen` (13 ans, ch31-42) | `+vivian:0.6` | 225 Hz | 200 | 94 | ❌ |
| `s05_academy` (15 ans, ch43-97) | `+vivian:0.55` | 194 Hz | 175 | 72 | ❌ |

Deux stades tiennent, un passe, **deux ne sont pas résolus** — et le défaut le plus
audible est que `s03_child` et `s04_teen` sortent à la même hauteur (226 et 225 Hz) alors
que sept ans les séparent. À l'écoute, l'enfant et l'adolescent risquent d'être le même.

La narration vieillit avec le personnage (c'est sa voix intérieure), sauf au prologue :
là, celui qui pense est encore le roi d'avant la réincarnation.

## Ce qui n'a pas marché, pour ne pas le refaire

**Le mélange sature.** L'idée de départ était une seule composante aiguë dosée en
croissant, pour que la mue soit continue. `vivian` était la candidate — seule des trois à
monter de façon monotone au premier balayage. Mais elle plafonne : 0,6 → 206 Hz,
0,8 → 226, 0,9 → 220. Elle ne peut pas tirer une base à 131 Hz jusqu'aux stades jeunes,
d'où trois composantes différentes et le risque d'entendre trois personnes.

**La dose ne contrôle pas la hauteur au-delà du gros grain.** La relation est en
ESCALIER, pas en pente, et elle n'est pas interpolable même à stade et répliques
constants : `s05_academy` donne 156 Hz à 0,45 et 194 Hz à 0,55, donc 0,50 devait tomber
vers 175 — il a rendu **150**, plus bas que 0,45. Ne rien régler au centième ici.

**Un calibrage n'est pas transférable d'un stade à l'autre.** Le premier balayage a été
fait sur des répliques d'enfant puis appliqué partout. Or la hauteur dépend du texte
prononcé autant que du mélange : `vivian:0.6` donne 206 Hz sur des répliques d'enfant,
225 sur celles d'adolescent. Calibrer sur les répliques du stade visé, ou ne pas calibrer.

**Comparer des plages d'échantillons de tailles différentes n'a pas de sens.** La plage
est un écart entre extrêmes : elle croît mécaniquement avec le nombre de clips. Les 9 Hz
annoncés pour `s05_academy` au calibrage (4 clips) contre 99 Hz en production (6 clips)
ne mesuraient pas la même chose. À taille d'échantillon constante, ou pas de comparaison.

**Une part de la plage est du bruit de mesure.** La F0 médiane d'un clip de deux secondes
repose sur peu de trames voisées. Dans `s05_academy`, les deux clips les plus courts
(2,0 et 2,3 s) sortent à 207 et 232 Hz quand les quatre longs sont à 133-157. Avant de
resserrer un stade, exclure ou pondérer les clips courts — sinon on optimise du bruit.

## Écouter

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 6
```

Trois choses à vérifier, dans cet ordre :

1. **Est-ce le même personnage qui grandit ?** C'est la question qui décide, et la mesure
   n'y répond pas : trois composantes aiguës différentes se relaient d'un stade à l'autre.
2. **Distingue-t-on l'enfant de l'adolescent ?** Mesuré, non : 226 contre 225 Hz.
3. **Le prologue sonne-t-il comme un roi qui meurt ?** C'est le seul stade qui utilise ta
   base telle quelle, sans ajout — et le seul qui tombe exactement sur sa cible.
