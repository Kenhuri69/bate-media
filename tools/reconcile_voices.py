#!/usr/bin/env python3
"""Remet un dossier de voix à la convention par empreinte, et écarte ce qui n'est plus valide.

    python3 tools/reconcile_voices.py --chapitre chapter_00            # annonce, n'écrit rien
    python3 tools/reconcile_voices.py --chapitre chapter_00 --appliquer
    python3 tools/reconcile_voices.py --tout --appliquer               # tous les chapitres
    python3 tools/reconcile_voices.py --selftest

CE QUE CET OUTIL PEUT ET NE PEUT PAS FAIRE — à lire avant de s'y fier.

Les clips de la 0.3.0 s'appellent `<rôle>_ch<NN>_<II>` : leur nom donne la PLACE d'une réplique,
jamais son texte. Aucun manifeste, ici ou dans le pack, ne conserve ce qui est prononcé. Le lien
entre un fichier et sa réplique est donc **perdu**, et rien ne peut le rétablir avec certitude
depuis ce dépôt.

Ce qui reste : une hypothèse et une mesure. L'hypothèse est que le clip n° II dit la II-ᵉ
réplique de ce rôle dans la timeline. La mesure est la DURÉE : un enregistrement de parole dure,
au débit de la forge, à peu près `len(texte) / 14` secondes. Quand les deux concordent à
quelques pour cent, l'hypothèse tient ; quand le clip dure moitié moins que son texte, elle est
fausse et le fichier est écarté.

C'EST UNE PRÉSOMPTION, PAS UNE PREUVE. Un clip retenu ici a une durée compatible avec son texte,
ce qui n'exclut pas qu'il dise autre chose d'une longueur voisine. La table imprimée en fin
d'exécution existe pour ça : elle donne clip et texte côte à côte, pour un contrôle à l'oreille
qui, lui, tranche. Rien de ce que l'outil écarte n'est perdu — la Release v0.3.0 garde tout.

Une fois la reprise faite, cette incertitude disparaît pour de bon : les clips régénérés
porteront l'empreinte de leur texte, et `bate/tools/checks/check_voices.py` répondra par oui ou
par non, sans mesurer quoi que ce soit.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from empreinte import (JEU, REPLIQUE, chemin_relatif, clip_id,  # noqa: E402
                       repliques_du_chapitre, role_du_locuteur)

RACINE = Path(__file__).resolve().parent.parent
VOIX = RACINE / "voices"

# Débit de la forge, en caractères par seconde (`qwen3tts.py` : `attendue = len(texte) / 14`).
CAR_PAR_SECONDE = 14.0
# Écart relatif maximal accepté entre durée mesurée et durée attendue. 0,30 n'est pas un réglage
# arbitraire : sur le chapitre 0, les six premiers clips tombent entre 0 et 24 % et le septième
# saute à 47 %. Le seuil se pose dans ce vide, pas au milieu d'un continuum.
ECART_MAX = 0.30

ANCIEN = __import__("re").compile(r"^(?P<role>[a-z0-9]+)_ch(?P<chapitre>\d+)_(?P<rang>\d+)$")
NOUVEAU = __import__("re").compile(r"^(?P<role>[a-z0-9]+)_(?P<empreinte>[0-9a-f]{10})$")


def duree_ogg(chemin: Path) -> float:
    """Durée d'un Ogg Vorbis, sans décodeur : dernière position de granule / fréquence."""
    data = chemin.read_bytes()
    i = data.find(b"\x01vorbis")
    j = data.rfind(b"OggS")
    if i < 0 or j < 0:
        return 0.0
    frequence = struct.unpack_from("<I", data, i + 12)[0]
    granule = struct.unpack_from("<q", data, j + 6)[0]
    return granule / frequence if frequence else 0.0


def duree_attendue(texte: str) -> float:
    return max(0.6, len(texte) / CAR_PAR_SECONDE)


