# Voix des personnages

Un dossier par **voix** (`arthur/`, `tessia/`…), rempli par la forge.
Non versionné : voir README à la racine.

## Nommage : `<rôle>_<empreinte>.ogg`

L'empreinte est celle du **texte** de la réplique, pas de sa place dans une timeline —
`tools/empreinte.py` la calcule, `bate/src/systems/audio/VoiceLines.cs` la recalcule côté jeu.

    voices/arthur/narrator_c03132187d.ogg

Les clips s'appelaient auparavant `<rôle>_ch<NN>_<II>`, où `II` était le rang de la réplique.
Ce nom ne disait que sa **place** : insérer une ligne en amont périmait en silence tous les
clips suivants, et rien ne pouvait le détecter — le fichier attendu existait toujours, il
disait seulement autre chose. C'est ce qui est arrivé au pack 0.3.0 quand les chapitres 0 à 9
du jeu ont été réécrits.

Avec l'empreinte :

| événement sur une réplique | conséquence |
|---|---|
| déplacée | garde son clip |
| réécrite | perd son clip → silence **visible**, à régénérer seul |
| ajoutée | ne dérange rien |

## Rôle et dossier ne sont pas la même chose

Le **rôle** est ce que la timeline écrit devant les deux-points (`narrator`, `Arthur`,
`Note`) et il porte l'empreinte. Le **dossier** est la voix qui le dit, et plusieurs rôles
peuvent la partager :

| dossier | rôles | pourquoi |
|---|---|---|
| `arthur` | `arthur`, `narrator`, `note` | « Note » est son pseudonyme d'aventurier ; le jeu est narré à la première personne |

## Vérifier

    python3 tools/empreinte.py --selftest              # la règle contre le contrat partagé
    python3 tools/reconcile_voices.py --tout           # ce qui ne correspond plus, sans écrire

Et côté jeu, la réponse binaire — chaque clip correspond-il à une réplique existante :

    python3 tools/checks/check_voices.py --plan
