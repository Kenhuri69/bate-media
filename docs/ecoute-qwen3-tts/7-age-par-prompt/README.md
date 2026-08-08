# Lot 7 — l'âge par le prompt, timbre validé intact

Le lot 6 faisait l'âge en diluant `aiden:0.5+ryan:0.5` dans une composante plus aiguë.
Efficace sur la hauteur, mais au stade toddler le timbre validé ne pesait plus que **20 %**
du mélange. Refusé — et c'est la bonne objection : une validation porte sur une voix
entendue, pas sur une formule qui en garde le nom.

Ce lot teste le levier qui n'avait pas été essayé : CustomVoice accepte un `instruct` en
français, et l'âge perçu tient autant au débit, à l'attaque et au souffle qu'à la hauteur.
Sept répliques parlées du stade toddler, quatre formulations, comparées aux dilutions.

| variante | F0 | plage | **timbre validé gardé** |
|---|---|---|---|
| dilution refusée (`serena:0.8`) | 242 Hz | 37 | **20 %** |
| **`enfant-insistant` (prompt seul)** | **164 Hz** | 67 | **100 %** |
| dilution douce (`serena:0.3`) | 162 Hz | 70 | 70 % |
| `enfant-sobre` (prompt seul) | 149 Hz | 45 | **100 %** |
| `enfant-jeu` (prompt seul) | 130 Hz | 73 | **100 %** |
| timbre nu, sans prompt | 125 Hz | 40 | **100 %** |

**Le prompt fait aussi bien que la dilution à 30 % sans toucher au timbre** — 164 contre
162 Hz. À hauteur égale il est donc strictement meilleur. Ce qu'il ne fait pas : atteindre
les 270 Hz d'un enfant de trois ans. Cette cible était un repère physiologique, pas une
exigence : elle ne vaut pas de dénaturer la voix du personnage.

**Une formulation se mesure comme une dose.** `enfant-jeu` retombe à 130 Hz quand
`enfant-insistant` monte à 164 : plus insistant ne veut pas dire plus haut. Les deux
décrivent une FAÇON DE PARLER et non un timbre — CustomVoice n'accepte pas qu'on lui
décrive une voix, c'était le rôle de VoiceDesign, écarté pour sa dérive.

**Le registre annule le prompt sur la narration.** Sur le lot toddler complet, les
répliques parlées d'Arthur sortent à 164 Hz et ses narrations du même stade à 127 : le
registre « posé, presque murmuré, sans emphase » l'emporte sur la consigne d'âge. D'où la
règle retenue — **la narration ne suit pas l'âge**, une seule voix de narrateur sur tout
le jeu. Arthur parle jeune et raconte d'une voix posée.

## Écouter

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 7
```

La même réplique enchaînée sur les six variantes, avec la hauteur et le pourcentage de
timbre conservé annoncés à chaque fois. Les deux dilutions sont là pour comparaison — ce
ne sont pas des options, elles écrasent le timbre validé.
