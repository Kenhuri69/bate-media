#!/usr/bin/env python3
"""Assemble un pack de médias immuable, prêt à être attaché à une Release GitHub.

Un pack est une archive **tar.zst** accompagnée de sa somme SHA-256 et d'un manifeste
embarqué. Pourquoi une archive de Release plutôt que des binaires versionnés dans Git :
un pack se télécharge en un appel, se vérifie, se remplace sans réécrire l'historique, et
n'alourdit jamais un `git clone` du code.

    python3 tools/build_pack.py --version 0.1.0
    python3 tools/build_pack.py --version 0.1.0 --inclure voices,video

Sortie : `dist/bate-media-<contenu>-<version>.tar.zst` + `.sha256`.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIERS = ("voices", "video", "animation")


def _sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="version du pack, ex. 0.1.0")
    ap.add_argument("--inclure", default="voices",
                    help=f"dossiers à empaqueter parmi {','.join(DOSSIERS)}")
    ap.add_argument("--niveau", type=int, default=19, help="compression zstd (1-19)")
    args = ap.parse_args()

    inclus = [d.strip() for d in args.inclure.split(",") if d.strip() in DOSSIERS]
    if not inclus:
        print(f"rien à inclure (attendu : {DOSSIERS})", file=sys.stderr)
        return 1
    presents = [d for d in inclus if any((RACINE / d).rglob("*")) and (RACINE / d).is_dir()]
    if not presents:
        print("les dossiers demandés sont vides — lancer tools/sync_from_forge.py d'abord",
              file=sys.stderr)
        return 1

    manifeste = {}
    chemin_manifeste = RACINE / "manifest.json"
    if chemin_manifeste.exists():
        manifeste = json.loads(chemin_manifeste.read_text(encoding="utf-8"))
    manifeste["version_pack"] = args.version
    manifeste["construit"] = dt.datetime.now().isoformat(timespec="seconds")
    manifeste["contenu"] = presents
    chemin_manifeste.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2),
                               encoding="utf-8")

    etiquette = "-".join(presents)
    base = f"bate-media-{etiquette}-{args.version}"
    dist = RACINE / "dist"
    dist.mkdir(exist_ok=True)
    archive_zst = dist / f"{base}.tar.zst"

    fichiers = 0
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        chemin_tar = Path(tmp.name)
    try:
        with tarfile.open(chemin_tar, "w") as tar:
            # Le manifeste voyage DANS le pack : un pack téléchargé doit être vérifiable
            # sans le dépôt, et savoir dire ce qu'il contient.
            tar.add(chemin_manifeste, arcname=f"{base}/manifest.json")
            tar.add(RACINE / "NOTICE.md", arcname=f"{base}/NOTICE.md")
            for dossier in presents:
                for f in sorted((RACINE / dossier).rglob("*")):
                    if f.is_file() and not f.name.startswith("."):
                        tar.add(f, arcname=f"{base}/{f.relative_to(RACINE)}")
                        fichiers += 1
        subprocess.run(["zstd", f"-{args.niveau}", "-q", "-f",
                        str(chemin_tar), "-o", str(archive_zst)], check=True)
    finally:
        chemin_tar.unlink(missing_ok=True)

    empreinte = _sha256(archive_zst)
    (dist / f"{base}.tar.zst.sha256").write_text(
        f"{empreinte}  {archive_zst.name}\n", encoding="utf-8")
    taille = archive_zst.stat().st_size / 1e6
    print(f"pack : {archive_zst.relative_to(RACINE)}")
    print(f"  {fichiers} fichiers, {taille:.1f} Mo, sha256 {empreinte[:16]}…")
    print(f"\npublier : gh release create v{args.version} {archive_zst} "
          f"{dist / (base + '.tar.zst.sha256')} --notes-file docs/notes-release.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
