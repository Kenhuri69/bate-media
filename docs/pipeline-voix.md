# Comment les voix sont produites

Tout est généré **localement**, sans service en ligne, par la pipeline `voice-agent forge`
(dépôt `voice-agent`). Ce dépôt-ci ne fait que collecter, indexer et empaqueter le résultat :
la forge reste la source de vérité reproductible.

> **Un second moteur existe depuis le 2026-07-27 : Qwen3-TTS.** Il donne l'émotion d'une
> réplique par une **phrase en français** au lieu des deux curseurs Chatterbox, et va trois
> fois plus vite. Les voix décrites ci-dessous sont celles produites par Chatterbox, qui
> reste le moteur par défaut. Verdict, mesures et pièges : [`qwen3-tts.md`](qwen3-tts.md).

## Chaîne

1. **Description** — une demande en français (« une femme d'une trentaine d'années, douce et
   maternelle, avec une pointe d'inquiétude retenue ») est traduite par un LLM local en
   descriptions **anglaises** au format Parler-TTS, seul format que ce modèle comprend pour
   décrire un timbre. En mode distribution complète, la description est **déduite des
   répliques du personnage lui-même** : le modèle lit six extraits et en tire genre, âge,
   timbre, tempérament.
2. **Candidats** — Parler-TTS génère 3 à 5 extraits, chacun avec une graine déterministe,
   donc reproductible à l'identique. C'est le seul moteur de la chaîne qui fabrique une voix
   depuis du **texte** : Kokoro n'a que des voix figées, Chatterbox clone un audio existant.
3. **Écoute et validation** — un humain choisit. Rien n'est produit en masse sans ce passage.
4. **Répliques** — Chatterbox multilingue clone la voix retenue et lit **chaque réplique**
   du personnage extraite des timelines Dialogic. Sortie en Ogg Vorbis mono 24 kHz.

## Reproduire une voix

Chaque dossier de forge conserve `request.json` (la demande), `candidates.json` (les
descriptions et graines) et `choice.json` (le candidat retenu). Une voix est donc
reconstructible à l'identique : même description + même graine = même timbre.

    voice-agent forge listen bate-alice        # réécouter les candidats
    voice-agent forge select bate-alice 2      # changer d'avis
    voice-agent forge lines  bate-alice --personnage Alice   # regénérer ses répliques

## Rôles regroupés

Un personnage peut parler sous plusieurs noms dans les timelines. Ces rôles doivent
partager **une seule** voix, sinon le même personnage change de timbre en cours de partie :

| voix | rôles regroupés | pourquoi |
|---|---|---|
| Arthur | `Arthur`, `Note`, `narrator` | « Note » est son pseudonyme d'aventurier ; le jeu est narré à la première personne |
| Tessia | `Tessia`, `Tessia Eralith` | le nom complet apparaît dans les scènes de cour |
| Virion | `Virion`, `Virion Eralith` | idem |

Le nom complet n'est pas un détail de style : extraire `Tessia` seul laissait **21 répliques**
muettes, et rien ne le signalait — le jeu, lui, déduit le dossier de voix du PREMIER MOT du
locuteur (`VoiceLines.Role`), donc il réclamait bien un clip pour elles. Chercher un rôle par son
nom exact et le résoudre par son premier mot sont deux règles différentes ; tant qu'elles ne sont
pas alignées, l'écart est invisible des deux côtés.

## La voix est STANDARDISÉE, et ne varie plus dans le temps

Une seule voix par personnage, du premier chapitre au dernier, histoires secondaires comprises.
Arthur portait auparavant un prompt d'âge par stade sur ses répliques parlées, qui faisait
lentement varier sa voix au fil du récit ; il est retiré (2026-08-15).

Ce n'est pas un renoncement, c'est ce que la mesure disait déjà : le prompt d'âge ne crée un
registre distinct qu'au stade bambin (+48 Hz à trois ans), et **les stades ne se distinguent pas
entre eux** — au-delà, les formulations essayées apportaient −6, +4, −21 et +17 Hz, c'est-à-dire
du bruit, signes compris. On payait une inconnue pour un effet que la mesure ne trouvait pas.

Ce qui subsiste, et qui n'est pas une variation dans le temps :

- le **registre de rôle** — Arthur ne raconte pas comme il parle (`narration` contre `dialogue`) ;
- l'**écart de niveau parole / pensée**, appliqué au mixage côté jeu et non dans les fichiers
  (voir [`integration-dialogic.md`](integration-dialogic.md)).

## Produire

    python3 tools/extraire_repliques.py bate-arthur Arthur Note narrator
    ../.venv-mlx/bin/python tools/voix_personnage.py livrer    arthur
    ../.venv-mlx/bin/python tools/voix_personnage.py verifier  arthur
    ../.venv-mlx/bin/python tools/voix_personnage.py reprendre arthur
    python3 tools/migrer_empreintes.py --personnage Arthur --roles Arthur,Note,narrator \
        --slug bate-arthur

`livrer` ne produit **que ce qui manque** et n'écrase jamais un clip existant : le fichier naît
directement sous le nom que le jeu lui demandera (`<rôle>_<empreinte>`), si bien que « ce qui est
déjà là est déjà bon » se lit sur le disque. Auparavant les clips naissaient sous un identifiant
de forge (`arthur_ch11_02`) puis étaient renommés : une reprise ne reconnaissait donc rien et
regénérait tout le lot.

`verifier` puis `reprendre` ne sont pas optionnels — sur les 4433 premiers clips d'Arthur, 11,0 %
étaient défectueux, et le défaut ne se voit pas dans un log : il s'entend.

Et ils ne suffisent pas : ils jugent le TIMBRE. Un clip peut dire son texte à moitié avec un
timbre parfait, ce que ni eux ni le garde-fou de génération ne voient. Le contenu se contrôle
en réécoutant le clip par ASR (`tools/audit_texte.py`, whisper-server local), et le verdict se
croise avec la DURÉE — sur 42 clips que l'ASR déclarait incomplets, 37 disaient tout leur texte
et c'est le transcripteur qui butait sur les noms propres du projet. Détail, seuils et résultats :
[`audit-texte-asr.md`](audit-texte-asr.md).

    ../.venv-mlx/bin/python tools/audit_texte.py <perso...>
    ../.venv-mlx/bin/python tools/audit_texte.py --relire   scratch/audit_texte.json
    ../.venv-mlx/bin/python tools/audit_texte.py --regenerer scratch/audit_texte.json

## Les histoires secondaires étaient invisibles

L'extraction faisait un `glob("*.dtl")` **non récursif** : `dialogues/side/` n'a jamais été lu, et
les 38 timelines d'arcs secondaires n'ont donc jamais réclamé un seul clip — 547 répliques
d'Arthur et 16 de Tessia muettes, sans qu'aucun contrôle puisse le dire. Corrigé le 2026-08-15
(`voice_forge._extrait_repliques` en `rglob`).

Il a fallu en même temps changer la règle d'étiquette de lot. Elle valait « `ch` + premier nombre
du nom de fichier », ce qui donnait `ch01` pour `side/gates_design/gates_design_01.dtl` — six arcs
en collision entre eux et avec le chapitre 1. Une timeline rangée dans un sous-dossier garde
désormais son nom entier (`gates_design_01`).

## Détails techniques utiles

- **Réglages Chatterbox** : `exaggeration=0.6`, `cfg_weight=0.5` pour des répliques jouées.
  Un dataset d'entraînement demanderait l'inverse (0.4 / 0.6) : une voix stable et neutre.
- **Encodage Ogg** : par `oggenc` (vorbis-tools). Le ffmpeg de Homebrew est construit sans
  `libvorbis` — seul l'encodeur natif `vorbis`, marqué expérimental, est disponible.
- **Marquage audio** : le watermark implicite de Chatterbox (Perth) est laissé actif, les
  fichiers restent identifiables comme synthétiques.
- **Débit observé** : environ 20 s par candidat Parler-TTS, 10 s par réplique Chatterbox, sur
  un Mac mini M4 Pro. Une distribution de 1645 répliques demande donc une nuit.
