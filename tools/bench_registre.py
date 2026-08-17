#!/usr/bin/env python3
"""Banc des CONSIGNES de jeu d'un personnage — à lancer avec .venv-mlx.

    ../.venv-mlx/bin/python tools/bench_registre.py virion
    ../.venv-mlx/bin/python tools/bench_registre.py virion --lot 10

Le timbre dit QUI parle, la consigne dit COMMENT. Ce banc ne touche pas au timbre : il fait
dire les MÊMES répliques, par le MÊME timbre et aux MÊMES graines, avec des consignes
différentes — la seule variable est la phrase d'intention donnée au modèle.

POURQUOI CE LEVIER PLUTÔT QU'UN AUTRE. Qwen3-TTS n'expose ni hauteur ni vitesse : tout ce qui
n'est pas le timbre passe par une phrase en français. Et ce dépôt a déjà mesuré ce que cette
phrase sait faire — sur Arthur, elle échouait à distinguer trois ans de six ans (des STADES)
mais créait sans peine un registre d'enfant contre un registre de narration (des REGISTRES).
« Homme âgé, grave » est un registre. C'est le bon usage du levier, pas celui qui avait raté.

CE QUE LA MESURE PEUT DIRE, ET CE QU'ELLE NE PEUT PAS. Elle donne la hauteur (F0 médiane) et
la couleur (barycentre spectral) : une voix qui descend et qui perd ses aigus est objectivement
plus grave et plus sombre. Elle ne dit RIEN de « est-ce que ça sonne vieux » — la sensation
d'âge tient au débit, au souffle, aux fins de phrase, et aucun de ces chiffres ne l'attrape.
Le banc classe donc les candidates et produit un dossier d'écoute ; il ne choisit pas.
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

# Consignes candidates, par personnage. La première est TOUJOURS le témoin : la consigne
# réellement en service, sans quoi on comparerait des variantes entre elles sans savoir si
# l'une d'elles fait mieux que ce qu'on a déjà.
CANDIDATES = {
    "virion": [
        ("temoin", "Ton naturel de conversation, engagé et vivant."),
        ("age_pose", "Voix d'homme âgé, grave et posée. Débit lent, appuyé sur les fins de "
                     "phrase."),
        ("vieux_roi", "Ton d'un vieil homme qui n'a plus rien à prouver : grave, lent, "
                      "autorité tranquille, sans jamais hausser le ton."),
        ("grand_pere", "Voix de grand-père, grave et chaude, un peu voilée par l'âge."),
        ("use", "Voix très grave de vieil homme, timbre rauque et usé, souffle court entre "
                "les groupes de mots."),
        ("poitrine", "Parle comme un homme très âgé : voix descendue dans la poitrine, lente, "
                     "légèrement éraillée, sans énergie juvénile."),
    ],
}


def _barycentre(chemin: Path) -> float:
    """Barycentre spectral de la bande vocale — la « couleur », sans erreur d'octave."""
    import soundfile as sf

    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    spectre = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    masque = (f > 60) & (f < 4000)
    poids = spectre[masque].sum()
    return float((f[masque] * spectre[masque]).sum() / poids) if poids > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personnage", choices=sorted(CANDIDATES))
    ap.add_argument("--lot", type=int, default=8, help="nombre de répliques par consigne")
    args = ap.parse_args()

    import bench_qwen3tts as mesures
    import qwen3tts
    import voix_personnage as vp
    from casting_timbre import _echantillon

    perso = vp._perso(args.personnage)
    echantillon = _echantillon(vp._lignes(perso), args.lot)
    sortie = MEDIA / f"docs/ecoute-qwen3-tts/12-registre-{args.personnage}"
    print(f"{perso['nom']} · timbre {perso['timbre']} (inchangé) · "
          f"{len(echantillon)} répliques × {len(CANDIDATES[args.personnage])} consignes")
    for l in echantillon:
        print(f"  [{l['chapitre']:>8s}] « {l['texte'][:64]} »")

    modele = qwen3tts._charge("customvoice")
    rapport = {"personnage": perso["nom"], "timbre": perso["timbre"],
               "repliques": [{k: l[k] for k in ("clip", "chapitre", "texte")}
                             for l in echantillon],
               "consignes": {}}
    for nom, consigne in CANDIDATES[args.personnage]:
        clips = []
        for i, ligne in enumerate(echantillon):
            # Graine liée au RANG dans l'échantillon, identique d'une consigne à l'autre :
            # c'est ce qui rend les lots comparables. Changer la graine avec la consigne
            # mélangerait l'effet de l'intention et celui du tirage.
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"], consigne,
                                       perso["timbre"], seed=5000 + i, temperature=0.7)
            chemin = sortie / nom / f"{ligne['clip']}.ogg"
            qwen3tts._ecrit(onde, modele.sample_rate, chemin, "ogg")
            clips.append(chemin)
        descr = [mesures._descripteurs(c) for c in clips]
        f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
        r = {"consigne": consigne,
             "f0_median": float(np.median(f0)) if f0 else 0.0,
             "barycentre": float(np.median([_barycentre(c) for c in clips])),
             "duree_totale": float(sum(d["duree"] for d in descr)),
             "voise": float(np.median([d["voise"] for d in descr]))}
        rapport["consignes"][nom] = r
        print(f"  {nom:12s} F0 {r['f0_median']:5.0f} Hz   barycentre {r['barycentre']:5.0f} Hz"
              f"   durée {r['duree_totale']:5.1f} s", flush=True)
    del modele

    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "rapport_registre.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    ref = rapport["consignes"]["temoin"]
    print("\n" + "=" * 76)
    print(f"{'consigne':13s} {'F0':>7s} {'Δ F0':>7s} {'barycentre':>11s} {'Δ bary':>8s} "
          f"{'durée':>7s} {'Δ durée':>8s}")
    for nom, r in rapport["consignes"].items():
        print(f"{nom:13s} {r['f0_median']:5.0f}Hz {r['f0_median'] - ref['f0_median']:+6.0f} "
              f"{r['barycentre']:9.0f}Hz {r['barycentre'] - ref['barycentre']:+7.0f} "
              f"{r['duree_totale']:6.1f}s {r['duree_totale'] - ref['duree_totale']:+7.1f}")
    print(f"\nÀ écouter : {sortie.relative_to(MEDIA)}")
    print("La durée est le témoin du DÉBIT : une consigne qui ralentit vieillit une voix "
          "plus sûrement qu'une consigne qui la descend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
