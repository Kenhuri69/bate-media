#!/usr/bin/env python3
"""Décliner la voix d'Arthur par stade d'âge — à lancer avec .venv-mlx.

Arthur est le seul rôle de BATE qui traverse quatre âges en parlant : trois ans au
chapitre 2, quinze à l'académie. Une voix unique sur tout le jeu ferait dire « Papa,
comment on sait qu'on a réussi ? » par un homme de trente ans. Les stades sont ceux
que le jeu utilise déjà pour ses sprites (`bate/tools/assets/character_plan.json`) —
les inventer ici ferait diverger la voix et l'image du même personnage.

Le timbre est `aiden:0.5+ryan:0.5`, validé à l'oreille, et il ne bouge JAMAIS : l'âge se
fait par le prompt (`PROMPTS_AGE`). La première version le diluait dans une composante
aiguë pour monter en hauteur ; à trois ans il n'en restait que 20 %, et ce n'était plus la
voix choisie. Le prompt seul suffit en gardant le timbre entier — voir
`tools/age_par_prompt_arthur.py` et le lot d'écoute 7.

CE QUE LE PROMPT FAIT, ET CE QU'IL NE FAIT PAS (mesuré le 2026-08-10 sur les 4433 répliques
livrées, au barycentre spectral) : il crée un vrai registre d'enfant — **289 à 308 Hz** en
réplique parlée contre **209 à 214 Hz** en narration, dix fois les intervalles de confiance.
Mais il **ne distingue pas les stades entre eux** : trois ans, cinq ans, six ans et treize ans
se recouvrent tous. Arthur a deux voix, pas cinq âges.

**La narration ne suit pas l'âge** : une seule voix de narrateur sur tout le jeu. Seules
les répliques PARLÉES d'Arthur portent un prompt d'âge (1121 sur les ch0-60, contre 3312
narrations) — voir `_instruct`.

    python tools/voix_age_arthur.py produire                      # banc des prompts d'âge
    python tools/voix_age_arthur.py livrer prologue,s02_toddler   # génère pour de bon
    python tools/voix_age_arthur.py bilan  prologue,s02_toddler   # hauteur du lot, par rôle
    python tools/voix_age_arthur.py verifier prologue,s02_toddler # contrôle qualité
    python tools/voix_age_arthur.py reprendre prologue,s02_toddler # régénère les ratés

`calibrer` et `ajuster` restent pour explorer le MÉLANGE — ils n'appliquent pas le prompt
d'âge, justement pour isoler l'effet de la dose. Ce sont des outils d'analyse, plus le
chemin de production.

⚠️ **NE JAMAIS CONCLURE SUR UNE HAUTEUR À PARTIR DE LA F0 ICI.** L'autocorrélation divise le
fondamental par deux sur les répliques parlées — elle rend ~140 Hz quand 96 % de l'énergie est
au-dessus — et cette erreur est invisible parce que la valeur reste plausible et stable. Elle a
produit un verdict entièrement faux le 2026-08-10. Utiliser `bilan` (barycentre spectral) pour
la hauteur et `verifier` (énergie en bande) pour la qualité ; `produire` et `calibrer` affichent
encore des F0, elles ne valent que comme indices.

La contrainte qui prime sur la hauteur reste la **dispersion** : un lot dont les clips vont de
138 à 296 Hz n'est pas un personnage, c'en est trois — voir le lot 5.
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
LIGNES = RACINE / "voice-agent/training/forge/bate-arthur/lines.json"
PLAN = RACINE / "bate/tools/assets/character_plan.json"
ECOUTE = MEDIA / "docs/ecoute-qwen3-tts/6-ages-arthur"
# Le banc des âges PAR LE PROMPT a son propre lot : le 6 garde les mesures de la déclinaison
# par DILUTION du timbre, écartée le 2026-08-08, et mélanger les deux dans un dossier ferait
# comparer des clips qui ne répondent pas à la même question.
ECOUTE_AGES = MEDIA / "docs/ecoute-qwen3-tts/8-ages-par-prompt"

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = "aiden:0.5+ryan:0.5"          # validé à l'oreille le 2026-08-08

# Cibles de hauteur par âge. Repères physiologiques de la voix parlée, pas des mesures
# maison : ~270 Hz à trois ans, ~240 à six, la mue vers treize, ~175 à quinze. Le stade
# académie retombe donc pile sur l'Arthur que le jeu fait déjà entendre (176-211 Hz).
CIBLES = {
    "s02_toddler": 270.0,
    "s03_road": 250.0,               # 5 ans, entre le bambin (270) et l'enfant (240)
    "s04_elenoir": 230.0,            # 8 ans, la fin du séjour chez les elfes
    "s03_child": 240.0,
    "s04_teen": 200.0,
    "s05_academy": 175.0,
    "prologue": 132.0,               # King Grey : la base pure, aucun ajout
}

# Composantes aiguës candidates. `eric` et `dylan` sont exclus d'office (dialectaux, ils
# produisent les clips dégénérés en français) ; `uncle_fu` va dans le mauvais sens.
AIGUES = ["vivian", "serena", "ono_anna"]
DOSES = [0.0, 0.15, 0.3, 0.45, 0.6]
# Prolongement mesuré le 2026-08-08 : à 0,6 la courbe de `vivian` plafonne à 206 Hz, sous
# les cibles enfant (240) et toddler (270). Or `vivian` est la SEULE composante monotone
# des trois — `serena` et `ono_anna` redescendent quand la dose monte, avec des plages de
# plus de 100 Hz à leur point de rupture. Prendre une composante par stade ferait entendre
# trois personnes différentes au lieu d'un enfant qui grandit : mieux vaut prolonger la
# seule courbe qui se tienne que panacher les autres.
DOSES_HAUTES = [0.7, 0.8, 0.9]


def _stades() -> dict:
    """Les stades d'Arthur tels que le JEU les définit, pas tels que je les imaginerais."""
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    arthur = next(c for c in plan["characters"] if c["id"] == "arthur")
    return {s["id"]: {"label": s["label"], "chapitres": s["chapters"]}
            for s in arthur["stages"] if s["chapters"]}


