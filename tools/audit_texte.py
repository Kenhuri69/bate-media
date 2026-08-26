#!/usr/bin/env python3
"""Vérifie que chaque clip DIT VRAIMENT son texte, en le réécoutant par ASR.

Le trou que ce contrôle comble. Trois garde-fous existaient déjà et aucun ne voit un clip
tronqué :

- `qwen3tts._suspect` n'attrape que l'aberration franche — trop long, quasi muet, souffle —
  et un clip qui s'arrête au milieu de la phrase est parfaitement normal de ce point de vue :
  bon niveau, trames actives, durée cohérente avec ce qu'il a effectivement dit ;
- `voix_personnage.py verifier` mesure OÙ est l'énergie, donc le timbre, pas le contenu ;
- `export_audit.py` mesure l'énergie des 120 dernières ms, ce qui détecte une coupure NETTE
  en plein son, mais pas une phrase qui se termine proprement trois mots trop tôt.

Le seul juge du contenu est un transcripteur. Il tourne déjà en local et en permanence :
`whisper-server` (large-v3-turbo q5, français), servi par `com.kenhrui.whisper-server` sur
127.0.0.1:8910 — environ 0,7 s par réplique, soit une dizaine de minutes pour les 697 clips
des dix voix récentes.

    ../.venv-mlx/bin/python tools/audit_texte.py alice reynolds jasmine
    ../.venv-mlx/bin/python tools/audit_texte.py --tous
    ../.venv-mlx/bin/python tools/audit_texte.py alice --selftest

Ce que la mesure NE dit pas : la transcription n'est pas le texte. Whisper francise les noms
propres inventés du projet (Loriande, Elenoir, Zestier), tranche autrement les nombres et
oublie des mots outils. C'est pourquoi le verdict porte sur un TAUX d'appariement de mots et
non sur une égalité, que la comparaison ignore accents et ponctuation, et que le rapport
imprime toujours les deux textes côte à côte : c'est un tri de suspects pour l'oreille, pas
un juge automatique.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib import request as urlrequest

MEDIA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from empreinte import clip_id  # noqa: E402

WHISPER = "http://127.0.0.1:8910/inference"

# Seuils. Le premier est le seul qui décide ; les deux autres nomment le défaut.
SEUIL_COUVERTURE = 0.80     # sous ce taux de mots retrouvés, le clip est suspect
SEUIL_QUEUE = 0.60          # part des mots retrouvés dans le dernier tiers du texte
SEUIL_RADOTAGE = 1.60       # mots entendus / mots attendus au-delà : le clip radote
MOTS_MINIMUM = 4            # en dessous, un mot manquant fait 25 % : on ne juge pas


def _perso(cle: str) -> dict:
    """Le personnage tel que la PRODUCTION le déclare — même registre, pas une copie.

    Dupliquer ici la liste des rôles ou le slug de forge ferait diverger le contrôle de ce
    qui est produit, et un contrôle qui regarde ailleurs que la production ne contrôle rien.
    """
    import voix_personnage
    return voix_personnage._perso(cle)


def _lignes(cle: str) -> list:
    import voix_personnage
    return voix_personnage._lignes(_perso(cle))


def transcrire(chemin: Path) -> str:
    """Texte entendu dans le clip, par le whisper-server local.

    Passage par ffmpeg parce que whisper.cpp veut du PCM 16 kHz mono : lui donner l'Ogg
    directement rend une transcription vide, ce qui ressemblerait exactement au défaut
    cherché. D'où le `--selftest`, qui vérifie qu'un clip sain est bien transcrit.
    """
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "clip.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(chemin),
                        "-ar", "16000", "-ac", "1", str(wav)], check=True)
        octets = wav.read_bytes()

    limite = "----bate" + "".join(f"{b:02x}" for b in b"audit")
    corps = b"".join([
        f"--{limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="clip.wav"\r\n',
        b"Content-Type: audio/wav\r\n\r\n", octets, b"\r\n",
        f"--{limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="response_format"\r\n\r\njson\r\n',
        f"--{limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="language"\r\n\r\nfr\r\n',
        f"--{limite}--\r\n".encode(),
    ])
    req = urlrequest.Request(WHISPER, data=corps, headers={
        "Content-Type": f"multipart/form-data; boundary={limite}"})
    with urlrequest.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8")).get("text", "").strip()


def duree(chemin: Path) -> float:
    import soundfile as sf

    info = sf.info(str(chemin))
    return info.frames / info.samplerate


def duree_attendue(texte: str) -> float:
    """~14 caractères par seconde en français parlé — la constante de `reconcile_voices`."""
    return max(0.6, len(texte) / 14.0)


def mots(texte: str) -> list:
    """Mots comparables : sans accent, sans ponctuation, en minuscules.

    L'apostrophe SÉPARE (« s'il » -> « s il ») : le transcripteur écrit tantôt « qu'il »,
    tantôt « qu il », et cette variation d'orthographe n'est pas un mot manquant.
    """
    plat = unicodedata.normalize("NFD", texte.lower())
    plat = "".join(c for c in plat if unicodedata.category(c) != "Mn")
    return [m for m in re.split(r"[^0-9a-z]+", plat) if m]


def couverture(attendu: str, entendu: str) -> dict:
    """Part des mots attendus réellement entendus, et où le manque se trouve.

    `SequenceMatcher` sur les listes de mots plutôt qu'une intersection d'ensembles : l'ORDRE
    compte, et un clip qui répète trois fois le même mot ne « couvre » pas trois mots.
    La queue est mesurée à part parce que le défaut cherché est presque toujours une fin
    manquante — une couverture globale de 0,85 sur une réplique longue peut n'être QUE la
    dernière proposition, celle qui porte la chute.
    """
    a, b = mots(attendu), mots(entendu)
    if not a:
        return {"ratio": 1.0, "queue": 1.0, "attendus": 0, "entendus": len(b)}
    apparies = [False] * len(a)
    for bloc in SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(bloc.size):
            apparies[bloc.a + k] = True
    debut_queue = int(len(a) * 2 / 3)
    queue = apparies[debut_queue:] or apparies
    return {"ratio": sum(apparies) / len(a),
            "queue": sum(queue) / len(queue),
            "attendus": len(a), "entendus": len(b)}


def motif(mesure: dict) -> str:
    """Nom du défaut, ou chaîne vide si le clip dit son texte."""
    if mesure["attendus"] < MOTS_MINIMUM:
        return ""
    if mesure["entendus"] == 0:
        return "muet (rien de transcrit)"
    if mesure["ratio"] < SEUIL_COUVERTURE:
        manque = "fin manquante" if mesure["queue"] < SEUIL_QUEUE else "texte incomplet"
        return f"{manque} ({mesure['ratio']:.0%} des mots)"
    if mesure["entendus"] > SEUIL_RADOTAGE * mesure["attendus"]:
        return f"radotage ({mesure['entendus']} mots pour {mesure['attendus']})"
    return ""


def auditer(cle: str, limite: int = 0, bavard: bool = False) -> dict:
    perso = _perso(cle)
    lignes = _lignes(cle)
    resultats, absents = [], []
    a_faire = []
    for l in lignes:
        chemin = perso["sortie"] / f"{l['clip']}.ogg"
        (a_faire if chemin.exists() else absents).append((chemin, l))
    if limite:
        a_faire = a_faire[:limite]
    print(f"{perso['nom']} : {len(a_faire)} clips à réécouter"
          + (f", {len(absents)} répliques sans clip" if absents else ""), flush=True)

    for i, (chemin, ligne) in enumerate(a_faire):
        entendu = transcrire(chemin)
        mesure = couverture(ligne["texte"], entendu)
        m = motif(mesure)
        resultats.append({"clip": chemin.stem, "personnage": perso["nom"],
                          "role": ligne["role"], "chapitre": ligne["chapitre"],
                          "texte": ligne["texte"], "entendu": entendu,
                          "motif": m, **{k: round(v, 3) if isinstance(v, float) else v
                                         for k, v in mesure.items()},
                          # La durée est le TÉMOIN CROISÉ du verdict ASR, et elle est
                          # indispensable : whisper francise les noms propres du projet
                          # (« Twin Horns » -> « Twinornes ») et rend alors une couverture
                          # basse sur un clip parfaitement complet. Un clip réellement
                          # tronqué, lui, est aussi trop COURT — deux mesures indépendantes
                          # qui doivent tomber d'accord avant qu'on régénère.
                          "duree": round(duree(chemin), 2),
                          "duree_attendue": round(duree_attendue(ligne["texte"]), 2)})
        if m or bavard:
            print(f"    {chemin.stem:22s} {m or 'ok':38s} {entendu[:70]}", flush=True)
        if (i + 1) % 50 == 0:
            print(f"    … {i + 1}/{len(a_faire)}", flush=True)

    suspects = [r for r in resultats if r["motif"]]
    print(f"  -> {len(suspects)} suspects sur {len(resultats)} "
          f"({len(suspects) / max(1, len(resultats)):.1%})", flush=True)
    return {"personnage": cle, "clips": len(resultats), "suspects": len(suspects),
            "resultats": resultats,
            "repliques_sans_clip": [l["clip"] for _, l in absents]}


def selftest(cle: str) -> int:
    """Prouve que le détecteur détecte, sur un clip SAIN qu'on abîme exprès.

    Un contrôle qui ne rend jamais de suspect est indiscernable d'un contrôle en panne — le
    dépôt en a déjà payé plusieurs. On fabrique donc les deux verdicts sur le même fichier :
    intact il doit passer, tronqué à 45 % il doit être pris, et la fin manquante nommée.
    """
    perso = _perso(cle)
    lignes = [l for l in _lignes(cle)
              if (perso["sortie"] / f"{l['clip']}.ogg").exists()
              and len(mots(l["texte"])) >= 12]
    if not lignes:
        print("aucun clip assez long pour le test", file=sys.stderr)
        return 1
    ligne = lignes[0]
    chemin = perso["sortie"] / f"{ligne['clip']}.ogg"

    intact = couverture(ligne["texte"], transcrire(chemin))
    print(f"intact    ratio {intact['ratio']:.0%} queue {intact['queue']:.0%} "
          f"motif « {motif(intact) or 'aucun'} »")

    duree = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(chemin)], capture_output=True, text=True,
        check=True).stdout.strip())
    with tempfile.TemporaryDirectory() as tmp:
        coupe = Path(tmp) / "coupe.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(chemin), "-t",
                        f"{duree * 0.45:.2f}", str(coupe)], check=True)
        tronque = couverture(ligne["texte"], transcrire(coupe))
    print(f"tronqué   ratio {tronque['ratio']:.0%} queue {tronque['queue']:.0%} "
          f"motif « {motif(tronque) or 'aucun'} »")

    ok = (not motif(intact)) and "fin manquante" in motif(tronque)
    print(f"texte attendu : {ligne['texte']}")
    print("SELFTEST " + ("OK" if ok else "ÉCHEC — le détecteur ne détecte pas"))
    return 0 if ok else 1


SEUIL_DUREE_TRONQUE = 0.75      # durée réelle / durée attendue en dessous de laquelle il
                                # manque vraiment du son, et pas seulement des mots au
                                # transcripteur
# Au-dessus de ce rapport, le clip contient du son que le texte ne demande pas : baragouin
# avant la réplique, syllabe étirée, silence installé au milieu. Calibré sur les 697 clips des
# dix voix récentes, dont la médiane est à 1,01 et le p95 à 1,84 — à 2,2 on prend les 5 clips
# les plus longs du lot, et les quatre premiers sont des défauts manifestes (10,7 s de
# baragouin pour huit mots, 23,0 s pour vingt-cinq). Les six clips entre 2,0 et 2,2 sont
# laissés : ils disent tout leur texte, lentement, et régénérer sur un doute dégrade au tirage.
SEUIL_DUREE_TRAINE = 2.2
MOTS_MINIMUM_DUREE = 8          # sous ce compte, la durée attendue est trop imprécise : une
                                # exclamation de deux mots dure mécaniquement trois fois
                                # « ce qu'il faut »


def verdict_croise(r: dict) -> str:
    """Confronte le verdict ASR à la DURÉE du clip. Sans ce croisement, le tri est inversé.

    Mesuré sur les dix voix récentes : sur 42 clips que l'ASR déclarait incomplets, 37 disaient
    en réalité tout leur texte — whisper francise les noms propres du projet (« les Twin
    Horns » entendu « les Twinornes », « Helen Shard » entendu « Elinchard »). Régénérer sur le
    seul verdict ASR aurait donc refait 37 clips sains pour en réparer 5.

    Un clip réellement tronqué est aussi trop COURT pour son texte ; un clip qui déraille est
    trop LONG. Deux mesures indépendantes qui doivent tomber d'accord.
    """
    if r["attendus"] < MOTS_MINIMUM:
        return "trop court pour juger"
    rd = r["duree"] / r["duree_attendue"] if r.get("duree_attendue") else 1.0
    if r["entendus"] == 0:
        return "MUET (à regénérer)"
    # Le radotage AVANT la couverture, et l'ordre n'est pas cosmétique : un clip peut être les
    # deux à la fois, et c'est même le cas typique. `reynolds_34b01b500e` émet dix secondes de
    # syllabes inventées PUIS la moitié de sa réplique — le tester d'abord sur la couverture le
    # classait « fin manquante, durée normale », c'est-à-dire à écouter, alors que c'est le clip
    # le plus abîmé du lot.
    if r["entendus"] > SEUIL_RADOTAGE * r["attendus"] and rd > 1.3:
        return "RADOTAGE (à regénérer)"
    if r["attendus"] >= MOTS_MINIMUM_DUREE and rd > SEUIL_DUREE_TRAINE:
        return "TRAÎNE (à regénérer)"
    if r["ratio"] < SEUIL_COUVERTURE and rd < SEUIL_DUREE_TRONQUE:
        return "TRONQUÉ (à regénérer)"
    if r["ratio"] < SEUIL_COUVERTURE:
        return "à écouter (durée normale)"
    return "sain"


def relire(chemin: Path) -> int:
    """Réimprime un rapport d'audit, durée à l'appui, sans retranscrire quoi que ce soit."""
    import voix_personnage

    rapport = json.loads(chemin.read_text(encoding="utf-8"))
    a_regenerer, a_ecouter = [], []
    for voix in rapport["voix"]:
        perso = voix_personnage._perso(voix["personnage"])
        for r in voix["resultats"]:
            if "duree" not in r:
                clip = perso["sortie"] / f"{r['clip']}.ogg"
                r["duree"] = round(duree(clip), 2) if clip.exists() else 0.0
                r["duree_attendue"] = round(duree_attendue(r["texte"]), 2)
            r["verdict"] = verdict_croise(r)
            if "regénérer" in r["verdict"]:
                a_regenerer.append(r)
            elif r["motif"]:
                a_ecouter.append(r)

    for titre, lot in (("À REGÉNÉRER", a_regenerer), ("À ÉCOUTER (verdict incertain)",
                                                      a_ecouter)):
        print(f"\n{titre} — {len(lot)} clips")
        print("-" * 100)
        for r in sorted(lot, key=lambda r: r["ratio"]):
            print(f"{r['clip']:22s} {r['ratio']:4.0%} mots  "
                  f"{r['duree']:5.1f}s / {r['duree_attendue']:4.1f}s attendues  "
                  f"{r['verdict']}")
            print(f"    attendu : {r['texte']}")
            print(f"    entendu : {r['entendu']}")

    chemin.write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    par_voix = {}
    for voix in rapport["voix"]:
        for r in voix["resultats"]:
            if "regénérer" in r["verdict"]:
                par_voix[voix["personnage"]] = par_voix.get(voix["personnage"], 0) + 1
    print(f"\n{len(a_regenerer)} clips à regénérer, {len(a_ecouter)} à écouter")
    for nom, n in sorted(par_voix.items(), key=lambda kv: -kv[1]):
        print(f"  {nom:10s} {n}")
    return 0


def _score(ratio: float, rd: float) -> float:
    """Qualité d'un clip en un seul nombre : le texte dit, moins l'excès de durée.

    La pénalité ne mord qu'au-delà de 1,3× la durée attendue — en dessous, un débit lent est un
    choix de jeu, pas un défaut. Un clip complet et de durée juste vaut 1,00 ; le même à 2,7×
    tombe à 0,30, donc sous n'importe quel essai correct.
    """
    return ratio - 0.5 * max(0.0, rd - 1.3)


def regenerer(rapport_chemin: Path, essais: int = 4, limite: int = 0) -> int:
    """Régénère sur d'autres graines les clips que le rapport dit tronqués, et REVÉRIFIE.

    Le critère de reprise est celui qui a détecté le défaut — la couverture du texte — et pas
    l'énergie spectrale : `voix_personnage.py reprendre` garde le meilleur essai au sens du
    timbre, ce qui n'a aucune raison de rendre un clip plus complet. Deux critères, deux
    reprises ; les mêmes graines de secours (7000 + n · 613) pour n'en pas inventer une
    troisième famille.

    Le nouveau clip n'est écrit QUE s'il fait mieux que celui en place : une reprise qui
    n'améliore rien ne doit pas remplacer un fichier déjà livré, sinon un lot relancé dégrade
    au hasard des tirages.

    « Mieux » ne peut PAS être la seule couverture, et la première version de cette fonction a
    échoué là-dessus : `vincent_49f4b1b2cf` (23,0 s pour 8,6 s attendues) et `alice_0b41a2d2b3`
    (11,2 s pour 4,2 s) disaient déjà 92 % de leur texte — aucun essai ne pouvait battre ça, la
    fonction annonçait « 92 % -> 92 % OK » et laissait les deux clips en place, intacts. Le
    défaut à réparer était la DURÉE. Le score pénalise donc l'excès de durée, et le critère
    d'arrêt exige les deux : texte complet ET durée plausible.
    """
    import bench_qwen3tts as mesures
    import voix_personnage
    import qwen3tts
    from descente_voix import descendre

    rapport = json.loads(rapport_chemin.read_text(encoding="utf-8"))
    a_faire, portes = [], {}
    for voix in rapport["voix"]:
        perso = voix_personnage._perso(voix["personnage"])
        par_clip = {l["clip"]: l for l in voix_personnage._lignes(perso)}
        # LA PORTE D'ÉNERGIE DU LOT EN PLACE, et elle n'est pas une précaution théorique.
        # Réparer le texte peut casser le timbre : sur les dix voix récentes, deux des neuf
        # clips repris pour leur texte (`reynolds_f3e53b7bf1`, `alice_f46cf74e82`) sont
        # ressortis complets mais HORS BANDE, et c'est `voix_personnage.py verifier` qui les a
        # signalés après coup. Un essai n'est donc accepté que s'il tient les deux critères,
        # au seuil exact de `_douteux` — la moitié de la médiane du rôle.
        clips_roles = voix_personnage._clips_presents(perso, voix_personnage._lignes(perso))
        _, medianes, cibles = voix_personnage._douteux(perso, clips_roles, mesures)
        portes[voix["personnage"]] = (medianes, cibles)
        for r in voix["resultats"]:
            v = r.get("verdict") or verdict_croise(r)
            if "regénérer" not in v:
                continue
            ligne = par_clip.get(r["clip"])
            if ligne is None:
                print(f"    {r['clip']:22s} absent de lines.json — ignoré")
                continue
            a_faire.append((voix["personnage"], perso, ligne, r))
    if limite:
        a_faire = a_faire[:limite]
    print(f"{len(a_faire)} clips à regénérer, {essais} essais chacun", flush=True)
    if not a_faire:
        return 0

    modele = qwen3tts._charge("customvoice")
    sauves, restants = 0, []
    for cle, perso, ligne, r in a_faire:
        medianes, cibles = portes[cle]
        role = ligne["role"]
        cible_hz = cibles.get(role, next(iter(cibles.values())))
        plancher = 0.5 * medianes.get(role, next(iter(medianes.values())))
        chemin = perso["sortie"] / f"{ligne['clip']}.ogg"
        attendue = duree_attendue(ligne["texte"])
        # Le score de départ se MESURE sur le fichier en place, énergie comprise : le rapport
        # d'audit ne porte que le texte et la durée, si bien qu'un clip hors bande y affichait
        # un score parfait — et aucun essai ne pouvait alors le battre. Deux clips sont restés
        # « encore défectueux » pour cette seule raison, alors que les essais étaient bons.
        part_en_place = voix_personnage._part_bande(chemin, cible_hz) if chemin.exists() else 0.0
        depart = (_score(r["ratio"], r["duree"] / attendue)
                  - (0.0 if part_en_place >= plancher else 1.0))
        meilleur, meilleure = None, depart
        detail = f"{r['ratio']:.0%}/{r['duree'] / attendue:.1f}x"
        # Le verdict de sortie se prononce sur les DEUX critères d'origine, pas sur le score :
        # celui-ci mélange un taux et une pénalité, il ordonne les essais et rien de plus.
        # Comparer un score à un seuil de couverture avait fait déclarer « encore défectueux »
        # un clip ramené de 2,7x à 1,8x, c'est-à-dire sous le seuil qui l'avait signalé.
        accepte = False
        for n in range(essais):
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                       voix_personnage._instruct(qwen3tts, ligne),
                                       perso["timbre"], seed=7000 + n * 613,
                                       temperature=0.7)
            onde = descendre(onde, perso.get("grave_demi_tons", 0.0), modele.sample_rate)
            essai = chemin.with_suffix(".essai.ogg")
            qwen3tts._ecrit(onde, modele.sample_rate, essai, "ogg")
            mesure = couverture(ligne["texte"], transcrire(essai))
            rd = duree(essai) / attendue
            part = voix_personnage._part_bande(essai, cible_hz)
            essai.unlink()
            # Un essai hors bande est écarté quel que soit son texte : le remède ne doit pas
            # créer l'autre défaut. S'il n'y en a aucun dans la bande, on ne remplace rien.
            score = _score(mesure["ratio"], rd) - (0.0 if part >= plancher else 1.0)
            if score > meilleure:
                meilleur, meilleure = onde, score
                detail = f"{mesure['ratio']:.0%}/{rd:.1f}x/énergie {part:.0%}"
                accepte = (mesure["ratio"] >= SEUIL_COUVERTURE
                           and rd <= SEUIL_DUREE_TRAINE and part >= plancher)
            if (mesure["ratio"] >= SEUIL_COUVERTURE and rd <= SEUIL_DUREE_TRAINE
                    and part >= plancher and score >= meilleure):
                break
        if meilleur is not None:
            qwen3tts._ecrit(meilleur, modele.sample_rate, chemin, "ogg")
        bon = accepte
        etat = "OK" if bon else "encore défectueux"
        if bon:
            sauves += 1
        else:
            restants.append(chemin.stem)
        print(f"    {chemin.stem:22s} score {depart:5.2f} -> {meilleure:5.2f}  "
              f"({detail})  {etat}", flush=True)
    del modele
    print(f"\n{sauves}/{len(a_faire)} récupérés"
          + (f", restants : {', '.join(restants)}" if restants else ""))
    return 0


def main() -> int:
    import voix_personnage

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personnages", nargs="*", help="clés de PERSONNAGES, ex. alice reynolds")
    ap.add_argument("--tous", action="store_true", help="tous les personnages déclarés")
    ap.add_argument("--limite", type=int, default=0, help="ne réécouter que N clips par voix")
    ap.add_argument("--bavard", action="store_true", help="imprimer aussi les clips sains")
    ap.add_argument("--selftest", action="store_true",
                    help="vérifier le détecteur sur un clip sain puis tronqué")
    ap.add_argument("--sortie", type=Path, default=MEDIA / "scratch" / "audit_texte.json")
    ap.add_argument("--relire", type=Path,
                    help="réimprimer un rapport déjà produit, durée à l'appui, sans ASR")
    ap.add_argument("--regenerer", type=Path, metavar="RAPPORT",
                    help="reprendre les clips que ce rapport déclare tronqués")
    ap.add_argument("--essais", type=int, default=4, help="graines de secours par clip")
    args = ap.parse_args()

    if args.relire:
        return relire(args.relire)
    if args.regenerer:
        return regenerer(args.regenerer, args.essais, args.limite)

    cles = sorted(voix_personnage.PERSONNAGES) if args.tous else args.personnages
    if not cles:
        ap.error("nommer au moins un personnage, ou --tous")
    inconnus = [c for c in cles if c not in voix_personnage.PERSONNAGES]
    if inconnus:
        ap.error(f"personnage inconnu : {', '.join(inconnus)}")

    if args.selftest:
        return selftest(cles[0])

    rapports = [auditer(c, args.limite, args.bavard) for c in cles]
    total = sum(r["clips"] for r in rapports)
    suspects = sum(r["suspects"] for r in rapports)
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(
        {"seuils": {"couverture": SEUIL_COUVERTURE, "queue": SEUIL_QUEUE,
                    "radotage": SEUIL_RADOTAGE, "mots_minimum": MOTS_MINIMUM},
         "voix": rapports}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{suspects} suspects sur {total} clips "
          f"({suspects / max(1, total):.1%}) — {args.sortie}")
    for r in rapports:
        print(f"  {r['personnage']:10s} {r['suspects']:4d}/{r['clips']:<5d}"
              + (f"  ({len(r['repliques_sans_clip'])} répliques sans clip)"
                 if r["repliques_sans_clip"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
