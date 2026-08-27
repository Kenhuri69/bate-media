# Pack de voix 0.8.0 — les 119 personnages des cent premiers chapitres

**11 645 clips** (0.7.0 : 9 132), **129 voix**, 717,6 Mo.

## Couverture

**100 % des répliques prononçables** des chapitres 1 à 100 et des douze arcs secondaires :
10 471 sur 10 471. Les deux seules lignes non doublées sont des indications scéniques écrites
comme des répliques de narrateur (`[Tempête.]`, `[Volonté du dragon. Phase un.]`) : il n'y a
rien à prononcer dedans, et elles sont exclues à raison.

## Ce que la vague ajoute

| lot | voix | clips |
|---|---|---|
| principaux masculins | 9 (Elijah, Windsom, Gideon, Kaspian, Perrin, Curtis, Feyrith, Lucas, Blaine) | 630 |
| principales féminines | 10 (Goodsky, Claire, Glory, Kathyln, Sylvia, Alea, Nima, Rinia, Emily, Tabitha) | 638 |
| troupe | 93 figurants sur 12 archétypes | 832 |
| combat | 1 voix d'ennemi générique | 33 |
| rattrapages | Arthur, Sylvie, Virion | 375 |

## Trois axes de distinction, dont deux inexplorés jusqu'ici

CustomVoice n'expose que quatre timbres féminins et trois masculins. Les mélanges à **trois et
quatre composants** fonctionnaient depuis toujours sans que personne les essaie, et le **débit**
(WSOLA, durée modifiée sans toucher la hauteur) ne coûte aucun appel au modèle : un mélange
généré une fois se décline en 7 décalages × 3 débits.

Mesuré sur 2 303 variantes : le débit fait passer l'espace masculin de 14 à **44 places
distinctes**, et n'ouvre **rien** côté féminin — vingt candidates féminines testées une à une,
quatorze refusées pour proximité avec une voix en service. Six places, et pas une de plus. Quatre
personnages féminins partagent donc une voix d'archétype, chacun avec le registre qui lui
correspond ; c'est déclaré dans le code et dans `docs/casting-troupe.md`.

## Deux contrats corrigés, des deux côtés

**Le dossier de voix ne peut pas être le premier mot du locuteur.** Les six professeurs de
l'Académie tombaient tous dans `professeur/` — le clip de Glory aurait été joué pour Geist, un
doublage FAUX et non simplement muet. Trois silhouettes tombaient dans `le/`, deux dans `l/`. Et
l'inverse existait : « Directrice Goodsky » et « Goodsky » vivaient dans deux dossiers. Table
explicite `LOCUTEURS` ajoutée dans `tools/empreinte.py` **et** dans
`bate/src/systems/audio/VoiceLines.cs`, plus un contrôle qui refuse toute collision résiduelle
(156 dossiers, zéro collision) et qui a été validé par sabotage.

**L'empreinte se calcule sur le texte BRUT.** La forge la calculait sur le texte nettoyé de ses
balises : les 75 répliques du jeu qui portent une balise de style étaient muettes à 100 %, dont
les 66 répliques télépathiques de Sylvie et 7 d'Arthur. Le texte brut sert désormais à
l'identifiant, le nettoyé à la synthèse — ce que la convention disait déjà, sans que le code
l'applique.

## Contrôles

Les 2 508 clips neufs sont passés aux deux critères, **timbre** (part d'énergie dans la bande du
rôle) et **texte** (ASR local croisé avec la durée). 235 clips défectueux ont été repris ; 8
résistent et sont nommés dans les rapports plutôt que noyés dans une moyenne.

Deux défauts de contrôle ont été trouvés au passage, plus graves que les clips :

- **34 des 93 voix de troupe ne pouvaient pas être jugées** — `_cible` refuse de mesurer un lot
  dont plus de 5 % de l'énergie passe sous 150 Hz, et toutes les voix graves étaient dans ce cas.
  Une cible étalonnée par archétype a réglé les 34 : zéro voix non jugeable au second passage ;
- **l'audit du texte de la troupe n'avait jamais tourné** : `xargs -a` est une option GNU absente
  de macOS, et le script affichait « FIN » comme si de rien n'était. 832 clips passaient pour
  contrôlés alors que seul leur timbre l'avait été.

## Le combat parle

33 répliques génériques (`bate/resources/combat_barks.json`), une voix `Ennemi` (premier mélange
à trois timbres du dépôt), et le registre change par catégorie : ouverture en `dialogue`, coup
critique en `peur`, chute en `emu`. Quatre déclencheurs dans `CombatScreen`, aucun code audio
nouveau — `PlayVoice` existait et le contrat d'empreinte faisait le travail.

## Réserves déclarées

- le seuil de distinction par **débit** (8 %) n'est pas calibré à l'oreille, contrairement au
  cosinus ; trente des quarante-quatre places masculines ne tiennent que par lui ;
- **Perrin 181 Hz et Elijah 190 Hz** sont la paire la plus serrée, et tous deux sont camarades de
  classe d'Arthur : à écouter en premier ;
- 134 clips sont orphelins (répliques réécrites depuis leur production), contre 101 en 0.7.0.
