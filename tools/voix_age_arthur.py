#!/usr/bin/env python3
"""Décliner la voix d'Arthur par stade d'âge — à lancer avec .venv-mlx.

Arthur est le seul rôle de BATE qui traverse quatre âges en parlant : trois ans au
chapitre 2, quinze à l'académie. Une voix unique sur tout le jeu ferait dire « Papa,
comment on sait qu'on a réussi ? » par un homme de trente ans. Les stades sont ceux
que le jeu utilise déjà pour ses sprites (`bate/tools/assets/character_plan.json`) —
les inventer ici ferait diverger la voix et l'image du même personnage.

Le timbre de base est `aiden:0.5+ryan:0.5`, validé à l'oreille. Il sort à ~132 Hz, soit
la voix la plus grave des mélanges essayés : c'est l'ancrage ADULTE, celui du prologue
où King Grey meurt avant de renaître. Les stades jeunes se construisent en montant
depuis lui, par ajout dosé d'une composante aiguë au mélange d'embeddings.

Deux étapes, parce que la dose ne se devine pas :

    python tools/voix_age_arthur.py calibrer   # courbe dose -> F0, à lire avant de choisir
    python tools/voix_age_arthur.py produire   # le lot d'écoute par stade

`calibrer` balaie plusieurs composantes aiguës à plusieurs doses et mesure ce qui sort
vraiment. Sans lui on choisirait « 0,3 de vivian » au jugé, alors que le rapport entre la
dose et la hauteur obtenue n'a aucune raison d'être linéaire — et qu'il dépend du couple
(mesuré au lot 4 : +serena stabilise, +vivian monte, +ryan descend).

La contrainte qui prime sur la hauteur : la **plage F0 intra-stade**. Un stade dont les
clips vont de 138 à 296 Hz n'est pas un âge, c'est trois personnages — voir le lot 5.
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
LIGNES = RACINE / "voice-agent/training/forge/bate-arthur/lines.json"
PLAN = RACINE / "bate/tools/assets/character_plan.json"
ECOUTE = MEDIA / "docs/ecoute-qwen3-tts/6-ages-arthur"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = "aiden:0.5+ryan:0.5"          # validé à l'oreille le 2026-08-08

# Cibles de hauteur par âge. Repères physiologiques de la voix parlée, pas des mesures
# maison : ~270 Hz à trois ans, ~240 à six, la mue vers treize, ~175 à quinze. Le stade
# académie retombe donc pile sur l'Arthur que le jeu fait déjà entendre (176-211 Hz).
CIBLES = {
    "s02_toddler": 270.0,
    "s03_child": 240.0,
    "s04_teen": 200.0,
    "s05_academy": 175.0,
    "prologue": 132.0,               # King Grey : la base pure, aucun ajout
}

# Composantes aiguës candidates. `eric` et `dylan` sont exclus d'office (dialectaux, ils
# produisent les clips dégénérés en français) ; `uncle_fu` va dans le mauvais sens.
AIGUES = ["vivian", "serena", "ono_anna"]
DOSES = [0.0, 0.15, 0.3, 0.45, 0.6]
# Prolongement mesuré le 2026-08-08 : à 0,6 la courbe de `vivian` plafonne à 206 Hz, sous
# les cibles enfant (240) et toddler (270). Or `vivian` est la SEULE composante monotone
# des trois — `serena` et `ono_anna` redescendent quand la dose monte, avec des plages de
# plus de 100 Hz à leur point de rupture. Prendre une composante par stade ferait entendre
# trois personnes différentes au lieu d'un enfant qui grandit : mieux vaut prolonger la
# seule courbe qui se tienne que panacher les autres.
DOSES_HAUTES = [0.7, 0.8, 0.9]


def _stades() -> dict:
    """Les stades d'Arthur tels que le JEU les définit, pas tels que je les imaginerais."""
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    arthur = next(c for c in plan["characters"] if c["id"] == "arthur")
    return {s["id"]: {"label": s["label"], "chapitres": s["chapters"]}
            for s in arthur["stages"] if s["chapters"]}


