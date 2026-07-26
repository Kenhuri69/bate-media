#!/usr/bin/env python3
"""Installe un pack de médias dans le jeu, ou le retire.

Le jeu doit tourner **sans** ce pack : l'installation ne fait que déposer des fichiers dans
`assets/audio/voice/<personnage>/`, que le code charge s'ils existent et ignore sinon (voir
`docs/integration-dialogic.md`). D'où la désinstallation, qui doit ramener le jeu à un état
strictement jouable.

    python3 tools/install_pack.py dist/bate-media-voices-0.1.0.tar.zst --jeu ~/workspace/bate
    python3 tools/install_pack.py --jeu ~/workspace/bate --desinstaller
    python3 tools/install_pack.py <archive> --jeu … --dry-run
"""
import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

SOUS_DOSSIER = Path("assets/audio/voice")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archive", nargs="?")
    ap.add_argument("--jeu", required=True, help="racine du dépôt du jeu")
    ap.add_argument("--desinstaller", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jeu = Path(args.jeu).expanduser()
    if not (jeu / "project.godot").exists():
        print(f"{jeu} ne ressemble pas à un projet Godot (project.godot absent)",
              file=sys.stderr)
        return 1
    cible = jeu / SOUS_DOSSIER

    if args.desinstaller:
        if not cible.exists():
            print("rien à désinstaller")
            return 0
        fichiers = [f for f in cible.rglob("*") if f.is_file()]
        print(f"{'(dry-run) ' if args.dry_run else ''}suppression de {len(fichiers)} "
              f"fichier(s) dans {cible.relative_to(jeu)}")
        if not args.dry_run:
            shutil.rmtree(cible)
            # Godot garde des .import à côté des ressources : on prévient plutôt que
            # de fouiller dans .godot/, dont la régénération est de son ressort.
            print("relancer le jeu une fois pour que Godot purge son cache d'import")
        return 0

    if not args.archive:
        print("il faut une archive (ou --desinstaller)", file=sys.stderr)
        return 1
    archive = Path(args.archive).expanduser()
    if not archive.exists():
        print(f"archive introuvable : {archive}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tar = tmp / "pack.tar"
        subprocess.run(["zstd", "-d", "-q", "-f", str(archive), "-o", str(tar)], check=True)
        with tarfile.open(tar) as t:
            t.extractall(tmp / "extrait")
        racines = [d for d in (tmp / "extrait").iterdir() if d.is_dir()]
        if len(racines) != 1:
            print("structure de pack inattendue", file=sys.stderr)
            return 1
        contenu = racines[0]
        manifeste = json.loads((contenu / "manifest.json").read_text(encoding="utf-8"))
        source_voix = contenu / "voices"
        if not source_voix.is_dir():
            print("ce pack ne contient pas de voix", file=sys.stderr)
            return 1

        total = 0
        for dossier in sorted(source_voix.iterdir()):
            if not dossier.is_dir():
                continue
            fichiers = [f for f in dossier.iterdir() if f.suffix in (".ogg", ".wav")]
            print(f"  {dossier.name:<18} {len(fichiers):>4} fichiers")
            total += len(fichiers)
            if args.dry_run:
                continue
            destination = cible / dossier.name
            destination.mkdir(parents=True, exist_ok=True)
            for f in fichiers:
                shutil.copy2(f, destination / f.name)
            # Le manifeste par personnage suit : le jeu peut ainsi relier une réplique
            # à son fichier sans deviner la convention de nommage.
            local = dossier / "manifest.json"
            if local.exists():
                shutil.copy2(local, destination / "manifest.json")

    print(f"\n{'(dry-run) ' if args.dry_run else ''}pack "
          f"{manifeste.get('version_pack')} : {total} fichiers "
          f"-> {cible.relative_to(jeu)}")
    if not args.dry_run:
        (cible / "PACK_VERSION").write_text(
            f"{manifeste.get('version_pack')}\n", encoding="utf-8")
        print("ces fichiers ne sont pas suivis par Git côté jeu (cf. .gitignore du jeu) : "
              "le pack reste un artefact externe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
