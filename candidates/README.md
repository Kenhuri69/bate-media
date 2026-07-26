# Voix candidates — trace du casting

Pour chaque personnage, les timbres proposés par la pipeline, dont **celui qui a été
retenu**. `index.json` donne pour chaque candidat sa description, sa graine et son statut.

Contrairement aux répliques finales — distribuées en Release, cf. le README de la racine —
ces extraits sont versionnés ici : ils sont peu nombreux, légers en Ogg (~50 Ko chacun), et
documentent une décision. On peut réécouter une alternative écartée sans relancer la
génération.

    afplay candidates/tessia/cand_02.ogg      # écouter un candidat écarté

## Reproduire ou changer un choix

Une voix est entièrement déterminée par sa **description** et sa **graine** : les deux
figurent dans `index.json`, donc un candidat est reconstructible à l'identique. Pour changer
le timbre d'un personnage :

    voice-agent forge listen bate-tessia            # réécouter les trois
    voice-agent forge select bate-tessia 2          # préférer le second
    voice-agent forge lines  bate-tessia --personnage Tessia   # regénérer ses répliques

## Essais d'expressivité

Choisir un timbre ne suffit pas toujours : la voix retenue pour Arthur (`cand_02.ogg`)
manquait de l'énergie du héros. `arthur/expressivite/` compare trois dosages sur une même
réplique, avec la même voix — `reglages.json` donne les valeurs exactes.

    afplay candidates/arthur/expressivite/B_passionne.ogg

Deux paramètres, à bouger **ensemble** : `exaggeration` pousse l'intensité émotionnelle,
tandis que `cfg_weight` contrôle la fidélité au timbre de référence. Le laisser haut bride
les écarts de prosodie qui font justement l'énergie : monter l'un sans baisser l'autre donne
une voix forte mais raide.

Sur un personnage qui parle à la fois en dialogue et en narration — Arthur cumule les deux —
un réglage unique ne convient pas : l'introspection supporte mal l'emphase des scènes
d'action. Même voix, deux registres.

## Statut

Ces extraits prononcent une réplique réelle du personnage — ils relèvent donc du même statut
que les autres contenus de ce dépôt : œuvre dérivée, usage personnel, non commercial.
Voir [`../NOTICE.md`](../NOTICE.md).
