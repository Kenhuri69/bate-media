#!/usr/bin/env python3
"""Faire l'âge d'Arthur par le PROMPT, en gardant le timbre validé intact.

Le premier essai déclinait l'âge en diluant `aiden:0.5+ryan:0.5` dans une composante plus
aiguë. Ça marchait sur le papier — 245 Hz au stade toddler — mais au prix de réduire le
timbre validé à 20 % du mélange : ce n'était plus la voix choisie. Objection d'Olivier,
fondée. Une validation porte sur une voix entendue, pas sur une formule.

D'où cette piste, jamais testée : CustomVoice accepte un `instruct` en français, et
l'âge perçu fait partie de ce qu'une voix exprime — pas seulement sa hauteur. Si le prompt
suffit à faire entendre un enfant, le timbre reste à 100 % celui d'Arthur et le problème
de dilution disparaît.

On mesure les deux choses qui décident :
  * la HAUTEUR obtenue, pour savoir si le prompt déplace vraiment la voix ;
  * la part du timbre conservée, qui vaut 100 % par construction ici — c'est le point.

Comparé au mélange à dose égale de dilution, pour ne pas conclure sur une seule branche.

    python tools/age_par_prompt_arthur.py
"""
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
ECOUTE = MEDIA / "docs/ecoute-qwen3-tts/7-age-par-prompt"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = "aiden:0.5+ryan:0.5"          # le timbre validé, gardé INTACT dans les variantes 1-4

# Quatre formulations, de la plus sobre à la plus insistante. Elles ne décrivent pas un
# timbre (CustomVoice ne l'accepte pas, c'est le rôle de VoiceDesign, écarté) mais une
# FAÇON DE PARLER : c'est par là qu'un enfant s'entend — débit, attaque, souffle court —
# autant que par la hauteur.
PROMPTS = {
    "nu": "",
    "enfant-sobre": "Voix d'un petit garçon de trois ans.",
    "enfant-jeu": ("Voix d'un petit garçon de trois ans, aiguë et légère, débit rapide et "
                   "enjoué, phrases courtes, souffle court."),
    "enfant-insistant": ("Parle exactement comme un très jeune enfant de trois ans : voix "
                         "haut perchée, fluette et claire, intonation montante, mots "
                         "détachés, comme un petit garçon qui découvre le monde."),
}

# Le point de comparaison : la dilution livrée, celle qui est refusée. Sans elle on ne
# saurait pas si le prompt fait mieux ou moins bien que ce qu'il remplace.
COMPARAISON = {
    "dilution-refusee (serena 0.8)": ("aiden:0.100+ryan:0.100+serena:0.800", ""),
    "dilution-douce (serena 0.3)": ("aiden:0.350+ryan:0.350+serena:0.300", ""),
}

CIBLE = 270.0                        # repère physiologique d'une voix de trois ans


def main() -> int:
    import bench_qwen3tts as mesures
    import qwen3tts

    lignes = json.loads((RACINE / "voice-agent/training/forge/bate-arthur/lines.json")
                        .read_text(encoding="utf-8"))
    # Les vraies répliques parlées du stade toddler : c'est là que l'âge s'entend, pas
    # dans la narration. Il n'y en a que sept, on les prend toutes.
    lot = [l for l in lignes if l["role"] == "Arthur"
           and l["chapitre"] in ("ch02", "ch03", "ch04", "ch05")]
    print(f"{len(lot)} répliques parlées du stade toddler", flush=True)

    modele = qwen3tts._charge("customvoice")
    rapport = {"base": BASE, "cible_f0": CIBLE, "variantes": {}}
    essais = [(nom, BASE, p) for nom, p in PROMPTS.items()]
    essais += [(nom, spec, p) for nom, (spec, p) in COMPARAISON.items()]

    for nom, spec, prompt in essais:
        dossier = ECOUTE / nom.split(" ")[0].replace(".", "-")
        instruct = f"{prompt} {qwen3tts.REGISTRES['dialogue']}".strip()
        print(f"\n=== {nom}", flush=True)
        clips = []
        for i, ligne in enumerate(lot):
            cible = dossier / f"{ligne['id']}.ogg"
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"], instruct,
                                       spec, seed=2000 + i, temperature=0.7)
            qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
            clips.append(cible)
        descr = [mesures._descripteurs(c) for c in clips]
        f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
        part_base = 1.0 if spec == BASE else round(
            sum(float(x.partition(":")[2]) for x in spec.split("+")
                if x.startswith(("aiden", "ryan"))), 2)
        rapport["variantes"][nom] = {
            "spec": spec, "instruct": instruct, "part_timbre_valide": part_base,
            "f0_median": float(np.median(f0)) if f0 else 0.0,
            "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0,
            "ambitus_st": float(np.mean([d["f0_ambitus_st"] for d in descr])),
            "dossier": str(dossier.relative_to(MEDIA)),
        }
        r = rapport["variantes"][nom]
        print(f"    F0 {r['f0_median']:5.0f} Hz   plage {r['f0_plage']:4.0f} Hz   "
              f"timbre validé conservé à {part_base:.0%}", flush=True)
    del modele

    ECOUTE.mkdir(parents=True, exist_ok=True)
    (ECOUTE / "rapport_prompt.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n" + "=" * 76)
    print(f"{'variante':32s} {'F0':>7s} {'plage':>7s} {'timbre gardé':>13s}")
    for nom, r in sorted(rapport["variantes"].items(), key=lambda kv: -kv[1]["f0_median"]):
        print(f"{nom:32s} {r['f0_median']:6.0f}Hz {r['f0_plage']:6.0f}Hz "
              f"{r['part_timbre_valide']:12.0%}")
    print(f"\ncible {CIBLE:.0f} Hz — mais un timbre gardé à 100 % prime sur l'atteindre")
    return 0


if __name__ == "__main__":
    sys.exit(main())
