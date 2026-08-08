#!/usr/bin/env python3
"""Tournoi de timbres Qwen3-TTS pour Arthur (BATE) — à lancer avec .venv-mlx.

Ce banc-ci ne rejoue pas le choix du MOTEUR : il est tranché (CustomVoice, cf.
`docs/qwen3-tts.md`). Il tranche l'arbitrage que ce verdict a laissé ouvert — QUEL
timbre pour Arthur — et il le fait parce que les deux candidats sortis en tête ne
gagnent pas sur le même critère :

  * `aiden:0.7+serena:0.3` a la meilleure cohésion (0,959) mais sort à 148 Hz,
  * `aiden:0.8+vivian:0.2` sort à 183 Hz — la hauteur de l'Arthur en service (176–211 Hz,
    un garçon de seize ans) — mais retombe à 0,899 de cohésion, sous Chatterbox (0,941).

Aucun des deux n'est acceptable tel quel : l'un a l'âge du rôle sans la stabilité,
l'autre l'inverse. La question mesurable est donc **la dose** : jusqu'où monter la part
qui remonte la hauteur avant que la cohésion ne passe sous le repère Chatterbox. C'est
un balayage, pas un duel — d'où plusieurs points sur chacun des deux axes.

Deux garde-fous de méthode, hérités des erreurs du banc précédent :

  * **conditions de production** — vraies répliques d'Arthur tirées des timelines
    Dialogic, registres attribués comme en production (`REGISTRE_PAR_ROLE`), graine
    variable d'une réplique à l'autre. Un timbre jugé sur une phrase unique et une
    graine fixe ne dit rien de sa tenue sur quatre-vingt-dix chapitres.
  * **repère réel** — la référence n'est pas un chiffre recopié de la note, elle est
    recalculée sur les .ogg Chatterbox effectivement livrés dans `voices/arthur/`, donc
    au même format que les candidats. Les chiffres de la note, eux, ont été pris sur des
    .wav : ils ne se comparent PAS à ceux d'ici, seul le classement interne vaut.

Le critère qui départage n'est pas celui qu'on attendait. La cohésion MFCC sépare mal
(sept candidats tiennent en 0,10) et elle est biaisée : une voix qui varie peu à
l'intérieur d'une réplique marque mécaniquement mieux, si bien que la porte de cohésion
récompense le timbre le plus PLAT. Ce qui sépare vraiment, c'est la **dispersion de la
hauteur d'un clip à l'autre** (`f0_plage`) : un timbre dont F0 saute de 138 à 296 Hz
selon la réplique n'est pas un personnage, c'en est trois. Et la médiane du lot le
masque complètement — elle affiche alors 195 Hz, pile dans la cible.

La mesure écarte, elle ne choisit pas : elle sert à ne soumettre à l'oreille que les
timbres qui restent le même personnage. Le choix final reste humain — convention de la
forge.

Usage :
    python tools/tournoi_timbre_arthur.py                 # génère puis mesure
    python tools/tournoi_timbre_arthur.py --mesures-seules # re-mesure les clips en place
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
LIGNES = RACINE / "voice-agent/training/forge/bate-arthur/lines.json"
ECOUTE = MEDIA / "docs/ecoute-qwen3-tts/5-tournoi-arthur"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Les candidats du balayage. `aiden` pur et les deux têtes de série servent de points
# d'ancrage : sans eux, rien ne dirait si un écart mesuré vient du candidat ou du jour.
# Les timbres dialectaux (eric, dylan) sont exclus — ce sont eux qui produisaient les
# clips dégénérés en français.
CANDIDATS = [
    "aiden",                       # ancrage : le timbre pur, 140 Hz
    "aiden:0.7+serena:0.3",        # ancrage : tête de série « stabilité »
    "aiden:0.5+serena:0.5",        # dose de serena poussée
    "aiden:0.8+vivian:0.2",        # ancrage : tête de série « hauteur »
    "aiden:0.9+vivian:0.1",        # vivian réduite : la cohésion remonte-t-elle ?
    "aiden:0.7+vivian:0.3",        # vivian poussée : jusqu'où avant de casser ?
    "aiden:0.6+serena:0.3+vivian:0.1",   # les deux effets cumulés
]

# La hauteur à atteindre : celle de l'Arthur que le jeu fait déjà entendre. On ne cherche
# pas la voix la plus jolie dans l'absolu mais celle qui reste ce personnage-là.
CIBLE_F0 = (176.0, 211.0)
# Tolérance sur la dispersion inter-clips, exprimée en multiple de celle de Chatterbox
# (38 Hz mesurés). 1,5× laisse la marge d'un moteur plus expressif sans laisser passer
# un timbre qui change d'âge entre deux répliques.
TOLERANCE_PLAGE = 1.5


def _mesure_lot(clips: list, mesures) -> dict:
    """Descripteurs d'un lot de clips : cohésion, hauteur, et surtout sa DISPERSION."""
    descr = [mesures._descripteurs(c) for c in clips]
    f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
    return {
        **mesures._dispersion_timbre(clips),
        "f0_median": float(np.median(f0)) if f0 else 0.0,
        "f0_min": float(np.min(f0)) if f0 else 0.0,
        "f0_max": float(np.max(f0)) if f0 else 0.0,
        # Le critère décisif : l'écart de hauteur entre le clip le plus grave et le plus
        # aigu du MÊME timbre. C'est lui qui dit « même personnage » ou non.
        "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0,
        "ambitus_st": float(np.mean([d["f0_ambitus_st"] for d in descr])),
        "par_clip": {c.stem: {"f0": round(d["f0_median"]), "duree": round(d["duree"], 1),
                              "ambitus_st": round(d["f0_ambitus_st"], 1)}
                     for c, d in zip(clips, descr)},
    }


