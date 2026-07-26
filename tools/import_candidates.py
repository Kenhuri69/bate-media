#!/usr/bin/env python3
"""Importe les voix candidates de la forge et les indexe, pour garder trace du casting.

Pourquoi versionner ces extraits alors que les répliques finales, elles, partent en
Release : ils sont peu nombreux, très légers en Ogg, et documentent une décision — quel
timbre a été retenu pour chaque personnage, et lesquels ont été écartés. On peut ainsi
réécouter les alternatives sans relancer la génération.

Les WAV de la forge (~700 Ko chacun) sont convertis en Ogg (~50 Ko) : 90 candidats
tiennent alors dans quelques mégaoctets, ce qui reste honnête pour un dépôt Git.

    python3 tools/import_candidates.py
    python3 tools/import_candidates.py --dry-run
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FORGE_DEFAUT = Path.home() / "workspace/voice-agent/training/forge"
OGGENC = shutil.which("oggenc")


def _convertit(source: Path, cible: Path) -> bool:
    """WAV -> Ogg Vorbis. Le ffmpeg de Homebrew n'a pas libvorbis, d'où oggenc."""
    cible.parent.mkdir(parents=True, exist_ok=True)
    try:
        if OGGENC:
            subprocess.run([OGGENC, "-Q", "-q", "4", "-o", str(cible), str(source)],
                           check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
                            "-c:a", "vorbis", "-strict", "-2", "-q:a", "4", str(cible)],
                           check=True)
        return True
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"  échec conversion {source.name} ({e.__class__.__name__})", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forge", default=str(FORGE_DEFAUT))
    ap.add_argument("--prefixe", default="bate-",
                    help="ne prendre que les forges de ce projet (défaut : bate-)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    forge = Path(args.forge).expanduser()
    index, total, convertis = {}, 0, 0
    for fichier in sorted(forge.glob(f"{args.prefixe}*/candidates.json")):
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        slug = donnees.get("slug", fichier.parent.name)
        personnage = slug[len(args.prefixe):] if slug.startswith(args.prefixe) else slug
        choix = {}
        chemin_choix = fichier.parent / "choice.json"
        if chemin_choix.exists():
            choix = json.loads(chemin_choix.read_text(encoding="utf-8"))

        entrees = []
        for candidat in donnees.get("candidats", []):
            source = Path.home() / "workspace/voice-agent" / candidat["wav"]
            if not source.exists():
                continue
            cible = RACINE / "candidates" / personnage / f"cand_{candidat['n']:02d}.ogg"
            total += 1
            if not args.dry_run and (not cible.exists()
                                     or cible.stat().st_mtime < source.stat().st_mtime):
                if _convertit(source, cible):
                    convertis += 1
            entrees.append({
                "n": candidat["n"], "fichier": cible.name, "seed": candidat["seed"],
                "description": candidat["description"],
                "retenu": bool(choix) and choix.get("n") == candidat["n"],
                "retenu_par": choix.get("valide") if choix.get("n") == candidat["n"] else None,
            })
        if entrees:
            index[personnage] = {"slug": slug, "candidats": entrees}
            marque = next((e["n"] for e in entrees if e["retenu"]), None)
            print(f"  {personnage:<16} {len(entrees)} candidats"
                  + (f", retenu n°{marque}" if marque else ", aucun retenu"))

    if not index:
        print("aucun candidat trouvé", file=sys.stderr)
        return 1
    print(f"\n{len(index)} personnages, {total} candidats"
          + (f", {convertis} convertis" if not args.dry_run else " (dry-run)"))
    if args.dry_run:
        return 0

    (RACINE / "candidates").mkdir(exist_ok=True)
    (RACINE / "candidates" / "index.json").write_text(
        json.dumps({"source": "voice-agent forge", "personnages": index},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    poids = sum(f.stat().st_size for f in (RACINE / "candidates").rglob("*.ogg")) / 1e6
    print(f"candidates/index.json écrit — {poids:.1f} Mo d'extraits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
