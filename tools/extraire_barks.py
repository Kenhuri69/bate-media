#!/usr/bin/env python3
"""Transforme `bate/resources/combat_barks.json` en lignes de forge, comme une timeline.

    python3 tools/extraire_barks.py
    python3 tools/extraire_barks.py --dry-run
    python3 tools/extraire_barks.py --selftest

POURQUOI UN OUTIL DE PLUS. `extraire_repliques.py` lit les timelines Dialogic ; les répliques de
combat n'y sont pas, et n'y seront jamais — elles sont déclenchées par l'état du combat, pas par
un tour de dialogue. Mais elles obéissent au MÊME contrat : le jeu appellera
`AudioManager.PlayVoice("Ennemi", texte)`, qui calcule `ennemi_<empreinte du texte>`. La voix des
ennemis se produit donc avec la chaîne habituelle (`voix_personnage.py livrer ennemi`) sans qu'un
seul octet de code audio soit ajouté au jeu.

Le champ `chapitre` reçoit la CATÉGORIE (`ouverture`, `touche`, `critique`…) : c'est ce que la
forge utilise comme étiquette de lot, et cela rend le rapport de livraison lisible par situation
de jeu plutôt que par numéro de chapitre, qui n'a aucun sens ici.
"""
import argparse
import json
import sys
from pathlib import Path

RACINE = Path.home() / "workspace"
BARKS = RACINE / "bate/resources/combat_barks.json"
FORGE = RACINE / "voice-agent/training/forge"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from empreinte import clip_id  # noqa: E402


def lignes_de(source: dict) -> list:
    """Une ligne de forge par réplique, dans l'ordre des catégories déclarées."""
    locuteur = source.get("_locuteur", "Ennemi")
    sortie, vus = [], set()
    for categorie, bloc in source["categories"].items():
        for i, texte in enumerate(bloc["lignes"], 1):
            texte = texte.strip()
            ident = clip_id(locuteur, texte)
            if ident is None or ident in vus:
                continue                     # deux catégories peuvent partager une réplique
            vus.add(ident)
            sortie.append({"id": f"{categorie}_{i:02d}", "chapitre": categorie,
                           "texte": texte, "texte_brut": texte, "role": locuteur,
                           "source": "combat_barks.json", "registre": "colere"})
    return sortie


def _selftest() -> int:
    ok = True

    def check(nom, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'OK ' if cond else 'ECHEC'}] {nom}")

    source = {"_locuteur": "Ennemi", "categories": {
        "touche": {"lignes": ["Aïe ! Sale gosse !", "Aïe ! Sale gosse !"]},
        "vaincu": {"lignes": ["Non... pas comme ça..."]}}}
    l = lignes_de(source)
    check("une réplique en double ne produit qu'une ligne", len(l) == 2)
    check("la catégorie sert d'étiquette de lot",
          {x["chapitre"] for x in l} == {"touche", "vaincu"})
    check("texte et texte_brut sont identiques (aucune balise dans un bark)",
          all(x["texte"] == x["texte_brut"] for x in l))
    check("l'identifiant est celui que le jeu demandera",
          clip_id("Ennemi", "Aïe ! Sale gosse !").startswith("ennemi_"))
    # Le registre compte : un bark dit sur le ton de la conversation ne fait pas un combat.
    check("le registre de jeu est la colère", all(x["registre"] == "colere" for x in l))
    print("auto-test extraire_barks :", "OK" if ok else "ECHEC")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", default="bate-ennemi")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    if not BARKS.exists():
        print(f"ressource introuvable : {BARKS}", file=sys.stderr)
        return 1
    source = json.loads(BARKS.read_text(encoding="utf-8"))
    lignes = lignes_de(source)
    par_cat = {}
    for l in lignes:
        par_cat[l["chapitre"]] = par_cat.get(l["chapitre"], 0) + 1
    print(f"{len(lignes)} répliques · " + " · ".join(f"{k} {v}" for k, v in par_cat.items()))
    if args.dry_run:
        for l in lignes[:5]:
            print(f"    [{l['chapitre']:10s}] {clip_id(l['role'], l['texte'])}  « {l['texte']} »")
        print("(dry-run) rien écrit")
        return 0
    dossier = FORGE / args.slug
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "request.json").write_text(json.dumps(
        {"demande": "voix générique des ennemis de combat (BATE)",
         "roles": [source.get("_locuteur", "Ennemi")],
         "source": "bate/resources/combat_barks.json"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    (dossier / "lines.json").write_text(json.dumps(lignes, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(f"écrit : {dossier / 'lines.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
