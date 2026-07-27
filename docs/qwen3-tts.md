# Qwen3-TTS pour les voix BATE — évaluation et bascule (2026-07-27)

Remplacement du couple **Parler-TTS (timbre) + Chatterbox (répliques)** par
**Qwen3-TTS**, motivé par une capacité que ni l'un ni l'autre n'avait : donner
l'émotion d'une réplique par un **prompt en français**, au lieu de deux curseurs
d'intensité (`exaggeration`, `cfg_weight`).

## Ce qui tourne

- Poids : `mlx-community/Qwen3-TTS-12Hz-1.7B-{CustomVoice,VoiceDesign}-8bit`
  (3,1 Go chacun, speech_tokenizer inclus, dans le cache HF).
- Runtime : `mlx-audio` (déjà présent dans `~/workspace/.venv-mlx`), 100 % local.
  `soundfile` a été ajouté à ce venv.
- Outil : `tools/qwen3tts.py` (miroir de `voice-agent/training/qwen3tts.py`), branché dans la forge par
  `voice-agent forge lines --moteur qwen3` et `forge cast --moteur qwen3`.
  **Chatterbox reste le défaut** — la bascule est une décision d'écoute.
- Français natif : plus besoin de rédiger les descriptions en anglais comme
  l'imposait Parler-TTS.

## Verdict mesuré — et il est contre-intuitif

Banc : `tools/bench_qwen3tts.py` (vraies répliques d'Arthur, seeds variables
comme en production). Cohésion du timbre = cosinus des MFCC moyens entre clips.

| moteur | cohésion timbre | pire paire | ambitus selon registre | RTF |
|---|---|---|---|---|
| Chatterbox (actuel) | **0,941** | 0,824 | 5,0–6,2 st | ~1 (lent, MPS) |
| Qwen3 **CustomVoice** | **0,939** | 0,785 | **4,2–5,9 st** | **0,29** |
| Qwen3 **VoiceDesign** | 0,832 | **0,518** | 2,3–3,4 st | 0,30 |

**VoiceDesign — le mode « décris la voix que tu veux » — perd**, alors que c'est
celui qu'on choisirait spontanément pour « injecter un prompt sur la voix » :

1. **Il ne reproduit pas le timbre.** Chaque réplique est une génération
   indépendante : pire paire à 0,52, la voix dérive au fil des chapitres. Chatterbox
   tenait la cohérence en clonant un WAV ; une description ne suffit pas.
2. **Il ne respecte pas la description.** « Voix de garçon de seize ans » sortait à
   **282–320 Hz**, soit une voix d'enfant ou de femme. L'Arthur produit par
   Chatterbox est à 176–211 Hz.
3. **Il est le moins expressif** : ambitus 2,3–3,4 demi-tons, sous Chatterbox.

**CustomVoice gagne** : timbre premium figé (choix contraint à neuf voix), prompt
réservé au style. Cohésion à parité avec Chatterbox, expressivité supérieure,
trois fois plus rapide que le temps réel. Le prompt d'émotion fonctionne mieux
**sur un timbre figé que sur un timbre lui-même décrit par prompt**.

## Choix du timbre d'Arthur

Les quatre timbres masculins, mesurés sur huit répliques + cinq registres :

| timbre | cohésion | F0 selon registre | remarque |
|---|---|---|---|
| **aiden** | **0,939** | 117–157 Hz | retenu : seul sans clip dégénéré |
| ryan | 0,942 | 183–300 Hz | monte à 300 Hz en dialogue |
| dylan | 0,904 | 122–242 Hz | a rendu 23 s de quasi-silence en registre ému |
| eric | 0,873 | 142–240 Hz | le moins stable |

`aiden` (~140 Hz) est **plus grave que l'Arthur actuel** (176–211 Hz) : plus mûr
qu'un garçon de seize ans. Défendable pour un roi réincarné, mais c'est un choix
d'oreille, pas de mesure — il reste à valider.

## Deux pièges, coûteux à re-diagnostiquer

- **Dégénérescences de génération.** Deux clips sur soixante étaient cassés : une
  phrase de 2 s étirée à 23 s à −44 dB, une autre de 1,9 s à 7,4 s. Sur mille six
  cents répliques ça se compte en dizaines, et personne ne réécoute mille six cents
  fichiers. D'où le garde-fou `_suspect()` dans `qwen3tts.py` (durée hors de
  proportion avec le texte, niveau trop bas, trames actives < 10 %) et la relance
  automatique sur une autre graine, trois essais.
- **`hash()` est randomisé par processus** en Python 3 : inutilisable pour dériver
  une graine reproductible d'un identifiant de réplique. `qwen3tts.py` somme les
  octets. (`voice_forge.py` utilise encore `hash()` pour décaler les graines de
  candidats Parler-TTS — même défaut, hérité.)

## Les neuf timbres se MÉLANGENT — la limite n'existe pas

