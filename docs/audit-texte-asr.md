# Vérifier qu'un clip dit son texte — audit ASR

Contrôle ajouté le 2026-08-26, sur demande : « revoir les voix générées qui ont des défauts,
manque de texte ». Il répond à une question qu'aucun contrôle du dépôt ne posait.

## Le trou

Trois garde-fous existaient, et aucun ne regarde le CONTENU du clip :

| garde-fou | ce qu'il mesure | ce qu'il laisse passer |
|---|---|---|
| `qwen3tts._suspect` (dans la boucle de génération) | durée > 3× + 5 s, niveau < −38 dB, < 10 % de trames actives | une phrase qui s'arrête proprement trois mots trop tôt : niveau correct, trames actives, durée cohérente avec ce qu'elle a effectivement dit |
| `voix_personnage.py verifier` | part de l'énergie dans la bande du fondamental | tout ce qui n'est pas un problème de timbre |
| `export_audit.py` | énergie des 120 dernières ms | une fin coupée qui retombe dans le silence |

Le seul juge du contenu est un transcripteur, et il tourne déjà en permanence sur cette
machine : `whisper-server` (large-v3-turbo q5_0, français), service launchd
`com.kenhrui.whisper-server`, sur `127.0.0.1:8910`. ~0,7 s par réplique, soit **11 minutes
pour les 697 clips** des dix voix récentes.

```
../.venv-mlx/bin/python tools/audit_texte.py alice reynolds jasmine   # transcrire et mesurer
../.venv-mlx/bin/python tools/audit_texte.py --relire  scratch/audit_texte_recentes.json
../.venv-mlx/bin/python tools/audit_texte.py --regenerer scratch/audit_texte_recentes.json
../.venv-mlx/bin/python tools/audit_texte.py alice --selftest
```

## LA TRANSCRIPTION NE SUFFIT PAS — c'est le résultat principal

Sur les 697 clips, l'ASR déclare **42 clips incomplets**. En les croisant avec la durée,
**37 disent en réalité tout leur texte** : whisper francise les noms propres inventés du
projet, et chaque nom raté fait chuter le taux d'appariement de mots.

| attendu | entendu | taux |
|---|---|---|
| J'AI TROUVÉ. Les Twin Horns. | J'ai trouvé les Twinornes. | 67 % |
| Helen Shard. L'arc. Ne l'écoute pas, petit… | Elinchard. Lark. Ne l'écoute pas, petit… | 71 % |
| On quitte Ashber, petit Art. Cap sur Xyrus. | On quitte H-Peur, Petit Tarte, Cap sur Xyrus. | 75 % |

Régénérer sur le seul verdict ASR aurait donc **refait 37 clips sains pour en réparer 5**.
D'où le croisement, qui est la vraie mesure : un clip réellement tronqué est aussi trop
**court** pour son texte, un clip qui déraille est trop **long**. Deux mesures indépendantes
qui doivent tomber d'accord avant qu'on touche à un fichier livré.

Repères de durée mesurés sur le lot (durée réelle / durée attendue à 14 car/s) :
médiane **1,01**, p75 1,20, p90 1,45, p95 1,84, p99 2,79.

## Les verdicts

| verdict | condition | issue |
|---|---|---|
| `MUET` | rien de transcrit | à regénérer |
| `RADOTAGE` | mots entendus > 1,6 × attendus **et** durée > 1,3 × | à regénérer |
| `TRAÎNE` | ≥ 8 mots attendus **et** durée > 2,2 × | à regénérer |
| `TRONQUÉ` | couverture < 80 % **et** durée < 0,75 × | à regénérer |
| `à écouter` | couverture < 80 %, durée normale | l'oreille tranche |

L'ordre compte, et ce n'est pas cosmétique : le radotage se teste **avant** la couverture,
parce qu'un clip peut être les deux à la fois et que c'est le cas typique. `reynolds_34b01b500e`
émet dix secondes de syllabes inventées (« Peyo, oz, do, do et gud, so ever, willow willok »)
PUIS la moitié de sa réplique ; testé d'abord sur la couverture, il ressortait « fin manquante,
durée normale » — à écouter — alors que c'est le clip le plus abîmé du lot.

Le seuil `TRAÎNE` à 2,2 prend les cinq clips les plus longs du lot et laisse les six qui sont
entre 2,0 et 2,2 : ceux-là disent tout leur texte, lentement. Régénérer sur un doute dégrade au
tirage.

## Le détecteur se valide sur un défaut fabriqué

`--selftest` prend un clip sain, le transcrit (attendu : aucun motif), le tronque à 45 % avec
ffmpeg et le retranscrit (attendu : « fin manquante »). Les deux verdicts doivent tomber sur le
même fichier, sinon le contrôle est indiscernable d'un contrôle en panne :

```
intact    ratio 100% queue 100% motif « aucun »
tronqué   ratio  25% queue   0% motif « fin manquante (25% des mots) »
SELFTEST OK
```

Il vérifie au passage le chemin technique complet — ffmpeg vers 16 kHz mono, multipart vers
`/inference`. Donner l'Ogg directement au serveur rend une transcription **vide**, c'est-à-dire
exactement le défaut cherché : sans ce test, un audit en panne aurait déclaré tout le pack muet.