def _chapitre(ligne: dict):
    m = re.search(r"\d+", str(ligne.get("chapitre", "")))
    return int(m.group()) if m else None


def _repliques_par_stade() -> dict:
    """Range chaque réplique dans son stade. Le prologue (ch0-1) est King Grey, pas Arthur.

    La narration vieillit avec le personnage — c'est sa voix intérieure — sauf ces deux
    chapitres-là, où celui qui pense est encore le roi d'avant la réincarnation.
    """
    stades = _stades()
    lignes = json.loads(LIGNES.read_text(encoding="utf-8"))
    lots = {"prologue": []}
    for sid, s in stades.items():
        lots[sid] = []
    for ligne in lignes:
        ch = _chapitre(ligne)
        if ch is None:
            continue
        if ch <= 1:
            lots["prologue"].append(ligne)
            continue
        for sid, s in stades.items():
            if ch in s["chapitres"]:
                lots[sid].append(ligne)
                break
    return {k: v for k, v in lots.items() if v}


def _melange(dose: float, aigue: str) -> str:
    """La base validée, pondérée (1-dose), plus la composante aiguë. Dose 0 = base pure."""
    if dose <= 0:
        return BASE
    parts = []
    for part in BASE.split("+"):
        nom, _, poids = part.partition(":")
        parts.append(f"{nom}:{float(poids or 1.0) * (1 - dose):.3f}")
    return "+".join(parts) + f"+{aigue}:{dose:.3f}"


def _echantillon(lot: list, n: int) -> list:
    """Des répliques du stade, dialogues d'abord : c'est la voix parlée qu'on calibre."""
    parles = [l for l in lot if l["role"] not in ("narrator",)]
    autres = [l for l in lot if l["role"] == "narrator"]
    return (parles + autres)[:n]


def _genere_lot(modele, qwen3tts, spec: str, lignes: list, dossier: Path) -> list:
    faits = []
    for i, ligne in enumerate(lignes):
        registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
        cible = dossier / f"{ligne['id']}.ogg"
        onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                   qwen3tts.REGISTRES[registre], spec,
                                   seed=2000 + i, temperature=0.7)
        qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
        faits.append(cible)
    return faits


def _mesure(clips: list, mesures) -> dict:
    descr = [mesures._descripteurs(c) for c in clips]
    f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
    return {"f0_median": float(np.median(f0)) if f0 else 0.0,
            "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0,
            **mesures._dispersion_timbre(clips)}


