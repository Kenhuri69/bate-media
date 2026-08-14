#!/usr/bin/env python3
"""Balayage de doses pour la voix de Tessia (BATE) — à lancer avec .venv-mlx.

    ../.venv-mlx/bin/python tools/tournoi_timbre_tessia.py
    ../.venv-mlx/bin/python tools/tournoi_timbre_tessia.py --mesures-seules

Même principe que le tournoi d'Arthur (`tournoi_timbre_arthur.py`, lot 5), appliqué à
l'arbitrage que le casting a laissé ouvert. Le casting (lot 9) a fait ce que fait un
casting : auditionner les timbres PURS — les quatre féminins de CustomVoice, soit la
totalité du choix contraint du modèle. Il en est sorti deux têtes de série, et comme pour
Arthur **elles ne gagnent pas sur le même critère** :

  * `sohee` tient la F0 (plage 13 Hz contre 58-69 aux autres) mais bouge de 23 Hz au
    barycentre entre l'enfant et l'adolescente ;
  * `ono_anna` est la seule qui ne bouge pas au barycentre (-11 Hz) mais c'est la plus
    dispersée en F0 (plage 69 Hz).

Chacune est donc imparfaite sur la grandeur que l'autre tient. La question restante n'est
pas « laquelle des deux » mais **quelle dose** — d'où un balayage, et non un duel. C'est
exactement ce qui s'est produit sur Arthur : deux têtes de série imparfaites chacune à sa
manière, et un mélange 50/50 qui gagnait sur les deux critères à la fois.

À battre : `sohee` passe déjà les deux portes de ce banc (13 Hz de plage, 23 Hz d'écart
entre âges). Un mélange ne se justifie que s'il fait mieux, et « mieux » inclut
l'**ambitus** — le casting signalait lui-même que la stabilité récompense la voix la plus
plate, et `sohee` est peut-être régulière parce qu'elle joue moins.

Ce que ce banc NE fait pas, et c'est volontaire :

  * **aucun prompt d'âge.** Tessia traverse deux âges sur les ch0-60 et c'est la même voix
    qui devra les porter — le registre par âge est un second problème, tranché après. Les
    mêler ferait juger un timbre sur un réglage. (Sur Arthur, le prompt d'âge sépare bien
    la voix parlée de la narration mais ne distingue pas les stades entre eux : lot 8.)
  * **aucune dilution sous 50 %.** Un timbre qu'on validera à l'oreille ne se diluera pas
    ensuite pour atteindre une hauteur — la règle est écrite au prix d'une erreur (Arthur
    toddler livré à 80 % `serena`). Les doses balayées ici gardent donc une majoritaire
    identifiable, et l'expressivité se teste à 20 %, pas à 80.

La mesure écarte, elle ne choisit pas : elle sert à ne soumettre à l'oreille que les
timbres qui restent le même personnage d'une réplique à l'autre. Le choix final est humain
— convention de la forge depuis le premier timbre d'Arthur.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
CASTING = MEDIA / "docs/ecoute-qwen3-tts/9-casting-tessia"
ECOUTE = MEDIA / "docs/ecoute-qwen3-tts/10-melanges-tessia"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Le balayage. Les deux timbres purs sont des ANCRAGES : sans eux, rien ne dirait si un
# écart mesuré vient de la dose ou du jour. Ils sont repris tels quels du lot 9 (mêmes
# graines, donc mêmes clips) plutôt que régénérés — régénérer pour recalculer une
# statistique donnerait d'autres clips, donc d'autres chiffres, sans qu'on sache lequel du
# critère ou du tirage a bougé.
#
# `serena` revient à 20 % et seulement là : c'est la candidate la plus expressive du lot 9
# (elle bouge de 75 Hz selon le TEXTE prononcé, ce qui la disqualifiait comme voix
# principale), donc le contre-poison du biais que le casting signalait lui-même — « la
# stabilité récompense la voix la plus plate ». Un lot trop plat ne fait entendre personne.
CANDIDATS = [
    "sohee",                        # ancrage : tête de série « stabilité F0 »
    "ono_anna",                     # ancrage : tête de série « stabilité entre âges »
    "sohee:0.7+ono_anna:0.3",       # sohee dominante, une pointe d'ono_anna
    "sohee:0.5+ono_anna:0.5",       # le point qui a gagné sur Arthur
    "sohee:0.3+ono_anna:0.7",       # l'inverse : ono_anna dominante
    "sohee:0.8+serena:0.2",         # la plus stable, rendue un peu plus joueuse
    "ono_anna:0.8+serena:0.2",      # la même question sur l'autre tête de série
]

# Les deux ancrages, et les dossiers du lot 9 d'où leurs clips sont repris.
PURS = {"sohee": CASTING / "sohee", "ono_anna": CASTING / "ono_anna"}

# Les deux portes, une par grandeur, parce qu'aucune ne suffit et qu'elles divergent.
# 30 Hz : au-dessus des meilleurs purs de chaque grandeur (13 Hz de plage F0 pour `sohee`,
# 11 Hz d'écart entre âges pour `ono_anna`) et nettement sous le paquet des écartées
# (58-69 Hz de plage, 71-75 Hz d'écart). Ce n'est pas un seuil physiologique, c'est la
# frontière observée entre les deux paquets du lot 9 — un candidat qui la franchit sur les
# DEUX grandeurs est ce que le balayage cherche.
PORTE_PLAGE_F0 = 30.0
PORTE_ECART_AGE = 30.0


def _barycentre(chemin: Path) -> float:
    """Barycentre de l'énergie vocale (60-800 Hz) — copié de `voix_age_arthur._barycentre`.

    Recopié et non importé : `voix_age_arthur` est le module des âges d'Arthur, l'importer
    ici pour six lignes attacherait ce banc à ses 45 ko et à ses constantes de stades.

    La F0 par autocorrélation se trompe d'octave quand l'énergie basse est faible et a déjà
    produit un verdict entièrement faux sur les voix d'Arthur (lot 8). Ici elle est
    crédible — 0,0 à 0,1 % d'énergie sous 150 Hz, cohérent avec un fondamental à
    210-255 Hz — mais elle reste la grandeur qui PEUT se tromper, d'où les deux.
    """
    import soundfile as sf

    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    spectre = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    m = (f > 60) & (f < 800)
    return float((f[m] * spectre[m]).sum() / spectre[m].sum()) if spectre[m].sum() > 0 else 0.0


def _mesure_lot(clips: list, ages: dict, mesures) -> dict:
    """Descripteurs d'un timbre : les deux grandeurs, et pour chacune sa DISPERSION."""
    descr = {c: mesures._descripteurs(c) for c in clips}
    f0 = [d["f0_median"] for d in descr.values() if d["f0_median"] > 0]
    bary = {c: _barycentre(c) for c in clips}
    par_age_f0, par_age_bary = {}, {}
    for age, chemins in ages.items():
        v = [descr[c]["f0_median"] for c in chemins if descr[c]["f0_median"] > 0]
        par_age_f0[age] = float(np.median(v)) if v else 0.0
        b = [bary[c] for c in chemins if bary[c] > 0]
        par_age_bary[age] = float(np.median(b)) if b else 0.0
    valeurs_bary = [v for v in bary.values() if v > 0]
    return {
        **mesures._dispersion_timbre(clips),
        "f0_median": float(np.median(f0)) if f0 else 0.0,
        "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0,
        "f0_par_age": par_age_f0,
        "barycentre_median": float(np.median(valeurs_bary)) if valeurs_bary else 0.0,
        "barycentre_plage": (float(np.max(valeurs_bary) - np.min(valeurs_bary))
                             if valeurs_bary else 0.0),
        "barycentre_par_age": par_age_bary,
        # Le critère décisif du lot 9, sur la grandeur qui ne peut pas se tromper d'octave :
        # de combien la voix change entre l'enfant et l'adolescente ALORS QU'AUCUN prompt
        # d'âge n'est donné. Ce qui bouge ici, c'est le texte qui le fait bouger.
        "ecart_age_barycentre": abs(par_age_bary.get("enfant", 0.0)
                                    - par_age_bary.get("adolescente", 0.0)),
        "ecart_age_f0": abs(par_age_f0.get("enfant", 0.0)
                            - par_age_f0.get("adolescente", 0.0)),
        # L'ambitus dit si la voix JOUE. Une porte de stabilité récompense mécaniquement le
        # timbre le plus plat : sans cette colonne, on choisirait la voix qui récite.
        "ambitus_st": float(np.mean([d["f0_ambitus_st"] for d in descr.values()])),
        "duree_totale": float(sum(d["duree"] for d in descr.values())),
        "par_clip": {c.stem: {"f0": round(descr[c]["f0_median"]),
                              "barycentre": round(bary[c]),
                              "duree": round(descr[c]["duree"], 1),
                              "ambitus_st": round(descr[c]["f0_ambitus_st"], 1)}
                     for c in clips},
    }


