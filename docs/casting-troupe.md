# Doubler 119 personnages avec 4 timbres féminins et 3 masculins

Demande du 2026-08-26 : « on finalise les personnages des 100 premiers chapitres, on ajoute les
voix sur les chapitres secondaires, on ajoute les voix sur les mini-jeux et interactions de
combat, on rend le tout vivant ». Puis, sur la contrainte de timbres : « utilise un maximum de
couplage de voix, monte 3 mix si nécessaire plus timbre grave et où aigu, sois inventif pour
maximiser les voies ».

## Le périmètre, mesuré et non supposé

| | personnages | clips à produire |
|---|---|---|
| chapitres 1 à 100 | 102 dont 88 muets | 1 676 |
| 12 arcs secondaires | 30 muets | 552 |
| **total après regroupement** | **119** | **2 228** |

Les mini-jeux et le combat n'avaient **aucun texte de réplique** — huit messages de journal
(« Aucun objet à utiliser. ») et rien d'autre. Ce volet est traité à part :
[`combat-barks.md`](#le-combat) plus bas.

## Trois axes de distinction, et deux étaient inexplorés

CustomVoice expose **quatre timbres féminins et trois masculins**. Les quinze voix en service
n'utilisaient qu'un seul levier — le mélange de deux timbres — et parfois un décalage de hauteur.
Deux axes dormaient :

1. **les mélanges à trois et quatre composants.** `_parse_timbre` les accepte depuis toujours (il
   boucle sur `split("+")` et `_vecteur_timbre` en fait une somme pondérée). Personne ne les avait
   essayés, non parce qu'ils échouent — parce que personne ne l'avait demandé ;
2. **le débit.** WSOLA change la durée sans toucher au fondamental : c'est déjà lui qui rend sa
   durée à une voix descendue. Deux personnages au même timbre et à la même hauteur restent
   distincts s'ils ne parlent pas à la même vitesse, et c'est même le premier indice qu'une
   oreille attrape dans un échange à deux voix.

Aucun des deux ne coûte un appel au modèle : un mélange généré une fois se décline en
7 décalages × 3 débits, soit **21 voix pour le prix d'une**.

## Ce que l'espace donne réellement — `catalogue_voix.py`

L'outil produit chaque mélange sur un échantillon commun (six répliques de figurants, celles que
ces voix auront à dire), décline décalages et débits sans repasser par le modèle, mesure tout
(F0, plage, ambitus, MFCC) et sélectionne un ensemble mutuellement distinct, les voix déjà en
service étant des points fixes.

Deux voix comptent pour distinctes si leur timbre diffère (cosinus ≤ 0,955), **ou** leur hauteur
(≥ 18 Hz), **ou** leur débit (≥ 8 %). Les deux premiers seuils sont calibrés sur des paires
réelles : Luna/Lise à 0,953 a été accepté à l'oreille, Lise/Ellie à 0,970 refusé. **Le troisième
ne l'est pas** — c'est une réserve, écrite ici et dans le code.

| genre | variantes mesurées | places sans le débit | places avec |
|---|---|---|---|
| masculin | 644 | 14 | **44** |
| féminin | 1 659 | 7 | 7 (l'axe n'ouvre rien) |

Le débit triple l'espace masculin et **n'apporte rien côté féminin**. Vingt candidates féminines
ont ensuite été testées une à une (`attribuer_voix.py`), réparties sur tout le registre —
190 à 300 Hz, mélanges à deux, trois et quatre composants, les trois débits : **quatorze ont été
refusées pour proximité** avec l'une des 33 voix féminines déjà en service. Six places, et pas une
de plus. Quatre timbres féminins ne font pas quarante voix ; c'est un plafond, pas un manque de
zèle.

## La règle retenue

**Voix propre au-dessus de trente répliques, archétype de troupe en dessous.** Chaque personnage
garde la même voix du premier au dernier chapitre — c'est la seule chose qui ne se négocie pas,
parce qu'un figurant qui change de timbre entre deux scènes se lit comme un bug, alors que deux
figurants qui partagent un timbre passent inaperçus. C'est la pratique du doublage : les petits
rôles sont tenus par les mêmes comédiens.

Les douze archétypes sont pris **tels quels** dans les places mesurées, en écartant celles dont la
plage dépassait 60 Hz — leçon payée sur Sylvie, dont un lot livré à 98 Hz de dispersion avait dû
être refait.

