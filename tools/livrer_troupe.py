#!/usr/bin/env python3
"""Extrait puis produit les répliques de TOUS les personnages de troupe, d'un seul appel.

    ../.venv-mlx/bin/python tools/livrer_troupe.py --dry-run
    ../.venv-mlx/bin/python tools/livrer_troupe.py
    ../.venv-mlx/bin/python tools/livrer_troupe.py --seulement juge,eleve

Quatre-vingt-treize figurants, quatre-vingt-treize dossiers de forge : à la main, c'est une
matinée de commandes et une chance sur deux d'en oublier un. Cet outil ne fait rien de neuf — il
appelle `extraire_repliques` puis `voix_personnage.livrer` pour chaque personnage déclaré dans
`resources/casting_troupe.json` — mais il le fait pour tous, et il DIT ce qu'il a sauté.

Le modèle est chargé UNE FOIS pour tout le lot. Quatre-vingt-treize chargements de cinq secondes
feraient huit minutes de pure attente, et surtout : décharger puis recharger entre deux
personnages, c'est rendre puis reprendre les vingt gigaoctets de poids à chaque fois.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
FORGE = RACINE / "voice-agent/training/forge"
REGISTRE = MEDIA / "resources" / "casting_troupe.json"
sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from descente_voix import descendre  # noqa: E402
from empreinte import dossier_du_locuteur  # noqa: E402


def a_produire() -> list:
    """`[(clé, fiche)]` des personnages de troupe qui ont une voix attribuée."""
    import voix_personnage

    registre = json.loads(REGISTRE.read_text(encoding="utf-8"))
    lot = []
    for nom, fiche in registre["personnages"].items():
        if not fiche.get("timbre"):
            continue
        cle = dossier_du_locuteur(nom)
        if cle not in voix_personnage._TROUPE_AJOUTEE:
            print(f"  ignoré : {nom} (dossier « {cle} » déjà tenu par une voix castée)")
            continue
        lot.append((cle, fiche))
    return lot


def extraire(cle: str, fiche: dict, dry_run: bool) -> bool:
    """Crée la forge du personnage et en extrait les répliques. Vrai si `lines.json` est prêt."""
    slug = f"bate-{cle}"
    dossier = FORGE / slug
    if dry_run:
        return (dossier / "lines.json").exists()
    dossier.mkdir(parents=True, exist_ok=True)
    if not (dossier / "request.json").exists():
        (dossier / "request.json").write_text(json.dumps(
            {"demande": f"personnage de troupe BATE : {fiche['roles'][0]}",
             "roles": fiche["roles"], "archetype": fiche.get("archetype"),
             "source": "resources/casting_troupe.json"},
            ensure_ascii=False, indent=2), encoding="utf-8")
    r = subprocess.run([sys.executable, str(MEDIA / "tools/extraire_repliques.py"), slug,
                        *fiche["roles"]], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    extraction échouée : {r.stderr.strip().splitlines()[-1:]}", flush=True)
        return False
    return (dossier / "lines.json").exists()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seulement", help="liste de clés séparées par des virgules")
    ap.add_argument("--limite", type=int, default=0, help="au plus N clips par personnage")
    args = ap.parse_args()

    import voix_personnage

    lot = a_produire()
    if args.seulement:
        garder = {c.strip() for c in args.seulement.split(",")}
        lot = [(c, f) for c, f in lot if c in garder]
    print(f"{len(lot)} personnages de troupe\n")

    # Phase 1 : les extractions (aucun modèle en mémoire, tout est du texte).
    prets, sans_lignes = [], []
    for cle, fiche in lot:
        (prets if extraire(cle, fiche, args.dry_run) else sans_lignes).append((cle, fiche))
    if sans_lignes:
        print(f"{len(sans_lignes)} sans extraction : "
              + ", ".join(c for c, _ in sans_lignes) + "\n")

    # Phase 2 : ce qui manque, personnage par personnage.
    reste = []
    for cle, fiche in prets:
        perso = voix_personnage._perso(cle)
        lignes = voix_personnage._lignes(perso)
        absents = [l for l in lignes
                   if not (perso["sortie"] / f"{l['clip']}.ogg").exists()
                   or (perso["sortie"] / f"{l['clip']}.ogg").stat().st_size == 0]
        if absents:
            reste.append((cle, perso, absents[:args.limite] if args.limite else absents))
    total = sum(len(a) for _, _, a in reste)
    print(f"{total} clips à générer sur {len(reste)} personnages")
    for cle, _, absents in sorted(reste, key=lambda x: -len(x[2]))[:12]:
        print(f"    {len(absents):4d}  {cle}")
    if args.dry_run:
        print("\n(dry-run) rien généré")
        return 0
    if not total:
        return 0

    import qwen3tts

    modele = qwen3tts._charge("customvoice")
    faits, relances, debut = 0, 0, time.time()
    for cle, perso, absents in reste:
        perso["sortie"].mkdir(parents=True, exist_ok=True)
        for ligne in absents:
            onde, essais = qwen3tts._genere(
                modele, "customvoice", ligne["texte"],
                voix_personnage._instruct(qwen3tts, ligne, perso), perso["timbre"],
                seed=qwen3tts._seed_de(ligne["clip"], 2000), temperature=0.7)
            relances += essais
            qwen3tts._ecrit(voix_personnage._traite(onde, perso, modele.sample_rate),
                            modele.sample_rate, perso["sortie"] / f"{ligne['clip']}.ogg", "ogg")
            faits += 1
            if faits % 25 == 0:
                ecoule = time.time() - debut
                print(f"    {faits}/{total}  ({ecoule / 60:.0f} min, {relances} relances, "
                      f"reste ~{ecoule / faits * (total - faits) / 60:.0f} min)", flush=True)
        print(f"  {cle} terminé ({len(absents)} clips)", flush=True)
    del modele
    print(f"\n{faits} clips en {(time.time() - debut) / 60:.0f} min, {relances} relances")
    print("Contrôler AVANT d'intégrer : voix_personnage.py verifier <clé> et audit_texte.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
