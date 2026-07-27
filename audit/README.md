# Audit des répliques — clips à vérifier à l'oreille

**45 suspects sur 1642 clips** (2.7 %).

Deux mesures, dont une seule fonctionne vraiment :

- **`fin`** — énergie des 120 dernières millisecondes rapportée à l'énergie moyenne.
  Une phrase qui se termine normalement retombe dans le silence (0,01–0,02) ; un clip
  coupé en plein son garde toute sa puissance jusqu'au bout (mesuré jusqu'à 3,0).
  C'est le détecteur utile.
- **`ratio`** — durée réelle sur durée attendue d'après la longueur du texte. Ne
  détecte presque rien : les répliques contenant « … » durent même PLUS longtemps
  que les autres (73 contre 63 ms par caractère), la suspension créant une pause.

Les fichiers sont dans `suspects/`, nommés `<mesure>_<id>.ogg` pour que l'ordre
alphabétique corresponde à la gravité décroissante.

| fin | ratio | durée | personnage | id | texte |
|---:|---:|---:|---|---|---|
| 3.04 | 164% | 4.9s | As | `as_ch60_02` | Un adversaire selon mon cœur. Rare, ici. En garde. |
| 2.98 | 152% | 5.1s | Reynolds | `reynolds_ch20_01` | De ta déviance, entre autres. Et d'autre chose : de toi. |
| 2.73 | 182% | 4.3s | Lilia | `lilia_ch26_02` | Tu es bizarre, toi. Mais bon, d'accord. |
| 2.31 | 230% | 4.4s | Perrin | `perrin_ch57_03` | Toi, ne pas éblouir ? On parie ? |
| 2.28 | 349% | 4.2s | Tessia | `tessia_ch10_03` | Je m'appelle Tessia. |
| 2.20 | 540% | 40.0s | Perrin | `perrin_ch45_04` | Félicitations, t'es déjà sur leur liste. Reste plus qu'à survivre aux cours de noyau — on dit que le prochain va faire mal. |
| 2.15 | 237% | 4.0s | Gardien | `gardien_ch54_04` | Oui. Là, tu es presque prêt. |
| 2.15 | 208% | 6.9s | Instructrice | `instructrice_ch61_02` | Sagesse rare chez un talent aussi jeune. Ça te servira. |
| 2.12 | 144% | 6.8s | Vincent | `vincent_ch28_03` | Bienvenue chez les aventuriers, gamin. La partie sérieuse commence maintenant. |
| 2.05 | 113% | 5.6s | Alice | `alice_ch20_03` | On y reviendra. Ce n'est pas le genre de décision qu'on prend sur un coin de table. |
| 2.02 | 240% | 14.9s | Sylvia | `sylvia_ch09_05` | Une zone étroite entre les Clairières des Bêtes et la Forêt d'Elshire. Personne ne connaît cet endroit. |
| 1.96 | 119% | 3.9s | Vincent | `vincent_ch31_03` | Personne ne t'en voudrait de ralentir un peu, tu sais. |
| 1.95 | 387% | 22.4s | Reynolds | `reynolds_ch22_01` | Xyrus. La plus grande cité de la région, et la porte de l'académie. Tu vas t'y perdre, au début. |
| 1.93 | 135% | 6.0s | Alice | `alice_ch04_02` | Il est encore tout noir, comme il se doit à cet âge. Ça grandira avec toi. |
| 1.90 | 135% | 7.5s | Réceptionniste | `receptionniste_ch38_02` | Entre les Tombes Redoutées et tes contrats réguliers, ton dossier parle pour toi, figure-toi. |
| 1.89 | 150% | 6.0s | Gardien | `gardien_ch53_03` | Curieux plutôt qu'avide. C'est ainsi qu'on survit à ce que je suis. |
| 1.76 | 170% | 3.5s | Perrin | `perrin_ch58_03` | Comment tu... tu vois tout venir ! |
| 1.72 | 152% | 5.1s | Reynolds | `reynolds_ch06_01` | Tout ira bien, petit Art. Les Twin Horns nous protègent. |
| 1.66 | 1622% | 37.1s | Arthur | `arthur_ch15_01` | Promis. Dès que j'en aurai l'occasion. |
| 1.52 | 97% | 12.5s | Agent | `agent_ch69_01` | L'aile ouest, les archives... c'était pour effacer une trace. Un nom, une lignée, quelque chose que certaines familles veulent voir disparaître de l'histoire de Xyrus. On m'a payé pour brûler, pas pour comprendre. |
| 1.43 | 172% | 4.4s | Tessia | `tessia_ch12_03` | Non... Je veux savoir. Laissez-les entrer. |
| 1.39 | 103% | 11.3s | Capitaine de milice | `capitaine-de-milice_ch85_01` | On a gagné, gamin. Mais regarde autour de toi. Chaque bannière qui flotte encore, c'est trois qui ne flotteront plus. C'est ça, la guerre. Ceux des académies l'oublient trop souvent. |
| 1.36 | 149% | 7.6s | Maître du culte | `maitre-du-culte_ch91_04` | ...L'insolence jusqu'au bord de l'abîme. Soit. Que ta chute serve d'ultime offrande. |
| 1.36 | 104% | 12.2s | Arthur | `note_ch78_04` | (Le premier fil qui remonte vraiment. Un notable, un soutien, un maillon assez haut pour savoir des noms. Et un homme terrifié parle toujours. Presque fini — reste à savoir QUI le terrifie tant.) |
| 1.33 | 107% | 10.7s | Tessia | `tessia_ch16_04` | L'Acquire. La première technique qu'on enseigne à tout Dompteur de Bêtes : sentir la signature de mana d'une créature, pour s'accorder à elle plutôt que de la forcer. |
| 1.33 | 129% | 5.9s | Instructrice | `instructrice_ch65_02` | « Sur les routes »... décidément, tu as un passé qui déborde de ton âge. Va. |
| 1.30 | 165% | 6.4s | Réceptionniste | `receptionniste_ch30_05` | Une livraison en avance ? Ça ne s'était pas vu depuis longtemps. |
| 1.30 | 146% | 3.6s | Tessia | `tessia_ch16_09` | Pas mal, pour un premier animal étranger. |
| 1.27 | 211% | 23.4s | Committee | `committee_ch80_01` | Ce que nous avons découvert dépasse l'Académie, Note. Des gens haut placés — de vrais pouvoirs — veulent t'entendre. Et te jauger. Ta chasse locale vient de devenir une affaire d'État. |
| 1.22 | 109% | 6.0s | Gardien | `gardien_ch55_03` | L'intégration est complète. Tu portes ma Volonté comme un égal la porte. Lève-toi, porteur. |
| 1.13 | 142% | 3.8s | Perrin | `perrin_ch67_02` | ...Tu me fais flipper, là. Mais ouais. Motus. |
| 1.13 | 485% | 24.0s | Captive | `captive_ch75_04` | Maintenant tu comprends. Et comprendre, c'est déjà cesser d'être une proie facile. |
| 0.99 | 110% | 7.7s | Arthur | `narrator_ch49_01` | Le brassard noir m'attendait au réfectoire, posé sur ma table sans un mot, comme une convocation qu'on ne refuse pas. |
| 0.96 | 140% | 5.8s | Professeure | `professeure_ch48_03` | Prudent. La plupart des élèves foncent. Toi, tu pèses. Ça te servira. |
| 0.96 | 184% | 4.4s | Instructrice | `instructrice_ch73_02` | Bien parlé. En position, tout le monde ! |
| 0.93 | 122% | 12.2s | Maître du culte | `maitre-du-culte_ch92_01` | Tu marches vers ta fin avec le calme d'un vieux guerrier. Curieux enfant. Mais aucune sérénité n'arrête ce qui vient. Regarde ! Contemple l'aube d'un monde retrouvé ! |
| 0.90 | 280% | 4.9s | Vincent | `vincent_ch27_07` | C'est tout ce que je demande. |
| 0.89 | 108% | 10.0s | Réceptionniste | `receptionniste_ch62_01` | Un étudiant de Xyrus qui bat l'as du Committee ? La guilde veut voir ça de ses yeux. Passe l'épreuve de grade, et ton rang d'aventurier montera d'un cran. |
| 0.87 | 142% | 6.1s | Réceptionniste | `receptionniste_ch62_02` | Bonne réponse. L'épreuve n'est pas une formalité, cela dit. Prépare-toi. |
| 0.85 | 203% | 4.5s | Alice | `alice_ch01_01` | Chéri, il vient tout juste de naître. |
| 0.84 | 105% | 3.7s | Adam | `adam_ch07_03` | C'est fini. Plus de symboles, plus de bandits en formation. |
| 0.83 | 108% | 6.9s | Capitaine de milice | `capitaine-de-milice_ch85_03` | Dur. Juste. C'est la seule manière de tenir, je crois. Allons honorer nos morts, puis reprenons le combat. |
| 0.82 | 127% | 5.2s | Vincent | `vincent_ch37_03` | Modeste en plus de ça. Reynolds a bien fait son travail, décidément. |
| 0.00 | 12% | 1.4s | Committee | `committee_ch86_04` | Tu as libéré ce front, uni ces gens, brisé une armée. Mais ce que tu viens de lire change tout : ce n'était que le premier acte. Ce qui vient maintenant décidera bien plus que le sort de Xyrus. |
| 0.00 | 37% | 3.5s | Alice | `alice_ch20_02` | Ce n'est pas une raison de s'enfermer à la maison, Art. Mais peut-être qu'il est temps de réfléchir à comment tu te présentes au monde, en dehors de Zestier. |

## Pour trancher

Comparer un suspect à un clip sain : ces derniers ont une valeur `fin` autour de
0,01. Si l'écart s'entend, supprimer et regénérer suffit — Chatterbox échantillonne
différemment à chaque appel, la coupure est un aléa du modèle (`forcing EOS token`
dans son journal), pas un défaut du texte :

```
voice-agent forge audit --supprimer
voice-agent forge cast --min-repliques 5 --auto-select 1 -n 3 --format ogg
```

Le seuil de 0,8 est un choix, pas une vérité : certaines phrases finissent
légitimement sur une syllabe accentuée. `--seuil-fin 0.6` en reprend davantage.
