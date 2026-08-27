#!/usr/bin/env python3
"""Combien de voix DISTINCTES ce moteur peut-il rendre ? Mesuré, pas supposé.

    ../.venv-mlx/bin/python tools/catalogue_voix.py --genre f
    ../.venv-mlx/bin/python tools/catalogue_voix.py --genre m --mesures-seules
    ../.venv-mlx/bin/python tools/catalogue_voix.py --selftest

LE PROBLÈME. Il reste 119 personnages à doubler sur les cent premiers chapitres et les arcs, et
CustomVoice n'expose que quatre timbres féminins et trois masculins. Mutualiser massivement était
la réponse facile ; la consigne est l'inverse — « maximiser les voies », par couplage, par
mélange à TROIS composants, et par décalage de hauteur.

CE QUI REND L'ESPACE PLUS GRAND QU'IL N'Y PARAÎT, et ce sont deux faits mesurés :

1. **`_parse_timbre` accepte déjà N composants** (il boucle sur `split("+")` et `_vecteur_timbre`
   en fait une somme pondérée). Les quinze voix en service n'en utilisent que deux : les mélanges
   à trois n'avaient jamais été essayés, pas parce qu'ils échouent — parce que personne ne les a
   demandés.
2. **le décalage de hauteur ne coûte AUCUN calcul de modèle.** `descente_voix.descendre` travaille
   sur l'onde : un mélange généré une fois se décline en sept voix (0, ±1, ±2, ±3 demi-tons) pour
   le prix d'une. C'est le levier le moins cher de la chaîne.

CE QUE CET OUTIL FAIT. Il produit chaque mélange candidat sur un échantillon COMMUN, décline les
décalages sans repasser par le modèle, mesure tout (F0, plage, ambitus, MFCC), puis sélectionne un
ensemble MAXIMAL de voix mutuellement distinctes — les voix déjà en service étant des points
fixes, puisqu'on ne les rejouera pas.

CE QU'IL NE FAIT PAS. Il ne choisit aucune voix pour aucun personnage : il dit combien de places
distinctes existent et lesquelles. L'attribution reste un acte d'auteur, et le verdict final reste
l'oreille — la mesure écarte, elle ne tranche pas.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FEMININS = ["serena", "vivian", "ono_anna", "sohee"]
MASCULINS = ["uncle_fu", "ryan", "aiden"]

# Décalages déclinés par traitement du signal, donc gratuits en calcul de modèle. Bornés à
# ±3 demi-tons : au-delà, le rééchantillonnage déplace aussi les formants assez pour que la voix
# cesse de sonner comme une personne (Durden est à −5 et c'est déjà un choix assumé).
DECALAGES = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0)

# LE DÉBIT, troisième axe et le dernier gratuit. Deux personnages au même timbre et à la même
# hauteur se distinguent encore s'ils ne parlent pas à la même vitesse — c'est même le premier
# indice qu'une oreille attrape dans une scène à deux voix. WSOLA change la durée sans toucher à
# la hauteur (c'est déjà lui qui rend sa durée à une voix descendue), donc l'axe ne coûte aucun
# calcul de modèle, comme le décalage.
#
# Bornes serrées à ±8 % : au-delà, le débit cesse d'être une caractéristique du personnage pour
# devenir un défaut de lecture, et l'audit de durée le signalerait comme un clip qui traîne.
DEBITS = (0.92, 1.0, 1.08)

# Doses. La majoritaire reste identifiable — règle écrite au prix d'une erreur (Arthur toddler
# livré à 80 % d'un timbre qu'on n'avait pas validé). À trois composants, la dominante garde donc
# au moins 40 %, ce qui laisse le troisième timbre en touche de couleur.
DOSES_2 = ((0.8, 0.2), (0.65, 0.35), (0.5, 0.5))
DOSES_3 = ((0.5, 0.3, 0.2), (0.4, 0.4, 0.2), (0.6, 0.2, 0.2))

# Seuils de séparation, calibrés sur les paires réelles du jeu. Ce qui a été jugé acceptable à
# l'oreille : Luna/Lise 0,953 ; Elijah/Arthur 0,922. Ce qui a été refusé comme collision :
# Lise/Ellie 0,970. Deux voix comptent donc pour distinctes si leur timbre diffère (cosinus sous
# le seuil) OU si leur hauteur diffère assez pour qu'on ne les confonde pas.
SEUIL_COSINUS = 0.955
SEUIL_F0_HZ = 25.0


def _voix_en_service(avec_troupe: bool = True) -> dict:
    """Les timbres déjà attribués, `nom -> (spec, décalage)`. Points fixes de la sélection.

    `avec_troupe=False` écarte les voix d'archétype des figurants. C'est nécessaire pour caster
    les personnages PRINCIPAUX : les douze archétypes occupent douze places, et les laisser en
    points fixes ne laissait que cinq places libres pour dix-neuf personnages qu'on entend
    revenir. L'ordre de priorité doit être l'inverse — un rôle de quatre-vingts répliques mérite
    la place qu'un figurant de trois n'a pas besoin d'avoir.
    """
    import voix_personnage
    return {p["nom"]: (p["timbre"], p.get("grave_demi_tons", 0.0))
            for p in voix_personnage.PERSONNAGES.values()
            if avec_troupe or not p.get("troupe")}


def specs(genre: str) -> list:
    """Tous les mélanges candidats d'un genre : deux composants, puis trois, puis quatre."""
    base = FEMININS if genre == "f" else MASCULINS
    sortie = []
    for paire in itertools.permutations(base, 2):
        for doses in DOSES_2:
            if doses[0] == doses[1] and paire[0] > paire[1]:
                continue                      # 0,5/0,5 est symétrique : une seule fois
            sortie.append("+".join(f"{n}:{d}" for n, d in zip(paire, doses)))
    for triplet in itertools.permutations(base, 3):
        for doses in DOSES_3:
            if doses[0] == doses[1] and triplet[0] > triplet[1]:
                continue
            if doses[1] == doses[2] and triplet[1] > triplet[2]:
                continue
            sortie.append("+".join(f"{n}:{d}" for n, d in zip(triplet, doses)))
    if len(base) >= 4:
        for quatre in (base,):
            sortie.append("+".join(f"{n}:0.25" for n in quatre))
    return sorted(set(sortie))


