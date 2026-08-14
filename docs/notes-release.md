# Pack de voix 0.5.0 — Tessia rejoint Arthur, chapitres 0 à 60

**114 clips de plus, 4 Mo, et une deuxième voix dans le jeu.** Tessia parle sur toute la
plage déjà couverte par Arthur : **114 répliques sur 114**, soit 100 % de ses répliques des
ch0-60. Les 117 autres sont au-delà du chapitre 60, comme celles d'Arthur.

## Son timbre : `sohee`, et pourquoi pas un mélange

Le casting du pack précédent avait auditionné les quatre timbres féminins de CustomVoice —
les quatre, c'est-à-dire tout le choix contraint du modèle — et laissé la décision ouverte.
Le principe qui avait tranché pour Arthur a été appliqué : sortir les têtes de série qui ne
gagnent pas sur le même critère, **balayer les doses entre elles** sur les mêmes répliques
réelles, faire primer la plage sur la médiane. Sur Arthur ce balayage avait produit un
mélange (`aiden:0.5+ryan:0.5`) meilleur que chacun de ses composants. Ici il conclut
l'inverse : **aucune des cinq doses essayées ne bat `sohee` pur.**

| timbre | plage F0 | écart entre les deux âges | ambitus |
|---|---|---|---|
| **`sohee`** | **13 Hz** | **23 Hz** | 3,1 st |
| `sohee:0.7+ono_anna:0.3` | 28 Hz | 33 Hz | 3,0 st |
| `sohee:0.5+ono_anna:0.5` | 63 Hz | 26 Hz | 3,3 st |
| `ono_anna` | 69 Hz | 11 Hz | 3,1 st |

Mélanger `ono_anna` coûte en dispersion plus qu'il ne rapporte en stabilité d'âge : sa
régularité entre les deux âges ne se transmet pas au mélange, sa dispersion si.

**Et le soupçon que le casting avait lui-même formulé est levé.** Il avertissait que « la
stabilité récompense la voix la plus plate » et que `sohee` était peut-être régulière parce
qu'elle jouait moins. L'ambitus mesuré dit non : 3,0 à 3,3 demi-tons pour les sept
candidats, `sohee` au milieu. Sur Arthur ce compromis existait bel et bien (3,6 st contre
5,1-5,8 aux perdants) ; ici il n'y en a pas.

Décision d'écoute ouverte : `bash docs/ecoute-qwen3-tts/ecouter.sh 6`, puis `6b sohee` pour
l'entendre tenir l'enfant de cinq ans puis l'adolescente d'affilée.

## Deux âges, une seule voix, et aucun prompt d'âge

Tessia a cinq ans aux ch10-18 et quinze aux ch44-60. **Aucun prompt d'âge n'est appliqué**,
et c'est mesuré, pas négligé : sur Arthur, ce levier crée un vrai registre d'enfant au stade
bambin (+48 Hz) mais ne fait plus rien au-delà — les formulations essayées y donnaient −6,
+4, −21 et +17 Hz, du bruit, signes compris. À cinq ans, Tessia est déjà hors de la zone où
il a montré un effet. Le tester sur ses seules répliques d'enfant reste possible
(`voix_tessia.py livrer --prompt-age`) ; le décider à l'avance sur tout le lot ne l'était pas.

Ce que le timbre fait de lui-même, sans prompt : 207 Hz en enfant, 215 en adolescente.

## Qualité

Contrôle d'énergie spectrale sur les 114 clips : **11 défectueux (9,6 %)** — le taux d'Arthur
était de 11,0 % — dont **10 récupérés** par régénération sur d'autres graines. Le seul
restant est « Qu'est-ce que — Art, attends — », trois mots interrompus : sur un clip aussi
court la mesure d'énergie est peu fiable, le même piège que la F0. Le garde-fou
anti-dégénérescence n'a eu à relancer **aucune** des 114 générations.

La cible de ce contrôle n'est pas écrite en dur comme celle d'Arthur : elle est **mesurée sur
le lot, et refusée si la F0 n'est pas croyable**. Sur les voix graves d'Arthur
l'autocorrélation divise le fondamental par deux et une cible ainsi calculée ferait regarder
sous la voix — le contrôle vérifie donc d'abord que moins de 5 % de l'énergie est sous
150 Hz. Sur Tessia : 0,02 %. Sur le lot d'Arthur, le même contrôle refuse (15 %).

## Installer

    python3 tools/verify_pack.py bate-media-voices-0.5.0.tar.zst
    python3 tools/install_pack.py bate-media-voices-0.5.0.tar.zst --jeu ~/workspace/bate
    cd ~/workspace/bate && python3 tools/checks/check_voices.py

