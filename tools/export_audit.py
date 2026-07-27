#!/usr/bin/env python3
"""Exporte le rapport d'audit et rassemble les clips suspects pour écoute à distance.

Le pack complet part en Release (une centaine de Mo) ; mais pour juger la qualité on n'a
besoin que des cas douteux. Ce script les copie dans `audit/suspects/` — quelques
mégaoctets, versionnés, écoutables directement depuis un clone du dépôt — et écrit un
rapport lisible qui donne pour chacun sa mesure, son texte et son personnage.

    python3 tools/export_audit.py            # rapport + copie des suspects
    python3 tools/export_audit.py --dry-run
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
VOICE_AGENT = Path.home() / "workspace/voice-agent"
AUDIT = VOICE_AGENT / "training/audit_lines.py"
PY_AUDIT = VOICE_AGENT / ".venv-chatterbox/bin/python"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seuil-fin", type=float, default=0.8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not AUDIT.exists():
        print(f"audit introuvable : {AUDIT}", file=sys.stderr)
        return 1

    # On réutilise l'outil de la forge plutôt que de redéfinir la mesure ici : une seule
    # définition de « clip suspect », pas deux qui divergeront.
    sys.path.insert(0, str(AUDIT.parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_lines", AUDIT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as e:
        print(f"lancer ce script avec {PY_AUDIT} (soundfile requis) : {e}", file=sys.stderr)
        return 1

    clips = module._collecte("bate-")
    if not clips:
        print("aucune réplique", file=sys.stderr)
        return 1
    import statistics
    references = [c["duree"] / len(c["texte"]) for c in clips
                  if len(c["texte"]) >= 30 and c["duree"] > 0]
    par_caractere = statistics.median(references)

    suspects = []
    for c in clips:
        attendue = par_caractere * len(c["texte"])
        ratio = c["duree"] / attendue if attendue else 1.0
        motif = ("trop court" if (c["duree"] < module.DUREE_PLANCHER or ratio < 0.6)
                 else "fin coupée" if c["fin"] > args.seuil_fin else "")
        if motif:
            suspects.append({**c, "ratio": ratio, "attendue": attendue, "motif": motif})
    suspects.sort(key=lambda c: -c["fin"])

    dossier = RACINE / "audit" / "suspects"
    if not args.dry_run:
        shutil.rmtree(dossier, ignore_errors=True)
        dossier.mkdir(parents=True, exist_ok=True)

    lignes = [
        "# Audit des répliques — clips à vérifier à l'oreille",
        "",
        f"**{len(suspects)} suspects sur {len(clips)} clips** ({100 * len(suspects) / len(clips):.1f} %).",
        "",
        "Deux mesures, dont une seule fonctionne vraiment :",
        "",
        "- **`fin`** — énergie des 120 dernières millisecondes rapportée à l'énergie moyenne.",
        "  Une phrase qui se termine normalement retombe dans le silence (0,01–0,02) ; un clip",
        "  coupé en plein son garde toute sa puissance jusqu'au bout (mesuré jusqu'à 3,0).",
        "  C'est le détecteur utile.",
        "- **`ratio`** — durée réelle sur durée attendue d'après la longueur du texte. Ne",
        "  détecte presque rien : les répliques contenant « … » durent même PLUS longtemps",
        "  que les autres (73 contre 63 ms par caractère), la suspension créant une pause.",
        "",
        "Les fichiers sont dans `suspects/`, nommés `<mesure>_<id>.ogg` pour que l'ordre",
        "alphabétique corresponde à la gravité décroissante.",
        "",
        "| fin | ratio | durée | personnage | id | texte |",
        "|---:|---:|---:|---|---|---|",
    ]
    for c in suspects:
        nom = f"{c['fin']:.2f}".replace(".", "") + f"_{c['id']}.ogg"
        if not args.dry_run:
            shutil.copy2(c["fichier"], dossier / nom)
        texte = c["texte"].replace("|", "\\|")
        lignes.append(f"| {c['fin']:.2f} | {c['ratio']:.0%} | {c['duree']:.1f}s | "
                      f"{c['personnage']} | `{c['id']}` | {texte} |")

    lignes += [
        "",
        "## Pour trancher",
        "",
        "Comparer un suspect à un clip sain : ces derniers ont une valeur `fin` autour de",
        "0,01. Si l'écart s'entend, supprimer et regénérer suffit — Chatterbox échantillonne",
        "différemment à chaque appel, la coupure est un aléa du modèle (`forcing EOS token`",
        "dans son journal), pas un défaut du texte :",
        "",
        "```",
        "voice-agent forge audit --supprimer",
        "voice-agent forge cast --min-repliques 5 --auto-select 1 -n 3 --format ogg",
        "```",
        "",
        "Le seuil de 0,8 est un choix, pas une vérité : certaines phrases finissent",
        "légitimement sur une syllabe accentuée. `--seuil-fin 0.6` en reprend davantage.",
    ]

    rapport = RACINE / "audit" / "README.md"
    if not args.dry_run:
        rapport.parent.mkdir(parents=True, exist_ok=True)
        rapport.write_text("\n".join(lignes) + "\n", encoding="utf-8")
        (RACINE / "audit" / "suspects.json").write_text(json.dumps(
            [{"id": c["id"], "personnage": c["personnage"], "texte": c["texte"],
              "fin": round(c["fin"], 3), "ratio": round(c["ratio"], 3),
              "duree": round(c["duree"], 2), "motif": c["motif"]} for c in suspects],
            ensure_ascii=False, indent=2), encoding="utf-8")
        poids = sum(f.stat().st_size for f in dossier.glob("*.ogg")) / 1e6
        print(f"{len(suspects)} suspects copiés ({poids:.1f} Mo) -> audit/suspects/")
        print(f"rapport : audit/README.md")
    else:
        print(f"(dry-run) {len(suspects)} suspects seraient exportés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
