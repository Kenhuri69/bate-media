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


def _personnages_declares() -> dict:
    """Les personnages que la PRODUCTION déclare, `clé -> nom` — pas ceux du disque.

    Sert à décider si un dossier de `voices/` absent du manifeste doit y entrer. La question
    n'est pas rhétorique : `voices/arthur-qwen3/` est un dossier de travail qui a déjà doublé
    un pack, et `build_pack._declaree` l'écarte précisément parce qu'il n'est pas déclaré. Le
    registre de `voix_personnage.py` tranche entre les deux cas — un personnage qu'on produit
    contre un répertoire qui traîne.
    """
    import importlib.util
    chemin = RACINE / "tools" / "voix_personnage.py"
    spec = importlib.util.spec_from_file_location("voix_personnage", chemin)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:                                  # numpy absent : on n'invente rien
        print(f"  (registre de production illisible : {e})", file=sys.stderr)
        return {}
    return {cle: p["nom"] for cle, p in module.PERSONNAGES.items()}


def reindexer(racine: Path, manifeste: dict) -> tuple[dict, list[str]]:
    """Rend (manifeste réindexé, lignes de rapport). Ne touche pas au disque."""
    voix = manifeste.get("voix") or {}
    rapport = []
    # UN DOSSIER DE VOIX ABSENT DU MANIFESTE EST EXCLU DU PACK, ET EN SILENCE. C'est le cas
    # de toute voix nouvelle : `build_pack._declaree` filtre sur les clés du manifeste, si
    # bien que les 67 clips de Luna et de Lise, produits et contrôlés, ne seraient jamais
    # partis dans l'archive — un message sur stderr, et un pack « complet » à la vérification
    # puisqu'il contient tout ce que son index annonce. Le titre de cet outil est « remettre
    # le manifeste d'accord avec les fichiers réellement présents » : il doit donc DÉCLARER
    # ce qui manque, pas seulement mettre à jour ce qui est déjà là.
    declares = _personnages_declares()
    for cle, nom in sorted(declares.items()):
        if cle in voix or not (racine / "voices" / cle).is_dir():
            continue
        voix[cle] = {"nom": nom, "repliques": 0, "format": "ogg",
                     "convention": "voice-fingerprint-1.0", "moteur_par_defaut": "qwen3-tts",
                     "fichiers": []}
        rapport.append(f"  {cle:<10} DÉCLARÉE — absente du manifeste, présente sur le disque")
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
    # UN DOSSIER PLEIN QUE PERSONNE NE DÉCLARE EST UNE ALERTE, pas un détail à ignorer. Deux
    # causes possibles et les deux sont graves : un dossier de travail qui partirait dans le pack
    # (celui qui a doublé le pack 0.4.0), ou — c'est arrivé le 2026-08-27 — des clips produits
    # sous une clé que le jeu ne demande plus. Cent deux clips de sept personnages étaient dans
    # `voices/l/`, `voices/le/`, `voices/maitre/`… quand le jeu réclamait `architecte/`,
    # `tenancier/`, `orwin/` : le contrat de rôle avait été corrigé partout sauf dans le calcul
    # du dossier de sortie de la production. Sans cette ligne, le pack se serait construit
    # « complet » en les laissant sur le disque.
    orphelins = []
    for d in sorted((racine / "voices").iterdir() if (racine / "voices").is_dir() else []):
        if d.is_dir() and d.name not in voix and any(d.glob("*.ogg")):
            orphelins.append(f"{d.name} ({len(list(d.glob('*.ogg')))} clips)")
    if orphelins:
        rapport.append("")
        rapport.append(f"  ⚠ {len(orphelins)} dossier(s) plein(s) NON déclaré(s), donc exclus du "
                       f"pack : {', '.join(orphelins)}")
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

        # Une voix présente sur le disque et absente du manifeste doit y ENTRER, sinon le pack
        # l'ignore en silence. Le registre de production est simulé pour ne pas dépendre de
        # voix_personnage (et de numpy) dans un auto-test.
        (td / "voices" / "luna").mkdir(parents=True)
        (td / "voices" / "luna" / "luna_cc.ogg").write_bytes(b"y")
        (td / "voices" / "arthur-qwen3").mkdir(parents=True)      # dossier de travail
        (td / "voices" / "arthur-qwen3" / "arthur_11.ogg").write_bytes(b"x")
        globals()["_personnages_declares"] = lambda: {"alice": "Alice", "arthur": "Arthur",
                                                      "luna": "Luna"}
        m2, _ = reindexer(td, {"voix": {"alice": {"nom": "Alice", "fichiers": []}}})
        check("une voix nouvelle déclarée en production entre au manifeste",
              [e["fichier"] for e in m2["voix"].get("luna", {}).get("fichiers", [])]
              == ["luna_cc.ogg"])
        check("un dossier de travail NON déclaré reste dehors",
              "arthur-qwen3" not in m2["voix"])
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
