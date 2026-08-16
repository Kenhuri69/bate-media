# Pack de voix 0.6.0 — quatre voix, une par personnage, la même d'un bout à l'autre

**8 228 clips, 543 Mo.** Quatre voix au lieu de deux, la déclinaison par âge retirée, et les
38 timelines d'histoires secondaires doublées pour la première fois.

| voix | clips | timbre | périmètre |
|---|---|---|---|
| Arthur (`narrator`+`Note`+`Arthur`) | 7 532 | `aiden:0.5+ryan:0.5` | ch0-150 + arcs |
| Virion | 350 | `uncle_fu:0.5+aiden:0.5` | intégral |
| Tessia | 247 | `sohee` | intégral |
| Sylvie | 99 | `ono_anna:0.5+serena:0.5` | intégral |

**Les chapitres 151 à 321 sont volontairement reportés.** Les histoires secondaires, elles, ne
portent aucun numéro de chapitre : elles échappent à cette borne par construction, et c'est
délibéré — c'est le contenu qui n'avait jamais eu une seule voix.

## Ce qui change

**La voix ne varie plus dans le temps.** Arthur portait un prompt d'âge par stade sur ses
répliques parlées ; il est retiré. Une voix par personnage, du premier chapitre au dernier.

Ce n'est pas un renoncement mais l'application de ce que la mesure disait déjà en 0.4.0 : le
prompt d'âge ne crée un registre distinct qu'au stade bambin (+48 Hz à trois ans), et **les
stades ne se distinguent pas entre eux** — au-delà, les formulations essayées apportaient −6,
+4, −21 et +17 Hz, du bruit, signes compris. Arthur avait deux voix, pas cinq âges ; il en a
désormais une, plus la distinction parole / pensée.

**Le périmètre passe des chapitres 0-60 au jeu entier**, histoires secondaires comprises.

| | 0.5.0 | 0.6.0 |
|---|---|---|
| Arthur | 4 401 | **7 532** |
| Tessia | 114 | **247** (100 %) |
| Virion | — | **350** (100 %) |
| Sylvie | — | **99** (100 %) |
| timelines couvertes | 61 | **335** dont 38 arcs secondaires |

## Trois défauts trouvés en chemin, tous silencieux

**Les histoires secondaires n'existaient pas pour la forge.** L'extraction faisait un
`glob("*.dtl")` non récursif : `dialogues/side/` n'a jamais été lu. 547 répliques d'Arthur et
16 de Tessia n'ont jamais réclamé un clip, et aucun contrôle ne pouvait le dire — un manque ne
se signale que si quelque chose le réclame. Pire, `migrer_empreintes.py` balayait le même
dossier de la même façon : les clips de ces répliques auraient été comptés **caducs** et
supprimés à chaque reconstruction du manifeste.

**Tessia perdait 21 répliques sur son propre nom.** Elle parle sous `Tessia` et sous
`Tessia Eralith` dans les scènes de cour. La forge cherchait le nom EXACT, le jeu résout le
dossier de voix sur le PREMIER MOT (`VoiceLines.Role`) : deux règles différentes, donc un jeu qui
réclamait 21 clips que rien ne produisait. Même cause pour Virion (29 répliques).

**Une reprise regénérait tout le lot.** Les clips naissaient sous un identifiant de forge
(`arthur_ch11_02`) puis étaient renommés par empreinte. Relancer une livraison cherchait donc des
fichiers qui n'existaient plus sous ce nom-là et reproduisait l'intégralité du lot — dix-huit
heures pour refaire ce qui était déjà bon. Le clip naît maintenant directement sous son nom
définitif.

## La pensée passe sous la parole

Le jeu est narré à la première personne : `narrator`, c'est Arthur qui se raconte, même voix et
même timbre que lorsqu'il parle. Rien ne les distinguait à l'oreille.

Mesuré au RMS sur 900 clips du pack en service : la narration sort déjà **1,5 dB** sous les
répliques parlées, effet de bord du registre de synthèse. Trop peu pour s'entendre comme une
intention. La convention porte l'écart à **3 dB**.

**L'écart est au mixage, jamais cuit dans les fichiers** (`VoiceLines.ThoughtGainDb`, bloc
`mixage` du manifeste). Le cuire dans les `.ogg` demanderait de regénérer 10 000 clips pour
changer d'avis d'un décibel.

## Le contrôle qualité de Tessia

247 clips, 0 relance à la génération, **21 douteux (8,5 %) au contrôle d'énergie, 20 récupérés**
par régénération sur d'autres graines. Un seul reste sous le seuil.

