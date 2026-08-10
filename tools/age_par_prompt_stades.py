#!/usr/bin/env python3
"""Chercher, pour CHAQUE stade d'Arthur, une formulation de prompt d'âge qui agisse.

    ../.venv-mlx/bin/python tools/age_par_prompt_stades.py

Le témoin de `voix_age_arthur.py temoin` a tranché : le prompt d'âge ne déplace la voix qu'au
stade bambin (+48 Hz). Sur `s03_road`, `s03_child`, `s04_teen` et `s05_academy` son apport est
de -6, +4, -21 et +17 Hz — du bruit, signes compris. Les quatre prompts étaient écrits, ils
étaient bien transmis, et ils ne faisaient rien : un mécanisme présent n'est pas un mécanisme
actif.

Avant d'envisager de toucher au timbre validé — ce qui a déjà été refusé une fois, à raison —
il faut épuiser le levier qui n'y touche pas. La seule formulation qui ait jamais marché est
celle du stade bambin, et elle a une forme précise : un IMPÉRATIF (« Parle exactement comme… »),
une hauteur nommée (« haut perchée »), une intonation, un débit. Les quatre autres décrivaient
un état (« voix claire et légère, curieuse ») sans jamais demander de monter.

On compare donc trois familles sur les répliques réelles de chaque stade :

  * `sobre`    — la formulation en place, pour repère ;
  * `insistant` — la forme du bambin, transposée à l'âge du stade ;
  * `intense`  — la même, plus le registre d'âge nommé deux fois et une consigne de tessiture.

Une formulation se mesure comme une dose : au stade bambin, « enfant-jeu » RETOMBAIT à 130 Hz
quand « enfant-insistant » montait à 164. Plus insistant ne veut pas dire plus haut, et c'est
pour ça qu'on mesure au lieu de choisir la plus emphatique.
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
SORTIE = MEDIA / "docs/ecoute-qwen3-tts/8-ages-par-prompt/formulations"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# `age` : ce que le stade doit faire entendre. Les âges viennent de `character_plan.json`, pas
# d'une invention d'ici — voix et sprite doivent parler du même personnage.
STADES = {
    "s03_road": ("cinq ans", 250.0),
    "s03_child": ("six ans", 240.0),
    "s04_teen": ("treize ans", 200.0),
    "s05_academy": ("quinze ans", 175.0),
}

SOBRES = {
    "s03_road": ("Parle comme un petit garçon de cinq ans : voix claire et haut perchée, "
                 "phrases courtes, élan un peu impatient."),
    "s03_child": ("Parle comme un garçon de six ans : voix claire et légère, un peu "
                  "haut perchée, curieuse, phrases nettes."),
    "s04_teen": ("Parle comme un garçon de treize ans : voix jeune qui commence à muer, "
                 "plus posée, encore claire mais moins aiguë."),
    "s05_academy": ("Parle comme un adolescent de quinze ans : voix presque adulte, "
                    "assurée et posée, sans rondeur enfantine."),
}


def _insistant(age: str) -> str:
    """La forme qui a marché au stade bambin, transposée : impératif + hauteur + intonation."""
    return (f"Parle exactement comme un garçon de {age} : voix claire et haut perchée, "
            f"jeune et légère, intonation montante, sans gravité d'adulte.")


def _intense(age: str) -> str:
    return (f"Tu ES un garçon de {age} et ta voix doit s'entendre comme telle : nettement plus "
            f"aiguë qu'une voix d'homme, timbre jeune et clair, tessiture haute, souffle court, "
            f"intonation montante en fin de phrase. Jamais une voix d'adulte.")


def main() -> int:
    import bench_qwen3tts as mesures
    import qwen3tts
    import voix_age_arthur as V

    lots = V._repliques_par_stade()
    modele = qwen3tts._charge("customvoice")
    rapport = {"base": V.BASE, "stades": {}}

    for sid, (age, cible) in STADES.items():
        echantillon = V._echantillon(lots.get(sid) or [], 6)
        if not echantillon:
            continue
        variantes = {"sobre": SOBRES[sid], "insistant": _insistant(age),
                     "intense": _intense(age)}
        print(f"\n=== {sid} — {age}, cible {cible:.0f} Hz, {len(echantillon)} répliques",
              flush=True)
        rapport["stades"][sid] = {"age": age, "cible": cible, "variantes": {}}
        for nom, prompt in variantes.items():
            dossier = SORTIE / sid / nom
            clips = []
            for i, ligne in enumerate(echantillon):
                registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"],
                                                          qwen3tts.REGISTRE_DEFAUT)
                instruct = f"{prompt} {qwen3tts.REGISTRES[registre]}".strip()
                chemin = dossier / f"{ligne['id']}.ogg"
                onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"], instruct,
                                           V.TIMBRE, seed=2000 + i, temperature=0.7)
                qwen3tts._ecrit(onde, modele.sample_rate, chemin, "ogg")
                clips.append(chemin)
            r = V._mesure(clips, mesures)
            r["prompt"] = prompt
            rapport["stades"][sid]["variantes"][nom] = r
            print(f"    {nom:10s} F0 {r['f0_median']:5.0f} Hz   plage {r['f0_plage']:4.0f} Hz"
                  f"   cohésion {r['cohesion_moyenne']:.3f}", flush=True)
    del modele

    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "rapport_formulations.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n" + "=" * 74)
    print(f"{'stade':14s} {'cible':>6s} {'sobre':>10s} {'insistant':>10s} {'intense':>10s}")
    for sid, d in rapport["stades"].items():
        v = d["variantes"]
        print(f"{sid:14s} {d['cible']:5.0f}Hz "
              + " ".join(f"{v[n]['f0_median']:9.0f}Hz" for n in ("sobre", "insistant", "intense")))
    print(f"\nÀ écouter : {SORTIE.relative_to(MEDIA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
