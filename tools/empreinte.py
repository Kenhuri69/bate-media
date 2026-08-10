#!/usr/bin/env python3
"""La règle d'empreinte des répliques, côté forge — miroir Python de `VoiceLines.cs`.

    python3 tools/empreinte.py --selftest      # rejoue les vecteurs partagés du jeu

Un clip s'appelle `<rôle>_<empreinte du texte>`. L'identifiant ne porte AUCUNE position, et
c'est tout l'intérêt : la convention précédente nommait les clips par leur rang
(`narrator_ch00_07`), si bien qu'insérer une réplique en amont périmait silencieusement toutes
les suivantes. C'est ce qui est arrivé au pack 0.3.0 quand les chapitres 0 à 9 ont été
réécrits — le fichier attendu existait toujours, il disait simplement autre chose. Une réplique
déplacée garde désormais son clip ; une réplique modifiée perd le sien et se tait : un manque
visible et régénérable à l'unité, au lieu d'un décalage inaudible.

CETTE RÈGLE EST ÉCRITE DEUX FOIS, DANS DEUX DÉPÔTS — ici en Python, dans `VoiceLines.cs` en C#.
Une divergence d'un seul espace rend le jeu muet **sans lever d'erreur** : la clé cherchée
n'existe simplement pas. D'où sa définition minimale et le `--selftest`, qui rejoue les vecteurs
que le jeu publie (`bate/resources/voice_fingerprints.json`). Le lancer après toute retouche,
et refuser de produire un pack s'il échoue.

Trois opérations de normalisation, pas une de plus :
  * **NFC** — « é » composé et « e + accent » sont le même caractère prononcé ;
  * **toute suite de blancs → une espace** — un `.dtl` réindenté ne doit pas périmer un clip ;
  * **coupe des bords**.

Casse, accents et ponctuation sont CONSERVÉS : ils changent ce qui est dit ou la façon de le
dire, donc deux textes qui n'en diffèrent que méritent deux enregistrements.

⚠️ L'empreinte se calcule sur la ligne **BRUTE** de la timeline, marqueurs Dialogic compris —
c'est ce que fait le jeu (`VoiceLine.gd` lit `event.text`, `check_voices.py` lit le texte après
les deux-points). La forge, elle, retire ces marqueurs avant de synthétiser : ils ne se
prononcent pas. Les deux textes sont donc distincts et c'est voulu — l'identifiant désigne la
LIGNE, l'audio dit sa partie prononçable. Sur les ch0-60, 2 répliques sur 4464 sont concernées.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
import unittest
from pathlib import Path

LONGUEUR_EMPREINTE = 10
VECTEURS = Path.home() / "workspace/bate/resources/voice_fingerprints.json"


def normalise_texte(texte: str) -> str:
    """Forme normalisée d'une réplique avant empreinte. Miroir de `VoiceLines.NormalizeText`."""
    if not texte or not texte.strip():
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", texte)).strip()


def empreinte(texte: str) -> str:
    """Les 10 premiers caractères hexadécimaux du SHA-256 de la forme normalisée."""
    normalise = normalise_texte(texte)
    if not normalise:
        return ""
    return hashlib.sha256(normalise.encode("utf-8")).hexdigest()[:LONGUEUR_EMPREINTE]


def role_du_locuteur(nom: str) -> str:
    """« Alice Leywin » -> « alice ». Miroir de `VoiceLines.Role`."""
    sortie = []
    for c in unicodedata.normalize("NFD", nom or ""):
        if unicodedata.combining(c):
            continue
        if c.isspace() or c in "'-_":
            if sortie:
                break
            continue
        if c.isalnum():
            sortie.append(c.lower())
    return "".join(sortie)


def clip_id(locuteur: str, texte: str):
    """`<rôle>_<empreinte>`, ou None s'il manque le locuteur ou le texte."""
    role = role_du_locuteur(locuteur)
    emp = empreinte(texte)
    return f"{role}_{emp}" if role and emp else None


class Contrat(unittest.TestCase):
    """Le contrat avec le jeu, rejoué depuis SES vecteurs — pas depuis des cas réécrits ici.

    Réécrire les cas de test dans ce dépôt reviendrait à vérifier que la forge est d'accord avec
    elle-même. Ce qu'il faut prouver est l'accord avec l'AUTRE implémentation, et les vecteurs
    qu'elle publie sont le seul point de contact qui ne puisse pas dériver en silence.
    """

    def test_vecteurs_partages(self):
        if not VECTEURS.exists():
            self.skipTest(f"vecteurs absents ({VECTEURS}) — dépôt du jeu non disponible")
        donnees = json.loads(VECTEURS.read_text(encoding="utf-8"))
        for v in donnees["vecteurs"]:
            with self.subTest(cas=v["cas"]):
                self.assertEqual(normalise_texte(v["texte"]), v["normalise"])
                self.assertEqual(empreinte(v["texte"]), v["empreinte"])

    def test_texte_vide(self):
        for vide in ("", "   ", "\n\t", None):
            self.assertEqual(empreinte(vide), "")
            self.assertIsNone(clip_id("narrator", vide))

    def test_role_sans_locuteur(self):
        self.assertIsNone(clip_id("", "Une réplique."))
        self.assertIsNone(clip_id("???", "Une réplique."))

    def test_roles_groupes_gardent_leur_propre_id(self):
        # « Note » et « narrator » sortent du dossier d'Arthur mais portent leur propre rôle :
        # c'est le DOSSIER qui les regroupe, pas l'identifiant.
        self.assertTrue(clip_id("Note", "x.").startswith("note_"))
        self.assertTrue(clip_id("narrator", "x.").startswith("narrator_"))
        self.assertEqual(clip_id("Note", "x.")[5:], clip_id("narrator", "x.")[9:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="rejoue les vecteurs partagés")
    ap.add_argument("--texte", help="afficher l'empreinte d'un texte")
    args = ap.parse_args()

    if args.texte:
        print(f"{empreinte(args.texte)}  « {normalise_texte(args.texte)} »")
        return 0
    if args.selftest:
        resultat = unittest.TextTestRunner(verbosity=2).run(
            unittest.TestLoader().loadTestsFromTestCase(Contrat))
        return 0 if resultat.wasSuccessful() else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