L'étalonnage des cibles de contrôle a lui-même été corrigé : le critère « maximiser l'énergie
captée dans la bande » est biaisé, la bande `[0,6·c ; 1,4·c]` s'élargissant avec la cible. Il
« retenait » 340 Hz pour Tessia (dont la F0 mesurée est 217) — c'est-à-dire la bande la plus
large avant de sortir de la voix. Normalisé par la largeur de bande, il redonne les valeurs déjà
validées à l'oreille : 205 Hz pour le parlé d'Arthur, 132 pour sa narration.

## Le troisième personnage : Virion, et un choix presque vide

Virion parle **350 fois sur 43 timelines** — plus que Tessia (248). C'est le récit qui le
désigne, pas une préférence.

Mais CustomVoice n'a que **trois timbres masculins utilisables** et Arthur en consomme deux
(`aiden:0.5+ryan:0.5`). Le casting ne se joue donc pas sur « quel timbre lui va » mais sur
« lequel ne sera pas pris pour Arthur ».

**Le premier verdict était faux, et la production l'a démenti.** `uncle_fu` avait été retenu
parce qu'il maximisait la distance à Arthur (0,949 au cosinus des MFCC). Ses 350 clips sont
sortis à **201,7 Hz de F0 médiane** — soit 14 Hz de Tessia, sa petite-fille adolescente, avec qui
il partage toutes ses scènes de cour — et à **79 Hz de dispersion**, le pire lot des quatre voix.
Il s'éloignait bien d'Arthur : par le haut, donc en atterrissant sur Tessia.

Leçon retenue et corrigée dans l'outil : **une distance à une seule référence ne mesure pas la
confusion, elle en déplace la cible.** `casting_timbre.py` mesure désormais contre toutes les
voix déjà casées et classe sur la PIRE proximité.

Le balayage de doses contre les deux références donne `uncle_fu:0.5+aiden:0.5` : dispersion
ramenée de 79 à 47 Hz, F0 à 130 — registre masculin franc, plus aucune collision avec Tessia. Ce
qu'on perd est la séparation d'avec Arthur, qui ne passe plus par la hauteur mais par le timbre.
Acceptable ici et nulle part ailleurs : Virion ne narre jamais, et l'essentiel de la voix
d'Arthur est de la narration, à 119 Hz et dans un tout autre registre de jeu.

## Sylvie, et pourquoi une dispersion ne se compare pas à l'aveugle

Même piège, deux fois de suite. Le casting donnait `vivian:0.7+serena:0.3` gagnant (plage 66 Hz) ;
les 111 clips produits sont sortis à **98 Hz**, avec 10 déclenchements du garde-fou
anti-dégénérescence contre 0 pour Tessia et Virion.

La cause n'est pas la taille de l'échantillon — rebalayer sur 20 répliques au lieu de 6 laisse le
même facteur d'écart. C'est que **le lot d'audition choisit délibérément les répliques les plus
longues**, sans quoi la F0 n'est pas mesurable. Or, mesuré sur les quatre voix, les répliques de
moins de 40 caractères dispersent environ 50 % de plus que celles de 90 et plus :

| | courtes (< 40 car.) | longues (≥ 90 car.) |
|---|---|---|
| Sylvie | 92 Hz | 57 Hz |
| Tessia | 59 Hz | 38 Hz |
| Virion | 60 Hz | 40 Hz |

Sylvie a 48 % de répliques courtes contre 11 % à Virion : c'est une bête liée, elle dit surtout
des choses brèves. Une part de sa dispersion tient à son matériau, pas à son timbre — et
continuer à balayer des doses reviendrait à optimiser un artefact de mesure.

Retenu : `ono_anna:0.5+serena:0.5`, qui **domine sur les deux critères** à échantillon égal —
aussi stable que le plus stable (57 Hz contre 56 pour `serena` pur) et le plus éloigné de Tessia
(0,922 contre 0,942).

Les deux lots écartés sont conservés hors dépôt (`scratch/`), pas détruits.

## Ce que ce pack ne corrige pas

**Tessia n'a que 248 répliques dans tout le jeu**, soit 1,75 % des 14 171 que comptent les 367
timelines, contre 73 % pour Arthur. Le pack couvre désormais 100 % d'entre elles ; il ne peut pas
en inventer. Elle est nommée par la narration dans **38 chapitres où elle ne dit pas un mot**
(ch23, 27, 53, 56, 58, 62, 73-74, 79-80, 84, 89, 91-93, 129, 133, 136-137, 143, 192, 236,
238-240, 244, 246, 248, 311-320). Combler ce manque est un travail d'écriture dans le dépôt
`bate`, pas de synthèse vocale.

**Les 3 542 options de choix ne sont pas doublées**, et ce n'est pas un oubli : ce sont des
intentions à l'infinitif, des actions du joueur, pas des paroles prononcées.
