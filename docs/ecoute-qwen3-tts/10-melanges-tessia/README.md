# Lot 10 — mélanges pour Tessia : le balayage ne bat pas le timbre pur

```bash
bash docs/ecoute-qwen3-tts/ecouter.sh 6            # la même réplique sur les 7 doses
bash docs/ecoute-qwen3-tts/ecouter.sh 6b sohee     # les 8 répliques d'une seule dose
```

Le casting (lot 9) a auditionné les quatre timbres féminins purs de CustomVoice et laissé
l'arbitrage ouvert. Ce lot-ci applique à Tessia **le principe qui avait tranché pour
Arthur** : sortir les têtes de série qui ne gagnent pas sur le même critère, balayer les
doses entre elles sur les mêmes répliques réelles, et faire primer la **plage** sur la
médiane. Sur Arthur, ce balayage avait produit un mélange 50/50 meilleur que chacun de ses
composants. Ici il conclut l'inverse, et c'est un résultat, pas un échec : **aucune dose ne
bat `sohee` pur.**

Même échantillon que le lot 9 — huit vraies répliques, quatre de l'enfant de cinq ans
(ch11-14), quatre de l'adolescente de l'académie (ch45-50), les plus longues de chaque âge.
Mêmes graines : `sohee` et `ono_anna` ne sont pas régénérés, ce sont **les clips du lot 9**,
copiés. Comparer un mélange à un pur régénéré ferait entrer le tirage dans l'écart mesuré.

## Verdict mesuré

| timbre | F0 méd. | plage F0 | barycentre | écart entre âges | ambitus | verdict |
|---|---|---|---|---|---|---|
| **`sohee`** | 210 Hz | **13 Hz** | 363 Hz | **23 Hz** | 3,1 st | **passe les deux portes** |
| `sohee:0.7+ono_anna:0.3` | 212 Hz | 28 Hz | 353 Hz | 33 Hz | 3,0 st | change d'âge selon le texte |
| `sohee:0.8+serena:0.2` | 220 Hz | 41 Hz | 345 Hz | 32 Hz | 3,2 st | écarté |
| `ono_anna` | 255 Hz | 69 Hz | 354 Hz | 11 Hz | 3,1 st | dispersé d'une réplique à l'autre |
| `sohee:0.5+ono_anna:0.5` | 240 Hz | 63 Hz | 374 Hz | 26 Hz | 3,3 st | dispersé |
| `sohee:0.3+ono_anna:0.7` | 253 Hz | 89 Hz | 372 Hz | 16 Hz | 3,1 st | dispersé |
| `ono_anna:0.8+serena:0.2` | 253 Hz | 77 Hz | 366 Hz | 35 Hz | 3,3 st | écarté |

Portes : plage F0 ≤ 30 Hz **et** écart entre âges (barycentre) ≤ 30 Hz. Ce ne sont pas des
seuils physiologiques, c'est la frontière observée entre les deux paquets du lot 9 — les
écartées y étaient à 58-69 Hz de plage et 71-75 Hz d'écart.

## Ce que le balayage apprend, au-delà du classement

**Mélanger `ono_anna` coûte en dispersion plus qu'il ne rapporte en stabilité d'âge.** À
30 % elle fait passer la plage F0 de 13 à 28 Hz pour un écart d'âge qui *monte* à 33 ; à
50 % la plage explose à 63 Hz. Sa stabilité entre les deux âges ne se transmet pas au
mélange, sa dispersion si.

**Le soupçon du lot 9 est levé, et c'est le résultat le plus utile.** Le casting avertissait
que « la stabilité récompense la voix la plus plate » et que `sohee` était peut-être
régulière parce qu'elle jouait moins. L'ambitus mesuré dit non : **3,0 à 3,3 demi-tons pour
les sept candidats**, `sohee` au milieu. Elle n'est pas plus plate que les autres — elle est
simplement plus stable d'une réplique à l'autre. Le compromis qu'on craignait de payer
n'existe pas ici. (Sur Arthur, il existait : le timbre retenu avait le plus petit ambitus du
lot, 3,6 st contre 5,1-5,8.)

**Le sens de l'écart d'âge diffère selon la candidate**, et aucun prompt d'âge n'est
appliqué — c'est le texte seul qui les fait bouger :

| | enfant → ado (F0) | enfant → ado (barycentre) |
|---|---|---|
| `sohee` | 207 → 215 Hz | 343 → 365 Hz |
| `ono_anna` | 284 → 240 Hz | 360 → 348 Hz |

`sohee` monte légèrement en devenant adolescente, `ono_anna` descend de 44 Hz. Aucune des
deux ne fait ce que le récit demanderait — mais celle de `sohee` est faible, et une voix
qui bouge peu est celle qu'un prompt de registre pourra encore infléchir.

## Ce que la mesure ne dit pas

Elle désigne `sohee`, elle ne le choisit pas. Deux questions restent à l'oreille :

1. **Est-ce Tessia ?** 210 Hz est plausible pour une adolescente comme pour une petite
   fille, mais la hauteur ne fait pas le personnage.
2. **Tient-elle les deux âges ?** C'est la question que le lot 6b pose directement : les
   quatre répliques de l'enfant puis les quatre de l'adolescente, d'affilée, même timbre.

## Suite

Le timbre retenu se note dans la production (`tools/voix_tessia.py --timbre`), et **l'âge
par prompt est un second arbitrage, délibérément non mêlé à celui-ci**. Sur Arthur, le
prompt d'âge crée un vrai registre d'enfant au stade bambin (+48 Hz) mais ne fait plus rien
au-delà : à cinq ans, Tessia est déjà hors de la zone où ce levier a montré un effet. Il se
testera sur ses seules répliques d'enfant, mesuré, plutôt que décidé à l'avance.

Mesures brutes : [`rapport_melanges.json`](rapport_melanges.json). Production :
[`../../tools/tournoi_timbre_tessia.py`](../../tools/tournoi_timbre_tessia.py).

> L'échantillon de ce lot vient de l'extraction du 2026-08-09. `lines.json` a été ré-extrait
> depuis (114 répliques, `chapter_10.dtl` découpé en `10a`/`10b`) : les huit répliques
> auditionnées ici existent toujours et leur texte n'a pas changé, mais leurs identifiants de
> forge, eux, ont bougé. Les textes exacts sont dans `rapport_melanges.json`.
