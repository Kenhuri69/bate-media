# Casting de Luna et Lise — deux voix qui se choisissent ensemble

Personnages originaux des trois arcs secondaires `loriande_awakening`, `xyrus_first_frost` et
`elven_dormitory` (fiche : `bate/notes/bible-luna-et-lise.md`). **70 répliques** :
Luna 27, Lise 43 — extraites le 2026-08-26 par
`tools/extraire_repliques.py bate-luna Luna` (idem `bate-lise Lise`).

## Pourquoi elles ne se castent pas séparément

Elles partagent la **totalité** de leurs scènes, et **Tessia est présente dans les trois arcs**
(31 répliques dans `xyrus_first_frost` seul). Il ne suffit donc pas que chacune soit loin de
Tessia : il faut aussi qu'elles soient loin **l'une de l'autre**, ce que la proximité aux
références ne dit pas — l'autre personnage n'est pas encore casté, donc pas dans la liste.
D'où la matrice candidat × candidat ajoutée à `casting_timbre.py`, lue sur les **mêmes textes
aux mêmes graines**, donc mesurant des timbres et non des phrases.

Contrainte de fond, la même que pour Virion côté masculin : CustomVoice n'a que **quatre
timbres féminins** utilisables, et trois personnages en service les occupent déjà
(Tessia `sohee` pur, Alice `vivian` pur, Sylvie `ono_anna:0.5+serena:0.5`). `sohee` est écarté
d'office — c'est la voix de Tessia, qui est dans toutes leurs scènes.

## Lot 14 — les timbres purs (8 répliques)

Sur les répliques de **Luna** :

| timbre | F0 | plage | ambitus | Tessia | Arthur |
|---|---|---|---|---|---|
| vivian | 226 Hz | 64 Hz | 3,8 st | **0,921** | 0,839 |
| ono_anna | 258 Hz | 44 Hz | 3,1 st | 0,949 | 0,890 |
| serena | 238 Hz | **23 Hz** | 3,1 st | 0,962 | 0,886 |

Sur celles de **Lise**, le même ordre : serena 27 Hz de plage / 0,960 de Tessia,
vivian 50 Hz / 0,914, ono_anna 49 Hz / 0,952. Deux têtes de série qui **ne gagnent pas sur le
même critère** — configuration du principe d'Arthur, donc balayage de doses et non duel.

## Lot 15 — balayage de doses (8 répliques)

| timbre | F0 | plage | ambitus | Tessia |
|---|---|---|---|---|
| vivian:0.7+serena:0.3 | 261 Hz | 74 Hz | 3,6 st | **0,891** |
| vivian:0.7+ono_anna:0.3 | 264 Hz | 73 Hz | 3,5 st | 0,895 |
| vivian | 226 Hz | 64 Hz | 3,8 st | 0,921 |
| serena:0.5+vivian:0.5 | 242 Hz | 51 Hz | 2,9 st | 0,942 |
| ono_anna | 258 Hz | 44 Hz | 3,1 st | 0,949 |
| serena:0.7+vivian:0.3 | 244 Hz | **32 Hz** | 3,1 st | 0,951 |
| serena | 238 Hz | 23 Hz | 3,1 st | 0,962 |

Lecture de l'époque : `serena:0.7+vivian:0.3` semblait le compromis (32 Hz de plage pour 0,951),
`vivian:0.7+serena:0.3` le plus distinct mais le plus dispersé.

## Lot 16 — LE MÊME BALAYAGE À 20 RÉPLIQUES, ET IL RÉORDONNE TOUT

C'est le piège déjà payé sur Sylvie, et il s'est reproduit à l'identique : **un échantillon de
huit répliques ne mesure pas une dispersion**, il la sous-estime pour tout le monde — donc il
réordonne les candidats.

Sur les 20 répliques de **Lise** :

| timbre | F0 | plage (8 rép.) | plage (20 rép.) | ambitus | Tessia |
|---|---|---|---|---|---|
| **vivian:0.7+serena:0.3** | 242 Hz | 74 | **41 Hz** | **3,6 st** | **0,921** |
| serena | 229 Hz | 27 | 41 Hz | 3,4 st | 0,939 |
| serena:0.7+vivian:0.3 | 247 Hz | 32 | **62 Hz** | 3,2 st | 0,944 |

Sur les 20 répliques de **Luna** :