def examiner(dossier: Path, chapitres: list[str]) -> tuple[list, list]:
    """(à renommer, à écarter). Chaque entrée porte de quoi justifier la décision."""
    # Répliques du jeu, par rôle et par rang, pour les chapitres considérés.
    par_role_rang: dict = {}
    valides: set = set()
    for chapitre in chapitres:
        rangs: dict = {}
        for r in repliques_du_chapitre(chapitre):
            rangs[r["role"]] = rangs.get(r["role"], 0) + 1
            par_role_rang[(r["role"], chapitre, rangs[r["role"]])] = r
            valides.add(r["id"])

    # Combien de répliques par (rôle, chapitre) — pour confronter les COMPTES avant les durées.
    total_par_role: dict = {}
    for (role, chapitre, _), _r in par_role_rang.items():
        total_par_role[(role, chapitre)] = total_par_role.get((role, chapitre), 0) + 1
    clips_par_role: dict = {}
    for clip in sorted(dossier.rglob("*.ogg")):
        v = ANCIEN.match(clip.stem)
        if v:
            cle = (v.group("role"), f"chapter_{int(v.group('chapitre')):02d}")
            clips_par_role[cle] = clips_par_role.get(cle, 0) + 1

    a_renommer, a_ecarter = [], []
    for clip in sorted(dossier.rglob("*.ogg")):
        nom = clip.stem
        neuf = NOUVEAU.match(nom)
        if neuf:
            # Déjà à la convention : on le garde s'il correspond encore à une réplique.
            if nom in valides:
                continue
            a_ecarter.append((clip, "aucune réplique ne dit ce texte", None))
            continue

        vieux = ANCIEN.match(nom)
        if not vieux:
            a_ecarter.append((clip, "nom hors de toute convention connue", None))
            continue

        role = vieux.group("role")
        chapitre = f"chapter_{int(vieux.group('chapitre')):02d}"
        if chapitre not in chapitres:
            continue          # hors du périmètre demandé : on n'y touche pas
        # LE COMPTE D'ABORD, LA DURÉE ENSUITE. Toute l'identification repose sur une hypothèse :
        # « le clip n° II dit la II-ᵉ réplique ». Si le nombre de clips d'un couple (rôle,
        # chapitre) ne fait pas le nombre de répliques, cette hypothèse est réfutée EN BLOC —
        # les rangs ne désignent plus les mêmes lignes, et une durée qui concorderait encore ne
        # serait qu'une coïncidence. Écarter tout le couple est alors la seule lecture honnête.
        attendus, presents = total_par_role.get((role, chapitre), 0), clips_par_role[(role, chapitre)]
        if attendus != presents:
            a_ecarter.append((clip, f"numérotation réfutée : {presents} clips pour {attendus} "
                                    f"répliques de « {role} » dans {chapitre}", None))
            continue

        replique = par_role_rang.get((role, chapitre, int(vieux.group("rang"))))
        if replique is None:
            a_ecarter.append((clip, f"la timeline {chapitre} n'a pas de {vieux.group('rang')}ᵉ "
                                    f"réplique pour « {role} »", None))
            continue

        mesuree = duree_ogg(clip)
        attendue = duree_attendue(replique["texte"])
        ecart = abs(mesuree - attendue) / attendue
        if ecart > ECART_MAX:
            a_ecarter.append((clip, f"durée incompatible : {mesuree:.1f} s pour un texte de "
                                    f"{attendue:.1f} s ({ecart * 100:.0f} % d'écart)", replique))
        else:
            a_renommer.append((clip, replique, mesuree, attendue, ecart))
    return a_renommer, a_ecarter


def executer(dossier: Path, chapitres: list[str], appliquer: bool) -> int:
    a_renommer, a_ecarter = examiner(dossier, chapitres)
    prefixe = "" if appliquer else "[annonce] "

    if a_renommer:
        print(f"\n{len(a_renommer)} clip(s) retenus — durée compatible avec leur réplique.")
        print("À CONTRÔLER À L'OREILLE : la durée présume, elle ne prouve pas.\n")
        print(f"  {'clip d’origine':22} {'durée':>7} {'attendu':>8} {'écart':>6}  réplique")
        for clip, replique, mesuree, attendue, ecart in a_renommer:
            print(f"  {clip.stem:22} {mesuree:6.1f}s {attendue:7.1f}s {ecart * 100:5.0f}%  "
                  f"« {replique['texte'][:52]} »")
            print(f"  {'→ ' + replique['chemin']:22}")

    if a_ecarter:
        print(f"\n{len(a_ecarter)} clip(s) écartés — leur réplique n'est plus identifiable.")
        for clip, raison, _ in a_ecarter:
            print(f"  {clip.stem:22} {raison}")

    if not appliquer:
        print(f"\n{prefixe}rien n'a été écrit. Relancer avec --appliquer.")
        return 0

    for clip, replique, *_ in a_renommer:
        cible = dossier / replique["chemin"]
        cible.parent.mkdir(parents=True, exist_ok=True)
        clip.rename(cible)
    for clip, _, _ in a_ecarter:
        clip.unlink()

    print(f"\n{len(a_renommer)} renommé(s), {len(a_ecarter)} supprimé(s).")
    print("Rien n'est perdu : la Release v0.3.0 conserve le pack d'origine intact.")
    return 0


def selftest() -> int:
    ok = True

    def verifie(nom: str, condition: bool) -> None:
        nonlocal ok
        print(f"  {'ok  ' if condition else 'ÉCHEC'} {nom}")
        ok = ok and condition

    verifie("reconnaît l'ancienne convention",
            ANCIEN.match("narrator_ch00_07").group("rang") == "07")
    verifie("reconnaît la nouvelle convention",
            NOUVEAU.match("narrator_9f3a1c4b2e").group("empreinte") == "9f3a1c4b2e")
    verifie("ne confond pas les deux",
            NOUVEAU.match("narrator_ch00_07") is None
            and ANCIEN.match("narrator_9f3a1c4b2e") is None)
    verifie("durée attendue proportionnelle au texte",
            abs(duree_attendue("x" * 140) - 10.0) < 0.01)
    verifie("durée attendue plancher sur un texte très court",
            duree_attendue("x") == 0.6)
    verifie("le seuil se pose dans le vide mesuré au ch0", 0.24 < ECART_MAX < 0.47)

    print("selftest :", "OK" if ok else "ÉCHEC")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapitre", action="append", default=[],
                    help="timeline à traiter, ex. chapter_00 (répétable)")
    ap.add_argument("--tout", action="store_true", help="tous les chapitres du jeu")
    ap.add_argument("--voix", default=str(VOIX), help=f"dossier de voix (défaut : {VOIX})")
    ap.add_argument("--appliquer", action="store_true", help="écrit vraiment")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    dossier = Path(args.voix).expanduser()
    if not dossier.exists():
        print(f"dossier de voix introuvable : {dossier}", file=sys.stderr)
        return 1

    chapitres = args.chapitre
    if args.tout:
        chapitres = sorted(p.stem for p in (JEU / "dialogues").glob("chapter_*.dtl"))
    if not chapitres:
        print("préciser --chapitre chapter_00 ou --tout", file=sys.stderr)
        return 1

    return executer(dossier, chapitres, args.appliquer)


if __name__ == "__main__":
    sys.exit(main())
