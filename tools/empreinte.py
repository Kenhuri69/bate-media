#!/usr/bin/env python3
"""Empreinte d'une réplique — la règle qui relie un clip au texte qu'il dit.

    python3 tools/empreinte.py --selftest                  # rejoue le contrat partagé
    python3 tools/empreinte.py --texte "Bonjour." --role Arthur

POURQUOI CETTE RÈGLE EXISTE. Un clip s'appelait `<rôle>_ch<NN>_<II>` : son nom ne disait que
la PLACE de la réplique dans une timeline. Insérer une ligne en amont périmait donc en silence
tous les clips suivants — c'est exactement ce qui est arrivé au pack 0.3.0 quand les chapitres
0 à 9 du jeu ont été réécrits le 2026-08-07. Rien ne pouvait le détecter : le fichier attendu
existait toujours, il disait simplement autre chose.

Le nom porte désormais une empreinte du TEXTE. Une réplique déplacée garde son clip ; une
réplique réécrite perd le sien et se tait — un manque visible, régénérable à l'unité, au lieu
d'un décalage inaudible qui contamine tout ce qui suit.

CETTE RÈGLE EST ÉCRITE DEUX FOIS, ici en Python et dans `bate/src/systems/audio/VoiceLines.cs`
en C#. C'est le seul endroit de la chaîne qui peut rompre en silence : une divergence d'un
espace produit une clé qui ne correspond à aucun fichier, donc un jeu MUET sans la moindre
erreur. D'où le contrat commun — `bate/resources/voice_fingerprints.json` — que les deux côtés
rejouent : `VoiceLinesTests` en C#, `--selftest` ici.

Ne rien « améliorer » dans la normalisation sans mettre le contrat à jour des DEUX côtés.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

LONGUEUR_EMPREINTE = 10

# Rôles regroupés sous une même voix : le dossier n'est pas le rôle. « Note » est le pseudonyme
# d'aventurier d'Arthur, et le jeu est narré à la première personne — les trois doivent sortir
# du même timbre, sinon le personnage change de voix en cours de partie.
ROLES_GROUPES = {"narrator": "arthur", "narrateur": "arthur", "note": "arthur"}

# Où trouver le dépôt du jeu : il porte les timelines et le contrat d'empreinte.
JEU = Path(os.environ.get("BATE_JEU", Path.home() / "workspace/bate")).expanduser()


def normalise_texte(texte: str) -> str:
    """NFC, toute suite de blancs compactée en une espace, bords coupés. Rien de plus.

    Casse, accents et ponctuation sont CONSERVÉS : ils changent ce qui est dit ou la façon de
    le dire, donc deux textes qui n'en diffèrent que méritent deux enregistrements.
    """
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", texte)).strip()


def empreinte(texte: str) -> str:
    """Les {n} premiers caractères hexadécimaux du SHA-256 de la forme normalisée."""
    n = normalise_texte(texte)
    return "" if not n else hashlib.sha256(n.encode("utf-8")).hexdigest()[:LONGUEUR_EMPREINTE]


def role_du_locuteur(nom: str) -> str:
    """« Alice Leywin » -> « alice ». Minuscules, sans accents, premier mot seulement."""
    sortie = []
    for c in unicodedata.normalize("NFD", nom):
        if unicodedata.combining(c):
            continue
        if c.isspace() or c in "'-_":
            if sortie:
                break
            continue
        if c.isalnum():
            sortie.append(c.lower())
    return "".join(sortie)


def dossier_de_voix(role: str) -> str:
    return ROLES_GROUPES.get(role, role)


def clip_id(locuteur: str, texte: str) -> str | None:
    """`<rôle>_<empreinte>`, ou None si le locuteur ou le texte ne donne rien."""
    role = role_du_locuteur(locuteur)
    emp = empreinte(texte)
    return f"{role}_{emp}" if role and emp else None


def chemin_relatif(locuteur: str, texte: str) -> str | None:
    """`<dossier de voix>/<rôle>_<empreinte>.ogg`, le chemin sous `voices/`."""
    ident = clip_id(locuteur, texte)
    if ident is None:
        return None
    return f"{dossier_de_voix(role_du_locuteur(locuteur))}/{ident}.ogg"


# --- répliques du jeu ---------------------------------------------------------

# `narrator: Il faisait nuit.` — on ignore commentaires, événements `[...]` et libellés de
# choix `- ...`, qui ne sont pas des répliques.
REPLIQUE = re.compile(r"^([A-Za-zÀ-ÿ][\w '\-À-ÿ]*)\s*:\s*(.+)$")


def repliques_du_chapitre(chapitre: str) -> list[dict]:
    """Les répliques d'une timeline du jeu, dans l'ordre du fichier.

    `chapitre` est le nom du fichier sans extension (`chapter_00`, `chapter_07a`). Lire les
    `.dtl` du jeu plutôt qu'un extrait stocké est délibéré : un extrait est une COPIE du texte,
    et c'est une copie figée qui a produit la dérive du pack 0.3.0.
    """
    chemin = JEU / "dialogues" / f"{chapitre}.dtl"
    if not chemin.exists():
        raise SystemExit(f"timeline introuvable : {chemin}\n"
                         f"  (BATE_JEU={JEU} — pointer la variable sur le dépôt du jeu)")
    sortie = []
    for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        s = ligne.strip()
        if not s or s.startswith("#") or s.startswith("[") or s.startswith("- "):
            continue
        m = REPLIQUE.match(s)
        if not m:
            continue
        locuteur, texte = m.group(1), m.group(2)
        sortie.append({"ligne": numero, "locuteur": locuteur,
                       "role": role_du_locuteur(locuteur), "texte": texte,
                       "id": clip_id(locuteur, texte),
                       "chemin": chemin_relatif(locuteur, texte)})
    return sortie


# --- contrat ------------------------------------------------------------------

def vecteurs_partages() -> list[dict]:
    contrat = JEU / "resources/voice_fingerprints.json"
    if not contrat.exists():
        raise SystemExit(f"contrat d'empreinte introuvable : {contrat}\n"
                         f"  (BATE_JEU={JEU} — pointer la variable sur le dépôt du jeu)")
    return json.loads(contrat.read_text(encoding="utf-8"))["vecteurs"]


def selftest() -> int:
    ok = True

    def verifie(nom: str, condition: bool) -> None:
        nonlocal ok
        print(f"  {'ok  ' if condition else 'ÉCHEC'} {nom}")
        ok = ok and condition

    verifie("role : le prénom seul", role_du_locuteur("Alice Leywin") == "alice")
    verifie("role : accents retirés", role_du_locuteur("Élénoir") == "elenoir")
    verifie("role : nom vide", role_du_locuteur("  ") == "")
    verifie("dossier : narrator et Note sortent de la voix d'Arthur",
            dossier_de_voix("narrator") == "arthur" and dossier_de_voix("note") == "arthur")
    verifie("dossier : un rôle hors table est son propre dossier",
            dossier_de_voix("tessia") == "tessia")

    verifie("empreinte : longueur annoncée", len(empreinte("x")) == LONGUEUR_EMPREINTE)
    verifie("empreinte : rien à prononcer", empreinte("  ") == "")
    verifie("id : aucune position dans l'identifiant",
            "ch" not in clip_id("narrator", "x").split("_", 1)[1])
    verifie("chemin : dossier de voix puis rôle",
            chemin_relatif("narrator", "x") == f"arthur/{clip_id('narrator', 'x')}.ogg")

    # LE contrôle : la même règle, calculée ici, doit rendre exactement ce que le C# du jeu
    # rend sur les mêmes entrées.
    try:
        vecteurs = vecteurs_partages()
    except SystemExit as e:
        print(f"  ÉCHEC contrat partagé : {e}")
        return 1
    ecarts = []
    for v in vecteurs:
        if normalise_texte(v["texte"]) != v["normalise"]:
            ecarts.append(f"normalisation « {v['cas']} »")
        if empreinte(v["texte"]) != v["empreinte"]:
            ecarts.append(f"empreinte « {v['cas']} »")
    verifie(f"contrat : {len(vecteurs)} vecteurs partagés rejoués sans écart", not ecarts)
    for e in ecarts:
        print(f"        {e}")

    print("selftest :", "OK" if ok else "ÉCHEC")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--texte", help="calcule l'empreinte de ce texte")
    ap.add_argument("--role", default="narrator", help="locuteur (défaut : narrator)")
    ap.add_argument("--chapitre", help="liste les répliques d'une timeline du jeu")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.chapitre:
        for r in repliques_du_chapitre(args.chapitre):
            print(f"{r['chemin']}  « {r['texte'][:60]} »")
        return 0
    if args.texte:
        print(chemin_relatif(args.role, args.texte))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
