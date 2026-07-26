# Comment les voix sont produites

Tout est généré **localement**, sans service en ligne, par la pipeline `voice-agent forge`
(dépôt `voice-agent`). Ce dépôt-ci ne fait que collecter, indexer et empaqueter le résultat :
la forge reste la source de vérité reproductible.

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

## Détails techniques utiles

- **Réglages Chatterbox** : `exaggeration=0.6`, `cfg_weight=0.5` pour des répliques jouées.
  Un dataset d'entraînement demanderait l'inverse (0.4 / 0.6) : une voix stable et neutre.
- **Encodage Ogg** : par `oggenc` (vorbis-tools). Le ffmpeg de Homebrew est construit sans
  `libvorbis` — seul l'encodeur natif `vorbis`, marqué expérimental, est disponible.
- **Marquage audio** : le watermark implicite de Chatterbox (Perth) est laissé actif, les
  fichiers restent identifiables comme synthétiques.
- **Débit observé** : environ 20 s par candidat Parler-TTS, 10 s par réplique Chatterbox, sur
  un Mac mini M4 Pro. Une distribution de 1645 répliques demande donc une nuit.