def echantillon(combien: int = 6) -> list:
    """Répliques réelles de PETITS RÔLES, celles que ces voix auront à dire.

    Prises chez des figurants et non chez un personnage principal : un échantillon tiré des
    répliques d'Arthur mesurerait les candidats sur un registre de héros, qui n'est pas celui
    qu'on cherche à peupler. Textes de longueur moyenne — la F0 d'un clip de deux secondes
    repose sur trop peu de trames voisées pour valoir une mesure.
    """
    import re
    JEU = RACINE / "bate/dialogues"
    motif = re.compile(r"^\s*([A-Za-zÀ-ÿ][\w '\-À-ÿ]*)\s*:\s*(.+)$")
    petits = {"Élève", "Garde", "Aventurier", "Réceptionniste", "Instructrice", "Juge",
              "Antiquaire", "Intendant", "Crieur", "Examinatrice", "Meneur", "Serveuse"}
    trouves = {}
    for f in sorted(JEU.rglob("*.dtl")):
        for ligne in f.read_text(encoding="utf-8").splitlines():
            m = motif.match(ligne)
            if not m:
                continue
            loc, texte = m.group(1).strip(), m.group(2).strip()
            if loc in petits and 70 <= len(texte) <= 190 and loc not in trouves:
                trouves[loc] = {"id": f"troupe_{len(trouves):02d}", "texte": texte,
                                "role": loc, "chapitre": f.stem}
        if len(trouves) >= combien:
            break
    return list(trouves.values())[:combien]


def _mesure(clips: list, mesures) -> dict:
    descr = [mesures._descripteurs(c) for c in clips]
    f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0] or [0.0]
    a = np.array(f0)
    return {"f0": float(np.median(a)),
            "plage": float(np.percentile(a, 90) - np.percentile(a, 10)),
            "ambitus": float(np.median([d["f0_ambitus_st"] for d in descr])),
            "mfcc": [d["mfcc"] for d in descr]}


def distinctes(voix: list, mesures) -> list:
    """Sélection GLOUTONNE d'un ensemble mutuellement distinct, les voix en service d'abord.

    Glouton et non exhaustif : le problème est un packing (choisir le plus grand ensemble dont
    toutes les paires sont séparées), NP-difficile, et un glouton par plage croissante donne un
    ensemble utilisable sans prétendre à l'optimum. Ce que l'outil promet est « voici N voix
    séparées », pas « il n'en existe pas N+1 ».
    """
    retenues = [v for v in voix if v["en_service"]]
    candidats = sorted((v for v in voix if not v["en_service"]), key=lambda v: v["plage"])
    for v in candidats:
        if all(_separees(v, r, mesures) for r in retenues):
            retenues.append(v)
    return retenues


