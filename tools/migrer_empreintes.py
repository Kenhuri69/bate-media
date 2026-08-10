#!/usr/bin/env python3
"""Renomme les clips de la convention POSITIONNELLE vers la convention d'EMPREINTE.

    python3 tools/migrer_empreintes.py --dry-run
    python3 tools/migrer_empreintes.py

Le jeu a changé de convention le 2026-08-10 (`bate` PR #333) : un clip s'appelle désormais
`<rôle>_<empreinte du texte>` et non plus `<rôle>_ch<NN>_<II>`. Les 4433 clips des ch0-60
venaient d'être produits sous l'ancienne — huit heures de génération.

**Ils n'ont pas besoin d'être régénérés.** L'empreinte se calcule sur le texte, et le texte est
connu : l'audio ne change pas, seul son nom change.

La correspondance part de `lines.json` — l'extraction qui a PRODUIT ces clips — et surtout PAS
d'un recalcul des rangs depuis les timelines actuelles. Elles ont encore bougé pendant les huit
heures de génération (`chapter_10.dtl` découpé en `10a`/`10b`), si bien qu'un rang recalculé ne
désigne plus la réplique enregistrée. Réintroduire une position dans l'outil qui adopte une
convention sans position serait la faute la plus évitable du lot.

Deux subtilités qui décident de la justesse du résultat.

**L'empreinte porte sur la ligne BRUTE**, marqueurs Dialogic compris, parce que c'est ce que le
jeu calcule (`VoiceLine.gd` lit `event.text`). La forge, elle, les retire avant de synthétiser :
ils ne se prononcent pas. L'identifiant désigne donc la LIGNE et l'audio en dit la partie
prononçable — ce n'est pas une incohérence, c'est la séparation des deux rôles. Sur les ch0-60,
2 répliques sur 4464 sont concernées, et elles ressortent en « manquantes ».

**Deux répliques identiques partagent un clip.** L'empreinte ne dépend que du texte : « ... » ou
« Oui. » dits à dix endroits donnent un seul fichier. C'est voulu — un seul enregistrement suffit
à les dire — mais ça veut dire que le compte de clips descend sous le compte de répliques, et
qu'un pack plus petit n'est pas un pack incomplet.

Ce que le script NE fait pas : produire les voix manquantes. Il dit combien il en reste, ce qui
est déjà ce que l'ancienne convention rendait impossible.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
DIALOGUES = RACINE / "bate/dialogues"
VOIX = MEDIA / "voices/arthur"
LIGNES = RACINE / "voice-agent/training/forge/bate-arthur/lines.json"
ANCIEN_NOM = re.compile(r"^[a-z0-9]+_ch\d+[a-z]*_\d+$")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empreinte import clip_id, normalise_texte, role_du_locuteur   # noqa: E402

ROLES = ("Arthur", "Note", "narrator")
# Même filtre que `check_voices.py` côté jeu : commentaires, événements et libellés de choix ne
# sont pas des répliques.
REPLIQUE = re.compile(r"^([A-Za-zÀ-ÿ][\w '\-À-ÿ]*)\s*:\s*(.+)$")


def correspondances() -> tuple[dict, dict, list, list]:
    """Ce que chaque clip DIT, confronté à ce que le jeu DEMANDE.

    La correspondance ne se recalcule surtout pas depuis les timelines : elles ont encore bougé
    pendant les huit heures de génération — `chapter_10.dtl` a été découpé en `10a`/`10b` — et
    un rang recalculé ne désigne plus la réplique qui a été enregistrée. C'est exactement le
    défaut que la nouvelle convention supprime, il ne faut pas le réintroduire dans l'outil qui
    l'adopte.

    La source de vérité est donc `lines.json`, l'extraction qui a PRODUIT ces clips : elle dit,
    pour chaque identifiant positionnel, le texte réellement synthétisé. L'empreinte de ce
    texte est le nouveau nom, et il est juste même si la réplique a changé de fichier depuis.

    Les timelines ne servent plus qu'à répondre à deux questions de couverture : quels clips ne
    correspondent plus à rien (texte réécrit), et quelles répliques n'ont pas de voix.
    """
    lignes = json.loads(LIGNES.read_text(encoding="utf-8"))
    a_dire = {}                          # nouvel id -> (ancien id, texte, chapitre)
    for l in lignes:
        nouveau = clip_id(l["role"], l["texte"])
        if nouveau is None:
            continue
        a_dire.setdefault(nouveau, (l["id"], l["texte"], l["chapitre"]))

    # Ce que le jeu demande aujourd'hui, à SA règle : empreinte de la ligne BRUTE.
    demandes = {}
    for timeline in sorted(DIALOGUES.glob("*.dtl")):
        # AUCUNE borne de chapitre ici, et c'est important : un clip dont le texte a migré
        # vers un chapitre au-delà de la plage produite passerait pour caduc alors qu'il est
        # demandé. La borne ne vaut que pour compter ce qui MANQUE dans le périmètre livré.
        m = re.search(r"(\d+)", timeline.stem)
        if not m:
            continue
        for ligne in timeline.read_text(encoding="utf-8").splitlines():
            s = ligne.strip()
            if not s or s.startswith("#") or s.startswith("[") or s.startswith("- "):
                continue
            mm = REPLIQUE.match(s)
            if not mm or mm.group(1) not in ROLES:
                continue
            ident = clip_id(mm.group(1), mm.group(2))
            if ident:
                demandes.setdefault(ident, (mm.group(2), timeline.stem))

    caducs = sorted(set(a_dire) - set(demandes))
    dans_perimetre = {i for i, (_, stem) in demandes.items()
                      if int(re.search(r"\d+", stem).group()) <= MAX_CHAPITRE}
    manquants = sorted(dans_perimetre - set(a_dire))
    return a_dire, demandes, caducs, manquants


MAX_CHAPITRE = 60


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    presents = {p.stem for p in VOIX.glob("*.ogg")}
    a_dire, demandes, caducs, manquants = correspondances()
    print(f"{len(presents)} clips présents dans {VOIX.relative_to(MEDIA)}")
    print(f"{len(a_dire)} textes distincts enregistrés (après fusion des répliques identiques)")
    print(f"{len(demandes)} répliques demandées par les timelines ch0-{MAX_CHAPITRE}")
    print(f"  caducs   (texte enregistré que plus personne ne dit) : {len(caducs)}")
    print(f"  manquants (réplique sans voix)                       : {len(manquants)}")

    if args.dry_run:
        for nouveau, (ancien, texte, ch) in list(a_dire.items())[:5]:
            etat = "ok" if nouveau in demandes else "CADUC"
            print(f"  {ancien:24s} -> {nouveau:22s} [{ch}] {etat} « {texte[:44]} »")
        return 0

    renommes, doublons, absents = 0, 0, 0
    for nouveau, (ancien, _, _) in a_dire.items():
        src, dst = VOIX / f"{ancien}.ogg", VOIX / f"{nouveau}.ogg"
        if not src.exists():
            absents += 1
            continue
        if dst.exists():
            src.unlink()                 # même texte déjà nommé : un seul enregistrement suffit
            doublons += 1
            continue
        src.rename(dst)
        renommes += 1
    # Tout ce qui garde un nom positionnel après ça ne correspond à aucun texte de `lines.json`.
    restants = [p for p in VOIX.glob("*.ogg") if ANCIEN_NOM.match(p.stem)]
    for p in restants:
        p.unlink()
    print(f"{renommes} renommés, {doublons} doublons fusionnés, {len(restants)} sans texte retirés"
          + (f", {absents} attendus absents" if absents else ""))

    import hashlib

    def sha(p):
        h = hashlib.sha256()
        with p.open("rb") as f:
            for bloc in iter(lambda: f.read(1 << 20), b""):
                h.update(bloc)
        return h.hexdigest()[:16]

    # Le manifeste porte désormais le TEXTE et le CHAPITRE : l'identifiant ne les dit plus, et
    # sans eux on ne pourrait ni retrouver une réplique à la main ni savoir ce qui reste à
    # doubler. C'est le pendant documentaire d'un identifiant devenu opaque.
    chemin = MEDIA / "manifest.json"
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    fichiers = []
    for nouveau, (_, texte, chapitre) in sorted(a_dire.items()):
        p = VOIX / f"{nouveau}.ogg"
        if not p.exists():
            continue
        if nouveau in caducs:
            # Aucune réplique du jeu ne dit ce texte : l'embarquer alourdirait le pack d'un
            # son que personne ne demandera jamais. Il se refabrique à l'unité si le texte
            # revient — c'est justement ce que la convention d'empreinte rend possible.
            p.unlink()
            continue
        fichiers.append({"id": nouveau, "fichier": p.name, "sha256": sha(p),
                         "moteur": "qwen3-tts", "chapitre": chapitre,
                         "texte": normalise_texte(texte)})
    manifeste["voix"]["arthur"] = {
        "nom": "Arthur", "repliques": len(fichiers), "format": "ogg",
        "convention": "voice-fingerprint-1.0", "moteur_par_defaut": "qwen3-tts",
        "fichiers": fichiers,
    }
    chemin.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(caducs)} clips caducs retirés (texte réécrit depuis la production)")
    print(f"manifeste reconstruit : {len(fichiers)} entrées, convention voice-fingerprint-1.0")
    print(f"couverture ch0-{MAX_CHAPITRE} : {len(fichiers)}/{len(fichiers) + len(manquants)} "
          f"({len(fichiers) / max(len(fichiers) + len(manquants), 1):.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
