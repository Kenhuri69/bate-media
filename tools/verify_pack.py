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
    # Combien de clips l'archive porte-t-elle RÉELLEMENT par dossier de voix ? Sert de repli
    # quand le manifeste ne détaille pas ses fichiers (voir plus bas).
    reels = {}
    for n in fichiers:
        pre = f"{racine}/voices/"
        if n.startswith(pre) and n.endswith(".ogg"):
            reste = n[len(pre):]
            if "/" in reste:
                reels[reste.split("/", 1)[0]] = reels.get(reste.split("/", 1)[0], 0) + 1

    manquants, comptes, sans_liste = [], {}, []
    for cle, voix in (manifeste.get("voix") or {}).items():
        attendus = voix.get("repliques", 0)
        listes = voix.get("fichiers", [])
        # UNE LISTE VIDE N'EST PAS UN FICHIER MANQUANT, et les confondre rendait ce contrôle
        # inutilisable. Le manifeste de la 0.6.9 ne détaille `fichiers` que pour 4 voix sur
        # 14 ; l'ancienne version comparait donc une liste VIDE au compteur de répliques et
        # annonçait « 2057 fichier(s) absent(s) — pack incomplet » sur une archive dont le
        # `tar` contenait bel et bien les 9 065 clips. Un vérificateur qui accuse un pack sain
        # finit ignoré, et c'est alors un pack réellement tronqué qui passera.
        if not listes and attendus:
            sans_liste.append(cle)
            comptes[voix.get("nom", cle)] = (reels.get(cle, 0), attendus, "compté")
            continue
        présents = 0
        for entree in listes:
            chemin = f"{racine}/voices/{cle}/{entree['fichier']}"
            if chemin in fichiers:
                présents += 1
            else:
                manquants.append(chemin)
        comptes[voix.get("nom", cle)] = (présents, attendus, "listé")

    print(f"pack version {manifeste.get('version_pack')} "
          f"(construit {manifeste.get('construit')}), contenu : "
          f"{', '.join(manifeste.get('contenu', []))}")
    insuffisants = []
    for nom, (présents, attendus, source) in sorted(comptes.items(), key=lambda kv: -kv[1][1]):
        if présents == attendus:
            etat = "ok" if source == "listé" else "ok (compté dans l'archive)"
        elif source == "compté":
            # Le manifeste ne dit pas QUELS fichiers ; on ne peut que comparer les nombres.
            etat = f"{'MANQUE' if présents < attendus else 'EN PLUS'} {abs(attendus - présents)} (compté, liste absente)"
            if présents < attendus:
                insuffisants.append(nom)
        else:
            etat = f"MANQUE {attendus - présents}"
        print(f"  {nom:<18} {présents:>4}/{attendus:<4} {etat}")

    if sans_liste:
        print(f"\n⚠ {len(sans_liste)} voix sans liste `fichiers` au manifeste "
              f"({', '.join(sorted(sans_liste))}) : leur présence est vérifiée par COMPTAGE "
              f"des .ogg de l'archive, pas fichier par fichier. Le manifeste est à compléter "
              f"côté forge — il porte le texte de chaque clip, qu'un scan ne peut pas deviner.",
              file=sys.stderr)
    if manquants:
        print(f"\n{len(manquants)} fichier(s) annoncé(s) mais absent(s) — pack incomplet",
              file=sys.stderr)
        return 1
    if insuffisants:
        print(f"\nmoins de clips que de répliques annoncées pour : {', '.join(insuffisants)}"
              f" — pack incomplet", file=sys.stderr)
        return 1
    print(f"\npack complet : {len(fichiers)} fichiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
