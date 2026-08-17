# Lot 13 — descendre la voix de Virion sans la ralentir

**Tranché le 2026-08-17 : −3 demi-tons**, à durée constante. Les 350 clips sont regénérés
dessus et le timbre passe à `valide: true`. Ce lot garde les quatre paliers, qui documentent le
choix et permettent d'y revenir.

Vérifié sur les 350 clips livrés, avant/après, clip par clip :

| | F0 médiane | plage | durée |
|---|---|---|---|
| avant | 131,9 Hz | 45 Hz | référence |
| **après (−3)** | **113,7 Hz** | 48 Hz | **−0,02 %** |
| Arthur parlé | 131,7 Hz | 57 Hz | |
| Arthur narration | 120,3 Hz | 46 Hz | |

Virion passe **sous** Arthur au lieu d'être exactement à sa hauteur, sa dispersion ne bouge pas,
et la durée est tenue à deux centièmes de pour cent — contre +18,9 % si la descente avait
ralenti.

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 9
```

## Le constat de départ

Le timbre retenu (`uncle_fu:0.5+aiden:0.5`) règle la confusion avec Tessia et la dispersion,
mais il **manque de maturité** : à 130 Hz, Virion parle exactement à la hauteur d'Arthur (131 Hz
en parlé, 119 en narration), alors qu'il est censé avoir plusieurs siècles.

## Le levier du modèle ne marche pas, et c'est mesuré

Premier réflexe : demander l'âge par la consigne, comme le moteur le permet pour l'émotion. Six
formulations essayées sur 8 répliques réelles (lot 12, clips non versionnés — voir
`12-registre-virion/rapport_registre.json`) :

| consigne | Δ F0 | Δ barycentre | Δ durée |
|---|---|---|---|
| « voix d'homme âgé, grave et posée » | **+14 Hz** | +56 Hz | +21,7 s |
| « rauque et usé, souffle court » | **+16 Hz** | +16 Hz | +15,3 s |
| « descendue dans la poitrine » | +8 Hz | +37 Hz | +34,4 s |
| « vieil homme qui n'a plus rien à prouver » | +1 Hz | +9 Hz | +19,6 s |

**Aucune ne descend la voix — toutes la montent**, de +1 à +16 Hz, et éclaircissent le timbre.
L'explication est simple : demander « rauque et usé » fait *forcer* la voix, et une voix forcée
monte. Qwen3-TTS n'expose ni hauteur ni vitesse, et les trois timbres masculins de CustomVoice
tiennent tous entre 130 et 175 Hz : il n'y a pas de voix grave à choisir dans le modèle.

Ces consignes **ralentissent** en revanche nettement (+7 à +24 %). Ce serait la moitié de
l'effet recherché — mais ralentir a été explicitement refusé.

## Ce qui marche : descendre le signal, puis rendre la durée

Deux étapes :

1. **rééchantillonnage** au rapport 2^(n/12) — descend la hauteur, descend aussi les formants,
   et rallonge d'autant ;
2. **compression WSOLA** du rapport inverse — rend la durée d'origine sans remonter la hauteur.

Vérifié d'abord sur un signal de synthèse, avant toute écoute : à −3 demi-tons, 130 Hz devient
exactement 109 Hz et la durée bouge de moins d'un millième.

| palier | F0 mesurée | Δ F0 | Δ durée |
|---|---|---|---|
| témoin | 156 Hz | — | — |
| −2 demi-tons | 140 Hz | −16 | −0 % |
| −3 | 133 Hz | −23 | −0 % |
| −4 | 126 Hz | −30 | +0 % |

*(mesures sur l'échantillon d'audition ; rapporté au lot livré à 130 Hz, cela donne 116 Hz à −2,
109 Hz à −3, 103 Hz à −4)*

**Les formants descendent avec la hauteur, et c'est voulu.** Un décalage « propre » à formants
préservés les garderait en place ; ici on veut l'inverse — des formants plus bas s'entendent
comme un conduit vocal plus grand, donc un corps plus vieux. La hauteur seule ne donne pas cet
effet.

## Ce que la mesure ne dit pas

- **Si ça sonne vieux.** La sensation d'âge tient aussi au souffle et aux fins de phrase, qu'aucun
  de ces chiffres n'attrape.
- **Les artefacts.** WSOLA lisse les attaques ; sur les consonnes occlusives cela peut s'entendre
  comme un léger hachage. La taille de trame (40 ms) est réglable si c'est le cas.
- **Le plancher.** En dessous de −4 demi-tons la voix se creuse vers le grondement. Non testé
  au-delà, faute d'intérêt probable.

## Où la descente est appliquée, et pourquoi pas ailleurs

**À la génération** (`voix_personnage.livrer`, champ `grave_demi_tons`), pas en post-traitement
des `.ogg` livrés. Retoucher les fichiers aurait pris quelques secondes au lieu d'une heure de
GPU, mais leur aurait infligé un **second encodage Vorbis** — une perte gratuite sur un pack
distribué. Les 350 clips ont donc été regénérés à graines identiques : mêmes prises, descendues
une fois, encodées une fois.

`reprendre` applique la même descente, sans quoi un clip repris ressortirait une tierce au-dessus
de ses voisins — un défaut qu'aucun compte ne montrerait.

La cible du contrôle d'énergie suit le même rapport : 150 Hz devient **126 Hz**. La laisser à 150
aurait fait chercher l'énergie une tierce au-dessus de la voix et déclaré défectueux des clips
sains — le piège déjà payé sur les narrations d'Arthur, où une cible fausse en avait condamné
13 sur 13.
