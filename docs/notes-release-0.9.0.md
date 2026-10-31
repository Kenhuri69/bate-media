# Pack de voix 0.9.0 — les vingt premiers chapitres passent à Drama-3

**11 645 clips** (inchangé), **129 voix**. **813 clips remplacés** par leur version Drama-3
(Fish Audio) ; les 10 832 autres restent ceux de Qwen3-TTS.

## Pourquoi changer de moteur

Les poids de Qwen3-TTS ont été retirés le 2026-10-25. Drama-3 (`mlx-community/fish-audio-drama-3-4bit`,
100 % local) a été retenu à l'écoute contre S2-Pro, sur un banc A/B Arthur + Tessia
(`docs/ecoute-fish-audio/`) : meilleure ressemblance à la voix d'origine (0,991 / 0,977
contre 0,984 / 0,973) et meilleure tenue du timbre sur une narration longue (0,984 / 0,966
contre 0,956 / 0,863).

**Aucune voix n'est réinventée.** Drama-3 CLONE la voix déjà livrée : chaque personnage a une
empreinte de 10 à 20 s construite sur ses propres clips Qwen3 (une par registre pour Arthur,
qui narre une octave sous sa voix parlée). Le personnage garde son timbre, sa hauteur et son
débit.

## Couverture

La trame datée des **chapitres 0 à 20**, arcs secondaires exclus :

| voix | clips Drama-3 |
|---|---|
| Arthur (narration + parole) | 277 sur 1 028 — **en cours**, le reste suit dans la prochaine version |
| Virion | 151 |
| Reynolds | 99 |
| Tessia | 57 |
| Sylvia | 48 (1 clip garde sa version Qwen3, voir plus bas) |
| Alice | 46 |
| Goodsky, Rinia, Adam, Vincent, Feyrith, Meneur, Ellie, Jasmine, Sylvie, Durden, Angela, Tabitha, Helen, Merial, Lilia | 135 |

Six rôles mineurs restent en Qwen3, faute de 10 s de clips propres pour une empreinte :
alduin, doctor, garde, danek, elfe, guetteur (21 répliques). Chacun garde ainsi une seule
voix d'un bout à l'autre.

## Qualité

Drama-3 rate 15 à 30 % de ses générations sur les répliques difficiles : silence soufflé,
réplique étirée, ou phrase abandonnée en route. Chaque clip passe donc trois portes avant
d'entrer dans le pack : forme du signal, **relecture par whisper** (taux d'erreur ≤ 50 % au-delà
de 6 caractères) et jusqu'à six essais, le meilleur conservé. Un clip qui échoue garde sa
version Qwen3 : c'est le cas d'**un seul** sur 814, « Hum. Est-ce que ça marche ? ...Bien.
Bonjour, Art. C'est Sylvia. », que Drama-3 abandonne après la question.

Le murmure et la voix douce (`[whisper]`, `[speaking softly]`) ont été écartés : ils
dégénèrent le contenu. Le ton posé de la narration vient de l'empreinte, pas d'une balise.

## Pour le jeu

Les clips gardent leur nom (`<rôle>_<empreinte>`) : aucune réplique ne change d'identifiant,
le jeu n'a rien à adapter. Ils sont en 44,1 kHz au lieu de 24 kHz.