Un timbre premium n'est pas une voix figée : c'est un **token de la table d'embedding**
du talker (`spk_id` : aiden=2861, ryan=3061…). Une combinaison pondérée de ces vecteurs
donne un timbre intermédiaire réel, sans dégénérescence — l'espace des voix est donc
continu, et « neuf timbres » n'est pas une limite.

    --speaker "aiden:0.7+serena:0.3"        # forge lines / qwen3tts.py
    --timbre "Arthur=aiden:0.7+serena:0.3"  # forge cast

Interpolation vérifiée : aiden 188 Hz, ryan 161, `aiden:0.5+ryan:0.5` 155. Et la
cohésion de timbre ne se dégrade pas systématiquement — elle peut **s'améliorer** :

| timbre | cohésion | pire paire | F0 médian du lot |
|---|---|---|---|
| **aiden:0.7+serena:0.3** | **0,959** | **0,911** | 148 Hz |
| aiden pur | 0,948 | 0,815 | 140 Hz |
| aiden:0.5+ryan:0.5 | 0,926 | 0,748 | 132 Hz |
| aiden:0.8+vivian:0.2 | 0,899 | 0,601 | **183 Hz** |
| *repère Chatterbox* | *0,941* | *0,824* | *176–211 Hz* |

`aiden:0.7+serena:0.3` bat le timbre pur ET Chatterbox. Mais **ça dépend du couple** :
`+vivian` retombe sous Chatterbox. Un mélange se mesure, il ne se suppose pas. Arbitrage
ouvert pour Arthur : `+serena` est le plus stable, `+vivian` le plus proche en hauteur de
l'Arthur actuel (183 vs 176–211 Hz).

**Le piège à ne pas reproduire.** Le mélange se fait en substituant le vecteur au seul
**premier** accès de forme (1,1) à la table d'embedding — celui du speaker dans
`_prepare_generation_inputs`. La boucle de génération réclame ensuite des `code_0_embed`
de forme (1,1) elle aussi : un proxy permanent les détourne et le modèle part en boucle
(**318 s** d'audio pour une phrase de 4,6 s). C'est le bug qui m'avait fait conclure, à
tort, que le mélange était impossible ; le contrôle qui l'a révélé est de mélanger un
timbre **avec lui-même** et de vérifier qu'on retrouve le timbre pur à l'identique.

**`eric` et `dylan` sont dialectaux** (`spk_is_dialect` : sichuanais, pékinois). C'est
l'explication de leurs mauvais scores et de leurs clips dégénérés en français. Ils sont
désormais écartés du tour de rôle automatique.

Reste vrai : le tour de rôle **ignore le genre** des personnages (Alice héritait
d'`eric`, Virion de `sohee`). `cast` affiche une colonne M/F et attend `--timbre`.

Le troisième modèle, **Base**, clone un WAV en 3 s mais n'accepte **pas** de prompt de
style. Non testé : avec le mélange, il n'a plus d'intérêt ici.

## Mode hybride : Qwen3 pour les rôles travaillés, Chatterbox pour le reste

    forge cast --moteur hybride --timbre "Arthur=aiden:0.7+serena:0.3" --timbre Alice=vivian

Un rôle passe en Qwen3 **si et seulement si** il a un `--timbre` ; les autres restent sur
Chatterbox. `--timbre` fait donc double emploi, et c'est voulu : une seconde option pour
dire la même chose n'aurait ouvert la porte qu'aux contradictions. Les deux moteurs ne
tournent jamais en même temps (deux modèles lourds ne cohabitent pas en RAM) et Qwen3
passe d'abord, puisqu'il finit en minutes là où Chatterbox prend la nuit. Plans séparés :
`cast_repliques_qwen3.json` et `cast_repliques_chatterbox.json`.

## Écouter les essais

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh      # tout
bash docs/ecoute-qwen3-tts/ecouter.sh 1    # 4 timbres masculins
bash docs/ecoute-qwen3-tts/ecouter.sh 2    # 7 registres sur aiden
bash docs/ecoute-qwen3-tts/ecouter.sh 3    # A/B contre Chatterbox
bash docs/ecoute-qwen3-tts/ecouter.sh 4    # mélanges + registres
```

## Produire

```bash
cd ~/workspace/voice-agent
# auditionner les neuf timbres avant de choisir
../.venv-mlx/bin/python training/qwen3tts.py --auditionne-speakers \
    --texte "Papa, comment on sait qu'on a réussi ?"

# les répliques d'Arthur (1065 répliques ≈ 25 min au lieu d'une nuit)
python3 training/voice_forge.py lines bate-arthur --moteur qwen3 \
    --speaker aiden --personnage Arthur

# la distribution — vérifier la colonne M/F du dry-run AVANT de lancer
python3 training/voice_forge.py cast --moteur qwen3 --dry-run \
    --timbre Alice=vivian --timbre Tessia=serena --timbre Virion=uncle_fu
```

Une réplique peut porter son propre `instruct` (phrase libre) ou un `registre`
nommé parmi : narration, dialogue, emu, colere, peur, joie, determination. La
priorité va du plus précis au moins : `instruct` de la réplique > `registre` de la
réplique > registre du rôle > registre du travail > défaut.