def _dossier(spec: str) -> Path:
    return ECOUTE / spec.replace(":", "-").replace(".", "-").replace("+", "_")


def _reprend_ancrage(spec: str, echantillon: list) -> list:
    """Copie les clips d'un timbre pur depuis le lot 9 plutôt que de les régénérer."""
    source = PURS[spec]
    cible = _dossier(spec)
    cible.mkdir(parents=True, exist_ok=True)
    faits = []
    for ligne in echantillon:
        origine = source / f"{ligne['id']}.ogg"
        if not origine.exists():
            raise SystemExit(f"ancrage manquant : {origine} — relancer tessia_casting.py")
        destination = cible / origine.name
        if not destination.exists():
            shutil.copy2(origine, destination)
        faits.append(destination)
    print(f"  {len(faits)} clips repris du lot 9 (mêmes graines, mêmes clips)", flush=True)
    return faits


def _genere(modele, qwen3tts, spec: str, echantillon: list) -> tuple:
    """Les 8 répliques d'un mélange. Rend les clips, le RTF et le nombre de relances."""
    dossier = _dossier(spec)
    faits, secondes_audio, secondes_calcul, relances = [], 0.0, 0.0, 0
    for i, ligne in enumerate(echantillon):
        registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
        cible = dossier / f"{ligne['id']}.ogg"
        t0 = time.time()
        # seed=3000+i : LA MÊME que le casting. Sans quoi les ancrages repris du lot 9 et
        # les mélanges générés ici seraient tirés différemment, et l'écart mesuré entre un
        # pur et son mélange contiendrait le tirage en plus de la dose.
        onde, essais = qwen3tts._genere(
            modele, "customvoice", ligne["texte"], qwen3tts.REGISTRES[registre],
            spec, seed=3000 + i, temperature=0.7)
        secondes_calcul += time.time() - t0
        secondes_audio += len(onde) / modele.sample_rate
        relances += essais
        qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
        faits.append(cible)
        print(f"  [{ligne['age']:12s}] {ligne['id']:18s} "
              f"{len(onde) / modele.sample_rate:5.1f}s", flush=True)
    return faits, secondes_calcul / max(secondes_audio, 1e-9), relances


