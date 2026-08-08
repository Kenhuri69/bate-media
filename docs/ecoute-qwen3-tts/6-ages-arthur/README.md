# Lot 6 — la voix d'Arthur par âge (2026-08-08)

> **Refondu le même jour.** Ce lot déclinait d'abord l'âge en DILUANT le timbre validé
> dans une composante plus aiguë. Ça atteignait la hauteur (245 Hz à trois ans) au prix de
> réduire `aiden:0.5+ryan:0.5` à **20 %** du mélange : ce n'était plus la voix choisie,
> seulement son nom. Refusé, et à raison — une validation porte sur une voix entendue, pas
> sur une formule, et les 270 Hz visés n'étaient qu'un repère physiologique que je m'étais
> fixé.
>
> **L'âge se fait désormais par le PROMPT, timbre intact à 100 %** (lot 7). Mesuré : le
> prompt seul fait aussi bien que la dilution à 30 % — 164 Hz contre 162 — donc à hauteur
> égale il est strictement meilleur. C'est le levier qui aurait dû être essayé en premier.
>
> **Et la narration ne suit pas l'âge** : une seule voix de narrateur sur tout le jeu.
> Décision de simplicité, appuyée par la mesure — le registre narration annulait déjà le
> prompt enfantin (127 Hz contre 164 pour le parlé du même stade). Arthur PARLE jeune et
> RACONTE d'une voix posée. Seules 149 répliques parlées sur 1065 portent un âge.
>
> Les tableaux de dilution ci-dessous sont conservés comme trace de ce qui a été essayé,
> pas comme configuration en service.

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

## Livré : prologue et toddler (72 répliques)

```bash
python tools/voix_age_arthur.py livrer prologue,s02_toddler   # 72 clips, ~8 min
python tools/voix_age_arthur.py verifier prologue,s02_toddler # contrôle qualité
python tools/voix_age_arthur.py reprendre prologue,s02_toddler # régénère les défectueux
```

Sortie dans **`voices/arthur-qwen3/`** et non `voices/arthur/`, qui contient les 1065
répliques Chatterbox en service — celles qui font tourner le jeu et qui servent d'étalon
aux bancs (`_repere_chatterbox`). Les deux jeux cohabitent tant que les trois stades
restants ne sont pas résolus. Dossier non versionné (`voices/*/` est dans .gitignore) :
les médias partent en Release.

**Un échantillon de six clips ne prédit pas un lot de quarante-six.** Les deux stades
affichaient 37 Hz de plage à l'écoute ; livrés en entier, 298 et 127 Hz. Le défaut est
rare — 9 clips sur 72, soit 12,5 % — donc six tirages passent facilement à côté. Contrôler
le lot complet, jamais l'échantillon qui a servi à choisir.

**Le garde-fou `_suspect()` n'a rien vu** (0 relance sur 72) : ces clips avaient une durée
plausible, un niveau au-dessus de son seuil et une part de trames voisées normale. Ce
qu'ils avaient d'anormal, c'est que leur énergie n'était pas à la bonne hauteur — 4 à 18 %
dans la bande du fondamental attendu, contre 50 à 69 % pour le lot. D'où le contrôle
`verifier`, fondé sur l'énergie spectrale et non sur la F0.

**Et pourquoi pas sur la F0 : elle se trompe d'octave.** `narrator_ch00_08` est mesuré à
400 Hz — la borne même du détecteur — alors que la moitié de son énergie est en 80-200 Hz.
Le clip est sain, c'est la mesure qui est fausse : l'autocorrélation attrape une
harmonique quand le fondamental est faible. La plage de 298 Hz encore affichée pour le
prologue vient entièrement de ce seul clip. **Ne pas juger un clip sur sa F0 seule.**

Après reprise (jusqu'à 4 graines, on garde le meilleur essai au sens de l'énergie) :
**9 clips sur 9 récupérés**, de 3,6 % à 71 %, de 17 % à 90 %. C'étaient donc bien des
accidents de génération, pas une fatalité du texte.

Réserve sur le critère lui-même : son seuil est **relatif à la médiane du lot**, donc
réparer les mauvais clips relève la médiane et resserre le seuil — un clip du prologue
(`narrator_ch01_01`, 29 %) est passé « douteux » après coup sans avoir bougé. Ce critère
ne converge pas vers zéro et ne doit pas être itéré jusque-là ; il sert à isoler les
accidents francs, pas à trier la queue de distribution.

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
