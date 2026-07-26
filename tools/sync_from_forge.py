#!/usr/bin/env python3
"""Récupère les voix produites par `voice-agent forge` et met à jour le manifeste.

La pipeline de génération vit dans le dépôt `voice-agent` (elle est réutilisable pour
autre chose que BATE) ; ce dépôt-ci ne fait que collecter, indexer et empaqueter. On
copie donc plutôt qu'on ne déplace : la forge reste la source de vérité reproductible.

    python3 tools/sync_from_forge.py                       # tout ce qui est disponible
    python3 tools/sync_from_forge.py --personnages Alice,Tessia
    python3 tools/sync_from_forge.py --dry-run
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FORGE_DEFAUT = Path.home() / "workspace/voice-agent/training/forge"


def _sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forge", default=str(FORGE_DEFAUT), help="dossier training/forge")
    ap.add_argument("--personnages", help="liste séparée par des virgules (défaut : tous)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    forge = Path(args.forge).expanduser()
    if not forge.is_dir():
        print(f"forge introuvable : {forge}", file=sys.stderr)
        return 1
    filtre = {x.strip().lower() for x in args.personnages.split(",")} if args.personnages else None

    voix, total = {}, 0
    for manifeste in sorted(forge.glob("*/lines_*/manifest.json")):
        donnees = json.loads(manifeste.read_text(encoding="utf-8"))
        # `personnage` est absent des manifestes produits avant l'ajout du mode --jobs :
        # on retombe sur le nom du dossier (lines_alice -> alice).
        nom = donnees.get("personnage") or manifeste.parent.name
        # Les premiers manifestes annonçaient « lines_alice » comme nom de personnage :
        # on normalise ici aussi, pour ne pas dépendre de leur regénération.
        if nom.startswith("lines_"):
            nom = nom[len("lines_"):]
        cle = nom.lower()
        if filtre and cle not in filtre:
            continue
        cible = RACINE / "voices" / cle
        fichiers = []
        for entree in donnees.get("repliques", []):
            source = manifeste.parent / entree["fichier"]
            if not source.exists():
                continue
            destination = cible / entree["fichier"]
            if not args.dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Ne recopie que si le contenu diffère : un resync doit être bon marché.
                if not destination.exists() or destination.stat().st_size != source.stat().st_size:
                    shutil.copy2(source, destination)
            fichiers.append({"id": entree["id"], "fichier": entree["fichier"],
                             "texte": entree["texte"],
                             "sha256": _sha256(source)[:16] if not args.dry_run else None})
        if not fichiers:
            continue
        voix[cle] = {"nom": nom, "repliques": len(fichiers),
                     "format": donnees.get("format", "ogg"), "fichiers": fichiers}
        total += len(fichiers)
        print(f"  {nom:<16} {len(fichiers):>4} répliques -> voices/{cle}/")

    if not voix:
        print("rien à synchroniser", file=sys.stderr)
        return 1
    print(f"\n{len(voix)} voix, {total} répliques")
    if args.dry_run:
        return 0

    manifeste_global = RACINE / "manifest.json"
    ancien = {}
    if manifeste_global.exists():
        ancien = json.loads(manifeste_global.read_text(encoding="utf-8"))
    manifeste_global.write_text(json.dumps({
        "projet": "bate-media",
        "source": "voice-agent forge",
        "version_pack": ancien.get("version_pack"),
        "voix": voix,
        "medias": ancien.get("medias", {"video": [], "animation": []}),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest.json mis à jour ({total} répliques indexées)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