def main() -> int:
    import bench_qwen3tts as mesures
    import tessia_casting

    mesures_seules = "--mesures-seules" in sys.argv
    # Le même échantillon que le casting, par construction : quatre répliques réelles de
    # chaque âge, les plus longues. Longues à dessein — la F0 médiane d'un clip de deux
    # secondes repose sur trop peu de trames voisées pour valoir une mesure.
    echantillon = tessia_casting._echantillon()
    ECOUTE.mkdir(parents=True, exist_ok=True)

    print(f"{len(CANDIDATS)} timbres × {len(echantillon)} répliques réelles de Tessia "
          f"(aucun prompt d'âge)")
    for l in echantillon:
        print(f"  [{l['age']:12s}] {l['id']:18s} « {l['texte'][:60]} »")

    rapport = {"candidats": CANDIDATS,
               "portes": {"plage_f0_hz": PORTE_PLAGE_F0, "ecart_age_hz": PORTE_ECART_AGE},
               "repliques": [{k: l[k] for k in ("id", "chapitre", "texte", "age")}
                             for l in echantillon],
               "timbres": {}}

    modele = qwen3tts = None
    if not mesures_seules and any(c not in PURS for c in CANDIDATS):
        import qwen3tts
        modele = qwen3tts._charge("customvoice")

    for spec in CANDIDATS:
        print(f"\n=== {spec}", flush=True)
        if spec in PURS:
            faits, rtf, relances = _reprend_ancrage(spec, echantillon), None, None
        elif mesures_seules:
            faits = sorted(_dossier(spec).glob("*.ogg"))
            if not faits:
                print("  (aucun clip — lancer sans --mesures-seules)", flush=True)
                continue
            rtf, relances = None, None
        else:
            faits, rtf, relances = _genere(modele, qwen3tts, spec, echantillon)

        par_age = {}
        index = {l["id"]: l["age"] for l in echantillon}
        for c in faits:
            par_age.setdefault(index[c.stem], []).append(c)
        rapport["timbres"][spec] = {
            **_mesure_lot(faits, par_age, mesures), "rtf": rtf, "relances": relances,
            "ancrage": spec in PURS, "dossier": str(_dossier(spec).relative_to(MEDIA)),
        }
        r = rapport["timbres"][spec]
        print(f"    F0 {r['f0_median']:5.0f} Hz (plage {r['f0_plage']:4.0f})   "
              f"barycentre {r['barycentre_median']:5.0f} Hz "
              f"(écart entre âges {r['ecart_age_barycentre']:4.0f})", flush=True)

    del modele
    (ECOUTE / "rapport_melanges.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    # --- verdict ---------------------------------------------------------------
    print("\n" + "=" * 94)
    print(f"PORTES : plage F0 ≤ {PORTE_PLAGE_F0:.0f} Hz  ET  écart entre âges "
          f"(barycentre) ≤ {PORTE_ECART_AGE:.0f} Hz")
    print("Sur les timbres purs, `sohee` est le SEUL à passer les deux (13 et 23 Hz) ; c'est")
    print("donc lui que le balayage doit battre, pas seulement égaler — et sur l'ambitus")
    print("autant que sur la stabilité, puisqu'il gagne en partie en jouant moins.\n")
    print(f"{'timbre':26s} {'F0 méd.':>9s} {'plage':>7s} {'bary.':>7s} {'écart âges':>11s} "
          f"{'ambitus':>8s} {'cohés.':>7s}  verdict")
    for spec, r in sorted(rapport["timbres"].items(),
                          key=lambda kv: (kv[1]["f0_plage"] / PORTE_PLAGE_F0
                                          + kv[1]["ecart_age_barycentre"] / PORTE_ECART_AGE)):
        stable_f0 = r["f0_plage"] <= PORTE_PLAGE_F0
        stable_age = r["ecart_age_barycentre"] <= PORTE_ECART_AGE
        verdict = ("à écouter" if stable_f0 and stable_age else
                   "change d'âge selon le texte" if stable_f0 else
                   "dispersé d'une réplique à l'autre" if stable_age else "écarté")
        print(f"{spec:26s} {r['f0_median']:8.0f}Hz {r['f0_plage']:6.0f}Hz "
              f"{r['barycentre_median']:6.0f}Hz {r['ecart_age_barycentre']:10.0f}Hz "
              f"{r['ambitus_st']:7.1f}st {r['cohesion_moyenne']:7.3f}  {verdict}")
    print("\nL'ambitus est là pour l'arbitrage inverse : un timbre peut passer les deux")
    print("portes parce qu'il est PLAT. Un lot dispersé fait entendre plusieurs personnes,")
    print("un lot plat n'en fait entendre aucune. Seule l'oreille tranche entre les deux.")
    print(f"\nÀ écouter : bash {(ECOUTE / '..' / 'ecouter.sh').resolve().relative_to(MEDIA)} 6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