def _chapitre(ligne: dict):
    m = re.search(r"\d+", str(ligne.get("chapitre", "")))
    return int(m.group()) if m else None


def _repliques_par_stade() -> dict:
    """Range chaque réplique dans son stade. Le prologue (ch0-1) est King Grey, pas Arthur.

    La narration vieillit avec le personnage — c'est sa voix intérieure — sauf ces deux
    chapitres-là, où celui qui pense est encore le roi d'avant la réincarnation.

    **Les listes de chapitres du plan ont des trous, et il faut les combler.** Elles disent où
    le personnage APPARAÎT, ce qui n'a pas de raison de coïncider avec où il PARLE : `s05_academy`
    ne liste pas les ch50, 51, 54 et 59, alors qu'Arthur y narre 359 répliques — le narrateur
    étant sa voix intérieure, il est présent même quand le sprite ne l'est pas. Une appartenance
    exacte seule les jetterait en silence, et un lot muet sur quatre chapitres au milieu de
    l'académie ne se remarquerait qu'à l'écoute du jeu fini. Un chapitre orphelin rejoint donc le
    stade du chapitre listé le plus proche EN DESSOUS : c'est celui que le personnage traversait
    juste avant, donc son âge.
    """
    stades = _stades()
    lignes = json.loads(LIGNES.read_text(encoding="utf-8"))
    lots = {"prologue": []}
    for sid in stades:
        lots[sid] = []

    # Chapitre listé -> stade, dans l'ordre du plan (le premier stade qui revendique gagne).
    proprietaire = {}
    for sid, s in stades.items():
        for c in s["chapitres"]:
            proprietaire.setdefault(c, sid)

    def stade_de(ch: int):
        if ch in proprietaire:
            return proprietaire[ch]
        anterieurs = [c for c in proprietaire if c < ch]
        return proprietaire[max(anterieurs)] if anterieurs else None

    for ligne in lignes:
        ch = _chapitre(ligne)
        if ch is None:
            continue
        if ch <= 1:
            lots["prologue"].append(ligne)
            continue
        sid = stade_de(ch)
        if sid is not None:
            lots[sid].append(ligne)
    return {k: v for k, v in lots.items() if v}


def _melange(dose: float, aigue: str) -> str:
    """La base validée, pondérée (1-dose), plus la composante aiguë. Dose 0 = base pure."""
    if dose <= 0:
        return BASE
    parts = []
    for part in BASE.split("+"):
        nom, _, poids = part.partition(":")
        parts.append(f"{nom}:{float(poids or 1.0) * (1 - dose):.3f}")
    return "+".join(parts) + f"+{aigue}:{dose:.3f}"


def _echantillon(lot: list, n: int) -> list:
    """Des répliques du stade, dialogues d'abord : c'est la voix parlée qu'on calibre."""
    parles = [l for l in lot if l["role"] not in ("narrator",)]
    autres = [l for l in lot if l["role"] == "narrator"]
    return (parles + autres)[:n]


def _instruct(qwen3tts, sid: str, ligne: dict) -> str:
    """Prompt d'âge du stade + registre de jeu, SAUF pour la narration.

    **La narration ne suit pas l'âge** (décision du 2026-08-08) : une seule voix de
    narrateur du premier chapitre au dernier. C'est plus simple, et c'est aussi ce que la
    mesure disait déjà — le registre narration (« posé, presque murmuré, sans emphase »)
    annulait le prompt enfantin, qui tenait pourtant sur les répliques parlées : 164 Hz
    pour Arthur, 127 Hz pour ses narrations du même stade. Plutôt que de forcer un prompt
    contre un registre qui le contredit, on assume qu'Arthur PARLE jeune et RACONTE d'une
    voix posée.
    """
    registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
    age = "" if ligne["role"] == "narrator" else PROMPTS_AGE.get(sid, "")
    return f"{age} {qwen3tts.REGISTRES[registre]}".strip()


def _genere_lot(modele, qwen3tts, spec: str, lignes: list, dossier: Path,
                sid: str = None) -> list:
    """Un lot de répliques. Avec `sid`, applique le prompt d'âge du stade ; sans, le seul
    registre — c'est ce que veulent `calibrer` et `ajuster`, qui explorent le MÉLANGE et
    doivent donc isoler son effet du prompt."""
    faits = []
    for i, ligne in enumerate(lignes):
        registre = qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT)
        instruct = (_instruct(qwen3tts, sid, ligne) if sid
                    else qwen3tts.REGISTRES[registre])
        cible = dossier / f"{ligne['id']}.ogg"
        onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"], instruct, spec,
                                   seed=2000 + i, temperature=0.7)
        qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
        faits.append(cible)
    return faits


def _mesure(clips: list, mesures) -> dict:
    descr = [mesures._descripteurs(c) for c in clips]
    f0 = [d["f0_median"] for d in descr if d["f0_median"] > 0]
    return {"f0_median": float(np.median(f0)) if f0 else 0.0,
            "f0_plage": float(np.max(f0) - np.min(f0)) if f0 else 0.0,
            **mesures._dispersion_timbre(clips)}