| archétype | timbre | F0 | personnages |
|---|---|---|---|
| m_grave | `aiden:0.8+uncle_fu:0.2` +2 st | 136 Hz | 16 |
| m_pose | `aiden:0.5+uncle_fu:0.3+ryan:0.2` −3 st | 151 Hz | 15 |
| m_clair | `aiden:0.8+uncle_fu:0.2` −3 st | 179 Hz | 5 |
| m_rugueux | `uncle_fu:0.65+ryan:0.35` +1 st | 180 Hz | 6 |
| m_quelconque | `uncle_fu:0.8+aiden:0.2` | 188 Hz | 18 |
| m_jeune | `uncle_fu:0.65+ryan:0.35` −2 st | 211 Hz | 11 |
| f_autorite | `sohee:0.65+serena:0.35` +3 st | 176 Hz | 9 |
| f_mure | `serena:0.4+vivian:0.4+sohee:0.2` +3 st | 216 Hz | 4 |
| f_adulte | `serena:0.4+vivian:0.4+sohee:0.2` +1 st | 243 Hz | 5 |
| f_jeune | `ono_anna:0.65+vivian:0.35` −2 st | 268 Hz | 2 |
| f_claire | `serena:0.5+sohee:0.3+ono_anna:0.2` −3 st | 289 Hz | 1 |
| f_enfant | `ono_anna:0.8+sohee:0.2` −3 st | 298 Hz | 2 |

Le registre vit dans `resources/casting_troupe.json` et se régénère ; `voix_personnage.py` le
charge en plus de son dict écrit en code, sans jamais écraser une voix castée. Les quinze
décisions argumentées restent lisibles dans le code, les quatre-vingt-treize attributions
mécaniques sont des données.

## Le genre ne s'invente pas

Trois niveaux, du plus sûr au plus faible, et le premier qui parle décide : le **libellé**
(« Doyenne », « Roi nain » — le mot EST la preuve), un **motif accordé** dans les timelines
(« la directrice Goodsky », « Rinia, elle »), puis un **vote** entre le prénom et le pronom qui
suit les mentions du nom. Chaque fiche déclare la méthode employée.

Le troisième niveau a été ajouté après mesure : sans lui, **77 personnages sur 113** restaient
indéterminés et la répartition par défaut les envoyait tous sur des voix masculines — Charlotte,
Mary et Samantha comprises. Avec lui, il en reste 19, et les personnages féminins sont dans des
archétypes féminins. Un indice déclaré vaut mieux qu'un défaut silencieux.

## Le contrat de rôle était faux pour 18 personnages

Le jeu déduit le dossier de voix du **premier mot** du locuteur. Conséquence comptée sur les
timelines : les six professeurs de l'Académie tombaient tous dans `professeur/`, trois silhouettes
dans `le/`, deux dans `l/`. Un doublage **faux**, pas seulement muet — le clip de Glory aurait été
joué pour Geist. Et l'inverse existait aussi : « Directrice Goodsky » vivait dans un autre dossier
que « Goodsky », donc la moitié de ses répliques serait restée muette quel que soit le lot produit.

Table explicite `LOCUTEURS` ajoutée **des deux côtés** — `tools/empreinte.py` et
`bate/src/systems/audio/VoiceLines.cs` — parce que le contrat est implémenté deux fois et que rien
à l'exécution ne signale une divergence. Plus un contrôle dans `empreinte.py --selftest` qui
refuse toute collision résiduelle : 156 dossiers, zéro collision, et **validé par sabotage** —
retirer une entrée fait rougir le test.

Piège évité de justesse au passage : ma première version faisait porter le dossier à
l'identifiant du clip, ce qui renommait les 7 914 clips `narrator_*` d'Arthur. L'identifiant dit
QUI parle, le dossier dit quelle voix le dit. Rattrapé par le test C# du contrat partagé.

## Le combat

Trente-trois répliques génériques (`bate/resources/combat_barks.json`), une seule voix `Ennemi`
— premier mélange à trois timbres du dépôt — et le registre change par catégorie : l'ouverture en
`dialogue`, le coup critique en `peur`, la chute en `emu`. Quatre déclencheurs câblés dans
`CombatScreen` : ouverture une fois sur deux, coup encaissé une fois sur trois, critique toujours,
agonie sous 25 % des PV, chute.

Aucun code audio nouveau : `AudioManager.PlayVoice("Ennemi", ligne)` existait déjà et le contrat
d'empreinte faisait le travail. La couche de tirage est pure et testée (7 tests), dont un qui lit
la ressource réelle — sans lui, une catégorie renommée laisserait le combat muet sans qu'un test
rougisse.

## Ce qui reste ouvert

- **Quatre personnages féminins partagent** une voix d'archétype, faute de place : Rinia
  (`f_autorite`, et c'est son registre), Nima (`f_mure`), Tabitha (`f_adulte`), Emily (`f_jeune`).
- **Le seuil de débit à 8 % n'est pas calibré à l'oreille.** Trente des quarante-quatre places
  masculines ne tiennent que par lui.
- **La paire la plus serrée est Perrin 181 Hz / Elijah 190 Hz**, et tous deux sont camarades de
  classe d'Arthur donc présents dans les mêmes scènes. À écouter en premier.
- Le locuteur du Comité s'appelle `Committee`, en anglais, et c'est ce que Dialogic affiche.
