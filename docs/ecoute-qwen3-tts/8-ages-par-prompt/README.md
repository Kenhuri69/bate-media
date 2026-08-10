# Lot 8 — les âges d'Arthur par le prompt : deux voix, pas cinq âges

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 4
```

Le lot 7 avait établi le principe sur un seul stade : l'âge se fait par le **prompt**, pas en
diluant le timbre validé. Ce lot-ci l'étend aux six stades que traverse Arthur sur les ch0-60,
parce qu'il fallait le faire avant de produire 4433 répliques.

## ⚠️ Une première version de ce document concluait l'inverse, et elle était fausse

Elle disait : « au-delà du stade bambin, le prompt d'âge ne contrôle plus la hauteur ». **Cette
conclusion venait d'un estimateur de F0 qui divise le fondamental par deux.** Sur les répliques
parlées, l'autocorrélation rendait ~140 Hz alors que 3 à 6 % seulement de leur énergie vocale se
trouve sous 110 Hz.

Le dépôt le disait pourtant déjà, dans ce même dossier : *« le contrôle se fait sur l'énergie
spectrale, pas sur la F0, qui se trompe d'octave »*. Tous les chiffres en hertz issus de ce banc
— les apports +48/−6/+4/−21/+17, les paliers 167/158/144/149/137, les 139 contre 140 du lot
livré — sont des artefacts. Ils sont retirés, pas corrigés : il n'y a rien à en sauver.

L'erreur était invisible : 140 Hz est une valeur plausible pour une voix masculine, et elle
était stable d'un stade à l'autre. Une mesure fausse qui ne signale rien.

## Ce que dit la mesure d'énergie, la seule fiable ici

**Barycentre spectral**, sur **tous** les clips livrés — pas un échantillon, pas de F0. C'est la
mesure de référence désormais : un profil par bandes marche aussi, mais son « pic » bascule d'un
tirage à l'autre parce que les distributions sont larges et plates. L'intervalle est à 95 %.

| stade | âge | rôle | clips | barycentre | IC95 |
|---|---|---|---|---|---|
| `prologue` | King Grey | narration | 39 | 195 Hz | ±18 |
| `s02_toddler` | 3 ans | **Arthur parlé** | 23 | **289 Hz** | ±39 |
| `s02_toddler` | 3 ans | narration | 134 | 209 Hz | ±14 |
| `s03_road` | 5 ans | **Arthur parlé** | 221 | **294 Hz** | ±13 |
| `s03_road` | 5 ans | narration | 645 | 214 Hz | ±7 |
| `s03_child` | 6 ans | **Arthur parlé** | 107 | **308 Hz** | ±20 |
| `s03_child` | 6 ans | narration | 602 | 213 Hz | ±8 |
| `s04_teen` | 13 ans | **Arthur parlé** | 272 | **292 Hz** | ±12 |
| `s04_teen` | 13 ans | narration | 868 | 212 Hz | ±6 |
| `s05_academy` | 15 ans | **Arthur parlé** | 31 | **299 Hz** | ±26 |
| `s05_academy` | 15 ans | **« Note » parlé** | 467 | **301 Hz** | ±8 |
| `s05_academy` | 15 ans | narration | 1024 | 213 Hz | ±6 |

Trois choses s'y lisent, et elles sont nettes.

**1. Le prompt d'âge fonctionne.** 289-308 Hz en parlé contre 209-214 en narration : 80 à 95 Hz
d'écart, dix fois les intervalles de confiance. C'est bien le fondamental qui monte et non la
brillance — sous 110 Hz il ne reste que 3 à 6 % de l'énergie des répliques parlées, contre 12 à
20 % en narration.

**2. Les stades ne se distinguent pas entre eux.** 289 ±39, 294 ±13, 308 ±20, 292 ±12, 299 ±26 :
tous les intervalles se recouvrent, et l'ordre n'est même pas celui des âges. Un garçon de quinze
ans sort au même endroit qu'un enfant de trois ans.

**3. La narration est remarquablement stable** : 209, 214, 213, 212, 213 Hz sur **3273 clips**,
à ±6-14. La décision « une seule voix de narrateur sur tout le jeu » est tenue à la mesure, ce
qui n'allait pas de soi sur un corpus de cette taille. Le prologue s'en écarte de peu, vers le
bas (195 ±18) — c'est le seul lot sans prompt d'âge, et c'est King Grey : conforme à l'intention.

**4. Le regroupement des rôles tient.** « Note », le pseudonyme d'aventurier d'Arthur, sort à
301 Hz ±8 sur 467 clips, contre 299 ±26 pour ses répliques sous son propre nom dans le même
stade. Les deux se superposent : le personnage ne change pas de voix en changeant de nom, ce que
la table de `pipeline-voix.md` postulait sans l'avoir jamais vérifié à cette échelle.

Le témoin — mêmes répliques, mêmes graines, sans la consigne d'âge — le confirme au barycentre
spectral, grandeur insensible aux erreurs d'octave :

| stade | sans prompt | avec prompt | apport |
|---|---|---|---|
| `s02_toddler` | 260 Hz | 287 Hz | **+28** |
| `s03_road` | 329 Hz | 354 Hz | **+25** |
| `s03_child` | 308 Hz | 331 Hz | **+23** |
| `s04_teen` | 281 Hz | 321 Hz | **+40** |
| `s05_academy` | 328 Hz | 313 Hz | −15 |

## Ce qui ne marche pas : distinguer les stades ENTRE EUX

Les trois lots parlés ont le même profil spectral à un point près. Arthur a **deux voix** —
parlée jeune, narrée posée — et non cinq âges. Le stade `s05_academy` est le seul dont le prompt
va dans l'autre sens (−15 Hz), ce qui est cohérent avec son intention (une voix de quinze ans)
mais ne suffit pas à le séparer des autres.

Séparer trois ans de six ans demanderait un levier que le prompt n'a pas. Le seul connu est la
**dilution du timbre** dans une composante plus aiguë — refusée le 2026-08-08 parce qu'elle ne
laissait que 20 % de `aiden:0.5+ryan:0.5`, et qu'une validation porte sur une voix entendue, pas
sur une formule qui en garde le nom.

**La question posée à l'écoute est donc celle-ci : deux voix suffisent-elles pour un personnage
qui va de trois à quinze ans, ou faut-il rouvrir le dossier de la dilution ?** Ce n'est pas à la
mesure d'y répondre.

## Les formulations retenues

Chaque stade a été comparé sur trois familles de formulation (`sobre`, `insistant`, `intense`),
sur ses propres répliques. Ce qui est en service, par stade, est dans `PROMPTS_AGE`
(`tools/voix_age_arthur.py`) ; les clips de ce dossier sont ceux de la variante retenue, aux
mêmes graines que la production. **Les commentaires de ce code renvoyaient aux hauteurs F0 : ils
sont à relire avec la présente correction en tête** — le classement entre familles reposait lui
aussi sur la F0 et n'a pas été rejugé sur l'énergie.

La cohésion de timbre, elle, ne dépend pas de la F0 et reste excellente : **0,92 à 0,99** selon
les stades. Ce n'est pas la voix d'Arthur qui vacille.

## Mesures brutes

[`rapport_ages.json`](rapport_ages.json) (avec prompt),
[`rapport_temoin.json`](rapport_temoin.json) (sans),
[`formulations/rapport_formulations.json`](formulations/rapport_formulations.json) (les trois
familles). **Leurs champs `f0_median` et `f0_plage` sont affectés par l'erreur d'octave** ; les
champs de cohésion et de durée ne le sont pas.

Outils : [`../../tools/voix_age_arthur.py`](../../tools/voix_age_arthur.py) (`produire`,
`temoin`, `bilan`) et
[`../../tools/age_par_prompt_stades.py`](../../tools/age_par_prompt_stades.py).
