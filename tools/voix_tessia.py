#!/usr/bin/env python3
"""Production des répliques de Tessia (BATE) — à lancer avec .venv-mlx.

    ../.venv-mlx/bin/python tools/voix_tessia.py livrer   --timbre <spec>
    ../.venv-mlx/bin/python tools/voix_tessia.py verifier
    ../.venv-mlx/bin/python tools/voix_tessia.py reprendre --timbre <spec>
    python3 tools/migrer_empreintes.py --personnage Tessia --roles Tessia --slug bate-tessia

Le pendant de `voix_age_arthur.py` pour un personnage à UNE voix. Tout ce qui, chez Arthur,
existait pour gérer cinq stades d'âge et la coexistence Chatterbox/Qwen3 est absent ici, et
c'est la seule différence de fond : Tessia n'a pas de voix en service à préserver, et son
timbre ne se décline pas.

**Le contrôle qualité n'est pas optionnel.** Sur les 4433 clips d'Arthur, 486 sont sortis
défectueux (11,0 %) — énergie spectrale au mauvais endroit, voix qui part dans les aigus ou
s'effondre — et 481 ont été récupérés en régénérant sur d'autres graines. Livrer sans
`verifier` puis `reprendre`, c'est livrer un clip sur neuf inécoutable, et le défaut ne se
voit pas dans un log : il s'entend.

**Aucun prompt d'âge n'est appliqué, et c'est un choix mesuré, pas un oubli.** Tessia a cinq
ans aux ch10-18 et quinze aux ch44-60. Sur Arthur, le prompt d'âge crée bien un registre
d'enfant — mais SEULEMENT au stade bambin (+48 Hz à trois ans) : au-delà, les formulations
essayées apportaient -6, +4, -21 et +17 Hz, c'est-à-dire du bruit, signes compris. À cinq ans
le levier est déjà hors de sa zone utile. Le mettre par défaut serait donc payer une
inconnue pour un effet que la mesure ne trouve pas. `--prompt-age` existe pour le tester sur
les seules répliques d'enfant (une cinquantaine de clips, quelques minutes) plutôt que de le
décider à l'aveugle sur tout le lot.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
LIGNES = RACINE / "voice-agent/training/forge/bate-tessia/lines.json"
# Directement le dossier final, sans tampon : `voices/tessia/` n'existe pas encore. Le
# `voices/arthur-qwen3/` d'Arthur ne servait qu'à ne pas écraser ses 1065 clips Chatterbox
# en service — il n'y a rien à protéger ici, et un tampon de plus serait une étape de plus
# où se tromper de dossier.
SORTIE = MEDIA / "voices/tessia"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Les deux âges, par plage de chapitres — utilisés pour le seul `--prompt-age` et pour
# rapporter les mesures séparément. Ce sont les bornes du casting (lot 9).
AGES = {"enfant": range(0, 44), "adolescente": range(44, 200)}

PROMPT_AGE_ENFANT = ("Parle exactement comme une petite fille de cinq ans : voix haut "
                     "perchée, fluette et claire, intonation montante, mots détachés.")


def _chapitre(ligne: dict):
    m = re.search(r"\d+", str(ligne.get("chapitre", "")))
    return int(m.group()) if m else None


def _age(ligne: dict) -> str:
    ch = _chapitre(ligne)
    for nom, plage in AGES.items():
        if ch is not None and ch in plage:
            return nom
    return "adolescente"


def _lignes() -> list:
    if not LIGNES.exists():
        raise SystemExit(f"extraction introuvable : {LIGNES}\n"
                         f"  python3 tools/extraire_repliques.py bate-tessia Tessia "
                         f"--max-chapitre 60")
    return json.loads(LIGNES.read_text(encoding="utf-8"))


def _instruct(qwen3tts, ligne: dict, prompt_age: bool) -> str:
    registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
    age = PROMPT_AGE_ENFANT if (prompt_age and _age(ligne) == "enfant") else ""
    return f"{age} {qwen3tts.REGISTRES[registre]}".strip()


# --- contrôle d'énergie -------------------------------------------------------

def _part_bande(chemin: Path, cible: float) -> float:
    """Part de l'énergie vocale située dans la bande du fondamental attendu.

    Critère VOLONTAIREMENT distinct de la F0 : l'autocorrélation attrape régulièrement une
    harmonique quand le fondamental est faible et rend la borne même du détecteur. Mesurer
    OÙ est l'énergie ne se trompe pas d'octave. Un clip sain met la moitié ou plus de son
    énergie vocale dans cette bande ; les clips cassés d'Arthur tombaient à 4-14 %.
    """
    import soundfile as sf

    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    spectre = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    total = spectre[(f > 60) & (f < 2000)].sum()
    bande = spectre[(f >= 0.6 * cible) & (f < 1.4 * cible)].sum()
    return float(bande / total) if total > 0 else 0.0


def _part_grave(chemin: Path, borne: float = 150.0) -> float:
    """Part de l'énergie vocale sous `borne` — le témoin qui dit si la F0 est croyable."""
    import soundfile as sf

    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    spectre = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    total = spectre[(f > 60) & (f < 2000)].sum()
    return float(spectre[(f > 60) & (f < borne)].sum() / total) if total > 0 else 0.0