| timbre | F0 | plage | ambitus | Tessia | distance à la Lise retenue |
|---|---|---|---|---|---|
| vivian:0.7+serena:0.3 | 255 Hz | 72 Hz | 3,6 st | 0,885 | — |
| serena:0.5+vivian:0.5 | 264 Hz | 72 Hz | 3,2 st | 0,920 | 0,947 |
| **ono_anna** | 257 Hz | **56 Hz** | 3,2 st | **0,926** | **0,926** |
| serena | 238 Hz | 67 Hz | 3,0 st | 0,953 | 0,930 |

Le « compromis » du lot 15 est **le pire** des trois à 20 répliques (62 Hz contre 32), et
`serena`, le plus stable du casting (23 Hz), sort à 41 puis 67 Hz. Ce qui domine à 20 répliques
n'était pas identifiable à 8.

## Lots 18 et 19 — AUCUN TIMBRE PUR : la contrainte qui change le couple

Verdict d'Olivier sur le premier couple proposé (Luna `ono_anna` pur) : « je ne veux pas de
voix pure ». Deux purs sont déjà en service (Tessia `sohee`, Alice `vivian`) et c'est assez —
un pur consomme un timbre entier et rapproche mécaniquement des voix qui l'utilisent en
mélange. Balayage refait, toujours sur 20 répliques réelles.

**Luna** (lot 18, ses 20 répliques ; dilution minimale 50 % pour la majoritaire) :

| timbre | F0 | plage | ambitus | Tessia |
|---|---|---|---|---|
| **ono_anna:0.8+vivian:0.2** | 257 Hz | **61 Hz** | 3,1 st | **0,920** |
| ono_anna:0.7+serena:0.3 | 267 Hz | 64 Hz | 2,9 st | 0,928 |
| ono_anna:0.5+serena:0.5 | 257 Hz | 72 Hz | 3,3 st | 0,927 |
| ono_anna:0.7+vivian:0.3 | 257 Hz | 82 Hz | 2,7 st | 0,918 |

**Lise** (lot 19, ses 20 répliques). Et il a fallu le refaire pour une raison qui n'existait pas
la veille : `vivian:0.7+serena:0.3`, que la mesure désignait pour elle, **est le timbre
d'Ellie** — et la correction de `descendre()` venait de monter Ellie de deux demi-tons, à
270 Hz, c'est-à-dire juste au-dessus de la Lise proposée. Deux voix à 0,970 de cosinus et 28 Hz
d'écart : la collision était nouvelle, créée par la réparation d'à côté.

| timbre | F0 | plage | ambitus | Tessia | distance à Luna |
|---|---|---|---|---|---|
| **vivian:0.8+ono_anna:0.2** | 262 Hz | **39 Hz** | **3,7 st** | **0,903** | 0,953 |
| vivian:0.7+serena:0.3 (= Ellie) | 242 Hz | 41 Hz | 3,6 st | 0,921 | 0,958 |
| vivian:0.5+ono_anna:0.5 | 243 Hz | 46 Hz | 3,6 st | 0,929 | 0,983 |
| vivian:0.7+ono_anna:0.3 | 250 Hz | 87 Hz | 3,6 st | 0,916 | 0,959 |

Éviter le timbre d'Ellie coûte **0,006** de distance mutuelle (0,953 contre 0,947) et rapporte
sur les trois autres colonnes. Aucun arbitrage à faire là non plus.

## La hauteur, et pourquoi elle n'est pas un détail ici

Les deux retenus sortent à **262 et 265 Hz** : leur cosinus de 0,953 ne suffira pas si elles
parlent à la même hauteur, et elles ne se quittent pas. Luna est l'aînée posée, c'est elle qui
descend — mais pas trop : Tessia est à 213 Hz et c'est l'autre voix à ne pas confondre.

| | F0 |
|---|---|
| Tessia (sohee) | 213 Hz |
| Luna −3 st | 223 Hz — trop près de Tessia |
| **Luna −2 st** | **237 Hz** — 24 Hz sous Lise, 24 au-dessus de Tessia |
| Luna −1 st | 250 Hz — 12 Hz de Lise, indistinguable |
| Luna sans décalage | 265 Hz — 3 Hz de Lise |
| Lise (sans décalage) | 262 Hz |
| Ellie (livrée, montée de 2 st) | 270 Hz |

`Tessia 213 < Luna 237 < Lise 262 < Ellie 270` place les quatre voix féminines jeunes du jeu
sans en coller deux. C'est ce que la mesure propose ; l'oreille tranche
(`bash docs/ecoute-qwen3-tts/ecouter.sh 10`).