def _repliques(n_dialogue: int = 6, n_narration: int = 2) -> list:
    """Les mêmes répliques que le banc de bascule, pour que les chiffres se comparent."""
    lignes = json.loads(LIGNES.read_text(encoding="utf-8"))
    dialogues = [l for l in lignes if l["role"] == "Arthur"][:n_dialogue]
    narrations = [l for l in lignes if l["role"] == "narrator"][:n_narration]
    return dialogues + narrations


def _repere_chatterbox(mesures) -> dict:
    """Cohésion et hauteur du Chatterbox RÉELLEMENT livré — pas le chiffre de la note.

    Lit `docs/ecoute-qwen3-tts/repere-chatterbox/` en priorité, et non `voices/arthur/` :
    depuis l'intégration du lot Qwen3 (2026-08-08), sept des huit clips qui servaient de
    repère y ont été REMPLACÉS. Les relire là mesurerait du Qwen3 en croyant mesurer du
    Chatterbox — une mesure fausse qui ne signale rien. Les originaux ont été copiés dans
    le dossier d'écoute, versionné, précisément pour que les chiffres publiés restent
    reproductibles. Repli sur `voices/arthur/` si cette copie n'existe pas (dépôt frais,
    intégration pas encore faite).
    """
    fige = MEDIA / "docs/ecoute-qwen3-tts/repere-chatterbox"
    clips = sorted(fige.glob("*.ogg"))[:8]
    if not clips:
        clips = sorted((MEDIA / "voices/arthur").glob("arthur_ch0*.ogg"))[:8]
    if not clips:
        return {}
    return {"clips": len(clips), "source": str(clips[0].parent.relative_to(MEDIA)),
            **_mesure_lot(clips, mesures)}


def _dossier(spec: str) -> Path:
    return ECOUTE / spec.replace(":", "-").replace(".", "-").replace("+", "_")


