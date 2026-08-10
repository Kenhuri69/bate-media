#!/usr/bin/env python3
"""Auditionner les voix candidates de Tessia sur ses VRAIES répliques.

    ../.venv-mlx/bin/python tools/tessia_casting.py

Quatre candidates, et ce ne sont pas quatre au hasard : CustomVoice compte neuf timbres premium
dont **exactement quatre féminins** (`serena`, `vivian`, `ono_anna`, `sohee`). Les auditionner
tous les quatre épuise le choix contraint du modèle — il n'y a pas de cinquième voix de femme à
essayer.

Ce sont des timbres PURS, pas des mélanges. Un mélange se mesure et peut battre un timbre pur
(c'est le cas pour Arthur), mais une audition doit d'abord porter sur des voix entières :
valider `serena:0.6+vivian:0.4` avant d'avoir entendu `serena` reviendrait à choisir une formule
plutôt qu'une voix. Les mélanges viendront après, si l'oreille le demande.

TESSIA TRAVERSE DEUX ÂGES DANS LES CH0-60, et l'échantillon les couvre tous les deux :
cinq ans quand Arthur la trouve captive (ch10-18), adolescente à l'académie de Xyrus (ch44-60).
Un timbre qui tient sur « Tessia Eralith. Et j'ai eu cinq ans. » ne dit rien de ce qu'il donnera
sur ses répliques d'adolescente — et c'est le même personnage, donc la même voix devra porter
les deux. Aucun prompt d'âge n'est appliqué ici : on écoute le TIMBRE, pas sa déclinaison. La
déclinaison par âge est un second problème, et sur Arthur elle s'est révélée sans effet au-delà
du stade bambin (lot d'écoute 8) — raison de plus pour ne pas la mélanger à ce choix-ci.

Rien n'est intégré : ce script ne produit qu'un dossier d'écoute et ses mesures.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
LIGNES = RACINE / "voice-agent/training/forge/bate-tessia/lines.json"
SORTIE = MEDIA / "docs/ecoute-qwen3-tts/9-casting-tessia"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Les quatre timbres féminins de CustomVoice. `eric` et `dylan` sont masculins ET dialectaux ;
# la question ne se pose pas.
CANDIDATES = ["serena", "vivian", "ono_anna", "sohee"]

# Les deux âges que la voix devra porter, et leurs bornes dans `character_plan.json`.
AGES = {"enfant": range(10, 19), "adolescente": range(44, 61)}
PAR_AGE = 4


def _chapitre(ligne: dict) -> int:
    return int(re.search(r"\d+", ligne["chapitre"]).group())


def _echantillon() -> list:
    """Quatre répliques par âge, les plus longues d'abord.

    Les plus longues à dessein : la F0 médiane d'un clip de deux secondes repose sur trop peu de
    trames voisées pour valoir une mesure, piège déjà payé sur le lot 6 des âges d'Arthur — deux
    clips courts y sortaient 50 à 80 Hz au-dessus des quatre longs du même lot. Et une réplique
    longue en dit plus à l'oreille qu'un « ...Je ne sais pas. »
    """
    lignes = json.loads(LIGNES.read_text(encoding="utf-8"))
    lot = []
    for nom, plage in AGES.items():
        du_stade = [l for l in lignes if _chapitre(l) in plage]
        du_stade.sort(key=lambda l: -len(l["texte"]))
        lot += [{**l, "age": nom} for l in du_stade[:PAR_AGE]]
    return lot


def main() -> int:
    import bench_qwen3tts as mesures
    import qwen3tts

    echantillon = _echantillon()
    print(f"{len(echantillon)} répliques réelles de Tessia :")
    for l in echantillon:
        print(f"  [{l['age']:12s}] {l['id']:18s} « {l['texte'][:64]} »")

    modele = qwen3tts._charge("customvoice")
    rapport = {"candidates": CANDIDATES,
               "repliques": [{k: l[k] for k in ("id", "chapitre", "texte", "age")}
                             for l in echantillon],
               "timbres": {}}

    for timbre in CANDIDATES:
        dossier = SORTIE / timbre
        clips, par_age = [], {}
        print(f"\n=== {timbre}", flush=True)
        for i, ligne in enumerate(echantillon):
            registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
            chemin = dossier / f"{ligne['id']}.ogg"
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                       qwen3tts.REGISTRES[registre], timbre,
                                       seed=3000 + i, temperature=0.7)
            qwen3tts._ecrit(onde, modele.sample_rate, chemin, "ogg")
            clips.append(chemin)
            par_age.setdefault(ligne["age"], []).append(chemin)

        descr = [mesures._descripteurs(c) for c in clips]
        f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
        cohesion = mesures._cohesion(clips) if hasattr(mesures, "_cohesion") else None
        r = {"f0_median": float(np.median(f0)) if f0 else 0.0,
             "f0_min": float(np.min(f0)) if f0 else 0.0,
             "f0_max": float(np.max(f0)) if f0 else 0.0,
             "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0,
             "duree_totale": float(sum(d["duree"] for d in descr)),
             "par_age": {}}
        # La F0 par âge n'est pas un test de l'âge — aucun prompt d'âge n'est donné — mais un
        # test de STABILITÉ : un timbre qui change de hauteur selon le texte prononcé ferait
        # entendre deux personnes là où le récit n'en a qu'une.
        for age, chemins in par_age.items():
            f0a = [d["f0_median"] for d in (mesures._descripteurs(c) for c in chemins)
                   if d["f0_median"] > 0]
            r["par_age"][age] = float(np.median(f0a)) if f0a else 0.0
        rapport["timbres"][timbre] = r
        ecart = abs(r["par_age"].get("enfant", 0) - r["par_age"].get("adolescente", 0))
        print(f"    F0 {r['f0_median']:5.0f} Hz   plage {r['f0_plage']:4.0f} Hz   "
              f"enfant {r['par_age'].get('enfant', 0):.0f} / adolescente "
              f"{r['par_age'].get('adolescente', 0):.0f} (écart {ecart:.0f})", flush=True)
    del modele

    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "rapport_casting.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"{'timbre':10s} {'F0':>7s} {'plage':>7s} {'enfant':>8s} {'ado':>7s} {'écart':>7s}")
    for t, r in rapport["timbres"].items():
        e, a = r["par_age"].get("enfant", 0), r["par_age"].get("adolescente", 0)
        print(f"{t:10s} {r['f0_median']:6.0f}Hz {r['f0_plage']:6.0f}Hz "
              f"{e:7.0f}Hz {a:6.0f}Hz {abs(e - a):6.0f}Hz")
    print(f"\nÀ écouter : {SORTIE.relative_to(MEDIA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
