# Lot 11 — casting de Sylvie : une dispersion ne se compare pas à l'aveugle

**Rien n'est validé ici.** Le timbre retenu l'a été par la mesure ; il est marqué
`valide: false` au manifeste tant que l'oreille n'a pas tranché.

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 8
```

## Sa référence est Tessia, pas Arthur

Sylvie est la quatrième voix du jeu, avec **107 répliques sur 52 timelines** (ch17 → ch249). Le
risque de confusion n'est pas avec Arthur — une voix de bête liée juvénile ne se prend pas pour
celle du narrateur — mais avec **Tessia** : deux voix féminines jeunes, et elles partagent la
plupart de leurs scènes. C'est donc contre elle que la distance est mesurée en premier.

`sohee` est hors jeu, c'est le timbre de Tessia. Restent `serena`, `vivian` et `ono_anna`.

## Le premier verdict était faux, et pour une raison instructive

Sur l'échantillon de casting, `vivian:0.7+serena:0.3` gagnait franchement — plage 66 Hz, distance
à Tessia 0,866, meilleur que ses deux composants. Les **111 clips produits dessus sont sortis à
98 Hz de plage**, le double des autres voix du jeu, avec 10 déclenchements du garde-fou
anti-dégénérescence contre 0 pour Tessia et Virion. Écarté.

Rebalayer sur 20 répliques au lieu de 6 n'a pas suffi à corriger l'écart : le lot livré sur le
timbre suivant sortait encore à 84 Hz contre 57 annoncés. **Ce n'est donc pas un problème de
taille d'échantillon, mais de biais de sélection** — le lot d'audition choisit délibérément les
répliques les *plus longues*, sans quoi la F0 n'est pas mesurable.

Mesuré sur les quatre voix, l'effet est général et il est grand :

| | répliques < 40 car. | répliques ≥ 90 car. |
|---|---|---|
| Sylvie | 92 Hz | 57 Hz |
| Tessia | 59 Hz | 38 Hz |
| Virion | 60 Hz | 40 Hz |

Une F0 médiane sur deux secondes repose sur trop peu de trames voisées. Or Sylvie a **48 % de
répliques de moins de 40 caractères** contre 11 % à Virion : c'est une bête liée, elle dit
surtout des choses brèves. Une bonne part de sa dispersion tient à son matériau et non à son
timbre — continuer à balayer des doses reviendrait à optimiser un artefact de mesure.

**Règle qui en sort : ne jamais comparer deux timbres sur des plages brutes.** Soit on borne à
une tranche de longueur commune, soit on ne s'en sert que pour classer des candidats sur le même
échantillon.

## Retenu : `ono_anna:0.5+serena:0.5`

Mesures à 20 répliques, contre les deux références :

| timbre | F0 | plage | proximité Tessia | proximité Arthur |
|---|---|---|---|---|
| **`ono_anna:0.5+serena:0.5`** | 258 Hz | **57 Hz** | **0,922** | 0,842 |
| `serena` pur | 244 Hz | 56 Hz | 0,942 | 0,859 |
| `vivian:0.3+serena:0.7` | 253 Hz | 62 Hz | 0,932 | 0,849 |
| `vivian:0.5+serena:0.5` | 242 Hz | 75 Hz | 0,932 | 0,848 |

Il **domine** : aussi stable que le plus stable, et le plus éloigné de Tessia. Il n'y a pas
d'arbitrage à faire, donc pas de regret à avoir — ce qui n'était vrai ni pour Arthur (où le
mélange gagnait au prix d'un compromis) ni pour Tessia (où le pur gagnait).

Ce dossier ne garde que le timbre retenu et les deux références, de quoi juger la confusion à
l'oreille. Les doses écartées vivent dans `rapport_casting.json`.

## Ce qui reste à ton oreille

Sylvie parle de deux façons dans les timelines : **entre parenthèses** (télépathie, 35 répliques)
et hors parenthèses (72). Le pack ne fait aucune différence entre les deux — même timbre, même
registre. Si l'écoute demande de les distinguer, c'est un travail de mixage, comme l'écart
parole / pensée d'Arthur, pas un second casting.
