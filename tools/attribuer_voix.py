#!/usr/bin/env python3
"""Vérifie qu'une liste de voix CHOISIES est distincte de tout ce qui est déjà en service.

    ../.venv-mlx/bin/python tools/attribuer_voix.py --genre f \\
        "serena:0.8+sohee:0.2@+3x0.92" "vivian:0.65+sohee:0.35@+3x1.00"
    ../.venv-mlx/bin/python tools/attribuer_voix.py --genre f --fichier scratch/candidates.txt

POURQUOI, ALORS QUE `catalogue_voix.py` EXISTE. Le catalogue balaie tout l'espace — 1 659
variantes féminines avec l'axe débit — et met une demi-heure par genre, quand il ne se fait pas
tuer en route (trois fois de suite côté féminin). Or la question du jour n'est pas « combien de
places existe-t-il » : c'est « ces dix voix-là tiennent-elles ». Mesurer dix candidates prend deux
minutes et répond exactement à ça.

Les clips des mélanges sont ceux du catalogue, déjà sur le disque : décalage et débit s'appliquent
par traitement du signal, donc aucun appel au modèle. Un mélange jamais généré est signalé, pas
inventé.

Format d'une candidate : `<timbre>@<décalage>x<débit>` — `serena:0.8+sohee:0.2@+3x0.92` se lit
« ce mélange, descendu de 3 demi-tons, à 92 % de la vitesse ».
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalogue_voix as CAT  # noqa: E402
from descente_voix import _comprimer_wsola, descendre  # noqa: E402

CANDIDATE = re.compile(r"^(?P<spec>[^@]+)@(?P<dec>[+-]?\d+(?:\.\d+)?)x(?P<debit>\d+(?:\.\d+)?)$")


def parse(brut: str) -> dict:
    m = CANDIDATE.match(brut.strip())
    if not m:
        raise SystemExit(f"candidate illisible : {brut!r} (attendu « timbre@+3x0.92 »)")
    return {"spec": m.group("spec").strip(), "decalage": float(m.group("dec")),
            "debit": float(m.group("debit"))}


def _variante(dossier: Path, ids: list, dec: float, debit: float, qwen3tts) -> list:
    """Les clips d'un mélange, décalés et redébités. Rend [] si le mélange n'a jamais été généré."""
    import soundfile as sf

    sortie = []
    for ident in ids:
        source = dossier / f"{ident}.ogg"
        if not source.exists():
            return []
        if dec == 0.0 and debit == 1.0:
            sortie.append(source)
            continue
        cible = source.with_suffix(f".a{int(dec)}v{int(debit * 100)}.ogg")
        if not cible.exists():
            onde, sr = sf.read(str(source))
            y = descendre(onde, dec, sr) if dec else onde
            if debit != 1.0:
                y = _comprimer_wsola(y, debit, sr)
            qwen3tts._ecrit(y, sr, cible, "ogg")
        sortie.append(cible)
    return sortie


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates", nargs="*")
    ap.add_argument("--genre", choices=["f", "m"], default="f")
    ap.add_argument("--fichier", type=Path, help="une candidate par ligne (# = commentaire)")
    ap.add_argument("--lot", type=int, default=6)
    args = ap.parse_args()

    brutes = list(args.candidates)
    if args.fichier:
        brutes += [l.split("#")[0].strip() for l in
                   args.fichier.read_text(encoding="utf-8").splitlines()
                   if l.split("#")[0].strip()]
    if not brutes:
        ap.error("aucune candidate")
    candidates = [parse(b) for b in brutes]

    import bench_qwen3tts as mesures
    import qwen3tts

    base = CAT.FEMININS if args.genre == "f" else CAT.MASCULINS
    catalogue = MEDIA / f"docs/ecoute-qwen3-tts/25-catalogue-{args.genre}"
    ech = CAT.echantillon(args.lot)
    ids = [l["id"] for l in ech]

    def dossier_de(spec: str) -> Path:
        return catalogue / spec.replace(":", "-").replace("+", "_")

    # Les voix en service, mesurées sur le MÊME échantillon. Sans cela, la distance mêlerait le
    # timbre et le texte prononcé.
    service = {n: (s, d) for n, (s, d) in CAT._voix_en_service().items()
               if all(p.split(":")[0] in base for p in s.split("+"))}
    import voix_personnage
    debits = {p["nom"]: float(p.get("debit", 1.0) or 1.0)
              for p in voix_personnage.PERSONNAGES.values()}

    mesurees, absents = [], []
    for nom, (spec, dec) in sorted(service.items()):
        clips = _variante(dossier_de(spec), ids, dec or 0.0, debits.get(nom, 1.0), qwen3tts)
        if not clips:
            absents.append(f"{nom} ({spec})")
            continue
        mesurees.append({"nom": nom, "spec": spec, "decalage": dec or 0.0,
                         "debit": debits.get(nom, 1.0), "en_service": True,
                         **CAT._mesure(clips, mesures)})
    if absents:
        print(f"{len(absents)} voix en service non mesurables (mélange jamais généré) : "
              + ", ".join(absents[:6]) + ("…" if len(absents) > 6 else ""))

    print(f"\n{len(mesurees)} voix en service mesurées · {len(candidates)} candidates\n")
    retenues, refusees = list(mesurees), []
    for c in candidates:
        clips = _variante(dossier_de(c["spec"]), ids, c["decalage"], c["debit"], qwen3tts)
        if not clips:
            print(f"  ✗ {c['spec']}@{c['decalage']:+.0f}x{c['debit']:.2f} — mélange jamais "
                  f"généré, lancer catalogue_voix.py")
            continue
        v = {"nom": f"{c['spec']} {c['decalage']:+.0f}st ×{c['debit']:.2f}", **c,
             "en_service": False, **CAT._mesure(clips, mesures)}
        proches = [r["nom"] for r in retenues if not CAT._separees(v, r, mesures)]
        if proches:
            refusees.append((v, proches))
            print(f"  ✗ {v['nom']:46s} {v['f0']:5.0f}Hz  trop proche de : "
                  + ", ".join(proches[:3]))
        else:
            retenues.append(v)
            print(f"  ✓ {v['nom']:46s} {v['f0']:5.0f}Hz  plage {v['plage']:4.0f}Hz  "
                  f"ambitus {v['ambitus']:.1f}st")

    neuves = [v for v in retenues if not v["en_service"]]
    print(f"\n{len(neuves)} candidates retenues, {len(refusees)} refusées")
    print("Rappel : la mesure écarte, elle ne choisit pas. À écouter avant d'attribuer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