---

# Pack de voix 0.4.0 — Arthur et le narrateur, chapitres 0 à 60

**4401 répliques, une seule voix, 253 Mo.** Le pack passe de 72 clips (ch0-5) à 4401 : dix heures
d'audio pour les soixante premiers chapitres, narration comprise.

## Contenu

| rôle | clips | ce que c'est |
|---|---|---|
| `narrator` | ~3250 | la voix intérieure d'Arthur, qui porte le récit |
| `Arthur` | ~700 | ses répliques parlées |
| `Note` | ~450 | son pseudonyme d'aventurier, même voix |

Couverture : **4401 répliques sur 4451** demandées par les timelines ch0-60, soit 98,9 %. Les
50 manquantes sont des répliques écrites pendant la production ; elles se rattrapent à l'unité.

## Les noms de fichiers ont changé, et c'est la vraie nouveauté

Un clip s'appelait `narrator_ch00_07` : son nom disait une **position**. Insérer une réplique en
amont périmait silencieusement toutes les suivantes — c'est ce qui est arrivé au pack 0.3.0 quand
les chapitres 0 à 9 ont été réécrits, sans que rien puisse le voir, puisque le fichier attendu
existait toujours et disait simplement autre chose.

Un clip s'appelle désormais **`<rôle>_<empreinte du texte>`** (`narrator_c03132187d`). Une
réplique déplacée garde sa voix ; une réplique réécrite perd la sienne et se tait — un manque
visible et régénérable à l'unité, au lieu d'un décalage inaudible. La règle est publiée et
vérifiable des deux côtés : `bate/resources/voice_fingerprints.json` porte les vecteurs de test
que la forge rejoue (`tools/empreinte.py --selftest`).

Conséquence pratique : **le manifeste porte maintenant le texte et le chapitre de chaque clip.**
L'identifiant ne les dit plus, et sans eux on ne pourrait ni retrouver une réplique à la main ni
savoir ce qui reste à doubler.

Autre conséquence, voulue : deux répliques identiques partagent un clip. Un pack plus petit que
le nombre de répliques n'est pas un pack incomplet.

## La voix

Timbre `aiden:0.5+ryan:0.5`, validé à l'oreille, **le même à tous les âges**. L'âge se joue par un
prompt de style, jamais en modifiant la voix.

Mesuré au barycentre spectral sur la totalité du lot :

| | barycentre | clips |
|---|---|---|
| répliques **parlées** d'Arthur | 289-308 Hz | 1121 |
| **narration** | 209-214 Hz | 3273 |
| prologue (King Grey, sans prompt d'âge) | 195 Hz | 39 |

Le prompt d'âge crée bien un registre d'enfant, une octave au-dessus de la narration. **Ce qu'il
ne fait pas : distinguer les stades entre eux** — trois ans, cinq ans, six ans et quinze ans se
recouvrent tous. Arthur a deux voix, pas cinq âges. Aller plus loin demanderait de diluer le
timbre validé, ce qui a été refusé. Décision d'écoute ouverte :
`bash docs/ecoute-qwen3-tts/ecouter.sh 4`.

⚠️ Une première version de ces mesures concluait l'inverse : elle reposait sur une F0 par
autocorrélation qui divise le fondamental par deux sur ces voix. Voir
[`docs/ecoute-qwen3-tts/8-ages-par-prompt/README.md`](ecoute-qwen3-tts/8-ages-par-prompt/README.md).

## Qualité

Contrôle d'énergie spectrale sur les 4433 clips produits : **486 défectueux détectés (11,0 %),
481 récupérés** par régénération sur d'autres graines, 5 non sauvés. Le garde-fou
anti-dégénérescence n'a eu à relancer que **12 fois sur 4433** générations.

## Installer

    python3 tools/verify_pack.py bate-media-voices-0.4.0.tar.zst
    python3 tools/install_pack.py bate-media-voices-0.4.0.tar.zst --jeu ~/workspace/bate
    cd ~/workspace/bate && python3 tools/checks/check_voices.py

Rien ici n'est nécessaire pour jouer : une voix absente laisse le dialogue continuer en silence.
Les chapitres 61 et suivants, et tous les autres personnages, sont donc simplement muets.

## Suite

- **Tessia** : quatre candidates auditionnées, en attente d'écoute
  (`bash docs/ecoute-qwen3-tts/ecouter.sh 5`). Ses 112 répliques des ch0-60 sont prêtes à
  produire dès que le timbre est choisi.
- Les 50 répliques manquantes des ch0-60, et les chapitres au-delà du 60.