def calibrer(aigues=None, doses=None) -> int:
    """Courbe dose -> hauteur obtenue, sur de vraies répliques d'Arthur enfant.

    Les clips déjà produits ne sont pas régénérés : prolonger la courbe ne doit pas
    redessiner les points qu'on a déjà lus, sinon on ne saurait plus si un écart vient
    de la dose ajoutée ou d'un nouveau tirage.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    aigues, doses = aigues or AIGUES, doses if doses is not None else DOSES
    lots = _repliques_par_stade()
    # Calibrer sur le stade enfant : c'est celui qui demande la plus grosse remontée
    # depuis 132 Hz, donc celui où une dose mal choisie s'entendra le plus.
    echantillon = _echantillon(lots["s03_child"], 4)
    print(f"calibrage sur {len(echantillon)} répliques de s03_child : "
          f"{', '.join(l['id'] for l in echantillon)}", flush=True)

    fichier = ECOUTE / "calibrage" / "courbe.json"
    courbe = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    modele = qwen3tts._charge("customvoice")
    for aigue in aigues:
        for dose in doses:
            if dose == 0 and aigue != aigues[0]:
                continue                      # la base pure ne dépend pas de la composante
            spec = _melange(dose, aigue)
            nom = "base" if dose == 0 else f"{aigue}:{dose}"
            if nom in courbe:
                print(f"\n=== {nom} — déjà mesuré, conservé", flush=True)
                continue
            dossier = ECOUTE / "calibrage" / nom.replace(":", "-").replace(".", "-")
            print(f"\n=== {nom}  ({spec})", flush=True)
            clips = _genere_lot(modele, qwen3tts, spec, echantillon, dossier)
            courbe[nom] = {"spec": spec, **_mesure(clips, mesures)}
            r = courbe[nom]
            print(f"    F0 {r['f0_median']:5.0f} Hz   plage {r['f0_plage']:4.0f} Hz   "
                  f"cohésion {r['cohesion_moyenne']:.3f}", flush=True)
    del modele

    fichier.write_text(
        json.dumps(courbe, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n" + "=" * 70)
    print("DOSE -> HAUTEUR OBTENUE   (base aiden:0.5+ryan:0.5)")
    print(f"{'mélange':22s} {'F0':>7s} {'plage':>7s} {'cohés.':>8s}   cible la plus proche")
    for nom, r in sorted(courbe.items(), key=lambda kv: kv[1]["f0_median"]):
        proche = min(CIBLES.items(), key=lambda kv: abs(kv[1] - r["f0_median"]))
        ecart = abs(proche[1] - r["f0_median"])
        print(f"{nom:22s} {r['f0_median']:6.0f}Hz {r['f0_plage']:6.0f}Hz "
              f"{r['cohesion_moyenne']:8.3f}   {proche[0]} ({proche[1]:.0f}, écart {ecart:.0f})")
    print("\nChoisir une dose par stade, la reporter dans DOSES_RETENUES, puis `produire`.")
    return 0


# L'ÂGE SE FAIT PAR LE PROMPT, PAS PAR LE MÉLANGE — décision du 2026-08-08.
#
# La première approche déclinait l'âge en diluant le timbre validé dans une composante
# plus aiguë. Elle atteignait la hauteur (245 Hz au stade toddler) mais réduisait
# `aiden:0.5+ryan:0.5` à 20 % du mélange : ce n'était plus la voix choisie, seulement son
# nom. Refusée, et à raison — une validation porte sur une voix entendue, pas sur une
# formule.
#
# Mesuré ensuite sur les sept répliques parlées du stade toddler
# (`tools/age_par_prompt_arthur.py`, lot d'écoute 7) : le prompt seul fait AUSSI BIEN que
# la dilution à 30 % — 164 Hz contre 162 — en gardant le timbre à 100 %. À hauteur égale
# il est donc strictement meilleur, et c'est le levier qui aurait dû être essayé en
# premier.
#
# Ce qu'il ne fait pas : atteindre les 270 Hz d'un enfant de trois ans. Cette cible était
# un repère physiologique que je m'étais fixé, pas une exigence : elle ne vaut pas de
# dénaturer la voix du personnage. Arthur parle jeune, il ne change pas de gorge.
TIMBRE = BASE                        # le même à tous les âges, sans exception

PROMPTS_AGE = {
    # Le prologue garde le timbre nu, sans prompt d'âge : c'est déjà la voix d'un homme
    # mûr, et il tombait à 131 Hz pour 132 visés. Ne pas réparer ce qui marche.
    "prologue": "",
    # Formulation « enfant-insistant », la meilleure des quatre essayées (164 Hz). Les plus
    # sobres montaient moins, et « enfant-jeu » RETOMBAIT à 130 : plus insistant ne veut
    # pas dire plus haut, la formulation se mesure elle aussi.
    "s02_toddler": ("Parle exactement comme un très jeune enfant de trois ans : voix "
                    "haut perchée, fluette et claire, intonation montante, mots détachés, "
                    "comme un petit garçon qui découvre le monde."),
    # LES QUATRE STADES SUIVANTS SONT UN CHOIX SOUS CONTRAINTE, PAS UN RÉGLAGE RÉUSSI.
    #
    # Mesuré le 2026-08-09 (`temoin` puis `tools/age_par_prompt_stades.py`, lot d'écoute 8) : au
    # delà du bambin, le prompt d'âge NE CONTRÔLE PLUS LA HAUTEUR. Les formulations en place
    # apportaient -6, +4, -21 et +17 Hz par rapport au timbre nu — du bruit, signes compris,
    # alors que le même levier vaut +48 Hz au stade bambin. Trois familles de formulation ont été
    # comparées sur les répliques réelles de chaque stade : aucune n'approche la cible
    # physiologique, et la meilleure change d'un stade à l'autre sans logique.
    #
    # Ce qui est retenu ci-dessous est, par stade, la variante la plus proche de sa cible sans
    # dégrader la dispersion. Elle donne une échelle qui DESCEND avec l'âge — 167, 158, 144,
    # 149, 137 Hz — ce qui est le point ; elle reste loin sous les repères physiologiques
    # (270, 250, 240, 200, 175). Le seul levier connu pour combler l'écart est la dilution du
    # timbre, refusée le 2026-08-08 parce qu'elle ne laissait que 20 % de la voix validée. On ne
    # la reprend pas de notre propre chef : l'arbitrage appartient à l'oreille d'Olivier.
    #
    # Stades AJOUTÉS au plan du jeu le 2026-08-09 (`s03_road`, `s04_elenoir`) : aucun sprite ne
    # couvrait les 4-5 ans ni la fin du séjour chez les elfes. La voix suit les mêmes bornes que
    # le sprite, sinon les deux changeraient à des chapitres différents pour le même personnage.
    # `s04_elenoir` ne reçoit aujourd'hui aucune réplique — ses ch18-21 sont déjà revendiqués par
    # `s03_road` — mais son prompt est écrit pour le jour où le plan tranchera le partage.
    "s03_road": ("Tu ES un garçon de cinq ans et ta voix doit s'entendre comme telle : "
                 "nettement plus aiguë qu'une voix d'homme, timbre jeune et clair, tessiture "
                 "haute, souffle court, intonation montante en fin de phrase. Jamais une voix "
                 "d'adulte."),                                      # 158 Hz (sobre : 130)
    "s04_elenoir": ("Tu ES un garçon de huit ans et ta voix doit s'entendre comme telle : "
                    "nettement plus aiguë qu'une voix d'homme, timbre jeune et clair, tessiture "
                    "haute, intonation montante en fin de phrase. Jamais une voix d'adulte."),
    "s03_child": ("Tu ES un garçon de six ans et ta voix doit s'entendre comme telle : "
                  "nettement plus aiguë qu'une voix d'homme, timbre jeune et clair, tessiture "
                  "haute, souffle court, intonation montante en fin de phrase. Jamais une voix "
                  "d'adulte."),                                     # 144 Hz, plage 56, la plus
                                                                    # resserrée du banc
    "s04_teen": ("Tu ES un garçon de treize ans et ta voix doit s'entendre comme telle : "
                 "nettement plus aiguë qu'une voix d'homme, timbre jeune et clair, tessiture "
                 "haute, souffle court, intonation montante en fin de phrase. Jamais une voix "
                 "d'adulte."),                                      # 149 Hz (sobre : 117)
    # Seul stade où la forme « intense » fait PERDRE de la hauteur (123 contre 134) : la
    # transposition sobre du bambin l'emporte de peu. Ne pas uniformiser par cohérence d'écriture,
    # c'est la mesure qui départage.
    "s05_academy": ("Parle exactement comme un garçon de quinze ans : voix claire et haut "
                    "perchée, jeune et légère, intonation montante, sans gravité d'adulte."),
}


def ajuster(sid: str, aigue: str, doses: list) -> int:
    """Rebalaye un stade sur SES PROPRES répliques, à la taille d'échantillon de prod.

    Le calibrage global s'est révélé non transférable : la hauteur obtenue dépend du texte
    prononcé autant que du mélange (`vivian:0.6` = 206 Hz sur des répliques d'enfant, mais
    225 Hz sur celles d'adolescent). Et comparer la plage d'un lot de 4 clips à celle d'un
    lot de 6 n'a pas de sens — c'est un écart entre extrêmes, il croît avec l'échantillon.
    D'où ce mode : même stade, mêmes répliques, même compte qu'en production.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    lot = _repliques_par_stade().get(sid) or []
    echantillon = _echantillon(lot, 6)
    print(f"ajustement {sid} sur ses {len(echantillon)} répliques", flush=True)
    modele = qwen3tts._charge("customvoice")
    for dose in doses:
        spec = _melange(dose, aigue)
        dossier = ECOUTE / "ajustage" / f"{sid}-{aigue}-{dose}".replace(".", "-")
        print(f"\n=== {sid} {aigue}:{dose}  ({spec})", flush=True)
        clips = _genere_lot(modele, qwen3tts, spec, echantillon, dossier)
        r = _mesure(clips, mesures)
        print(f"    F0 {r['f0_median']:5.0f} Hz (cible {CIBLES.get(sid, 0):.0f})   "
              f"plage {r['f0_plage']:4.0f} Hz   cohésion {r['cohesion_moyenne']:.3f}",
              flush=True)
    del modele
    return 0


def _part_bande(chemin: Path, cible: float) -> float:
    """Part de l'énergie vocale située dans la bande du fondamental attendu.

    Critère de contrôle VOLONTAIREMENT distinct de la F0, parce que la F0 est le mouchard
    peu fiable ici : l'autocorrélation attrape régulièrement une harmonique quand le
    fondamental est faible, et rend 400 Hz — la borne même du détecteur — sur des clips
    dont l'énergie est en réalité à 100 Hz. Mesurer où est l'énergie ne se trompe pas
    d'octave. Un clip sain met la moitié ou plus de son énergie vocale dans cette bande ;
    les clips cassés du prologue tombaient à 4-14 %.
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


CIBLE_NARRATION = 132.0              # la narration ne suit pas l'âge : voix nue partout


def _cible(sid: str, role: str) -> float:
    """Hauteur attendue d'un clip — elle dépend du RÔLE autant que du stade.

    Piège rencontré : contrôler les narrations d'un stade jeune avec la cible de ce stade
    signalait 13 clips sur 13 comme défectueux, alors qu'ils étaient parfaitement sains —
    la narration ne suit pas l'âge, elle DOIT rester à ~130 Hz. Un contrôle qui applique
    la mauvaise attente ne détecte pas des défauts, il en invente.

    **NE PAS remplacer ces cibles par la F0 mesurée du lot** — essayé le 2026-08-10, à tort.
    L'intention paraissait bonne (« mesurer où la voix est vraiment plutôt que où on la
    voudrait ») mais la F0 mesurée est précisément la grandeur fausse ici : sur les répliques
    parlées, l'autocorrélation rend ~140 Hz alors que **3 à 6 % seulement** de l'énergie vocale
    se trouve sous 110 Hz et que la bande dominante est 200-270 Hz. Elle divise le fondamental
    par deux. Recentrer la bande sur cette valeur faisait tomber l'énergie captée de 45 % à
    28 % : le contrôle se mettait à regarder sous la voix. Les cibles de `CIBLES`, elles,
    tombent sur la bande dominante réelle — elles sont justes, c'est la F0 qui ment.
    """
    return CIBLE_NARRATION if role == "narrator" else CIBLES.get(sid, CIBLE_NARRATION)


def _douteux(clips_roles: list, sid: str) -> tuple:
    """Les clips dont l'énergie n'est pas là où elle devrait, à rôle comparable.

    Seuil relatif à la médiane, pas absolu : la part d'énergie dans la bande dépend du
    timbre et du texte, et un seuil fixe rejetterait tout un lot ou aucun. Médiane calculée
    PAR RÔLE, parce que narration et réplique parlée n'ont ni la même cible ni la même
    distribution — les mélanger ferait juger les unes à l'aune des autres.
    """
    mauvais, medianes = [], {}
    for role in {r for _, r in clips_roles}:
        cible = _cible(sid, role)
        parts = [(_part_bande(c, cible), c) for c, r in clips_roles if r == role]
        if not parts:
            continue
        mediane = float(np.median([p for p, _ in parts]))
        medianes[role] = mediane
        mauvais += [(p, c) for p, c in parts if p < 0.5 * mediane]
    return sorted(mauvais), medianes


def verifier(stades: list) -> int:
    """Contrôle qualité du lot livré, sans rien régénérer."""
    sortie = MEDIA / "voices/arthur-qwen3"
    lots = _repliques_par_stade()
    for sid in stades:
        clips_roles = [(sortie / f"{l['id']}.ogg", l["role"]) for l in lots[sid]
                       if (sortie / f"{l['id']}.ogg").exists()]
        role_par_clip = {c: r for c, r in clips_roles}
        mauvais, medianes = _douteux(clips_roles, sid)
        detail = ", ".join(f"{r} {m:.0%} (cible {_cible(sid, r):.0f} Hz)"
                           for r, m in sorted(medianes.items()))
        print(f"\n=== {sid} : {len(clips_roles)} clips — médiane d'énergie par rôle : "
              f"{detail} — {len(mauvais)} douteux", flush=True)
        for part, c in mauvais:
            cible = _cible(sid, role_par_clip[c])
            print(f"    {c.stem:22s} {part:5.1%} de l'énergie dans "
                  f"{0.6 * cible:.0f}-{1.4 * cible:.0f} Hz", flush=True)
    return 0


def reprendre(stades: list, essais: int = 4) -> int:
    """Régénère les clips douteux sur d'autres graines, en gardant le meilleur essai.

    « Meilleur » au sens du critère d'énergie, pas de la F0 : c'est celui qui a détecté le
    défaut, c'est celui qui doit valider la reprise. On garde le meilleur essai même s'il
    reste sous le seuil — un clip amélioré vaut mieux qu'un clip cassé conservé par
    principe — et on journalise ceux qui n'ont pas pu être sauvés.
    """
    import qwen3tts

    sortie = MEDIA / "voices/arthur-qwen3"
    lots = _repliques_par_stade()
    modele = qwen3tts._charge("customvoice")
    bilan = {}
    for sid in stades:
        spec = TIMBRE
        par_id = {l["id"]: l for l in lots[sid]}
        clips_roles = [(sortie / f"{i}.ogg", l["role"]) for i, l in par_id.items()
                       if (sortie / f"{i}.ogg").exists()]
        mauvais, medianes = _douteux(clips_roles, sid)
        print(f"\n=== {sid} : {len(mauvais)} clips à reprendre", flush=True)
        bilan[sid] = {"repris": 0, "sauves": 0, "restants": []}
        for part0, chemin in mauvais:
            ligne = par_id[chemin.stem]
            cible = _cible(sid, ligne["role"])
            seuil = 0.5 * medianes[ligne["role"]]
            meilleur, meilleure_part = None, part0
            for essai in range(essais):
                onde, _ = qwen3tts._genere(
                    modele, "customvoice", ligne["texte"], _instruct(qwen3tts, sid, ligne),
                    spec, seed=7000 + essai * 613, temperature=0.7)
                tmp = chemin.with_suffix(".essai.ogg")
                qwen3tts._ecrit(onde, modele.sample_rate, tmp, "ogg")
                part = _part_bande(tmp, cible)
                if part > meilleure_part:
                    meilleur, meilleure_part = onde, part
                tmp.unlink()
                if meilleure_part >= seuil:
                    break
            bilan[sid]["repris"] += 1
            if meilleur is not None:
                qwen3tts._ecrit(meilleur, modele.sample_rate, chemin, "ogg")
            etat = "OK" if meilleure_part >= seuil else "encore douteux"
            if meilleure_part >= seuil:
                bilan[sid]["sauves"] += 1
            else:
                bilan[sid]["restants"].append(chemin.stem)
            print(f"    {chemin.stem:22s} {part0:5.1%} -> {meilleure_part:5.1%}  {etat}",
                  flush=True)
    del modele

    print("\n" + "=" * 70)
    for sid, b in bilan.items():
        print(f"{sid:14s} {b['sauves']}/{b['repris']} récupérés"
              + (f", restants : {', '.join(b['restants'])}" if b["restants"] else ""))
    return 0


def integrer(stades: list) -> int:
    """Verse le lot dans `voices/arthur/`, met à jour le manifeste, retire le temporaire.

    C'est l'étape qui rend les voix consommables par le jeu : `build_pack.py` empaquette
    `voices/` tel quel et `AudioManager.ResolveClip` cherche `voice/<personnage>/<id>`, si
    bien qu'un dossier `voices/arthur-qwen3/` produirait la clé `voice/arthur-qwen3/…` que
    personne n'appelle. Le pack serait construit sans erreur et le jeu resterait muet.

    Deux précautions avant d'écraser :

    * les .ogg de `voices/` ne sont PAS versionnés (voir .gitignore) — un Chatterbox
      remplacé est perdu, pas récupérable par git. On ne remplace donc que les ids du lot ;
    * sept des huit clips qui servent de REPÈRE Chatterbox aux bancs sont dans le lot. Les
      écraser ferait mesurer du Qwen3 en croyant mesurer du Chatterbox — le pire des cas,
      une mesure qui ment sans rien signaler. Ils sont copiés dans le dossier d'écoute,
      versionné, avant remplacement, et `_repere_chatterbox` y est redirigé.
    """
    import shutil

    source = MEDIA / "voices/arthur-qwen3"
    cible = MEDIA / "voices/arthur"
    repere = MEDIA / "docs/ecoute-qwen3-tts/repere-chatterbox"
    clips = sorted(source.glob("*.ogg"))
    if not clips:
        print(f"rien à intégrer dans {source}", file=sys.stderr)
        return 1

    # 1. Sauver le repère Chatterbox AVANT tout écrasement.
    repere.mkdir(parents=True, exist_ok=True)
    sauves = 0
    for nom in sorted(p.name for p in cible.glob("arthur_ch0*.ogg"))[:8]:
        if (source / nom).exists() and not (repere / nom).exists():
            shutil.copy2(cible / nom, repere / nom)
            sauves += 1
    print(f"repère Chatterbox : {sauves} clips sauvés dans "
          f"{repere.relative_to(MEDIA)}", flush=True)

    # 2. Remplacer.
    for c in clips:
        shutil.copy2(c, cible / c.name)
    print(f"{len(clips)} clips versés dans {cible.relative_to(MEDIA)}", flush=True)

    # 3. Réaligner le manifeste : ses sha256 décrivent les anciens fichiers.
    chemin = MEDIA / "manifest.json"
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    remplaces = {c.stem for c in clips}
    touches = 0
    for entree in manifeste["voix"]["arthur"]["fichiers"]:
        if entree["id"] in remplaces:
            entree["sha256"] = _sha256(cible / entree["fichier"])[:16]
            entree["moteur"] = "qwen3-tts"
            touches += 1
    manifeste["voix"]["arthur"]["moteur_par_defaut"] = "chatterbox"
    chemin.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"manifeste : {touches} empreintes réalignées", flush=True)

    # 4. Retirer le temporaire, qui n'a plus de raison d'être et polluerait le pack.
    shutil.rmtree(source)
    print(f"{source.relative_to(MEDIA)} supprimé", flush=True)
    return 0


def _sha256(chemin: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def livrer(stades: list) -> int:
    """Génère TOUTES les répliques des stades donnés, pour de bon.

    Sortie dans `voices/arthur-qwen3/` et NON dans `voices/arthur/`, qui contient les 1065
    répliques Chatterbox en service : ce sont elles qui font tourner le jeu aujourd'hui, et
    ce sont elles que les bancs prennent pour repère (`_repere_chatterbox`). Les écraser
    ferait perdre à la fois la voix en production et l'étalon des mesures, pour un lot qui
    ne couvre que deux stades sur cinq. Les deux jeux cohabitent jusqu'à ce que les trois
    stades restants soient résolus. Le dossier n'est pas versionné (`voices/*/` est dans
    .gitignore) : les médias partent en Release, pas dans l'arborescence.

    **Reprenable** : un clip déjà présent et non vide est conservé. Sur les 72 répliques du
    premier pack la question ne se posait pas ; sur les 4433 des ch0-60 la génération dure des
    heures, et une coupure en cours de route reperdrait tout le travail fait. Pour refaire un
    stade pour de bon, vider son lot de `voices/arthur-qwen3/` — la reprise ne devine pas qu'un
    prompt d'âge a changé.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    sortie = MEDIA / "voices/arthur-qwen3"
    lots = _repliques_par_stade()
    total = sum(len(lots.get(s) or []) for s in stades)
    print(f"livraison de {total} répliques ({', '.join(stades)}) vers "
          f"{sortie.relative_to(MEDIA)}", flush=True)

    modele = qwen3tts._charge("customvoice")
    rapport = {"base": BASE, "sortie": str(sortie.relative_to(MEDIA)), "stades": {}}
    for sid in stades:
        spec = TIMBRE                    # le timbre validé, à tous les âges
        lot = lots.get(sid) or []
        age = PROMPTS_AGE.get(sid, "")
        print(f"\n=== {sid} : {len(lot)} répliques  ({spec})"
              f"{'  + prompt d âge' if age else '  (sans prompt d âge)'}", flush=True)
        faits, relances, gardes, debut = [], 0, 0, time.time()
        for i, ligne in enumerate(lot):
            cible = sortie / f"{ligne['id']}.ogg"
            if cible.exists() and cible.stat().st_size > 0:
                gardes += 1
                faits.append(cible)
                continue
            onde, essais = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                            _instruct(qwen3tts, sid, ligne), spec,
                                            seed=2000 + i, temperature=0.7)
            relances += essais
            qwen3tts._ecrit(onde, modele.sample_rate, cible, "ogg")
            faits.append(cible)
            if (i + 1) % 10 == 0 or i + 1 == len(lot):
                print(f"    {i + 1}/{len(lot)}  ({time.time() - debut:.0f}s, "
                      f"{relances} relances, {gardes} repris)", flush=True)
        rapport["stades"][sid] = {"spec": spec, "clips": len(faits), "relances": relances,
                                  "secondes": round(time.time() - debut, 1),
                                  **_mesure(faits, mesures)}
        r = rapport["stades"][sid]
        print(f"    F0 {r['f0_median']:5.0f} Hz (cible {CIBLES.get(sid, 0):.0f})   "
              f"plage {r['f0_plage']:4.0f} Hz", flush=True)
    del modele

    (sortie / "rapport_livraison.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\n" + "=" * 70)
    for sid, r in rapport["stades"].items():
        print(f"{sid:14s} {r['clips']:4d} clips  {r['secondes']:6.0f}s  "
              f"{r['relances']} relances  F0 {r['f0_median']:.0f}Hz  plage {r['f0_plage']:.0f}Hz")
    print(f"\nÉcrit dans {sortie}")
    return 0


