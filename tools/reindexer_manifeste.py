#!/usr/bin/env python3
"""Remet `manifest.json` d'accord avec les fichiers réellement présents dans `voices/`.

    python3 tools/reindexer_manifeste.py --dry-run   # annonce, n'écrit rien
    python3 tools/reindexer_manifeste.py
    python3 tools/reindexer_manifeste.py --selftest

POURQUOI CET OUTIL EXISTE
-------------------------
`sync_from_forge.py` remplit `voix[<clé>].fichiers` pour les personnages qu'il synchronise.
Les voix ajoutées autrement se retrouvent avec `repliques: N` et `fichiers: []` — le compte
est là, la liste non. Constaté le 2026-08-24 sur le pack 0.6.9 : **dix voix sur quatorze**
dans ce cas (alice, reynolds, jasmine, angela, helen, adam, durden, vincent, lilia, ellie).

Ce n'est pas cosmétique. `tools/verify_pack.py` s'en servait pour vérifier la présence
fichier par fichier ; devant une liste vide il comparait 0 au compteur de répliques et
déclarait « pack incomplet » sur une archive qui contenait bel et bien ses 9 065 clips.

L'index d'Arthur, lui, était PÉRIMÉ : 2 057 de ses 7 532 entrées ne correspondaient à aucun
fichier présent, tandis que 2 135 fichiers présents n'étaient pas listés — intersection
vide. Les noms portent l'empreinte du TEXTE (`<rôle>_<empreinte>`) : ils changent quand une
réplique est corrigée. Un index écrit une fois ne survit donc pas aux réécritures.

CE QUE CET OUTIL N'INVENTE PAS
------------------------------
Il ne produit que ce qui se mesure sur le disque : `id`, `fichier`, `sha256`. Les champs
`texte`, `chapitre` et `moteur` d'une entrée DÉJÀ indexée sont **reportés tels quels** — ils
viennent de la forge, qui seule les connaît, et rien ici ne les devine. Une entrée nouvelle
n'en reçoit pas : c'est la forme que produit déjà `sync_from_forge.py`, et elle est
volontaire — voir le commentaire de ce fichier sur les textes d'une œuvre protégée dans un
dépôt public.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REPORTES = ("texte", "chapitre", "moteur")


def _sha256_court(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()[:16]


def reindexer(racine: Path, manifeste: dict) -> tuple[dict, list[str]]:
    """Rend (manifeste réindexé, lignes de rapport). Ne touche pas au disque."""
    voix = manifeste.get("voix") or {}
    rapport = []
    for cle in sorted(voix):
        dossier = racine / "voices" / cle
        if not dossier.is_dir():
            rapport.append(f"  {cle:<10} dossier absent — laissé tel quel")
            continue
        anciens = {e.get("fichier"): e for e in voix[cle].get("fichiers", [])}
        neufs = []
        for f in sorted(dossier.glob("*.ogg")):
            entree = {"id": f.stem, "fichier": f.name, "sha256": _sha256_court(f)}
            precedent = anciens.get(f.name)
            if precedent:
                # Report des champs que seule la forge connaît, jamais une reconstruction.
                for champ in REPORTES:
                    if champ in precedent:
                        entree[champ] = precedent[champ]
            neufs.append(entree)
        avant_n, avant_r = len(anciens), voix[cle].get("repliques", 0)
        conserves = sum(1 for e in neufs if any(c in e for c in REPORTES))
        voix[cle]["fichiers"] = neufs
        voix[cle]["repliques"] = len(neufs)
        etat = "inchangé" if (avant_n == len(neufs) and avant_r == len(neufs)) else "RÉINDEXÉ"
        rapport.append(f"  {cle:<10} {avant_n:>5} -> {len(neufs):<5} fichiers "
                       f"(repliques {avant_r} -> {len(neufs)}, {conserves} avec texte)  {etat}")
    manifeste["voix"] = voix
    return manifeste, rapport


def _selftest() -> int:
    import tempfile
    ok = True

    def check(nom, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'OK ' if cond else 'ECHEC'}] {nom}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "voices" / "alice").mkdir(parents=True)
        for n in ("alice_aa.ogg", "alice_bb.ogg"):
            (td / "voices" / "alice" / n).write_bytes(n.encode())
        (td / "voices" / "arthur").mkdir(parents=True)
        (td / "voices" / "arthur" / "arthur_11.ogg").write_bytes(b"x")

        m = {"voix": {
            # liste vide, compteur non nul : le cas des dix voix de la 0.6.9
            "alice": {"nom": "Alice", "repliques": 2, "fichiers": []},
            # index périmé : une entrée qui n'existe plus, avec un texte à ne pas perdre
            "arthur": {"nom": "Arthur", "repliques": 2, "fichiers": [
                {"id": "arthur_11", "fichier": "arthur_11.ogg", "texte": "Bonjour.",
                 "chapitre": "ch01", "moteur": "qwen3-tts"},
                {"id": "arthur_99", "fichier": "arthur_99.ogg", "texte": "Disparu."},
            ]},
        }}
        m, _ = reindexer(td, m)
        check("une liste vide est remplie depuis le disque",
              [e["fichier"] for e in m["voix"]["alice"]["fichiers"]] == ["alice_aa.ogg", "alice_bb.ogg"])
        check("le compteur suit le disque, pas l'ancien manifeste",
              m["voix"]["alice"]["repliques"] == 2 and m["voix"]["arthur"]["repliques"] == 1)
        check("une entrée périmée disparaît",
              all(e["fichier"] != "arthur_99.ogg" for e in m["voix"]["arthur"]["fichiers"]))
        arth = m["voix"]["arthur"]["fichiers"][0]
        check("le texte d'une entrée conservée est REPORTÉ, pas perdu",
              arth.get("texte") == "Bonjour." and arth.get("chapitre") == "ch01")
        check("une entrée neuve ne reçoit AUCUN texte inventé",
              all("texte" not in e for e in m["voix"]["alice"]["fichiers"]))
        check("le sha256 est celui du fichier, tronqué à 16",
              arth["sha256"] == hashlib.sha256(b"x").hexdigest()[:16])
    print("auto-test reindexer_manifeste :", "OK" if ok else "ECHEC")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    chemin = RACINE / "manifest.json"
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    manifeste, rapport = reindexer(RACINE, manifeste)
    print("\n".join(rapport))
    total = sum(len(v.get("fichiers", [])) for v in manifeste["voix"].values())
    print(f"\n{len(manifeste['voix'])} voix, {total} fichiers indexés")
    if args.dry_run:
        print("[dry-run] manifest.json non modifié")
        return 0
    chemin.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest.json réindexé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