## Ce que la mesure désignait au tour précédent (Luna en pur, écarté)


- **Lise = `vivian:0.7+serena:0.3`** : elle domine ses deux rivales sur son propre matériau —
  plage la plus basse (41 Hz, à égalité), ambitus le plus haut (3,6 st, et c'est le personnage
  bavard et frontal), et la plus éloignée de Tessia (0,921). Aucun arbitrage à faire.
- **Luna = `ono_anna` pur** : plage la plus basse (56 Hz), deuxième plus éloignée de Tessia
  (0,926) — et surtout **la plus éloignée de la voix de Lise** de toute la matrice (0,926).

Un point que la mesure **ne** tranche pas : la hauteur. Tessia 213 Hz, Luna 257, Lise 242 —
c'est-à-dire la **cadette vive en dessous de l'aînée posée**, et seulement 15 Hz entre elles.
Ce tour-là a été dépassé par la contrainte suivante (aucun timbre pur), et ses clips
d'écoute ont été retirés — seuls restent ceux de la décision en vigueur.

## Un défaut trouvé en préparant ce lot : `descendre()` ne montait pas

`descente_voix.descendre()` commençait par `if demi_tons <= 0: return onde`. Trois personnages
déclarent pourtant une valeur **négative** en annonçant l'inverse en commentaire — `angela`
(−2, « +2st pour un registre plus aigu/venté »), `ellie` (−2) et `adam` (−1). Leurs **121 clips
en service ne portent donc aucun décalage**, et rien ne pouvait le signaler : la fonction
rendait l'onde intacte au lieu de refuser.

Corrigé le 2026-08-26, et prouvé par valeur extrême sur un signal de synthèse à 200 Hz :
`−12` rend 400 Hz, `+12` rend 100 Hz, durée tenue à 1,000 s dans les deux sens.

**Conséquence à trancher avant toute reprise sur ces trois voix** : leur regénération
appliquerait désormais le décalage, ce qui ferait entendre deux voix différentes dans le même
lot. Les 5 clips douteux d'`ellie` ont été laissés de côté pour cette raison.

## La remise à niveau des trois voix (décision d'Olivier, 2026-08-26)

Arbitrage rendu : refaire les 121 clips avec le décalage promis, plutôt que d'aligner le code
sur ce qui était livré. Les clips d'avant sont conservés dans `scratch/avant-shift-hauteur/`.

**La preuve que le décalage agit désormais** est dans la cible d'énergie mesurée sur le lot :
angela passe de 216 à 242 Hz, soit exactement 216 × 2^(2/12) = 242,5. Elle ne pouvait pas
bouger tant que la fonction rendait l'onde intacte.

| voix | décalage | douteux d'énergie après livraison | après reprise |
|---|---|---|---|
| ellie | +2 st (249 → 270 Hz) | **21/82 (25,6 %)** | 6/82 (7,3 %) |
| adam | +1 st (cible 205 → 217 Hz) | 2/28 | 0/28 |
| angela | +2 st (216 → 242 Hz) | 0/11 | 0/11 |

Deux choses à retenir de ces chiffres :

- **monter une voix disperse son énergie.** Le lot d'ellie est sorti à 25,6 % de douteux
  (contre 6,1 % avant la montée) et sa médiane d'énergie est tombée de 50 à 38 %. La reprise
  l'a ramenée à 49 % et 7,3 % — soit l'état d'avant, mais il a fallu refaire 21 clips en plus
  des 82. Un décalage n'est pas gratuit, même appliqué à durée constante ;
- **la cible écrite en dur doit suivre le décalage.** `adam` déclarait 205 Hz, étalonnés sur un
  lot qui n'avait jamais été monté. Laissée telle quelle, elle aurait fait chercher l'énergie
  une seconde mineure sous la voix et signalé des clips sains — le piège exact déjà payé sur
  les narrations d'Arthur et sur la descente de Virion. Corrigée à 217 Hz.

Côté texte, la montée n'a rien coûté : ellie 11 → 12 suspects ASR (dont 3 réels, 2 réparés),
adam 1 → 0, angela 0 → 0. Le seul récalcitrant est `ellie_3c4ff99fae` (« TU. ES. EN. RETARD. »),
que le transcripteur rend « T-E-S-N, retard » — un texte en capitales détachées, pas un clip
abîmé.