def _separees(a: dict, b: dict, mesures) -> bool:
    if abs(a["f0"] - b["f0"]) >= SEUIL_F0_HZ:
        return True
    # Un écart de débit d'au moins 8 % suffit à ne pas confondre deux voix par ailleurs
    # semblables : c'est l'indice qu'une oreille attrape en premier dans un échange. En dessous,
    # il ne compte pas — 2 % de vitesse ne fait pas un personnage.
    if abs(a.get("debit", 1.0) - b.get("debit", 1.0)) >= 0.08 - 1e-9:
        return True
    cos = float(np.mean([mesures._cosinus(x, y) for x, y in zip(a["mfcc"], b["mfcc"])]))
    return cos <= SEUIL_COSINUS


def _selftest() -> int:
    ok = True

    def check(nom, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'OK ' if cond else 'ECHEC'}] {nom}")

    f = specs("f")
    check("les mélanges à 3 composants sont bien produits",
          any(s.count("+") == 2 for s in f))
    check("un mélange à 4 composants existe côté féminin",
          any(s.count("+") == 3 for s in f))
    # La dominante reste identifiable À 40 % AU MOINS, sauf pour le mélange à parts égales des
    # quatre timbres — celui-là n'a pas de dominante par construction, et c'est son intérêt : une
    # voix moyenne, sans caractère marqué, exactement ce qu'un figurant demande. La règle des
    # 40 % protège contre la DILUTION d'un timbre déjà validé à l'oreille (Arthur toddler livré
    # à 80 % d'un timbre qu'on n'avait pas entendu) ; elle ne dit rien d'une voix neuve qu'on
    # validera telle quelle.
    sans_dominante = {"+".join(f"{n}:0.25" for n in FEMININS)}
    check("hors mélange à parts égales, la dominante garde 40 % au moins",
          all(max(float(p.split(":")[1]) for p in s.split("+")) >= 0.4
              for s in f if s not in sans_dominante))
    check("la dose 0,5/0,5 n'est comptée qu'une fois par paire",
          len([s for s in f if s == "serena:0.5+vivian:0.5"]) == 1
          and "vivian:0.5+serena:0.5" not in f)
    check("les sept décalages sont déclarés", len(DECALAGES) == 7)
    ech = echantillon(6)
    check("l'échantillon vient de petits rôles réels", len(ech) >= 3
          and all(70 <= len(e["texte"]) <= 190 for e in ech))
    print(f"  ({len(f)} mélanges féminins, {len(specs('m'))} masculins, "
          f"× {len(DECALAGES)} décalages = {len(f) * len(DECALAGES)} voix féminines candidates)")
    print("auto-test catalogue_voix :", "OK" if ok else "ECHEC")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--genre", choices=["f", "m"], default="f")
    ap.add_argument("--lot", type=int, default=6, help="répliques par candidat")
    ap.add_argument("--mesures-seules", action="store_true",
                    help="ne rien générer, remesurer les clips déjà là")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sans-troupe", action="store_true",
                    help="ne pas figer les voix d'archétype : caster les principaux d'abord")
    # DEUX NIVEAUX DE SÉPARATION, et c'est ce qui rend le compte utilisable. Le seuil strict
    # (25 Hz) sert les personnages qu'on entend revenir : il faut qu'on les reconnaisse. Un
    # figurant qui dit trois répliques dans tout le jeu n'a pas besoin d'autant — le contexte
    # le distingue mieux que son timbre. Relâcher l'écart de hauteur pour la troupe ouvre des
    # places qui, au seuil strict, seraient refusées pour quinze hertz.
    ap.add_argument("--seuil-f0", type=float, default=SEUIL_F0_HZ,
                    help=f"écart de F0 qui suffit à distinguer deux voix (défaut {SEUIL_F0_HZ:.0f} Hz)")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    globals()["SEUIL_F0_HZ"] = args.seuil_f0

    import bench_qwen3tts as mesures
    from descente_voix import _comprimer_wsola, descendre

    sortie = MEDIA / f"docs/ecoute-qwen3-tts/25-catalogue-{args.genre}"
    sortie.mkdir(parents=True, exist_ok=True)
    ech = echantillon(args.lot)
    if len(ech) < 3:
        print("échantillon trop court", file=sys.stderr)
        return 1
    candidats = specs(args.genre)
    service = _voix_en_service(avec_troupe=not args.sans_troupe)
    base = FEMININS if args.genre == "f" else MASCULINS
    en_service = {n: (s, d) for n, (s, d) in service.items()
                  if all(p.split(":")[0] in base for p in s.split("+"))}
    print(f"{len(candidats)} mélanges à produire × {len(ech)} répliques, "
          f"puis {len(DECALAGES)} décalages sans calcul de modèle")
    print(f"{len(en_service)} voix en service comme points fixes : "
          f"{', '.join(sorted(en_service))}\n")

    modele = None
    if not args.mesures_seules:
        import qwen3tts
        modele = qwen3tts._charge("customvoice")

    def _produit(spec: str) -> list:
        import qwen3tts
        dossier = sortie / spec.replace(":", "-").replace("+", "_")
        dossier.mkdir(parents=True, exist_ok=True)
        faits = []
        for i, ligne in enumerate(ech):
            cible = dossier / f"{ligne['id']}.ogg"
            if not cible.exists() and modele is not None:
                onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                           qwen3tts.REGISTRES["dialogue"], spec,
                                           seed=5000 + i, temperature=0.7)
                qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
            if cible.exists():
                faits.append(cible)
        return faits

    voix = []
    # Les voix en service, mesurées sur le MÊME échantillon : sans cela leur distance aux
    # candidats mêlerait le timbre et le texte.
    for nom, (spec, dec) in sorted(en_service.items()):
        clips = _produit(spec)
        if not clips:
            continue
        m = _mesure(clips, mesures)
        if dec:
            import soundfile as sf
            decales = []
            for c in clips:
                onde, sr = sf.read(str(c))
                tmp = c.with_suffix(f".d{int(dec)}.ogg")
                if not tmp.exists():
                    import qwen3tts
                    qwen3tts._ecrit(descendre(onde, dec, sr), sr, tmp, "ogg")
                decales.append(tmp)
            m = _mesure(decales, mesures)
        voix.append({"nom": nom, "spec": spec, "decalage": dec, "en_service": True, **m})
        print(f"  service  {nom:10s} {spec:34s} {dec:+.0f} st  F0 {m['f0']:5.0f} Hz")

    import soundfile as sf
    import qwen3tts
    for spec in candidats:
        clips = _produit(spec)
        if not clips:
            continue
        for dec in DECALAGES:
            for debit in DEBITS:
                if dec == 0.0 and debit == 1.0:
                    m = _mesure(clips, mesures)
                else:
                    variantes = []
                    for c in clips:
                        onde, sr = sf.read(str(c))
                        tmp = c.with_suffix(f".d{int(dec)}v{int(debit * 100)}.ogg")
                        if not tmp.exists():
                            y = descendre(onde, dec, sr) if dec else onde
                            if debit != 1.0:
                                y = _comprimer_wsola(y, debit, sr)
                            qwen3tts._ecrit(y, sr, tmp, "ogg")
                        variantes.append(tmp)
                    m = _mesure(variantes, mesures)
                nom = f"{spec} {dec:+.0f}st"
                if debit != 1.0:
                    nom += f" ×{debit:.2f}"
                voix.append({"nom": nom, "spec": spec, "decalage": dec, "debit": debit,
                             "en_service": False, **m})
        print(f"  candidat {spec:44s} F0 {voix[-1]['f0']:5.0f} Hz "
              f"(plage {voix[-1]['plage']:4.0f})", flush=True)
    del modele

    retenues = distinctes(voix, mesures)
    neuves = [v for v in retenues if not v["en_service"]]
    rapport = {"genre": args.genre, "seuils": {"cosinus": SEUIL_COSINUS, "f0_hz": SEUIL_F0_HZ},
               "repliques": [{k: l[k] for k in ("id", "role", "texte")} for l in ech],
               "candidats_mesures": len(voix), "en_service": len(en_service),
               "places_neuves": len(neuves),
               "retenues": [{**{k: v[k] for k in ("nom", "spec", "decalage", "f0", "plage",
                                                  "ambitus", "en_service")},
                             "debit": v.get("debit", 1.0)} for v in retenues]}
    (sortie / "catalogue.json").write_text(json.dumps(rapport, indent=2, ensure_ascii=False,
                                                      default=float), encoding="utf-8")
    print(f"\n{len(voix)} voix candidates mesurées ({len(candidats)} mélanges × "
          f"{len(DECALAGES)} décalages)")
    print(f"{len(neuves)} PLACES NEUVES distinctes, en plus des {len(en_service)} en service")
    print(f"(séparées si cosinus ≤ {SEUIL_COSINUS} ou écart de F0 ≥ {SEUIL_F0_HZ:.0f} Hz)\n")
    print(f"{'voix':46s} {'F0':>7s} {'plage':>7s} {'ambitus':>8s}")
    for v in sorted(retenues, key=lambda v: v["f0"]):
        marque = "  (en service)" if v["en_service"] else ""
        print(f"{v['nom']:46s} {v['f0']:6.0f}Hz {v['plage']:6.0f}Hz "
              f"{v['ambitus']:7.1f}st{marque}")
    print(f"\nÀ écouter : {sortie.relative_to(MEDIA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