## Résultat du 2026-08-26 — dix voix récentes (0.6.5 → 0.6.9)

697 clips réécoutés, **9 à regénérer** (1,3 %) :

| clip | verdict | détail |
|---|---|---|
| `jasmine_c322add692` | MUET | 8,7 s sans une syllabe pour « Je souhaite le parrainer pour un examen de rang. » |
| `reynolds_34b01b500e` | RADOTAGE | 10,7 s pour 8 mots, dix secondes de baragouin |
| `vincent_49f4b1b2cf` | TRAÎNE | 23,0 s pour 8,6 s attendues |
| `alice_0b41a2d2b3` | TRAÎNE | 11,2 s pour 4,2 s |
| `alice_f46cf74e82` | TRAÎNE | 8,6 s pour 3,1 s |
| `reynolds_f3e53b7bf1` | TRONQUÉ | 1,1 s pour 1,6 s |
| `reynolds_e7c753be08` | TRONQUÉ | 1,3 s pour 2,1 s |
| `vincent_44bafbfe92` | TRONQUÉ | 1,2 s pour 1,9 s |
| `vincent_d1050f5d94` | TRONQUÉ | 1,9 s pour 2,6 s |

Le contrôle d'énergie (`verifier`), lancé sur le même périmètre, en signale **11 autres**, et
ce sont d'autres clips : alice 1, jasmine 1, vincent 4, ellie 5. Les deux listes ne se
recoupent pas — un clip peut dire tout son texte avec le mauvais timbre, et l'inverse. Deux
critères, deux reprises :

```
../.venv-mlx/bin/python tools/voix_personnage.py reprendre <perso>          # timbre
../.venv-mlx/bin/python tools/audit_texte.py --regenerer <rapport.json>     # texte
```

## LES DEUX CRITÈRES S'OPPOSENT — le remède crée l'autre défaut

Après la reprise des neuf clips, `verifier` en a signalé **deux nouveaux** : `reynolds_f3e53b7bf1`
et `alice_f46cf74e82`, qui venaient d'être réparés. Complets, de bonne durée — et **hors bande**.
Une autre graine ne donne pas seulement un autre découpage du texte, elle donne une autre voix.

`--regenerer` mesure donc désormais les **trois** grandeurs sur chaque essai (couverture, durée,
part d'énergie dans la bande du rôle au seuil de `_douteux`) et n'écrit que si l'essai les tient
toutes. Deux corrections y ont été nécessaires, et chacune s'est vue sur le résultat :

1. **le critère de sélection ne peut pas être la seule couverture.** `vincent_49f4b1b2cf`
   (23,0 s) et `alice_0b41a2d2b3` (11,2 s) disaient déjà 92 % de leur texte : aucun essai ne
   pouvait battre ça, la fonction annonçait « 92 % → 92 % OK » et **laissait les fichiers
   intacts**. Le score pénalise maintenant l'excès de durée ;
2. **le score de départ doit être MESURÉ sur le fichier en place.** Le rapport ne porte que le
   texte et la durée : un clip hors bande y affichait un score parfait, donc imbattable, et les
   deux clips sont restés « encore défectueux » alors que les essais, eux, étaient bons.

Le dernier récalcitrant (`alice_f46cf74e82`) n'a tenu les trois critères sur aucune des 8 graines
de secours habituelles (`7000 + n·613`), et les a tenus **du premier coup** sur une autre famille
(`20000`). Devant un clip qui résiste, élargir la plage de graines avant de conclure.

## État final du 2026-08-26

| voix | défauts de texte | douteux d'énergie |
|---|---|---|
| reynolds | 0 (3 réparés) | 0 (1 réparé) |
| alice | 0 (3 réparés) | 1 — `alice_1628cda9dd`, qui dit 100 % de son texte |
| vincent | 0 (3 réparés) | 0 (4 réparés) |
| jasmine | 0 (1 réparé) | 1 — `jasmine_dae7e16c7e`, texte complet lui aussi |
| ellie | 0 | **5 non traités** — voir la réserve ci-dessous |
| adam, durden, helen, lilia, angela | 0 | 0 |

Les douze clips repris ont tous été revérifiés par un second passage, sur les deux critères.

Les deux douteux d'énergie qui résistent disent **tout leur texte** (100 % et 83 %) : leur
défaut est purement spectral, et quatre à huit graines n'ont pas fait mieux. À écouter avant de
décider s'il y a quelque chose à réparer.

**Réserve sur ellie, adam et angela.** Ces trois voix déclarent un `grave_demi_tons` **négatif**
(monter la voix), et `descente_voix.descendre()` renvoyait l'onde intacte pour toute valeur
≤ 0 : leurs 121 clips en service ne portent aucun décalage. La fonction est corrigée depuis, si
bien qu'une reprise appliquerait désormais le décalage — cinq clips montés de deux demi-tons au
milieu d'un lot qui, lui, n'a rien reçu. Les cinq clips d'ellie attendent donc l'arbitrage :
remettre les trois voix à niveau (121 clips, et une revalidation à l'oreille), ou déclarer leur
décalage à zéro pour aligner le code sur ce qui est livré.
