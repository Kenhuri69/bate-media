# Pack de voix 0.7.0 — Luna et Lise, et trois voix remises à niveau

**9 132 clips** (0.6.9 : 9 065), 16 personnages, 577,3 Mo.

## Deux personnages de plus

`luna` (25 clips) et `lise` (42) — les deux elfes de Loriande, personnages originaux des arcs
`loriande_awakening`, `xyrus_first_frost` et `elven_dormitory`. 70 répliques, 67 clips après
déduplication des textes identiques ; **aucune réplique muette** (vérifié timeline par timeline).

- Luna = `ono_anna:0.8+vivian:0.2`, descendue de 2 demi-tons — 237 Hz
- Lise = `vivian:0.8+ono_anna:0.2` — 262 Hz

Aucun timbre pur : deux sont déjà en service (Tessia `sohee`, Alice `vivian`) et c'est assez.
Le couple s'est choisi ensemble, sur 20 répliques réelles chacune, avec la matrice de proximité
entre candidats — elles partagent la totalité de leurs scènes et Tessia est dans les trois arcs.
Méthode, chiffres et pièges : [`casting-luna-lise.md`](casting-luna-lise.md).

Les hauteurs des quatre voix féminines jeunes du jeu : `Tessia 213 < Luna 237 < Lise 262 <
Ellie 270`.

## Trois voix refaites — leur décalage de hauteur était inopérant

`descente_voix.descendre()` rendait l'onde intacte pour tout demi-ton ≤ 0. `ellie` (−2),
`adam` (−1) et `angela` (−2) déclaraient donc une montée que le code n'appliquait pas : leurs
121 clips ont été refaits, cette fois avec le décalage. La cible d'énergie d'`adam`, étalonnée
sur un lot non monté, est passée de 205 à 217 Hz — sans quoi le contrôle aurait cherché
l'énergie sous la voix.

Monter une voix disperse son énergie : le lot d'ellie est sorti à 21 clips douteux sur 82, ramené
à 6 après reprise (l'état d'avant en comptait 5).

## Douze clips défectueux réparés dans les dix voix de 0.6.5 → 0.6.9

Premier passage du nouveau contrôle ASR (`tools/audit_texte.py`) : les 697 clips de ces voix ont
été réécoutés par le whisper-server local et confrontés à leur durée. 9 défauts de contenu
(1 muet, 1 radotage, 3 clips qui traînaient, 4 tronqués) et 6 défauts de timbre, tous repris et
revérifiés sur les deux critères. Détail : [`audit-texte-asr.md`](audit-texte-asr.md).