def produire() -> int:
    """Le lot d'écoute : chaque stade sur SES répliques, timbre validé + prompt d'âge."""
    import bench_qwen3tts as mesures
    import qwen3tts

    lots = _repliques_par_stade()
    modele = qwen3tts._charge("customvoice")
    rapport = {"base": BASE, "cibles_f0": CIBLES, "stades": {}}
    for sid in PROMPTS_AGE:
        spec = TIMBRE
        lot = lots.get(sid) or []
        if not lot:
            print(f"  {sid} : aucune réplique", flush=True)
            continue
        echantillon = _echantillon(lot, 6)
        dossier = ECOUTE_AGES / sid
        print(f"\n=== {sid}  ({spec})  {len(echantillon)} répliques", flush=True)
        clips = _genere_lot(modele, qwen3tts, spec, echantillon, dossier, sid=sid)
        rapport["stades"][sid] = {
            "spec": spec, "repliques_du_stade": len(lot),
            "dossier": str(dossier.relative_to(MEDIA)), **_mesure(clips, mesures),
        }
        r = rapport["stades"][sid]
        print(f"    F0 {r['f0_median']:5.0f} Hz (cible {CIBLES.get(sid, 0):.0f})   "
              f"plage {r['f0_plage']:4.0f} Hz", flush=True)
    del modele

    ECOUTE_AGES.mkdir(parents=True, exist_ok=True)
    (ECOUTE_AGES / "rapport_ages.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"{'stade':16s} {'mélange':34s} {'F0':>7s} {'cible':>7s} {'plage':>7s}")
    for sid, r in rapport["stades"].items():
        print(f"{sid:16s} {r['spec']:34s} {r['f0_median']:6.0f}Hz "
              f"{CIBLES.get(sid, 0):6.0f}Hz {r['f0_plage']:6.0f}Hz")
    print(f"\nÀ écouter : {ECOUTE_AGES.relative_to(MEDIA)}")
    return 0


def _barycentre(chemin: Path) -> float:
    """Barycentre de l'énergie vocale (60-800 Hz) d'un clip.

    **La grandeur de référence pour toute question de hauteur sur ces voix.** La F0 par
    autocorrélation, elle, divise le fondamental par deux sur les répliques parlées : elle rend
    ~140 Hz alors que 3 à 6 % seulement de l'énergie se trouve sous 110 Hz. L'erreur est
    invisible — 140 Hz est plausible pour une voix masculine, et la valeur est stable d'un stade
    à l'autre — et elle a produit un verdict entièrement faux le 2026-08-10 (« le prompt d'âge ne
    fait rien »), alors que l'écart réel entre voix parlée et narration est de 80 à 95 Hz.

    Un barycentre ne peut pas se tromper d'octave : il n'identifie aucun fondamental, il pèse
    l'énergie là où elle est.
    """
    import soundfile as sf

    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    spectre = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    m = (f > 60) & (f < 800)
    return float((f[m] * spectre[m]).sum() / spectre[m].sum()) if spectre[m].sum() > 0 else 0.0


def bilan(stades: list) -> int:
    """Hauteur du lot LIVRÉ, par rôle, au barycentre spectral — la mesure qui décrit le produit.

    Deux raisons de ne pas lire le rapport de `livrer` à la place.

    **Le rôle d'abord.** Sa médiane par stade mêle tous les rôles, or un stade compte cinq à six
    fois plus de narrations que de répliques parlées et la narration ne porte PAS le prompt d'âge
    (décision du 2026-08-08). La médiane du stade est donc celle de sa narration, et l'effet
    d'âge — qui ne vit que dans les répliques parlées — y est noyé.

    **La grandeur ensuite.** `livrer` rapporte une F0, inutilisable ici (voir `_barycentre`).

    L'intervalle de confiance est donné parce qu'il tranche la seule question ouverte : les
    stades se recouvrent tous, ils ne se distinguent pas entre eux.
    """
    sortie = MEDIA / "voices/arthur-qwen3"
    lots = _repliques_par_stade()
    rapport = {}
    print(f"{'stade':14s} {'rôle':10s} {'clips':>6s} {'barycentre':>11s} {'IC95':>7s}")
    for sid in stades:
        par_role = {}
        for ligne in lots.get(sid) or []:
            chemin = sortie / f"{ligne['id']}.ogg"
            if chemin.exists() and chemin.stat().st_size > 0:
                par_role.setdefault(ligne["role"], []).append(chemin)
        rapport[sid] = {}
        for role, clips in sorted(par_role.items()):
            v = [c for c in (_barycentre(p) for p in clips) if c > 0]
            if not v:
                continue
            mediane = float(np.median(v))
            # IC95 de la MÉDIANE : 1,253·σ/√n est son erreur type asymptotique. Pas celui de la
            # moyenne — la distribution est asymétrique, tirée vers le haut par les clips brefs.
            ic = 1.96 * 1.253 * float(np.std(v)) / np.sqrt(len(v))
            rapport[sid][role] = {"clips": len(clips), "barycentre": mediane, "ic95": ic}
            print(f"{sid:14s} {role:10s} {len(clips):6d} {mediane:10.0f}Hz {ic:6.0f}")
    (sortie / "rapport_bilan.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    return 0


def temoin() -> int:
    """Les mêmes répliques SANS prompt d'âge — le contrôle qui dit si le prompt agit.

    `produire` mesure ce que le prompt donne ; il ne dit pas ce qu'il APPORTE. Un prompt qui
    n'atteint pas le modèle, ou qu'il ignore, rend exactement les mêmes chiffres qu'un timbre nu
    et rien ne le signale : le mécanisme est là, il ne fait rien. Seul l'écart à ce témoin
    tranche, stade par stade — et il se mesure sur les mêmes textes et les mêmes graines, sans
    quoi on comparerait deux échantillons plutôt que deux consignes.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    lots = _repliques_par_stade()
    reference = json.loads((ECOUTE_AGES / "rapport_ages.json").read_text(encoding="utf-8"))
    modele = qwen3tts._charge("customvoice")
    rapport = {"base": BASE, "stades": {}}
    for sid in PROMPTS_AGE:
        lot = lots.get(sid) or []
        if not lot or not PROMPTS_AGE[sid]:
            continue                     # sans prompt d'âge, le témoin serait le lot lui-même
        echantillon = _echantillon(lot, 6)
        dossier = ECOUTE_AGES / "temoin-sans-prompt" / sid
        print(f"\n=== témoin {sid}  {len(echantillon)} répliques", flush=True)
        # `sid=None` : `_genere_lot` n'applique alors que le registre, pas le prompt d'âge.
        clips = _genere_lot(modele, qwen3tts, TIMBRE, echantillon, dossier)
        rapport["stades"][sid] = _mesure(clips, mesures)
        avec = reference["stades"][sid]["f0_median"]
        sans = rapport["stades"][sid]["f0_median"]
        print(f"    F0 {sans:5.0f} Hz sans prompt contre {avec:5.0f} avec "
              f"({avec - sans:+.0f} Hz)", flush=True)
    del modele

    (ECOUTE_AGES / "rapport_temoin.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"{'stade':16s} {'sans prompt':>12s} {'avec prompt':>12s} {'apport':>8s} {'cible':>7s}")
    for sid, r in rapport["stades"].items():
        avec = reference["stades"][sid]["f0_median"]
        print(f"{sid:16s} {r['f0_median']:11.0f}Hz {avec:11.0f}Hz "
              f"{avec - r['f0_median']:+7.0f}Hz {CIBLES.get(sid, 0):6.0f}Hz")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "calibrer"
    if action == "prolonger":
        # Prolonger une courbe existante : `prolonger [composante] [doses]`.
        # Sans argument, la seule monotone du premier balayage (vivian) aux doses hautes.
        aigue = sys.argv[2] if len(sys.argv) > 2 else "vivian"
        doses = ([float(d) for d in sys.argv[3].split(",")] if len(sys.argv) > 3
                 else DOSES_HAUTES)
        sys.exit(calibrer(aigues=[aigue], doses=doses))
    if action == "integrer":
        # Verse le lot dans voices/arthur/ — l'étape qui le rend jouable.
        sys.exit(integrer(sys.argv[2].split(",") if len(sys.argv) > 2 else []))
    if action == "bilan":
        # `bilan <stade>[,...]` — hauteur du lot livré, PAR RÔLE. La médiane tous rôles
        # confondus d'un stade est celle de sa narration, qui ne porte pas le prompt d'âge.
        sys.exit(bilan(sys.argv[2].split(",")))
    if action in ("verifier", "reprendre"):
        # Contrôle qualité du lot livré, puis reprise ciblée des clips défectueux.
        cibles = sys.argv[2].split(",")
        sys.exit(verifier(cibles) if action == "verifier" else reprendre(cibles))
    if action == "livrer":
        # `livrer <stade>[,<stade>...]` — toutes les répliques, pour de bon.
        sys.exit(livrer(sys.argv[2].split(",")))
    if action == "ajuster":
        # `ajuster <stade> <composante> <doses>` — rebalaye un stade sur ses répliques.
        sys.exit(ajuster(sys.argv[2], sys.argv[3],
                         [float(d) for d in sys.argv[4].split(",")]))
    sys.exit({"calibrer": calibrer, "produire": produire, "temoin": temoin}[action]())