def _cible(clips: list, mesures) -> float:
    """Bande dominante du lot, et REFUS si la F0 n'est pas croyable dessus.

    Chez Arthur, les cibles sont écrites en dur et une note interdit de les remplacer par la
    F0 mesurée : sur ses répliques parlées l'autocorrélation rend ~140 Hz alors que 3 à 6 %
    seulement de l'énergie est sous 110 Hz — elle divise le fondamental par deux, et
    recentrer la bande dessus faisait regarder SOUS la voix.

    Ici la F0 est utilisable, mais ça ne se suppose pas : le casting l'a vérifié (0,0 à
    0,1 % d'énergie sous 150 Hz sur les quatre timbres féminins) et ce contrôle le rejoue
    sur le lot réel. Si la part grave dépasse 5 %, la F0 redevient suspecte et la fonction
    REFUSE plutôt que de rendre une cible fausse — un contrôle qui applique la mauvaise
    attente ne détecte pas des défauts, il en invente.
    """
    parts = [_part_grave(c) for c in clips]
    grave = float(np.median(parts))
    if grave > 0.05:
        raise SystemExit(
            f"{grave:.1%} de l'énergie sous 150 Hz : la F0 n'est plus un fondamental "
            f"croyable sur ce lot, la cible de contrôle serait fausse. Mesurer la bande "
            f"dominante à la main (cf. `_barycentre` dans tournoi_timbre_tessia.py) et "
            f"écrire la cible en dur, comme pour Arthur.")
    f0 = [d["f0_median"] for d in (mesures._descripteurs(c) for c in clips)
          if d["f0_median"] > 0]
    return float(np.median(f0))


def _douteux(clips: list, cible: float) -> tuple:
    """Les clips dont l'énergie n'est pas là où elle devrait être.

    Seuil RELATIF à la médiane du lot, pas absolu : la part d'énergie dans la bande dépend
    du timbre et du texte, et un seuil fixe rejetterait tout le lot ou aucun clip. Un seul
    rôle ici, donc une seule médiane — chez Arthur elle se calcule par rôle, la narration
    et la réplique parlée n'ayant ni la même cible ni la même distribution.
    """
    parts = [(_part_bande(c, cible), c) for c in clips]
    mediane = float(np.median([p for p, _ in parts])) if parts else 0.0
    return sorted([(p, c) for p, c in parts if p < 0.5 * mediane]), mediane


# --- commandes ----------------------------------------------------------------

