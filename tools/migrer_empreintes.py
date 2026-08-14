#!/usr/bin/env python3
"""Renomme les clips de la convention POSITIONNELLE vers la convention d'EMPREINTE.

    python3 tools/migrer_empreintes.py --dry-run
    python3 tools/migrer_empreintes.py
    python3 tools/migrer_empreintes.py --personnage Tessia --roles Tessia --slug bate-tessia

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

DEUX OUTILS FONT CETTE MIGRATION, ET LE CHOIX ENTRE EUX N'EST PAS UNE PRÉFÉRENCE.
`reconcile_voices.py` s'applique quand le lien entre un fichier et son texte est **perdu** : il
le RECONSTITUE par le compte de répliques puis la durée, ce qui est une présomption et se
termine à l'oreille. Celui-ci s'applique quand ce lien est **conservé** — `lines.json` est
l'extraction qui a produit les clips, elle dit ce que chacun prononce — et il ne devine donc
rien. À lien conservé, ne pas se rabattre sur la présomption : ce serait jeter une preuve pour
un indice. Les deux implémentations de l'empreinte ont été confrontées sur les 4401 clips livrés,
elles rendent le même identifiant partout.
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
ANCIEN_NOM = re.compile(r"^[a-z0-9]+_ch\d+[a-z]*_\d+$")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empreinte import clip_id, dossier_de_voix, normalise_texte, role_du_locuteur  # noqa: E402

# Arthur reste le défaut : c'est le lot pour lequel cet outil a été écrit, et le seul dont la
# migration positionnelle -> empreinte ait réellement eu lieu. Les autres personnages n'ont
# jamais eu de clips à l'ancienne convention — pour eux, ce script ne migre rien et ne fait
# que la seconde moitié de son travail : nommer par l'empreinte et reconstruire le manifeste.
PERSONNAGE_DEFAUT = "Arthur"
ROLES_DEFAUT = ("Arthur", "Note", "narrator")
SLUG_DEFAUT = "bate-arthur"
# Même filtre que `check_voices.py` côté jeu : commentaires, événements et libellés de choix ne
# sont pas des répliques.
REPLIQUE = re.compile(r"^([A-Za-zÀ-ÿ][\w '\-À-ÿ]*)\s*:\s*(.+)$")


def correspondances(lignes_json: Path, roles: tuple, max_chapitre: int) -> tuple[dict, dict, list, list]:
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
    lignes = json.loads(lignes_json.read_text(encoding="utf-8"))
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
            if not mm or mm.group(1) not in roles:
                continue
            ident = clip_id(mm.group(1), mm.group(2))
            if ident:
                demandes.setdefault(ident, (mm.group(2), timeline.stem))

    caducs = sorted(set(a_dire) - set(demandes))
    dans_perimetre = {i for i, (_, stem) in demandes.items()
                      if int(re.search(r"\d+", stem).group()) <= max_chapitre}
    manquants = sorted(dans_perimetre - set(a_dire))
    return a_dire, demandes, caducs, manquants


MAX_CHAPITRE = 60


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--personnage", default=PERSONNAGE_DEFAUT,
                    help="nom affiché dans le manifeste (défaut : Arthur)")
    ap.add_argument("--roles", default=",".join(ROLES_DEFAUT),
                    help="noms EXACTS écrits dans les timelines, séparés par des virgules ; "
                         "plusieurs rôles ne partagent une voix que s'ils sont le même "
                         "personnage (Arthur/Note/narrator)")
    ap.add_argument("--slug", default=SLUG_DEFAUT, help="dossier de forge")
    ap.add_argument("--max-chapitre", type=int, default=MAX_CHAPITRE,
                    help="périmètre livré, pour le seul décompte des manquants")
    args = ap.parse_args()

    roles = tuple(r.strip() for r in args.roles.split(",") if r.strip())
    lignes_json = RACINE / f"voice-agent/training/forge/{args.slug}/lines.json"
    # Le dossier de voix se DÉDUIT du rôle par la même règle que le jeu, il ne se choisit
    # pas : `AudioManager` cherche `voice/<dossier>/<id>`, et un dossier inventé ici
    # produirait un pack complet que personne n'appelle — construit sans erreur, muet en jeu.
    voix = MEDIA / "voices" / dossier_de_voix(role_du_locuteur(roles[0]))
    if not lignes_json.exists():
        print(f"extraction introuvable : {lignes_json}", file=sys.stderr)
        return 1
    if not voix.is_dir():
        print(f"dossier de voix absent : {voix} — lancer la production d'abord",
              file=sys.stderr)
        return 1

    presents = {p.stem for p in voix.glob("*.ogg")}
    a_dire, demandes, caducs, manquants = correspondances(lignes_json, roles,
                                                          args.max_chapitre)
    print(f"{len(presents)} clips présents dans {voix.relative_to(MEDIA)}")
    print(f"{len(a_dire)} textes distincts enregistrés (après fusion des répliques identiques)")
    print(f"{len(demandes)} répliques demandées par les timelines ch0-{args.max_chapitre}")
    print(f"  caducs   (texte enregistré que plus personne ne dit) : {len(caducs)}")
    print(f"  manquants (réplique sans voix)                       : {len(manquants)}")

    if args.dry_run:
        for nouveau, (ancien, texte, ch) in list(a_dire.items())[:5]:
            etat = "ok" if nouveau in demandes else "CADUC"
            print(f"  {ancien:24s} -> {nouveau:22s} [{ch}] {etat} « {texte[:44]} »")
        return 0

    renommes, doublons, absents = 0, 0, 0
    for nouveau, (ancien, _, _) in a_dire.items():
        src, dst = voix / f"{ancien}.ogg", voix / f"{nouveau}.ogg"
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
    restants = [p for p in voix.glob("*.ogg") if ANCIEN_NOM.match(p.stem)]
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
        p = voix / f"{nouveau}.ogg"
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
    # Une seule entrée de manifeste est réécrite : celle de ce personnage. Les autres voix du
    # pack ne sont pas relues, donc pas menacées par une exécution ciblée.
    manifeste["voix"][voix.name] = {
        "nom": args.personnage, "repliques": len(fichiers), "format": "ogg",
        "convention": "voice-fingerprint-1.0", "moteur_par_defaut": "qwen3-tts",
        "fichiers": fichiers,
    }
    chemin.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(caducs)} clips caducs retirés (texte réécrit depuis la production)")
    print(f"manifeste reconstruit : {len(fichiers)} entrées, convention voice-fingerprint-1.0")
    print(f"couverture ch0-{args.max_chapitre} : {len(fichiers)}/{len(fichiers) + len(manquants)} "
          f"({len(fichiers) / max(len(fichiers) + len(manquants), 1):.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
