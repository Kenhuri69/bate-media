#!/usr/bin/env python3
"""Banc de DESCENTE DE VOIX à durée constante — à lancer avec .venv-mlx.

    ../.venv-mlx/bin/python tools/bench_grave.py virion
    ../.venv-mlx/bin/python tools/bench_grave.py virion --demi-tons 1,2,3,4

POURQUOI UN TRAITEMENT DU SIGNAL, ALORS QUE TOUT LE RESTE PASSE PAR LE MODÈLE. Parce que le
modèle ne sait pas descendre une voix. Mesuré sur Virion, 8 répliques réelles, six consignes
d'intention (`bench_registre.py`) : **toutes montent la F0**, de +1 à +16 Hz, et éclaircissent
le timbre de +9 à +56 Hz de barycentre. Demander « rauque et usé » fait forcer la voix, donc la
monte. Qwen3-TTS n'expose ni hauteur ni vitesse, et les trois timbres masculins de CustomVoice
tiennent tous entre 130 et 175 Hz : il n'y a pas de voix grave à choisir.

COMMENT ON DESCEND SANS RALENTIR. Rejouer les mêmes échantillons à une cadence plus lente
descend la hauteur mais rallonge la durée du même facteur — et RALENTIR A ÉTÉ REFUSÉ. On
rattrape donc la durée par une compression WSOLA du rapport inverse, qui raccourcit sans
remonter la hauteur. Vérifié sur signal de synthèse : à -3 demi-tons, 130 Hz devient 109 Hz et
la durée bouge de moins d'un millième.

Les FORMANTS descendent avec la hauteur, ce qu'un décalage « propre » à formants préservés
éviterait justement. On le garde volontairement : des formants plus bas s'entendent comme un
conduit vocal plus grand, donc un corps plus vieux. C'est là l'essentiel de l'effet « homme
mûr » — la hauteur seule ne le donne pas.

La contrepartie est ailleurs que dans le débit : trop de descente creuse la voix jusqu'au
grondement, et WSOLA lisse les attaques. C'est ce que ce banc met à l'oreille, et il ne
tranche pas — il produit un dossier d'écoute et les mesures qui vont avec.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


from descente_voix import descendre  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personnage")
    ap.add_argument("--demi-tons", default="1,2,3,4")
    ap.add_argument("--lot", type=int, default=6)
    ap.add_argument("--consigne", default=None,
                    help="consigne de jeu à ajouter au meilleur candidat (ex. vieux_roi)")
    args = ap.parse_args()

    import bench_qwen3tts as mesures
    import qwen3tts
    import voix_personnage as vp
    from casting_timbre import _echantillon

    perso = vp._perso(args.personnage)
    echantillon = _echantillon(vp._lignes(perso), args.lot)
    sortie = MEDIA / f"docs/ecoute-qwen3-tts/13-grave-{args.personnage}"
    paliers = [0.0] + [float(x) for x in args.demi_tons.split(",")]

    consigne = None
    if args.consigne:
        from bench_registre import CANDIDATES
        consigne = dict(CANDIDATES[args.personnage])[args.consigne]
    print(f"{perso['nom']} · timbre {perso['timbre']} · {len(echantillon)} répliques × "
          f"{len(paliers)} paliers" + (f" · consigne « {args.consigne} »" if consigne else ""))

    modele = qwen3tts._charge("customvoice")
    # UNE SEULE GÉNÉRATION, puis N descentes du même signal. Regénérer par palier ferait varier
    # la prise en même temps que la descente, et on ne saurait plus lequel des deux s'entend.
    base = []
    for i, ligne in enumerate(echantillon):
        instruct = consigne or vp._instruct(qwen3tts, ligne)
        onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"], instruct,
                                   perso["timbre"], seed=5000 + i, temperature=0.7)
        base.append((ligne, onde))
    sr = modele.sample_rate
    del modele

    rapport = {"personnage": perso["nom"], "timbre": perso["timbre"],
               "consigne": args.consigne, "paliers": {}}
    for n in paliers:
        nom = "temoin" if n == 0 else f"moins{str(n).replace('.', 'v')}st"
        clips = []
        for ligne, onde in base:
            chemin = sortie / nom / f"{ligne['clip']}.ogg"
            qwen3tts._ecrit(descendre(onde, n, sr), sr, chemin, "ogg")
            clips.append(chemin)
        descr = [mesures._descripteurs(c) for c in clips]
        f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
        rapport["paliers"][nom] = {
            "demi_tons": n,
            "f0_median": float(np.median(f0)) if f0 else 0.0,
            "duree_totale": float(sum(d["duree"] for d in descr))}
        r = rapport["paliers"][nom]
        print(f"  {nom:12s} F0 {r['f0_median']:5.0f} Hz   durée {r['duree_totale']:6.1f} s",
              flush=True)

    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "rapport_grave.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    ref = rapport["paliers"]["temoin"]
    print("\n" + "=" * 62)
    print(f"{'palier':13s} {'F0':>7s} {'Δ F0':>7s} {'durée':>8s} {'Δ durée':>9s}")
    for nom, r in rapport["paliers"].items():
        print(f"{nom:13s} {r['f0_median']:5.0f}Hz {r['f0_median'] - ref['f0_median']:+6.0f} "
              f"{r['duree_totale']:7.1f}s {100 * (r['duree_totale'] / ref['duree_totale'] - 1):+8.0f}%")
    print(f"\nÀ écouter : {sortie.relative_to(MEDIA)}")
    print("Repères : Arthur parlé 131 Hz, Arthur narration 119 Hz, Tessia 216 Hz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