def livrer(timbre: str, prompt_age: bool, limite: int = 0) -> int:
    """Génère les répliques, en conservant celles déjà présentes.

    **Reprenable** : un clip présent et non vide est gardé. Une coupure en cours de route ne
    reperd donc pas le travail fait. Revers assumé, le même que chez Arthur : la reprise ne
    devine pas qu'un TIMBRE ou un prompt a changé — pour refaire le lot pour de bon, vider
    `voices/tessia/` d'abord.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    lignes = _lignes()[:limite or None]
    SORTIE.mkdir(parents=True, exist_ok=True)
    par_age = {a: sum(1 for l in lignes if _age(l) == a) for a in AGES}
    print(f"livraison de {len(lignes)} répliques de Tessia ({timbre}) vers "
          f"{SORTIE.relative_to(MEDIA)}")
    print(f"  {par_age} — prompt d'âge : {'OUI sur l enfant' if prompt_age else 'non'}",
          flush=True)

    modele = qwen3tts._charge("customvoice")
    faits, relances, gardes, debut = [], 0, 0, time.time()
    for i, ligne in enumerate(lignes):
        cible = SORTIE / f"{ligne['id']}.ogg"
        if cible.exists() and cible.stat().st_size > 0:
            gardes += 1
            faits.append(cible)
            continue
        onde, essais = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                        _instruct(qwen3tts, ligne, prompt_age), timbre,
                                        seed=2000 + i, temperature=0.7)
        relances += essais
        qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
        faits.append(cible)
        if (i + 1) % 10 == 0 or i + 1 == len(lignes):
            print(f"    {i + 1}/{len(lignes)}  ({time.time() - debut:.0f}s, "
                  f"{relances} relances, {gardes} repris)", flush=True)
    del modele

    f0 = [d["f0_median"] for d in (mesures._descripteurs(c) for c in faits)
          if d["f0_median"] > 0]
    rapport = {"timbre": timbre, "prompt_age": prompt_age, "clips": len(faits),
               "relances": relances, "secondes": round(time.time() - debut, 1),
               "f0_median": float(np.median(f0)) if f0 else 0.0,
               "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0}
    # Dans la FORGE, pas dans `voices/tessia/` : `build_pack._declaree` filtre au dossier et
    # non au fichier, si bien que tout ce qui traîne dans un dossier de voix déclaré part
    # dans le pack public. Arthur y échappait par son dossier de travail séparé ; ici il n'y
    # en a pas, et un rapport interne n'a rien à faire dans une archive distribuée.
    (LIGNES.parent / "rapport_livraison.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"\n{len(faits)} clips  {rapport['secondes']:.0f}s  {relances} relances  "
          f"F0 {rapport['f0_median']:.0f} Hz (plage {rapport['f0_plage']:.0f})")
    print(f"\nContrôler AVANT d'intégrer : tools/voix_tessia.py verifier")
    return 0


def verifier() -> int:
    """Contrôle qualité du lot, sans rien régénérer."""
    import bench_qwen3tts as mesures

    clips = sorted(SORTIE.glob("*.ogg"))
    if not clips:
        print(f"aucun clip dans {SORTIE}", file=sys.stderr)
        return 1
    cible = _cible(clips, mesures)
    mauvais, mediane = _douteux(clips, cible)
    print(f"{len(clips)} clips — cible {cible:.0f} Hz, médiane d'énergie dans "
          f"{0.6 * cible:.0f}-{1.4 * cible:.0f} Hz : {mediane:.0%} — "
          f"{len(mauvais)} douteux ({len(mauvais) / len(clips):.1%})")
    for part, c in mauvais:
        print(f"    {c.stem:22s} {part:5.1%}")
    return 0


def reprendre(timbre: str, prompt_age: bool, essais: int = 4) -> int:
    """Régénère les clips douteux sur d'autres graines, en gardant le meilleur essai.

    « Meilleur » au sens du critère d'énergie, pas de la F0 : c'est lui qui a détecté le
    défaut, c'est lui qui valide la reprise. On garde le meilleur essai même s'il reste sous
    le seuil — un clip amélioré vaut mieux qu'un clip cassé conservé par principe — et on
    journalise ceux qui n'ont pas pu être sauvés.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    clips = sorted(SORTIE.glob("*.ogg"))
    par_id = {l["id"]: l for l in _lignes()}
    cible = _cible(clips, mesures)
    mauvais, mediane = _douteux(clips, cible)
    seuil = 0.5 * mediane
    print(f"{len(mauvais)} clips à reprendre (cible {cible:.0f} Hz, seuil {seuil:.0%})",
          flush=True)
    if not mauvais:
        return 0

    modele = qwen3tts._charge("customvoice")
    sauves, restants = 0, []
    for part0, chemin in mauvais:
        ligne = par_id.get(chemin.stem)
        if ligne is None:
            print(f"    {chemin.stem:22s} absent de lines.json — ignoré", flush=True)
            continue
        meilleur, meilleure_part = None, part0
        for essai in range(essais):
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                       _instruct(qwen3tts, ligne, prompt_age), timbre,
                                       seed=7000 + essai * 613, temperature=0.7)
            tmp = chemin.with_suffix(".essai.ogg")
            qwen3tts._ecrit(onde, modele.sample_rate, tmp, "ogg")
            part = _part_bande(tmp, cible)
            if part > meilleure_part:
                meilleur, meilleure_part = onde, part
            tmp.unlink()
            if meilleure_part >= seuil:
                break
        if meilleur is not None:
            qwen3tts._ecrit(meilleur, modele.sample_rate, chemin, "ogg")
        if meilleure_part >= seuil:
            sauves += 1
        else:
            restants.append(chemin.stem)
        print(f"    {chemin.stem:22s} {part0:5.1%} -> {meilleure_part:5.1%}  "
              f"{'OK' if meilleure_part >= seuil else 'encore douteux'}", flush=True)
    del modele

    print(f"\n{sauves}/{len(mauvais)} récupérés"
          + (f", restants : {', '.join(restants)}" if restants else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commande", choices=["livrer", "verifier", "reprendre"])
    ap.add_argument("--timbre", help="spec CustomVoice validée à l'oreille "
                                     "(ex. sohee, ou sohee:0.5+ono_anna:0.5)")
    ap.add_argument("--prompt-age", action="store_true",
                    help="prompt d'enfant sur les répliques ch0-43 (hors zone utile mesurée, "
                         "cf. docstring)")
    ap.add_argument("--limite", type=int, default=0, help="ne traiter que N répliques")
    args = ap.parse_args()

    if args.commande in ("livrer", "reprendre") and not args.timbre:
        # Pas de défaut : un timbre se choisit à l'oreille, et un défaut ici produirait
        # 114 clips dans une voix que personne n'a validée.
        print("--timbre est obligatoire : le timbre se valide à l'écoute "
              "(bash docs/ecoute-qwen3-tts/ecouter.sh 6)", file=sys.stderr)
        return 1
    if args.commande == "livrer":
        return livrer(args.timbre, args.prompt_age, args.limite)
    if args.commande == "verifier":
        return verifier()
    return reprendre(args.timbre, args.prompt_age)


if __name__ == "__main__":
    sys.exit(main())
