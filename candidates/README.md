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

## Statut

Ces extraits prononcent une réplique réelle du personnage — ils relèvent donc du même statut
que les autres contenus de ce dépôt : œuvre dérivée, usage personnel, non commercial.
Voir [`../NOTICE.md`](../NOTICE.md).
