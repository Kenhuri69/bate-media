# Pack de voix 0.6.9 — dix personnages de plus

**+813 clips par rapport à la 0.6.1 : 9 065 fichiers au total.** Dix personnages qui
n'avaient aucune voix en parlent maintenant, et les quatre déjà présents sont inchangés.

| voix | 0.6.1 | 0.6.9 |
|---|---|---|
| Arthur | 7 532 | 7 532 |
| Virion | 350 | 350 |
| Tessia | 247 | 247 |
| Sylvie | 99 | 99 |
| **Reynolds** | — | **207** |
| **Alice** | — | **143** |
| **Vincent** | — | **85** |
| **Ellie** | — | **82** |
| **Jasmine** | — | **77** |
| **Lilia** | — | **36** |
| **Adam** | — | **28** |
| **Durden** | — | **17** |
| **Helen** | — | **11** |
| **Angela** | — | **11** |

Les versions 0.6.5 à 0.6.8 ont été construites et étiquetées sans jamais être publiées :
elles ajoutaient Alice et Reynolds (0.6.5), les Twin Horns (0.6.6), leur remixage et une
descente de hauteur sur le motif de Virion (0.6.7), puis Vincent, Lilia et Ellie (0.6.9).
Cette release les porte toutes.

Archive : `bate-media-voices-0.6.9.tar.zst`, 574,7 Mo, 9 069 entrées.
Vérifiée avant publication : somme SHA-256 conforme, et les quatorze dossiers de voix
présents avec leur compte attendu.

## Réserve connue sur le manifeste embarqué

`manifest.json` annonce le bon nombre de répliques pour les quatorze voix, mais sa liste
détaillée `fichiers` (avec `texte`, `chapitre`, `moteur` par clip) **n'est remplie que pour
Arthur, Tessia, Virion et Sylvie**. Elle est vide pour les dix voix ajoutées ici.

Conséquence exacte, et rien de plus : `tools/verify_pack.py` compare cette liste vide au
compteur de répliques et rapporte donc « MANQUE » sur ces dix voix — **c'est un faux
négatif**, les fichiers audio sont bien dans l'archive (vérifié en listant le tar). Le jeu
n'utilise pas ce manifeste : `tools/fetch-voices.py` contrôle la somme SHA-256 de l'archive
puis extrait, et le moteur ne lit que les `.ogg`. L'installation et la lecture ne sont pas
affectées.

Ce qui l'est : l'auditabilité du pack. Ces listes portent le texte prononcé par chaque clip,
qui ne se déduit pas d'un scan du disque — seul l'outil qui a produit les clips le connaît.
Elles n'ont donc **pas** été reconstruites ici plutôt que devinées. À réparer côté forge
avant la prochaine version.
