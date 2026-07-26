#!/usr/bin/env python3
"""Vérifie un pack : somme de contrôle, manifeste, présence effective des fichiers.

À faire avant d'installer un pack téléchargé — un média manquant ne casse pas le jeu, mais
un pack tronqué installé silencieusement donne des dialogues muets sans qu'on comprenne
pourquoi.

    python3 tools/verify_pack.py dist/bate-media-voices-0.1.0.tar.zst
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def _sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archive")
    args = ap.parse_args()

    archive = Path(args.archive).expanduser()
    if not archive.exists():
        print(f"archive introuvable : {archive}", file=sys.stderr)
        return 1

    attendu = archive.with_suffix(archive.suffix + ".sha256")
    if attendu.exists():
        reference = attendu.read_text(encoding="utf-8").split()[0]
        obtenu = _sha256(archive)
        if reference != obtenu:
            print(f"SOMME INVALIDE\n  attendu : {reference}\n  obtenu  : {obtenu}",
                  file=sys.stderr)
            return 1
        print(f"somme SHA-256 conforme ({obtenu[:16]}…)")
    else:
        print("(pas de fichier .sha256 à côté — intégrité non vérifiable)")

    with tempfile.TemporaryDirectory() as tmp:
        tar = Path(tmp) / "pack.tar"
        subprocess.run(["zstd", "-d", "-q", "-f", str(archive), "-o", str(tar)], check=True)
        with tarfile.open(tar) as t:
            noms = t.getnames()
            manifestes = [n for n in noms if n.endswith("/manifest.json")
                          and n.count("/") == 1]
            if not manifestes:
                print("manifeste absent du pack", file=sys.stderr)
                return 1
            manifeste = json.loads(t.extractfile(manifestes[0]).read().decode("utf-8"))

    racine = manifestes[0].rsplit("/", 1)[0]
    fichiers = {n for n in noms if not n.endswith("/")}
    manquants, comptes = [], {}
    for cle, voix in (manifeste.get("voix") or {}).items():
        présents = 0
        for entree in voix.get("fichiers", []):
            chemin = f"{racine}/voices/{cle}/{entree['fichier']}"
            if chemin in fichiers:
                présents += 1
            else:
                manquants.append(chemin)
        comptes[voix.get("nom", cle)] = (présents, voix.get("repliques", 0))

    print(f"pack version {manifeste.get('version_pack')} "
          f"(construit {manifeste.get('construit')}), contenu : "
          f"{', '.join(manifeste.get('contenu', []))}")
    for nom, (présents, attendus) in sorted(comptes.items(), key=lambda kv: -kv[1][1]):
        etat = "ok" if présents == attendus else f"MANQUE {attendus - présents}"
        print(f"  {nom:<18} {présents:>4}/{attendus:<4} {etat}")
    if manquants:
        print(f"\n{len(manquants)} fichier(s) annoncé(s) mais absent(s) — pack incomplet",
              file=sys.stderr)
        return 1
    print(f"\npack complet : {len(fichiers)} fichiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
