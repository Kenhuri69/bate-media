# Lot 11 — casting de Virion : le choix est presque vide, et c'est le sujet

**Rien n'est décidé ici.** Ce lot existe pour être écouté ; la mesure ne fait qu'écarter, elle ne
choisit pas. C'est la convention de la forge depuis le premier timbre d'Arthur.

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 7
```

## Pourquoi Virion est le troisième personnage à doubler

Ce n'est pas un choix d'affection, c'est un comptage sur les 367 timelines du jeu :

| voix | répliques | timelines |
|---|---|---|
| Arthur (`narrator` + `Note` + `Arthur`) | 10 332 | 366 |
| **Virion** (`Virion` + `Virion Eralith`) | **350** | **43** |
| Tessia (`Tessia` + `Tessia Eralith`) | 248 | 48 |
| Elijah | 232 | 30 |
| Reynolds | 206 | 34 |

Virion parle **plus que Tessia** et sur presque autant de chapitres. Il est déjà casté par le
récit : il ouvre au ch11 et tient jusqu'au ch239.

## Le vrai problème : il ne reste presque plus de voix d'homme

CustomVoice a neuf timbres premium, et c'est tout le choix contraint du modèle :

- **quatre féminins** — `serena`, `vivian`, `ono_anna`, `sohee` (ce dernier est Tessia) ;
- **deux dialectaux** — `eric`, `dylan`, déclarés sichuanais et pékinois dans la config du
  modèle. Ce sont eux qui produisaient les clips dégénérés en français : hors sujet ;
- **trois masculins utilisables** — `uncle_fu`, `ryan`, `aiden`. **Arthur en consomme deux**
  (`aiden:0.5+ryan:0.5`).

Le casting de Virion ne se joue donc pas sur « quel timbre lui va le mieux » mais sur « lequel ne
sera pas pris pour Arthur ». Dans un dialogue à deux voix, ne plus savoir qui parle est un défaut
de récit, pas de son — et ces deux-là dialoguent beaucoup.

D'où un critère que le casting de Tessia n'avait pas besoin de mesurer : la **distance au timbre
d'Arthur**, par cosinus des MFCC sur les MÊMES textes, aux mêmes graines.

## Mesures — 6 répliques réelles, réparties du ch11 au ch239

| timbre | F0 médiane | plage F0 | ambitus | proximité Arthur |
|---|---|---|---|---|
| `uncle_fu` | 175 Hz | **111 Hz** | 5,1 st | **0,949** |
| `ryan` | 155 Hz | 45 Hz | 7,1 st | 0,975 |
| `aiden` | 137 Hz | **21 Hz** | 4,3 st | 0,965 |

Proximité : 1,000 = timbre identique à celui d'Arthur. Plus la valeur est basse, mieux les deux
personnages se distinguent.

## Retenu : `uncle_fu:0.5+aiden:0.5` — et `uncle_fu` pur a été produit puis écarté

⚠️ **La proposition initiale de ce lot était `uncle_fu` pur, et elle était fausse.** Elle reposait
sur la seule distance à Arthur (0,949, la meilleure des trois). Les 350 clips produits dessus
l'ont démentie :

| | F0 médiane | plage interdécile |
|---|---|---|
| `uncle_fu` pur | **201,7 Hz** | **79 Hz** |
| `uncle_fu:0.5+aiden:0.5` | 130 Hz | 47 Hz |
| Tessia | 216 Hz | 56 Hz |
| Arthur (narration) | 119 Hz | 48 Hz |

À 201,7 Hz, Virion parle à 14 Hz de **Tessia**, sa petite-fille adolescente, avec qui il partage
toutes ses scènes de cour — et son lot était le plus dispersé des quatre voix du jeu. Le timbre
s'éloignait bien d'Arthur : *par le haut*, donc en atterrissant sur Tessia.

**La leçon est dans l'outil maintenant** : `casting_timbre.py` mesure la distance à TOUTES les
voix déjà castées et classe sur la *pire* proximité. Une distance à une seule référence ne mesure
pas la confusion, elle en déplace la cible.

Le balayage de doses donne `uncle_fu:0.5+aiden:0.5` : dispersion divisée par 1,7, registre
masculin franc, plus aucune collision avec Tessia. Ce qu'on perd, c'est la séparation d'avec
Arthur, qui ne passe plus par la hauteur (130 contre 119) mais par le timbre (0,963). Acceptable
ici et nulle part ailleurs : **Virion ne narre jamais**, et l'essentiel de la voix d'Arthur est de
la narration, dans un tout autre registre de jeu.

Ce dossier ne garde que le timbre retenu et les deux références, de quoi juger la confusion à
l'oreille. Les doses intermédiaires ont été retirées ; leurs mesures sont dans
`rapport_casting.json`.

`ryan` et `aiden` purs restent écartés, et pour une raison structurelle : ce sont les deux
composants du mélange d'Arthur. `aiden` revient ici comme correcteur de hauteur à dose limitée,
pas comme voix.

**Ce qui reste à ton oreille** : `uncle_fu:0.5+aiden:0.5` ne se confond-il pas avec Arthur ? La
mesure dit que la séparation tient par le timbre et non par la hauteur, et c'est précisément le
genre de chose qu'un cosinus de MFCC juge mal. Le timbre est marqué `valide: false` au manifeste
tant que ce n'est pas tranché.

## Ce que ce lot ne dit pas

Rien sur l'âge du personnage. Virion est un elfe de plusieurs siècles, et aucun des trois timbres
ne « sonne vieux » en soi. Le prompt d'âge ayant été mesuré sans effet au-delà du stade bambin
chez Arthur (lot 8), il n'y a pas lieu de compter dessus ici : ce qui portera son âge est
l'écriture de ses répliques et le registre de jeu, pas un réglage de synthèse.