def calibrer(aigues=None, doses=None) -> int:
    """Courbe dose -> hauteur obtenue, sur de vraies répliques d'Arthur enfant.

    Les clips déjà produits ne sont pas régénérés : prolonger la courbe ne doit pas
    redessiner les points qu'on a déjà lus, sinon on ne saurait plus si un écart vient
    de la dose ajoutée ou d'un nouveau tirage.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    aigues, doses = aigues or AIGUES, doses if doses is not None else DOSES
    lots = _repliques_par_stade()
    # Calibrer sur le stade enfant : c'est celui qui demande la plus grosse remontée
    # depuis 132 Hz, donc celui où une dose mal choisie s'entendra le plus.
    echantillon = _echantillon(lots["s03_child"], 4)
    print(f"calibrage sur {len(echantillon)} répliques de s03_child : "
          f"{', '.join(l['id'] for l in echantillon)}", flush=True)

    fichier = ECOUTE / "calibrage" / "courbe.json"
    courbe = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    modele = qwen3tts._charge("customvoice")
    for aigue in aigues:
        for dose in doses:
            if dose == 0 and aigue != aigues[0]:
                continue                      # la base pure ne dépend pas de la composante
            spec = _melange(dose, aigue)
            nom = "base" if dose == 0 else f"{aigue}:{dose}"
            if nom in courbe:
                print(f"\n=== {nom} — déjà mesuré, conservé", flush=True)
                continue
            dossier = ECOUTE / "calibrage" / nom.replace(":", "-").replace(".", "-")
            print(f"\n=== {nom}  ({spec})", flush=True)
            clips = _genere_lot(modele, qwen3tts, spec, echantillon, dossier)
            courbe[nom] = {"spec": spec, **_mesure(clips, mesures)}
            r = courbe[nom]
            print(f"    F0 {r['f0_median']:5.0f} Hz   plage {r['f0_plage']:4.0f} Hz   "
                  f"cohésion {r['cohesion_moyenne']:.3f}", flush=True)
    del modele

    fichier.write_text(
        json.dumps(courbe, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n" + "=" * 70)
    print("DOSE -> HAUTEUR OBTENUE   (base aiden:0.5+ryan:0.5)")
    print(f"{'mélange':22s} {'F0':>7s} {'plage':>7s} {'cohés.':>8s}   cible la plus proche")
    for nom, r in sorted(courbe.items(), key=lambda kv: kv[1]["f0_median"]):
        proche = min(CIBLES.items(), key=lambda kv: abs(kv[1] - r["f0_median"]))
        ecart = abs(proche[1] - r["f0_median"])
        print(f"{nom:22s} {r['f0_median']:6.0f}Hz {r['f0_plage']:6.0f}Hz "
              f"{r['cohesion_moyenne']:8.3f}   {proche[0]} ({proche[1]:.0f}, écart {ecart:.0f})")
    print("\nChoisir une dose par stade, la reporter dans DOSES_RETENUES, puis `produire`.")
    return 0


# Retenus sur la courbe de calibrage du 2026-08-08 (`calibrage/courbe.json`), jamais au
# jugé. Critère : la plage F0 d'abord, la hauteur ensuite — un stade dispersé n'est pas un
# âge. D'où des écarts assumés à la cible quand le point le plus juste était le plus sale.
#
# Trois composantes différentes, et c'est le point faible du lot : chacune est celle qui
# tenait à cette hauteur-là. Panacher n'était pas le plan — `vivian` seule aurait donné une
# mue continue — mais elle SATURE à ~226 Hz (0,6 → 206, 0,8 → 226, 0,9 → 220), donc elle
# ne peut pas jouer les deux stades jeunes. C'est ce que l'oreille doit vérifier en
# priorité : un enfant qui grandit, ou trois personnes différentes.
DOSES_RETENUES = {
    "prologue": (None, 0.0),        # 125 Hz — King Grey, la base validée telle quelle
    "s02_toddler": ("serena", 0.8),  # 250 Hz, plage 29 — le plus aigu qui tienne
    "s03_child": ("ono_anna", 0.45),  # 235 Hz, plage 28
    # Ces deux-là ne sont PAS résolus, et les valeurs ci-dessous sont les moins mauvaises
    # effectivement mesurées — surtout pas interpolées. La tentative d'interpolation a
    # échoué de façon instructive : sur leurs propres répliques, academy donnait 156 Hz à
    # 0,45 et 194 à 0,55, donc 0,50 devait tomber vers 175 — il a rendu **150**, plus bas
    # que 0,45. Et teen, visé à 0,53 pour 200 Hz, a rendu 163 comme à 0,45 alors que 0,60
    # rend 225. La relation dose -> hauteur est en ESCALIER, pas en pente : elle ne
    # s'interpole pas, même à stade et répliques constants. Ne rien y régler au centième.
    "s04_teen": ("vivian", 0.6),     # 225 Hz pour 200 visés, plage 94 — trop haut, dispersé
    "s05_academy": ("vivian", 0.55),  # 194 Hz pour 175 visés, plage 72
}


def ajuster(sid: str, aigue: str, doses: list) -> int:
    """Rebalaye un stade sur SES PROPRES répliques, à la taille d'échantillon de prod.

    Le calibrage global s'est révélé non transférable : la hauteur obtenue dépend du texte
    prononcé autant que du mélange (`vivian:0.6` = 206 Hz sur des répliques d'enfant, mais
    225 Hz sur celles d'adolescent). Et comparer la plage d'un lot de 4 clips à celle d'un
    lot de 6 n'a pas de sens — c'est un écart entre extrêmes, il croît avec l'échantillon.
    D'où ce mode : même stade, mêmes répliques, même compte qu'en production.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    lot = _repliques_par_stade().get(sid) or []
    echantillon = _echantillon(lot, 6)
    print(f"ajustement {sid} sur ses {len(echantillon)} répliques", flush=True)
    modele = qwen3tts._charge("customvoice")
    for dose in doses:
        spec = _melange(dose, aigue)
        dossier = ECOUTE / "ajustage" / f"{sid}-{aigue}-{dose}".replace(".", "-")
        print(f"\n=== {sid} {aigue}:{dose}  ({spec})", flush=True)
        clips = _genere_lot(modele, qwen3tts, spec, echantillon, dossier)
        r = _mesure(clips, mesures)
        print(f"    F0 {r['f0_median']:5.0f} Hz (cible {CIBLES.get(sid, 0):.0f})   "
              f"plage {r['f0_plage']:4.0f} Hz   cohésion {r['cohesion_moyenne']:.3f}",
              flush=True)
    del modele
    return 0


def produire() -> int:
    """Le lot d'écoute : chaque stade sur SES répliques, avec le mélange retenu."""
    import bench_qwen3tts as mesures
    import qwen3tts

    if not DOSES_RETENUES:
        print("DOSES_RETENUES est vide — lancer `calibrer` d'abord.", file=sys.stderr)
        return 1

    lots = _repliques_par_stade()
    modele = qwen3tts._charge("customvoice")
    rapport = {"base": BASE, "cibles_f0": CIBLES, "stades": {}}
    for sid, (aigue, dose) in DOSES_RETENUES.items():
        spec = _melange(dose, aigue)
        lot = lots.get(sid) or []
        if not lot:
            print(f"  {sid} : aucune réplique", flush=True)
            continue
        echantillon = _echantillon(lot, 6)
        dossier = ECOUTE / sid
        print(f"\n=== {sid}  ({spec})  {len(echantillon)} répliques", flush=True)
        clips = _genere_lot(modele, qwen3tts, spec, echantillon, dossier)
        rapport["stades"][sid] = {
            "spec": spec, "repliques_du_stade": len(lot),
            "dossier": str(dossier.relative_to(MEDIA)), **_mesure(clips, mesures),
        }
        r = rapport["stades"][sid]
        print(f"    F0 {r['f0_median']:5.0f} Hz (cible {CIBLES.get(sid, 0):.0f})   "
              f"plage {r['f0_plage']:4.0f} Hz", flush=True)
    del modele

    (ECOUTE / "rapport_ages.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"{'stade':16s} {'mélange':34s} {'F0':>7s} {'cible':>7s} {'plage':>7s}")
    for sid, r in rapport["stades"].items():
        print(f"{sid:16s} {r['spec']:34s} {r['f0_median']:6.0f}Hz "
              f"{CIBLES.get(sid, 0):6.0f}Hz {r['f0_plage']:6.0f}Hz")
    print(f"\nÀ écouter : {ECOUTE.relative_to(MEDIA)}")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "calibrer"
    if action == "prolonger":
        # Prolonger une courbe existante : `prolonger [composante] [doses]`.
        # Sans argument, la seule monotone du premier balayage (vivian) aux doses hautes.
        aigue = sys.argv[2] if len(sys.argv) > 2 else "vivian"
        doses = ([float(d) for d in sys.argv[3].split(",")] if len(sys.argv) > 3
                 else DOSES_HAUTES)
        sys.exit(calibrer(aigues=[aigue], doses=doses))
    if action == "ajuster":
        # `ajuster <stade> <composante> <doses>` — rebalaye un stade sur ses répliques.
        sys.exit(ajuster(sys.argv[2], sys.argv[3],
                         [float(d) for d in sys.argv[4].split(",")]))
    sys.exit({"calibrer": calibrer, "produire": produire}[action]())
