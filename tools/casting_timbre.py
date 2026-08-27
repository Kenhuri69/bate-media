#!/usr/bin/env python3
"""Auditionner les timbres candidats d'un personnage sur ses VRAIES répliques.

    ../.venv-mlx/bin/python tools/casting_timbre.py virion
    ../.venv-mlx/bin/python tools/casting_timbre.py tessia --candidats serena,vivian

Généralisation de `tessia_casting.py` (dont il est le renommage) à n'importe quel personnage.
Rien n'est intégré : ce script ne produit qu'un dossier d'écoute et ses mesures. **Le timbre se
choisit à l'oreille** — la mesure écarte les candidats objectivement mauvais et éclaire le
choix, elle ne le remplace pas.

Ce sont des timbres PURS. Un mélange se mesure et peut battre un timbre pur (c'est le cas pour
Arthur, l'inverse pour Tessia), mais une audition doit d'abord porter sur des voix entières :
valider `uncle_fu:0.6+ryan:0.4` avant d'avoir entendu `uncle_fu` reviendrait à choisir une
formule plutôt qu'une voix. Les mélanges viennent après, par balayage de doses entre les têtes
de série (`tournoi_timbre_*.py`).

DEUX CRITÈRES, ET LE SECOND EST NOUVEAU.

1. **La stabilité** — un timbre qui change de hauteur selon le texte prononcé ferait entendre
   deux personnes là où le récit n'en a qu'une. Mesurée par la plage de F0 sur l'échantillon.

2. **La distance au personnage déjà casté** — mesurée par le cosinus des MFCC sur LES MÊMES
   textes, dits par le timbre candidat et par celui d'Arthur. Ce critère n'existait pas pour
   Tessia : une voix de femme ne risque pas d'être confondue avec celle d'Arthur. Il devient
   décisif au troisième personnage, parce que CustomVoice n'a que trois timbres masculins
   utilisables (`uncle_fu`, `ryan`, `aiden` ; `eric` et `dylan` sont déclarés dialectaux dans la
   config du modèle et produisent des clips dégénérés en français) — et Arthur en consomme
   DEUX, `aiden:0.5+ryan:0.5`. Deux personnages masculins qui se ressemblent coûtent plus cher
   à la compréhension d'une scène qu'un timbre un peu moins juste : dans un dialogue à deux
   voix, ne plus savoir qui parle est un défaut de récit, pas de son.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Les neuf timbres premium de CustomVoice, répartis. C'est tout le choix contraint du modèle :
# il n'y a pas de dixième voix à essayer.
FEMININS = ["serena", "vivian", "ono_anna", "sohee"]
MASCULINS = ["uncle_fu", "ryan", "aiden"]
DIALECTAUX = ["eric", "dylan"]           # sichuanais et pékinois : à éviter hors chinois

PERSONNAGES = {
    # DEUX références, et la seconde a été apprise à ses dépens. La première version ne mesurait
    # la distance qu'à Arthur : `uncle_fu` la maximisait (0,949) et a été retenu sur ce seul
    # critère. Les 350 clips produits sortent à **201,7 Hz de F0 médiane**, c'est-à-dire à 14 Hz
    # de TESSIA (215,3) — sa petite-fille adolescente, avec qui il partage toutes ses scènes de
    # cour — et à 72 Hz au-dessus d'Arthur. Le timbre s'éloignait bien d'Arthur : par le haut,
    # donc en atterrissant sur Tessia. Un critère à une seule référence ne mesure pas la
    # confusion, il en déplace la cible.
    "virion": {"nom": "Virion", "slug": "bate-virion", "candidats": MASCULINS,
               "references": [("Arthur", "aiden:0.5+ryan:0.5"), ("Tessia", "sohee")]},
    "tessia": {"nom": "Tessia", "slug": "bate-tessia", "candidats": FEMININS,
               "references": [("Arthur", "aiden:0.5+ryan:0.5")]},
    # `sohee` est retiré : il est la voix de Tessia. Restent les trois autres féminins, et la
    # référence à distinguer est TESSIA, pas Arthur — Sylvie et elle partagent beaucoup de
    # scènes, et ce sont ces deux-là qu'on risque de confondre, pas Sylvie et un garçon.
    "sylvie": {"nom": "Sylvie", "slug": "bate-sylvie",
               "candidats": [t for t in FEMININS if t != "sohee"],
               "references": [("Tessia", "sohee"), ("Arthur", "aiden:0.5+ryan:0.5")]},
    # Luna et Lise se castent ENSEMBLE, et c'est une contrainte de plus, pas une commodité :
    # elles partagent la totalité de leurs scènes (trois arcs, 70 répliques) et Tessia y est
    # présente dans les trois. Il ne suffit donc pas que chacune soit loin de Tessia — il faut
    # aussi qu'elles soient loin l'une de l'autre, ce que la seule proximité aux références ne
    # dit pas. D'où la matrice candidat × candidat imprimée en fin de casting : elle se lit sur
    # les MÊMES textes aux MÊMES graines, donc elle mesure des timbres et non des phrases.
    # Elijah Knight, 232 répliques sur 30 timelines (ch32 → ch248) : le locuteur non doublé le
    # plus bavard du jeu, et de loin (le suivant en compte la moitié). Il partage l'essentiel de
    # ses scènes avec ARTHUR — 790 répliques d'Arthur et 1 563 de narration dans les mêmes
    # timelines — donc c'est de lui qu'il doit d'abord se distinguer, puis de Reynolds et de
    # Vincent, les deux autres voix masculines qu'il croise et qui existent.
    #
    # LA CONTRAINTE EST ICI À SON MAXIMUM : CustomVoice n'a que trois timbres masculins
    # utilisables et SIX voix en sont déjà tirées (arthur, virion, reynolds, adam, durden,
    # vincent). Elijah sera la septième. Ce qui reste à faire varier est la dose et la hauteur,
    # plus aucun timbre neuf.
    "elijah": {"nom": "Elijah", "slug": "bate-elijah", "lot": 21,
               "candidats": MASCULINS,
               # TESSIA EN QUATRIÈME RÉFÉRENCE, et ce n'est pas un excès de prudence : les
               # doses retenues pour Elijah sortent à 190 Hz, quand Tessia est à 213 et qu'ils
               # partagent 60 répliques de scène. C'est le piège payé sur Virion — s'éloigner
               # d'Arthur PAR LE HAUT et atterrir sur une voix féminine.
               "references": [("Arthur", "aiden:0.5+ryan:0.5"),
                              ("Reynolds", "uncle_fu:0.5+ryan:0.5"),
                              ("Vincent", "uncle_fu:0.6+aiden:0.4"),
                              ("Tessia", "sohee")]},
    "luna": {"nom": "Luna", "slug": "bate-luna", "lot": 14,
             "candidats": [t for t in FEMININS if t != "sohee"],
             "references": [("Tessia", "sohee"), ("Arthur", "aiden:0.5+ryan:0.5")]},
    "lise": {"nom": "Lise", "slug": "bate-lise", "lot": 14,
             "candidats": [t for t in FEMININS if t != "sohee"],
             "references": [("Tessia", "sohee"), ("Arthur", "aiden:0.5+ryan:0.5")]},
}

PAR_LOT = 6


def _chapitre(ligne: dict):
    m = re.fullmatch(r"ch(\d+)[a-z]*", str(ligne.get("chapitre", "")))
    return int(m.group(1)) if m else None


def _echantillon(lignes: list, combien: int) -> list:
    """Les répliques les plus longues, réparties sur toute la carrière du personnage.

    Les plus longues à dessein : la F0 médiane d'un clip de deux secondes repose sur trop peu de
    trames voisées pour valoir une mesure — piège déjà payé sur le lot 6 des âges d'Arthur, où
    deux clips courts sortaient 50 à 80 Hz au-dessus des quatre longs du même lot. Et une
    réplique longue en dit plus à l'oreille qu'un « ...Je ne sais pas. »

    Réparties, parce qu'un échantillon pris dans un seul chapitre auditionne une SCÈNE et non un
    personnage : Virion ouvre en grand-père et finit en chef de guerre.
    """
    datees = [l for l in lignes if _chapitre(l) is not None]
    if not datees:
        datees = lignes
    datees.sort(key=lambda l: _chapitre(l) or 0)
    tranches = np.array_split(np.arange(len(datees)), combien)
    lot = []
    for t in tranches:
        if not len(t):
            continue
        candidats = sorted((datees[i] for i in t), key=lambda l: -len(l["texte"]))
        lot.append(candidats[0])
    return lot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personnage", choices=sorted(PERSONNAGES))
    ap.add_argument("--candidats", help="liste de timbres séparés par des virgules")
    ap.add_argument("--lot", type=int, default=PAR_LOT, help="nombre de répliques auditionnées")
    # Le balayage de doses (étape 3 du principe d'Arthur) n'a pas besoin d'un autre outil : un
    # mélange est une spec de timbre comme une autre pour `--candidats`, et les mesures sont
    # exactement celles qu'on veut. Seul le dossier doit changer, pour ne pas écraser
    # l'audition des purs dont il faut pouvoir comparer les clips.
    ap.add_argument("--dossier", help="nom du dossier d'écoute sous docs/ecoute-qwen3-tts/ "
                                      "(défaut : <lot>-casting-<personnage>)")
    # Reprendre plutôt que régénérer, pour la raison écrite dans `tournoi_timbre_tessia` : un
    # clip refait pour recalculer une statistique est un AUTRE clip, et l'écart mesuré entre un
    # pur et son mélange contiendrait alors le tirage en plus de la dose. Les graines étant
    # dérivées du rang dans l'échantillon (3000 + i), la reprise n'est valide que si
    # `--lot` est le même que celui du dossier source ; le nombre de clips par dossier le dit,
    # et la copie échoue franchement si un fichier manque.
    ap.add_argument("--reprendre-de", dest="reprendre_de",
                    help="dossier d'écoute d'où recopier les clips déjà produits "
                         "(références et timbres purs), au lieu de les régénérer")
    args = ap.parse_args()

    import bench_qwen3tts as mesures
    import qwen3tts

    perso = PERSONNAGES[args.personnage]
    candidats = ([c.strip() for c in args.candidats.split(",")] if args.candidats
                 else perso["candidats"])
    lignes_json = RACINE / f"voice-agent/training/forge/{perso['slug']}/lines.json"
    if not lignes_json.exists():
        print(f"extraction introuvable : {lignes_json}\n"
              f"  python3 tools/extraire_repliques.py {perso['slug']} <rôles>", file=sys.stderr)
        return 1
    sortie = MEDIA / "docs/ecoute-qwen3-tts" / (
        args.dossier or f"{perso.get('lot', 11)}-casting-{args.personnage}")

    echantillon = _echantillon(json.loads(lignes_json.read_text(encoding="utf-8")), args.lot)
    print(f"{len(echantillon)} répliques réelles de {perso['nom']} :")
    for l in echantillon:
        print(f"  [{l['chapitre']:>8s}] « {l['texte'][:66]} »")
    refs = perso["references"]
    print(f"\ncandidats : {', '.join(candidats)}   — références à distinguer : "
          + ", ".join(f"{n} ({s})" for n, s in refs))

    modele = qwen3tts._charge("customvoice")
    rapport = {"personnage": perso["nom"], "candidats": candidats,
               "references": [{"personnage": n, "timbre": s} for n, s in refs],
               "repliques": [{k: l[k] for k in ("id", "chapitre", "texte")} for l in echantillon],
               "timbres": {}}

    repris = (MEDIA / "docs/ecoute-qwen3-tts" / args.reprendre_de) if args.reprendre_de else None
    if repris is not None and not repris.is_dir():
        print(f"dossier à reprendre introuvable : {repris}", file=sys.stderr)
        return 1

    def _lot(timbre: str, dossier: Path) -> list:
        if repris is not None:
            source = repris / dossier.name
            attendus = [source / f"{l['id']}.ogg" for l in echantillon]
            if all(c.exists() for c in attendus):
                dossier.mkdir(parents=True, exist_ok=True)
                faits = []
                for c in attendus:
                    cible = dossier / c.name
                    if not cible.exists():
                        shutil.copy2(c, cible)
                    faits.append(cible)
                print(f"  {len(faits)} clips repris de {source.name} "
                      f"(mêmes graines, mêmes clips)", flush=True)
                return faits
        clips = []
        for i, ligne in enumerate(echantillon):
            registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
            chemin = dossier / f"{ligne['id']}.ogg"
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                       qwen3tts.REGISTRES[registre], timbre,
                                       seed=3000 + i, temperature=0.7)
            qwen3tts._ecrit(onde, modele.sample_rate, chemin, "ogg")
            clips.append(chemin)
        return clips

    # La référence est produite sur LES MÊMES TEXTES, aux MÊMES graines : sans cela, la distance
    # mesurée mélangerait la différence de timbre et celle des phrases prononcées.
    mfcc_ref = {}
    for nom_ref, timbre_ref in refs:
        print(f"\n=== référence {nom_ref}", flush=True)
        clips_ref = _lot(timbre_ref, sortie / f"_reference-{nom_ref.lower()}")
        mfcc_ref[nom_ref] = [mesures._descripteurs(c)["mfcc"] for c in clips_ref]

    mfcc_cand = {}
    for timbre in candidats:
        print(f"\n=== {timbre}", flush=True)
        clips = _lot(timbre, sortie / timbre)
        descr = [mesures._descripteurs(c) for c in clips]
        mfcc_cand[timbre] = [d["mfcc"] for d in descr]
        f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
        # Cosinus PAIRE À PAIRE sur la même réplique, puis moyenne : comparer le clip 1 du
        # candidat au clip 3 de la référence mesurerait surtout un écart de contenu.
        prox = {n: float(np.mean([mesures._cosinus(d["mfcc"], rr)
                                  for d, rr in zip(descr, mfcc_ref[n])]))
                for n, _ in refs}
        f0v = np.array(f0) if f0 else np.array([0.0])
        r = {"f0_median": float(np.median(f0v)),
             "f0_plage": float(np.percentile(f0v, 90) - np.percentile(f0v, 10)),
             "ambitus_st": float(np.median([d["f0_ambitus_st"] for d in descr])),
             "proximite": prox,
             # Ce qui compte n'est pas d'être loin d'UNE référence mais de n'être proche
             # d'AUCUNE : c'est le maximum qui décide, pas la moyenne.
             "proximite_pire": max(prox.values())}
        rapport["timbres"][timbre] = r
        print(f"    F0 {r['f0_median']:5.0f} Hz   plage {r['f0_plage']:4.0f} Hz   "
              f"ambitus {r['ambitus_st']:.1f} st   "
              + "  ".join(f"{n} {v:.3f}" for n, v in prox.items()), flush=True)
    del modele

    # Matrice candidat × candidat : de quoi choisir DEUX voix à la fois. Deux personnages qui
    # ne se quittent pas (Luna et Lise) peuvent chacun être loin des références et proches
    # l'un de l'autre — le classement par « pire proximité aux références » ne le voit pas,
    # puisque l'autre personnage n'est pas encore casté et n'est donc pas dans la liste.
    rapport["entre_candidats"] = {
        a: {b: float(np.mean([mesures._cosinus(x, y)
                              for x, y in zip(mfcc_cand[a], mfcc_cand[b])]))
            for b in candidats if b != a}
        for a in candidats}

    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "rapport_casting.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n" + "=" * 74)
    entetes = "".join(f"{n:>10s}" for n, _ in refs)
    print(f"{'timbre':24s} {'F0':>7s} {'plage':>7s} {'ambitus':>8s}{entetes}{'pire':>8s}")
    # Classé par la PIRE proximité : un timbre acceptable est celui qui n'est proche d'aucune
    # référence, pas celui qui est loin de la moyenne des deux.
    for nom_t, r in sorted(rapport["timbres"].items(), key=lambda kv: kv[1]["proximite_pire"]):
        cols = "".join(f"{r['proximite'][n]:10.3f}" for n, _ in refs)
        print(f"{nom_t:24s} {r['f0_median']:5.0f}Hz {r['f0_plage']:5.0f}Hz "
              f"{r['ambitus_st']:6.1f}st{cols}{r['proximite_pire']:8.3f}")
    if len(candidats) > 1:
        print("\nproximité ENTRE candidats (deux personnages qui partagent leurs scènes ne")
        print("peuvent pas prendre deux timbres proches, même s'ils sont tous deux loin des")
        print("références) :")
        print(" " * 24 + "".join(f"{b[:9]:>10s}" for b in candidats))
        for a in candidats:
            cols = "".join(f"{rapport['entre_candidats'][a][b]:10.3f}" if b != a
                           else f"{'—':>10s}" for b in candidats)
            print(f"{a:24s}{cols}")

    print(f"\nÀ écouter : {sortie.relative_to(MEDIA)}")
    print("La mesure éclaire, elle ne tranche pas : écouter avant de décider.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
