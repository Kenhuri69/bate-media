#!/usr/bin/env python3
"""Ré-extrait les répliques d'un personnage depuis les timelines ACTUELLES du jeu.

    python3 tools/extraire_repliques.py bate-arthur Arthur Note narrator
    python3 tools/extraire_repliques.py bate-tessia Tessia --max-chapitre 60

Le fichier `training/forge/<slug>/lines.json` est le texte de référence de la forge : c'est
lui que `voix_age_arthur.py` lit pour savoir quoi faire dire, et lui que `tessia_casting.py`
échantillonne. Il datait du 2026-07-26 et les timelines ont beaucoup bougé depuis — 728
répliques d'Arthur, Note et narrator sur les ch0-60 à l'époque, **4433** aujourd'hui.
Produire des voix sur ce fichier-là reviendrait à faire dire au jeu ce qu'il ne dit plus.

L'extraction elle-même n'est pas réimplémentée : elle vient de `voice_forge._extrait_repliques`,
seule source de vérité du format d'identifiant. Une deuxième copie de cette règle finirait par
diverger de celle du moteur, et un identifiant qui diverge ne se voit pas — le jeu joue un
fichier existant sur la mauvaise réplique.

L'ancien fichier est conservé à côté (`lines.<horodatage>.json`) : il porte les textes sur
lesquels les clips déjà livrés ont été produits, et c'est le seul moyen de savoir lesquels sont
devenus caducs.
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

RACINE = Path.home() / "workspace"
FORGE = RACINE / "voice-agent/training/forge"
DIALOGUES = RACINE / "bate/dialogues"

sys.path.insert(0, str(RACINE / "voice-agent/training"))


def _numero(etiquette: str):
    m = re.search(r"\d+", etiquette)
    return int(m.group()) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", help="dossier de forge, ex. bate-arthur")
    ap.add_argument("roles", nargs="+", help="noms EXACTS écrits dans les timelines")
    ap.add_argument("--max-chapitre", type=int, default=None,
                    help="ne garder que les chapitres jusqu'à ce numéro (inclus)")
    ap.add_argument("--dialogues", default=str(DIALOGUES))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import voice_forge

    dossier = FORGE / args.slug
    if not dossier.is_dir():
        print(f"forge inconnue : {dossier}", file=sys.stderr)
        return 1

    lignes = []
    for role in args.roles:
        lignes += [{**r, **voice_forge._expressivite(role)}
                   for r in voice_forge._extrait_repliques(Path(args.dialogues), role)]
    if args.max_chapitre is not None:
        lignes = [l for l in lignes
                  if (n := _numero(l["chapitre"])) is not None and n <= args.max_chapitre]
    lignes.sort(key=lambda l: (_numero(l["chapitre"]), l["chapitre"], l["role"], l["id"]))

    doublons = [i for i, c in Counter(l["id"] for l in lignes).items() if c > 1]
    if doublons:
        # Un identifiant en double, c'est un clip qui en écrase un autre : deux répliques
        # différentes, un seul fichier, aucune erreur nulle part. Refuser plutôt que livrer.
        print(f"{len(doublons)} identifiants en double, extraction refusée : "
              f"{', '.join(sorted(doublons)[:5])}…", file=sys.stderr)
        return 1

    par_role = Counter(l["role"] for l in lignes)
    chapitres = sorted({l["chapitre"] for l in lignes}, key=lambda c: (_numero(c), c))
    print(f"{len(lignes)} répliques — {dict(par_role)} — {len(chapitres)} timelines "
          f"({chapitres[0]} → {chapitres[-1]})")

    cible = dossier / "lines.json"
    if cible.exists():
        # Comparaison bornée à la MÊME plage, sinon les chapitres que la borne exclut
        # s'afficheraient comme « disparus » alors qu'ils n'ont pas été regardés.
        anciennes = {l["id"]: l["texte"]
                     for l in json.loads(cible.read_text(encoding="utf-8"))
                     if args.max_chapitre is None
                     or ((n := _numero(l["chapitre"])) is not None and n <= args.max_chapitre)}
        nouvelles = {l["id"]: l["texte"] for l in lignes}
        communs = set(anciennes) & set(nouvelles)
        print(f"  contre l'extraction précédente : +{len(set(nouvelles) - set(anciennes))} "
              f"ajoutées, -{len(set(anciennes) - set(nouvelles))} disparues, "
              f"{sum(1 for i in communs if anciennes[i] != nouvelles[i])} textes modifiés")

    if args.dry_run:
        return 0

    if cible.exists():
        from datetime import datetime, timezone
        horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        sauvegarde = cible.with_suffix(f".{horodatage}.json")
        shutil.copy2(cible, sauvegarde)
        print(f"  ancienne extraction gardée dans {sauvegarde.name}")

    cible.write_text(json.dumps(lignes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"écrit : {cible}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