def _genere_candidat(modele, qwen3tts, spec: str, repliques: list) -> tuple:
    """Les 8 répliques d'un timbre. Rend les clips produits, le RTF et les relances."""
    dossier = _dossier(spec)
    faits, secondes_audio, secondes_calcul, relances = [], 0.0, 0.0, 0
    for i, ligne in enumerate(repliques):
        registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
        cible = dossier / f"{ligne['id']}.ogg"
        t0 = time.time()
        # Graine variable d'une réplique à l'autre : c'est le régime de production. À
        # graine fixe, la dispersion mesurée serait celle du décodage, pas du timbre.
        onde, essais = qwen3tts._genere(
            modele, "customvoice", ligne["texte"], qwen3tts.REGISTRES[registre],
            spec, seed=2000 + i, temperature=0.7)
        secondes_calcul += time.time() - t0
        secondes_audio += len(onde) / modele.sample_rate
        relances += essais
        qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
        faits.append(cible)
        print(f"  {ligne['id']:22s} {len(onde) / modele.sample_rate:4.1f}s  ({registre})",
              flush=True)
    return faits, secondes_calcul / max(secondes_audio, 1e-9), relances


def main() -> int:
    import bench_qwen3tts as mesures

    # Re-mesurer les clips en place : les descripteurs ont évolué (f0_plage), et
    # régénérer pour recalculer une statistique donnerait d'autres clips — donc
    # d'autres chiffres, sans qu'on sache lequel du critère ou du tirage a bougé.
    mesures_seules = "--mesures-seules" in sys.argv
    repliques = _repliques()
    ECOUTE.mkdir(parents=True, exist_ok=True)
    rapport = {"repliques": [r["id"] for r in repliques], "cible_f0_hz": list(CIBLE_F0),
               "chatterbox": _repere_chatterbox(mesures), "candidats": {}}

    modele = qwen3tts = None
    if not mesures_seules:
        import qwen3tts
        print(f"{len(CANDIDATS)} timbres × {len(repliques)} répliques réelles d'Arthur",
              flush=True)
        modele = qwen3tts._charge("customvoice")

    for spec in CANDIDATS:
        print(f"\n=== {spec} ===", flush=True)
        if mesures_seules:
            faits = sorted(_dossier(spec).glob("*.ogg"))
            if not faits:
                print("  (aucun clip — lancer sans --mesures-seules)", flush=True)
                continue
            rtf, relances = None, None
        else:
            faits, rtf, relances = _genere_candidat(modele, qwen3tts, spec, repliques)
        rapport["candidats"][spec] = {
            **_mesure_lot(faits, mesures), "rtf": rtf, "relances": relances,
            "dossier": str(_dossier(spec).relative_to(MEDIA)),
        }

    del modele
    (ECOUTE / "rapport_tournoi.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    # --- verdict ---------------------------------------------------------------
    ref = rapport.get("chatterbox") or {}
    plage_max = ref.get("f0_plage", 38.0) * TOLERANCE_PLAGE
    print("\n" + "=" * 84)
    print(f"REPÈRE Chatterbox : F0 {ref.get('f0_min', 0):.0f}–{ref.get('f0_max', 0):.0f} Hz "
          f"(plage {ref.get('f0_plage', 0):.0f} Hz)  ·  cohésion "
          f"{ref.get('cohesion_moyenne', 0):.3f}")
    print(f"CIBLE : F0 médian dans {CIBLE_F0[0]:.0f}–{CIBLE_F0[1]:.0f} Hz "
          f"ET plage ≤ {plage_max:.0f} Hz\n")
    print(f"{'timbre':34s} {'F0 méd.':>9s} {'plage':>8s} {'cohés.':>7s} "
          f"{'ambitus':>8s}  verdict")
    # Classé par dispersion croissante : c'est le critère qui sépare, la cohésion MFCC
    # tient les sept candidats en un dixième et favorise le timbre le plus plat.
    for spec, r in sorted(rapport["candidats"].items(), key=lambda kv: kv[1]["f0_plage"]):
        juste = CIBLE_F0[0] <= r["f0_median"] <= CIBLE_F0[1]
        stable = r["f0_plage"] <= plage_max
        verdict = ("RETENU" if stable and juste else
                   "trop grave" if stable else
                   "change d'âge" if juste else "écarté")
        print(f"{spec:34s} {r['f0_median']:8.0f}Hz {r['f0_plage']:7.0f}Hz "
              f"{r['cohesion_moyenne']:7.3f} {r['ambitus_st']:7.1f}st  {verdict}")
    print(f"\nÀ écouter : {ECOUTE.relative_to(MEDIA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
