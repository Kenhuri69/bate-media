#!/usr/bin/env python3
"""Production des répliques d'un personnage de BATE — à lancer avec .venv-mlx.

    ../.venv-mlx/bin/python tools/voix_personnage.py livrer    arthur
    ../.venv-mlx/bin/python tools/voix_personnage.py verifier  arthur
    ../.venv-mlx/bin/python tools/voix_personnage.py reprendre arthur
    ../.venv-mlx/bin/python tools/voix_personnage.py etalonner arthur --limite 40

Le chemin de production STANDARDISÉ, et le seul : une voix par personnage, la même du premier
chapitre au dernier, histoires secondaires comprises. Il remplace `voix_tessia.py` (dont il est
le renommage) pour Tessia et `voix_age_arthur.py livrer` pour Arthur.

DEUX CHOSES ONT DISPARU AVEC LUI, ET C'EST LE FOND DU CHANGEMENT.

**La déclinaison par âge.** Arthur portait un prompt d'âge par stade sur ses répliques parlées,
qui faisait varier sa voix au fil du récit. La mesure disait déjà que ce levier ne crée un
registre distinct qu'au stade bambin (+48 Hz à trois ans) et que les stades ne se distinguent
pas entre eux — au-delà, les formulations essayées apportaient -6, +4, -21 et +17 Hz, du bruit,
signes compris. Il est retiré : le timbre validé et le registre de rôle, rien d'autre.

**Le nom positionnel, et l'étape de migration qui allait avec.** Les clips étaient produits sous
leur identifiant de forge (`arthur_ch11_02`) puis renommés par `migrer_empreintes.py`. Un lot
relancé ne reconnaissait donc plus ce qu'il avait déjà fait — les clips en service portent le nom
d'empreinte, celui que la reprise cherchait n'existait plus — et REGÉNÉRAIT TOUT. Ici le clip
naît directement sous le nom que le jeu lui demandera (`empreinte.clip_id`), si bien que
« ce qui est déjà là est déjà bon » se lit sur le disque, sans intermédiaire.

Corollaire : ce script ne produit JAMAIS deux fois la même réplique, et n'écrase jamais un clip
existant. Pour refaire un lot pour de bon, effacer les fichiers concernés d'abord.

**Le contrôle qualité n'est pas optionnel.** Sur les 4433 premiers clips d'Arthur, 486 sont
sortis défectueux (11,0 %) — énergie spectrale au mauvais endroit, voix qui part dans les aigus
ou s'effondre — et 481 ont été récupérés en régénérant sur d'autres graines. Livrer sans
`verifier` puis `reprendre`, c'est livrer un clip sur neuf inécoutable, et le défaut ne se voit
pas dans un log : il s'entend.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(RACINE / "voice-agent/training"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from empreinte import (clip_id, dossier_de_voix, dossier_du_locuteur,  # noqa: E402
                       role_du_locuteur)
from descente_voix import _comprimer_wsola, descendre  # noqa: E402


def _traite(onde, perso: dict, sr: int):
    """Décalage de hauteur puis DÉBIT — le post-traitement d'un personnage, en un seul endroit.

    Le débit est le troisième axe de distinction des voix, après le timbre et la hauteur, et le
    dernier qui ne coûte aucun calcul de modèle : WSOLA change la durée sans toucher au
    fondamental. Il a été ouvert quand la mesure a montré qu'il ne restait que quatre places
    masculines libres et zéro féminine — deux personnages au même timbre et à la même hauteur
    restent distincts s'ils ne parlent pas à la même vitesse.

    Un seul endroit, parce que `livrer` et `reprendre` appliquaient déjà `descendre` chacun de
    son côté : ajouter le débit deux fois aurait fini par produire des clips repris sans lui,
    au milieu d'un lot qui l'a — et rien ne l'aurait signalé.
    """
    y = descendre(onde, perso.get("grave_demi_tons", 0.0) or 0.0, sr)
    debit = float(perso.get("debit", 1.0) or 1.0)
    return y if debit == 1.0 else _comprimer_wsola(y, debit, sr)

# --- casting ------------------------------------------------------------------
# Le timbre de chaque personnage, sa date de validation à l'oreille, et la cible du contrôle
# d'énergie. `cibles` vaut None quand la F0 mesurée du lot est utilisable ; un dictionnaire
# rôle -> Hz quand elle ne l'est pas (cf. `_cible`).
PERSONNAGES = {
    "arthur": {
        "nom": "Arthur",
        "slug": "bate-arthur",
        # « Note » est son pseudonyme d'aventurier et le jeu est narré à la première personne :
        # les trois rôles sortent du même timbre, sinon le personnage change de voix en jeu.
        # « Arthur et Reynolds » est une anomalie d'écriture — un libellé pour deux personnes,
        # une seule réplique dans tout le jeu (« On s'entraîne. », ch38). Le premier mot l'envoie
        # déjà dans le dossier d'Arthur ; l'ajouter ici est ce qui fait qu'elle est EXTRAITE,
        # donc produite. Sans ça, elle reste muette et aucun contrôle ne la réclame.
        "roles": ("Arthur", "Note", "narrator", "Arthur et Reynolds"),
        "timbre": "aiden:0.5+ryan:0.5",       # validé à l'oreille le 2026-08-08
        # Écrites en dur, et SURTOUT PAS remplacées par la F0 mesurée : sur les répliques
        # parlées d'Arthur l'autocorrélation rend ~140 Hz alors que la bande dominante est bien
        # plus haut — elle divise le fondamental par deux, et recentrer le contrôle dessus le
        # ferait regarder SOUS la voix.
        #
        # Confirmées par `etalonner` le 2026-08-15 (concentration d'énergie, 100 clips/rôle) :
        # parlé 6,2 à 205 Hz contre 6,0 à 175 et 4,6 à 240 ; narration 10,5 à 132 contre 11,2 à
        # 110 et 9,9 à 150. Les deux valeurs sont sur le PLATEAU de leur courbe. `Arthur` sort à
        # 205 et `Note` à 175 pour 0,1 d'écart : c'est du bruit, pas deux registres — ils
        # partagent donc une seule cible, comme ils partagent une seule voix.
        "cibles": {"narrator": 132.0, "*": 205.0},
    },
    "tessia": {
        "nom": "Tessia",
        "slug": "bate-tessia",
        "roles": ("Tessia", "Tessia Eralith"),
        "timbre": "sohee",                    # balayage de doses du 2026-08-14 : le pur gagne
        "cibles": None,                       # F0 croyable sur ce timbre (0,02 % sous 150 Hz)
    },
    "virion": {
        "nom": "Virion",
        "slug": "bate-virion",
        "roles": ("Virion", "Virion Eralith"),
        # `uncle_fu` est le SEUL timbre masculin qu'Arthur n'utilise pas — CustomVoice n'en a
        # que trois et son mélange en consomme deux. Le casting (lot 11) le donne aussi comme
        # le plus éloigné d'Arthur au cosinus des MFCC (0,949 contre 0,965 et 0,975), ce qui
        # est LE critère ici : deux voix d'hommes confondues dans un dialogue à deux coûtent
        # plus cher à la scène qu'un timbre un peu moins juste.
        # RÉSERVE LEVÉE PAR LA MESURE, ET CONTRE LE PREMIER CHOIX. `uncle_fu` pur a été produit
        # (350 clips, 1,1 h) puis ÉCARTÉ sur ses propres chiffres :
        #   F0 médiane 201,7 Hz — soit 14 Hz de Tessia (215,3), sa petite-fille adolescente,
        #   avec qui il partage toutes ses scènes de cour ;
        #   plage interdécile 79 Hz — le lot le plus dispersé des quatre voix du jeu
        #   (Arthur narration 34, Tessia 44, Arthur parlé 57).
        # Le casting l'avait retenu parce qu'il maximisait la distance à Arthur. Il s'en
        # éloignait bien : PAR LE HAUT, donc en atterrissant sur Tessia. Une distance à une
        # seule référence ne mesure pas la confusion, elle en déplace la cible.
        #
        # Le balayage de doses contre les DEUX références donne le compromis : à parts égales
        # avec `aiden`, la plage tombe de 70 à 32 Hz et la F0 à 134 — registre masculin franc,
        # plus aucune collision avec Tessia. Ce qu'on perd est la séparation d'avec Arthur, qui
        # ne passe plus par la hauteur (134 contre 130) mais par le timbre (0,963). C'est
        # acceptable ici et nulle part ailleurs : Virion ne narre jamais, et l'essentiel de la
        # voix d'Arthur est de la narration, à 117 Hz et dans un tout autre registre de jeu.
        #
        # La contrainte de fond, à ne pas oublier : CustomVoice n'a que TROIS timbres masculins
        # utilisables et Arthur en consomme deux. Il n'y a pas de quatrième voix d'homme à
        # trouver — un quatrième personnage masculin devra partager ou changer de moteur.
        "timbre": "uncle_fu:0.5+aiden:0.5",
        # LE TIMBRE NE SUFFIT PAS, ET LE MODÈLE NE SAIT PAS COMPLÉTER. À 130 Hz, Virion parle
        # exactement à la hauteur d'Arthur (131 Hz en parlé, 119 en narration) pour un
        # personnage de plusieurs siècles. Les six consignes « vieil homme » essayées montent
        # toutes la F0 au lieu de la descendre (+1 à +16 Hz), et aucun des trois timbres
        # masculins de CustomVoice ne descend sous 130 Hz.
        #
        # On descend donc le signal de 3 demi-tons — 130 Hz devient 109 Hz, sous Arthur au lieu
        # d'être sur lui — À DURÉE CONSTANTE : ralentir a été refusé, et la compression WSOLA
        # rend la durée sans remonter la hauteur. Validé à l'écoute le 2026-08-17 (lot 13).
        "grave_demi_tons": 3.0,
        # Étalonnée à 150 Hz sur le lot AVANT descente (6,5 de concentration contre 6,1 à 132
        # et 5,4 à 205). La descente de 3 demi-tons la déplace du même rapport : 150 / 2^(3/12)
        # = 126 Hz. Ne PAS laisser 150 ici — le contrôle chercherait l'énergie une tierce
        # au-dessus de la voix et signalerait des clips sains, exactement le piège déjà payé sur
        # les narrations d'Arthur (13 clips sur 13 déclarés défectueux par une cible fausse).
        "cibles": {"*": 126.0},
    },
"sylvie": {
	        "nom": "Sylvie",
	        "slug": "bate-sylvie",
	        "roles": ("Sylvie",),
	        # ⚠️ SIX RÉPLIQUES NE MESURENT PAS UNE DISPERSION, et ce casting l'a payé deux fois.
	        # Premier verdict, sur l'échantillon de 6 du casting : `vivian:0.7+serena:0.3` battait
	        # ses deux composants (plage 66 Hz, Tessia 0,866). Les 111 clips produits dessus sont
	        # sortis à **98 Hz de plage** — le double des autres voix du jeu (Tessia 52, Virion 46,
	        # Arthur 45), pire que le `uncle_fu` écarté chez Virion — avec 10 relances du garde-fou
	        # anti-dégénérescence sur 111 clips, contre 0 pour Tessia et Virion.
	        #
	        # Rebalayé sur 20 répliques, tout le classement change, parce que le chiffre à 6
	        # sous-estimait la plage d'un facteur ~2 POUR TOUT LE MONDE : `serena` pur passe de 29
	        # à 56 Hz. Une grandeur mesurée sur un échantillon trop petit ne se contente pas d'être
	        # imprécise, elle réordonne les candidats.
	        #
	        # Verdict à 20 répliques, contre DEUX références (Tessia d'abord : c'est avec elle
	        # qu'on risque de confondre Sylvie, elles partagent la plupart de leurs scènes) :
	        #   ono_anna:0.5+serena:0.5   plage 57 Hz   Tessia 0,922   ← retenu, DOMINE
	        #   serena pur                plage 56 Hz   Tessia 0,942
	        #   vivian:0.3+serena:0.7     plage 62 Hz   Tessia 0,932
	        #   vivian:0.5+serena:0.5     plage 75 Hz   Tessia 0,932
	        # Le retenu n'est pas un compromis : il est aussi stable que le plus stable ET le plus
	        # éloigné de Tessia. Il n'y a pas d'arbitrage à faire, donc pas de regret à avoir.
	        "timbre": "ono_anna:0.5+serena:0.5",
	        "cibles": None,
	    },
	    "alice": {
	        "nom": "Alice",
	        "slug": "bate-alice",
	        "roles": ("Alice",),
	        # Mère d'Arthur, healer (Emitter), voix douce et maternelle.
	        # `vivian` pur : timbre féminin non utilisé comme principal ailleurs,
	        # distinct de Tessia (sohee) et Sylvie (ono_anna+serena).
	        "timbre": "vivian",
	        # Validé par etalonner : concentration max à 270 Hz
	        "cibles": {"*": 270.0},
	    },
	    "reynolds": {
	        "nom": "Reynolds",
	        "slug": "bate-reynolds",
	        "roles": ("Reynolds",),
	        # Père d'Arthur, ancien aventurier, voix masculine mature.
	        # `uncle_fu:0.5+ryan:0.5` : plus grave qu'Arthur (aiden+ryan),
	        # distinct de Virion (uncle_fu+aiden -3st).
	        # Ryan (161 Hz) + uncle_fu donne un registre père ~30-40 ans.
	        "timbre": "uncle_fu:0.5+ryan:0.5",
	        # Validé par etalonner : concentration max à 205 Hz
	        "cibles": {"*": 205.0},
	    },
	    "jasmine": {
	        "nom": "Jasmine",
	        "slug": "bate-jasmine",
	        "roles": ("Jasmine", "Jasmine Flamesworth"),
	        # Dagues jumelles, taciturne, froide. Mix serena+vivian -2st (WSOLA)
	        # pour un registre plus grave/froid, distinct de Tessia (sohee pur),
	        # Alice (vivian pur), Sylvie (ono_anna+serena). serena/ vivian restent purs dispo.
	        "timbre": "serena:0.6+vivian:0.4",
	        "grave_demi_tons": 2.0,
	        "cibles": None,
	    },
	    "angela": {
	        "nom": "Angela",
	        "slug": "bate-angela",
	        "roles": ("Angela", "Angela Rose"),
	        # Conjureuse vent, joyeuse. Mix sohee dominant + ono_anna +2st (WSOLA)
	        # Registre plus aigu/venté, sohee/ono_anna purs dispo pour futurs persos.
	        "timbre": "sohee:0.7+ono_anna:0.3",
	        "grave_demi_tons": -2.0,
	        "cibles": None,
	    },
	    "helen": {
	        "nom": "Helen",
	        "slug": "bate-helen",
	        "roles": ("Helen", "Helen Shard"),
	        # Archère demi-elfe, perçante. Mix ono_anna+serena -1st (WSOLA)
	        # Registre net/perçant, distinct de Sylvie (ono_anna+serena sans shift).
	        # ono_anna/serena purs dispo pour futurs persos.
	        "timbre": "ono_anna:0.5+serena:0.5",
	        "grave_demi_tons": 1.0,
	        "cibles": None,
	    },
	    "adam": {
	        "nom": "Adam",
	        "slug": "bate-adam",
	        "roles": ("Adam", "Adam Krensh"),
	        # Lance, énergique, taquin. Mix ryan+aiden +1st (WSOLA)
	        # Registre juvénile/énergique, distinct de Reynolds (uncle_fu+ryan),
	        # Arthur (aiden+ryan). ryan/aiden purs dispo pour futurs persos.
	        "timbre": "ryan:0.7+aiden:0.3",
	        "grave_demi_tons": -1.0,
	        # 217 Hz, ET NON 205. Les 205 Hz avaient été étalonnés sur le lot livré, qui ne
	        # portait AUCUNE montée : `descendre()` renvoyait l'onde intacte pour tout demi-ton
	        # négatif (corrigé le 2026-08-26). Le décalage étant désormais appliqué, la cible se
	        # déplace du même rapport — 205 × 2^(1/12) = 217 Hz. Laisser 205 ferait chercher
	        # l'énergie sous la voix et signalerait des clips sains, exactement le piège déjà
	        # payé sur les narrations d'Arthur et sur la descente de Virion.
	        "cibles": {"*": 217.0},
	    },
	    "durden": {
	        "nom": "Durden",
	        "slug": "bate-durden",
	        "roles": ("Durden", "Durden Walker"),
	        # Conjureur terre, géant doux. Le mix uncle_fu+aiden sort trop aigu.
	        # On applique une descente de 5 demi-tons (WSOLA, durée constante)
	        # pour le placer en registre grave homme ~134 Hz → ~112 Hz.
	        "timbre": "uncle_fu:0.8+aiden:0.2",
"grave_demi_tons": 5.0,
		        # Validé par etalonner AVANT descente : 380 Hz → après 5st = 380/2^(5/12) ≈ 268 Hz
		        "cibles": {"*": 268.0},
		    },
	    "vincent": {
	        "nom": "Vincent",
	        "slug": "bate-vincent",
	        "roles": ("Vincent",),
	        # Marchand Helstea, ami de Reynolds, père de Lilia. Homme mature ~35-40 ans.
	        # Mix uncle_fu+aiden -2st (WSOLA) pour registre mature/amical.
	        # uncle_fu/aiden purs dispo pour futurs persos.
	        "timbre": "uncle_fu:0.6+aiden:0.4",
	        "grave_demi_tons": 2.0,
	        # Validé par etalonner : concentration max à 150 Hz
	        "cibles": {"*": 150.0},
	    },
	    "lilia": {
	        "nom": "Lilia",
	        "slug": "bate-lilia",
	        "roles": ("Lilia",),
	        # Fille de Vincent/Tabitha, même âge qu'Arthur, s'éveille mage.
	        # Mix sohee+serena -1st (WSOLA) pour registre adolescent lumineux/ancré.
	        # sohee/serena purs dispo pour futurs persos.
	        "timbre": "sohee:0.6+serena:0.4",
	        "grave_demi_tons": 1.0,
	        "cibles": None,
	    },
	    # --- les dix principales féminines de ch1-100 -------------------------------------------
	    # SIX PLACES POUR DIX PERSONNAGES, et ce n'est pas un renoncement : c'est ce que vingt
	    # candidates mesurées ont donné. Elles couvraient tout le registre, sur les trois axes
	    # (timbre, hauteur, débit) ; quatorze ont été refusées pour proximité avec l'une des
	    # trente-trois voix féminines déjà en service. Quatre timbres féminins ne font pas
	    # quarante voix, et l'axe débit — qui a triplé l'espace masculin — ne suffit pas ici.
	    #
	    # Les six places vont aux six personnages dont le REGISTRE colle, et non aux six plus
	    # bavards : Sylvia est une dragonne ancienne, lui donner la place la plus aiguë pour la
	    # seule raison qu'elle parle beaucoup aurait été absurde. Les quatre restants partagent
	    # une voix d'archétype de troupe choisie pour son registre, ce qui est déclaré ici et
	    # dans `docs/casting-troupe.md` — pas caché derrière un timbre inventé.
	    "sylvia": {
	        "nom": "Sylvia", "slug": "bate-sylvia", "roles": ("Sylvia",),
	        # La dragonne : la place la plus grave et la plus posée du lot (203 Hz, plage 20 Hz,
	        # débit ralenti). C'est la seule des dix dont le registre l'exigeait vraiment.
	        "timbre": "serena:0.8+sohee:0.2", "grave_demi_tons": 3.0, "debit": 0.92,
	        "cibles": None,
	    },
	    "goodsky": {
	        "nom": "Goodsky", "slug": "bate-goodsky",
	        "roles": ("Goodsky", "Directrice Goodsky"),
	        # 170 répliques, la plus bavarde des dix. Directrice de l'Académie : autorité, débit
	        # vif — elle tranche et passe à la suite. Les deux libellés partagent son dossier via
	        # la table `LOCUTEURS` d'empreinte.py, sans quoi la moitié de ses répliques serait
	        # restée muette quel que soit le lot produit.
	        "timbre": "serena:0.65+ono_anna:0.35", "grave_demi_tons": 2.0, "debit": 1.08,
	        "cibles": None,
	    },
	    "claire": {
	        "nom": "Claire", "slug": "bate-claire",
	        "roles": ("Claire", "Claire Bladeheart"),
	        # Lance de Dicathen : la place la plus STABLE des vingt candidates (13 Hz de plage),
	        # ce qui convient à un personnage qui ne s'emporte jamais.
	        "timbre": "sohee:0.8+vivian:0.2", "grave_demi_tons": -1.0, "debit": 0.92,
	        "cibles": None,
	    },
	    "glory": {
	        "nom": "Professeur Glory", "slug": "bate-glory", "roles": ("Professeur Glory",),
	        # 54 Hz de plage, la plus dispersée des six retenues — assumé pour une professeure qui
	        # joue beaucoup en cours. À surveiller au contrôle : si le lot livré dépasse 70 Hz,
	        # c'est le piège de Sylvie qui recommence et il faudra changer de place.
	        "timbre": "vivian:0.5+serena:0.3+ono_anna:0.2", "grave_demi_tons": 0.0, "debit": 0.92,
	        "cibles": None,
	    },
	    "alea": {
	        "nom": "Alea Triscan", "slug": "bate-alea", "roles": ("Alea Triscan",),
	        "timbre": "vivian:0.6+ono_anna:0.2+sohee:0.2", "grave_demi_tons": -2.0, "debit": 1.08,
	        "cibles": None,
	    },
	    "kathyln": {
	        "nom": "Kathyln", "slug": "bate-kathyln",
	        "roles": ("Kathyln", "Kathlyn Glayder"),
	        # Princesse adolescente : la place la plus claire (283 Hz). Les deux orthographes du
	        # nom vivent dans les timelines — coquille jamais corrigée, réunie par `LOCUTEURS`.
	        "timbre": "ono_anna:0.5+vivian:0.5", "grave_demi_tons": -3.0, "debit": 0.92,
	        "cibles": None,
	    },
	    # LES QUATRE QUI PARTAGENT, faute de place. Chacune prend l'archétype de troupe dont le
	    # registre correspond : le timbre est juste, il n'est simplement pas exclusif.
	    "rinia": {
	        "nom": "Rinia", "slug": "bate-rinia", "roles": ("Rinia", "Elder Rinia"),
	        # Voyante âgée : l'archétype « f_autorite » (176 Hz) est le plus grave du jeu, et
	        # c'est exactement son registre. Partagé avec neuf figurants qu'elle ne croise pas.
	        "timbre": "sohee:0.65+serena:0.35", "grave_demi_tons": 3.0,
	        "partage": "f_autorite", "cibles": None,
	    },
	    "nima": {
	        "nom": "Nima Orsel", "slug": "bate-nima", "roles": ("Nima Orsel",),
	        "timbre": "serena:0.4+vivian:0.4+sohee:0.2", "grave_demi_tons": 3.0,
	        "partage": "f_mure", "cibles": None,
	    },
	    "tabitha": {
	        "nom": "Tabitha", "slug": "bate-tabitha", "roles": ("Tabitha",),
	        # Mère de Lilia : l'archétype adulte (243 Hz).
	        "timbre": "serena:0.4+vivian:0.4+sohee:0.2", "grave_demi_tons": 1.0,
	        "partage": "f_adulte", "cibles": None,
	    },
	    "emily": {
	        "nom": "Emily", "slug": "bate-emily", "roles": ("Emily",),
	        # Élève : l'archétype jeune (268 Hz).
	        "timbre": "ono_anna:0.65+vivian:0.35", "grave_demi_tons": -2.0,
	        "partage": "f_jeune", "cibles": None,
	    },
	    "elijah": {
	        "nom": "Elijah",
	        "slug": "bate-elijah",
	        "roles": ("Elijah", "Elijah Knight"),
	        # 232 répliques sur 30 timelines (ch32 → ch248) : le personnage non doublé le plus
	        # bavard du jeu, et le seul de cette vague à avoir eu un casting complet — timbres
	        # purs (lot 21) puis balayage de doses sur 20 répliques réelles (lots 22-24).
	        #
	        # `uncle_fu` pur gagnait sur la distance à Arthur (0,905) mais les purs sont écartés
	        # par principe. Parmi les mélanges, celui-ci domine : plage 61 Hz (la plus basse),
	        # Arthur 0,922, et surtout TESSIA 0,915 — c'est-à-dire plus loin d'elle que d'Arthur.
	        # Le contrôle était nécessaire : à 190 Hz il n'est qu'à 23 Hz sous Tessia, et ils
	        # partagent 60 répliques de scène. C'est le piège payé sur Virion, qui fuyait Arthur
	        # par le haut et atterrissait sur Tessia ; ici il est évité, mesuré.
	        #
	        # Sa hauteur le sépare aussi de tous les autres hommes du jeu (Arthur 131, Vincent 150,
	        # Virion 109, Durden 112) : c'est un adolescent, et il sonne comme tel.
	        "timbre": "uncle_fu:0.8+ryan:0.2",
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # étalonnage PLAT (3,1 à 3,6 de 175 à 380 Hz) : il ne discrimine pas, et son
	        # maximum nominal — 340 Hz — serait absurde pour une voix dont la F0 est à 190. On
	        # retient le plateau cohérent avec la hauteur mesurée.
	        "cibles": {"*": 205.0},
	    },
	    # --- les principaux masculins de ch1-100, castés sur le catalogue mesuré -----------------
	    # Aucun casting individuel pour eux, et c'est un choix argumenté : `catalogue_voix.py` a
	    # mesuré 644 variantes masculines et n'a dégagé que QUATRE places libres au-delà des six
	    # archétypes de troupe et des sept voix en service. Auditionner trois timbres par
	    # personnage aurait redécouvert huit fois la même contrainte. Ce qui décide ici est donc
	    # l'affectation sous contrainte : la place la plus distincte disponible, choisie selon le
	    # registre du personnage. Le verdict d'écoute reste à rendre — la mesure écarte, elle ne
	    # tranche pas.
	    #
	    # LE DÉBIT est ce qui a rendu l'affectation possible : 14 places sans lui, 44 avec. Trente
	    # de ces places ne tiennent QUE par lui, et le seuil de 8 % n'a PAS été calibré à
	    # l'oreille, contrairement au cosinus (0,955, calé sur Luna/Lise accepté et Lise/Ellie
	    # refusé). Les voix ci-dessous privilégient donc les places qui tiennent aussi par le
	    # timbre ou la hauteur.
	    "windsom": {
	        "nom": "Windsom", "slug": "bate-windsom", "roles": ("Windsom",),
	        # Asura, hautain, sans âge : la place la plus grave et la plus stable du catalogue
	        # (109 Hz, plage 10 Hz — la plus faible des 644 variantes mesurées).
	        "timbre": "aiden:0.5+uncle_fu:0.3+ryan:0.2", "grave_demi_tons": 3.0, "debit": 1.08,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic net à 7,4, décroissant ensuite — et c'est exactement sa F0 mesurée (109 Hz)
	        "cibles": {"*": 110.0},
	    },
	    "blaine": {
	        "nom": "Blaine", "slug": "bate-blaine", "roles": ("Blaine", "Blaine Glayder"),
	        # Roi de Sapin : un débit ralenti pour l'autorité, 119 Hz.
	        "timbre": "ryan:0.6+aiden:0.2+uncle_fu:0.2", "grave_demi_tons": 3.0, "debit": 0.92,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic à 4,9
	        "cibles": {"*": 205.0},
	    },
	    "gideon": {
	        "nom": "Gideon", "slug": "bate-gideon", "roles": ("Gideon", "Professeur Gideon"),
	        # Inventeur, parle vite et par-dessus les autres : même timbre que Windsom, trois
	        # demi-tons plus haut (129 Hz) et débit accéléré. Trois demi-tons, c'est le minimum
	        # que je m'autorise entre deux voix de MÊME timbre — en dessous, c'est la même
	        # personne transposée, pas un second comédien.
	        "timbre": "aiden:0.5+uncle_fu:0.3+ryan:0.2", "grave_demi_tons": 0.0, "debit": 1.08,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic net à 5,5
	        "cibles": {"*": 175.0},
	    },
	    "kaspian": {
	        "nom": "Kaspian", "slug": "bate-kaspian", "roles": ("Kaspian",),
	        "timbre": "ryan:0.6+aiden:0.2+uncle_fu:0.2", "grave_demi_tons": 0.0, "debit": 0.92,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic à 4,9
	        "cibles": {"*": 205.0},
	    },
	    "lucas": {
	        "nom": "Lucas", "slug": "bate-lucas", "roles": ("Lucas",),
	        # Élève arrogant : débit pressé, 152 Hz.
	        "timbre": "aiden:0.8+uncle_fu:0.2", "grave_demi_tons": 0.0, "debit": 1.08,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic net à 5,7
	        "cibles": {"*": 175.0},
	    },
	    "feyrith": {
	        "nom": "Feyrith", "slug": "bate-feyrith", "roles": ("Feyrith",),
	        "timbre": "ryan:0.6+aiden:0.2+uncle_fu:0.2", "grave_demi_tons": -3.0, "debit": 1.0,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic à 3,5
	        "cibles": {"*": 270.0},
	    },
	    "perrin": {
	        "nom": "Perrin", "slug": "bate-perrin", "roles": ("Perrin",),
	        # ⚠ 181 Hz, à NEUF hertz d'Elijah (190) — la paire la plus serrée de cette vague, et
	        # les deux sont camarades de classe d'Arthur, donc ils se croisent. Les timbres
	        # diffèrent nettement (ryan dominant contre uncle_fu dominant) et c'est ce qui la fait
	        # passer au critère. À écouter EN PREMIER : si la confusion s'entend, c'est cette
	        # voix-là qu'il faut changer.
	        "timbre": "ryan:0.5+uncle_fu:0.3+aiden:0.2", "grave_demi_tons": -2.0, "debit": 1.0,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # pic à 3,7
	        "cibles": {"*": 205.0},
	    },
	    "curtis": {
	        "nom": "Curtis", "slug": "bate-curtis", "roles": ("Curtis", "Curtis Glayder"),
	        # Prince adolescent : la place la plus claire du catalogue masculin (219 Hz), à
	        # 29 Hz au-dessus d'Elijah dont il partage le timbre de base.
	        "timbre": "uncle_fu:0.8+ryan:0.2", "grave_demi_tons": -3.0, "debit": 1.0,
	        	        # Cible ÉTALONNÉE, et non mesurée par F0 : à cette hauteur, plus de 5 % de
	        # l'énergie passe sous 150 Hz et `_cible` REFUSE alors de rendre une valeur —
	        # elle signalerait des clips sains, comme sur les narrations d'Arthur (13 sur
	        # 13 déclarés défectueux par une cible fausse). Tous les masculins du dépôt en
	        # déclarent une pour cette raison.
	        # étalonnage CROISSANT jusqu'à 440 Hz, donc sans pic exploitable : on prend le
	        # premier plateau au-dessus de sa F0 (219 Hz).
	        "cibles": {"*": 240.0},
	    },
	    "ennemi": {
	        "nom": "Ennemi",
	        "slug": "bate-ennemi",
	        "roles": ("Ennemi",),
	        # LA VOIX GÉNÉRIQUE DES ENNEMIS DE COMBAT, et c'est un choix de production : une seule
	        # voix pour toutes les rencontres, réutilisée telle quelle. Ses 33 répliques viennent
	        # de `bate/resources/combat_barks.json` (via `tools/extraire_barks.py`) et non d'une
	        # timeline — elles se déclenchent sur l'état du combat, pas sur un tour de dialogue.
	        #
	        # Timbre à TROIS composants, le premier du dépôt : `_parse_timbre` les accepte depuis
	        # toujours (il boucle sur `split("+")`), personne ne les avait essayés. Un mélange à
	        # trois donne exactement ce qu'un figurant demande — une voix sans caractère marqué,
	        # qui n'évoque aucun des six personnages masculins déjà en service.
	        "timbre": "uncle_fu:0.4+ryan:0.4+aiden:0.2",
	        # Le registre PAR LOT, l'étiquette de lot étant la catégorie de bark. Un
	        # « Tu t'es perdu, gamin ? » d'ouverture et un « Gah ! Tu vas me le payer ! » de coup
	        # critique ne se jouent pas sur le même ton, et c'est tout l'intérêt d'un bark : sans
	        # le ton, la ligne tombe à plat et le combat reste aussi mort qu'avant.
	        "registres_par_lot": {"ouverture": "dialogue", "attaque": "determination",
	                              "touche": "colere", "critique": "peur", "bas": "peur",
	                              "vaincu": "emu", "fuite": "peur"},
	        "cibles": None,
	    },
	    "luna": {
	        "nom": "Luna",
	        "slug": "bate-luna",
	        "roles": ("Luna",),
	        # Luna Sirenel, elfe de Loriande, arcs `loriande_awakening`, `xyrus_first_frost` et
	        # `elven_dormitory` — 9 ans au hameau, 13 à l'Académie. Sobre, phrases courtes,
	        # réponses exactes ; c'est l'aînée du duo et la plus posée des deux.
	        #
	        # AUCUN PUR (décision d'Olivier du 2026-08-26 : deux purs en service suffisent), et
	        # le couple Luna/Lise se choisit ENSEMBLE — elles partagent la totalité de leurs
	        # scènes, avec Tessia présente dans les trois arcs. Retenu sur 20 répliques réelles :
	        # plage 61 Hz (la plus basse des mélanges), Tessia 0,920 (la plus éloignée),
	        # Lise 0,953. Le balayage à 8 répliques désignait `serena` (23 Hz de plage) — il sort
	        # à 67 Hz sur vingt : c'est exactement l'erreur payée sur Sylvie.
	        "timbre": "ono_anna:0.8+vivian:0.2",
	        # 2 demi-tons de DESCENTE, et c'est le seul point que la mesure ne tranchait pas
	        # seule : sans décalage Luna sort à 265 Hz et Lise à 262, soit trois hertz d'écart
	        # pour deux personnages qui ne se quittent pas. Descendue de deux, elle se place
	        # entre Tessia et Lise — `Tessia 213 < Luna 237 < Lise 262 < Ellie 270`. Pas trois :
	        # à 223 Hz elle rejoindrait Tessia, qui est l'autre voix à ne pas confondre.
	        "grave_demi_tons": 2.0,
	        "cibles": None,
	    },
	    "lise": {
	        "nom": "Lise",
	        "slug": "bate-lise",
	        "roles": ("Lise",),
	        # Lise Tavaren, la cadette (8 ans au hameau, 12 à l'Académie). Bavarde, frontale,
	        # réponses trop rapides — d'où l'ambitus le plus large du lot (3,7 st), qui est ici
	        # une qualité et non un défaut de stabilité.
	        #
	        # Mélange INVERSE de celui de Luna. Retenu sur 20 de ses répliques : plage 39 Hz,
	        # ambitus 3,7, Tessia 0,903 — il domine ses trois rivales.
	        # ET IL ÉVITE `serena` VOLONTAIREMENT : `vivian:0.7+serena:0.3`, que la mesure
	        # désignait d'abord, EST le timbre d'ellie, dont la voix vient de monter à 270 Hz
	        # (correction de `descendre()`, même jour) — deux voix à 0,970 de cosinus et 28 Hz
	        # d'écart. Éviter la collision coûte 0,006 de distance à Luna et rapporte sur les
	        # trois autres colonnes.
	        "timbre": "vivian:0.8+ono_anna:0.2",
	        "cibles": None,
	    },
	    "ellie": {
	        "nom": "Ellie",
	        "slug": "bate-ellie",
	        "roles": ("Ellie", "Eleanor"),
	        # Petite sœur d'Arthur, ~8-10 ans, adorable/curieuse.
	        # Mix vivian+serena +2st (WSOLA) pour registre enfantin/pur.
	        # vivian/serena purs dispo pour futurs persos.
	        "timbre": "vivian:0.7+serena:0.3",
	        "grave_demi_tons": -2.0,
	        "cibles": None,
	    },
	}


# --- la troupe, déclarée en DONNÉES et non en code ------------------------------------------
# Les personnages ci-dessus portent chacun une décision argumentée : un casting, une mesure, une
# réserve. Les figurants, non — ils reçoivent une voix d'archétype attribuée par
# `tools/casting_troupe.py`, et ils sont quatre-vingt-quatorze. Les écrire ici noierait les
# quinze décisions qui comptent sous quatre-vingt-quatorze lignes qui n'en portent aucune ; le
# registre `resources/casting_troupe.json` les tient, et se régénère.
TROUPE = MEDIA / "resources" / "casting_troupe.json"


def _charge_troupe() -> dict:
    """Ajoute les personnages de troupe à `PERSONNAGES`, sans jamais écraser une voix castée.

    L'ordre compte : une entrée écrite en dur gagne toujours. Le registre est produit par un
    outil qui recense les timelines, donc il peut proposer un personnage qu'on a entre-temps
    casté à la main — et c'est le casting qui décide, pas le recensement.
    """
    if not TROUPE.exists():
        return {}
    registre = json.loads(TROUPE.read_text(encoding="utf-8"))
    ajoutes = {}
    for nom, fiche in registre.get("personnages", {}).items():
        if not fiche.get("timbre"):
            continue                                  # « À CASTER » : pas encore de voix
        # `dossier_du_locuteur` et non `dossier_de_voix(role…)` : le libellé complet décide, sinon
        # les six professeurs et les trois « Le … » retombent tous sur la même clé et douze
        # figurants disparaissent du registre en silence (mesuré : 82 chargés sur 94).
        cle = dossier_du_locuteur(nom)
        if not cle or cle in PERSONNAGES:
            continue
        ajoutes[cle] = {
            "nom": nom,
            "slug": f"bate-{cle}",
            "roles": tuple(fiche.get("roles") or (nom,)),
            "timbre": fiche["timbre"],
            "grave_demi_tons": float(fiche.get("decalage", 0.0)),
            # La cible vient de l'ARCHÉTYPE : sans elle, `_cible` refuse de juger les voix
            # graves (34 des 93) et le lot passe pour contrôlé alors qu'il ne l'est pas.
            "cibles": ({"*": float(fiche["cible"])} if fiche.get("cible") else None),
            "troupe": fiche.get("archetype"),
        }
    PERSONNAGES.update(ajoutes)
    return ajoutes


_TROUPE_AJOUTEE = _charge_troupe()


def _perso(cle: str) -> dict:
    if cle not in PERSONNAGES:
        raise SystemExit(f"personnage inconnu : {cle} (parmi {', '.join(PERSONNAGES)})")
    p = dict(PERSONNAGES[cle])
    p["lignes"] = RACINE / f"voice-agent/training/forge/{p['slug']}/lines.json"
    # Le dossier de voix se DÉDUIT du LIBELLÉ par la règle du jeu, il ne se choisit pas :
    # `AudioManager` cherche `voice/<dossier>/<id>`, et un dossier inventé ici produirait un
    # pack complet que personne n'appelle — construit sans erreur, muet en jeu.
    #
    # `dossier_du_locuteur` et non `dossier_de_voix(role_du_locuteur(…))`, et l'écart n'était pas
    # théorique : la seconde forme ne voit que le PREMIER MOT, donc « L'architecte du Dessein »
    # écrivait dans `voices/l/` quand le jeu, lui, cherche `voices/architecte/`. Cent deux clips
    # de sept personnages ont été produits dans le mauvais dossier avant que le réindexage du
    # manifeste ne le révèle — sept dossiers pleins que plus rien ne réclamait, et sept dossiers
    # attendus restés vides. Le contrat de rôle avait été corrigé partout SAUF ici.
    p["sortie"] = MEDIA / "voices" / dossier_du_locuteur(p["roles"][0])
    return p


def _lignes(perso: dict, max_chapitre: int = None) -> list:
    """Les répliques à dire, DÉDUPLIQUÉES par identifiant de clip.

    Deux répliques au texte identique dites par le même rôle partagent un clip — c'est la
    conséquence voulue du nommage par empreinte. Sans cette déduplication, le compte annoncé
    par `livrer` serait celui des répliques et non celui des fichiers, et une reprise
    afficherait des « gardés » qu'elle vient d'écrire elle-même au tour d'avant.
    """
    if not perso["lignes"].exists():
        raise SystemExit(
            f"extraction introuvable : {perso['lignes']}\n"
            f"  python3 tools/extraire_repliques.py {perso['slug']} "
            + " ".join(f'"{r}"' for r in perso["roles"]))
    brutes = json.loads(perso["lignes"].read_text(encoding="utf-8"))
    # LA BORNE S'APPLIQUE AVANT LA DÉDUPLICATION, et l'ordre n'est pas indifférent. La
    # déduplication garde la PREMIÈRE occurrence d'un texte, et les chapitres précèdent les arcs
    # secondaires dans l'extraction : dédupliquer d'abord fait donc porter la réplique par son
    # occurrence de chapitre, qu'une borne peut ensuite exclure — emportant avec elle
    # l'occurrence d'arc, pourtant dans le périmètre. Deux clips d'arcs ont disparu comme ça,
    # et `livrer` annonçait « 0 à générer » sans mentir : ils n'étaient plus dans sa liste.
    if max_chapitre is not None:
        brutes = [l for l in brutes
                  if (n := _numero_chapitre(l["chapitre"])) is None or n <= max_chapitre]
    vues, lot = set(), []
    for l in brutes:
        # L'identifiant se calcule sur le texte BRUT quand l'extraction l'a conservé : c'est
        # celui que le jeu demandera (`event.text`, balises comprises). Le texte prononcé, lui,
        # reste la version nettoyée. Sans cette distinction, une réplique portant une balise de
        # style était produite sous un identifiant introuvable côté jeu — 75 répliques muettes
        # à 100 %, dont 66 de Sylvie. Le repli sur `texte` couvre les extractions antérieures,
        # qui n'ont pas le champ.
        ident = clip_id(l["role"], l.get("texte_brut") or l["texte"])
        if ident is None or ident in vues:
            continue
        vues.add(ident)
        lot.append({**l, "clip": ident})
    return lot


def _instruct(qwen3tts, ligne: dict, perso: dict = None) -> str:
    """Le registre du rôle — et, quand le personnage en déclare un PAR LOT, celui du lot.

    Plus aucun prompt d'âge : c'est LA standardisation. Le registre, lui, reste — il ne fait
    pas varier la voix dans le temps, il distingue ce qu'Arthur DIT de ce qu'il PENSE, et cette
    distinction-là est permanente.

    LE CHAMP `registre` DES LIGNES EXTRAITES EST VOLONTAIREMENT IGNORÉ. `voice_forge` le remplit
    par défaut à « narration » : il vaut « narration » pour les 232 répliques d'Elijah, qui
    parle, et pour les 124 de Sylvie. Le respecter reviendrait à faire murmurer tout le monde
    comme un narrateur intérieur — une régression déguisée en correction.

    Ce qui est respecté, c'est `registres_par_lot` déclaré par le PERSONNAGE, indexé par
    l'étiquette de lot (le champ `chapitre`). Les répliques de combat en ont besoin : un
    « Tu t'es perdu, gamin ? » d'ouverture et un « Gah ! Tu vas me le payer ! » de coup
    critique ne se jouent pas sur le même ton, et un registre unique par personnage ne saurait
    pas les séparer.
    """
    par_lot = (perso or {}).get("registres_par_lot") or {}
    registre = (par_lot.get(ligne.get("chapitre"))
                or (perso or {}).get("registre")
                or qwen3tts.REGISTRE_PAR_ROLE.get(ligne["role"], qwen3tts.REGISTRE_DEFAUT))
    if registre not in qwen3tts.REGISTRES:
        raise SystemExit(f"registre inconnu : {registre} "
                         f"(parmi {', '.join(qwen3tts.REGISTRES)})")
    return qwen3tts.REGISTRES[registre]


# --- contrôle d'énergie -------------------------------------------------------

def _spectre(chemin: Path):
    import soundfile as sf

    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    spectre = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    return spectre, np.fft.rfftfreq(len(x), 1 / sr)


def _part_bande(chemin: Path, cible: float) -> float:
    """Part de l'énergie vocale située dans la bande du fondamental attendu.

    Critère VOLONTAIREMENT distinct de la F0 : l'autocorrélation attrape régulièrement une
    harmonique quand le fondamental est faible et rend la borne même du détecteur. Mesurer OÙ
    est l'énergie ne se trompe pas d'octave. Un clip sain met la moitié ou plus de son énergie
    vocale dans cette bande ; les clips cassés d'Arthur tombaient à 4-14 %.
    """
    spectre, f = _spectre(chemin)
    total = spectre[(f > 60) & (f < 2000)].sum()
    bande = spectre[(f >= 0.6 * cible) & (f < 1.4 * cible)].sum()
    return float(bande / total) if total > 0 else 0.0


def _part_grave(chemin: Path, borne: float = 150.0) -> float:
    """Part de l'énergie vocale sous `borne` — le témoin qui dit si la F0 est croyable."""
    spectre, f = _spectre(chemin)
    total = spectre[(f > 60) & (f < 2000)].sum()
    return float(spectre[(f > 60) & (f < borne)].sum() / total) if total > 0 else 0.0


def _barycentre(chemin: Path) -> float:
    """Barycentre spectral de la bande vocale — la hauteur, sans erreur d'octave possible."""
    spectre, f = _spectre(chemin)
    masque = (f > 60) & (f < 2000)
    poids = spectre[masque].sum()
    return float((f[masque] * spectre[masque]).sum() / poids) if poids > 0 else 0.0


def _cible(perso: dict, role: str, clips: list, mesures) -> float:
    """Hauteur attendue d'un clip. Écrite en dur si le personnage en déclare, mesurée sinon.

    Le contrôle applique une ATTENTE : si elle est fausse, il ne détecte pas des défauts, il en
    invente. Deux façons de se tromper, rencontrées toutes les deux :

    - contrôler les narrations d'Arthur avec la cible de ses répliques parlées signalait 13
      clips sur 13 comme défectueux, alors qu'ils étaient sains — d'où une cible PAR RÔLE ;
    - mesurer la cible par la F0 sur un lot où elle ment. Le garde-fou est la part d'énergie
      grave : au-delà de 5 % sous 150 Hz, la F0 n'est plus un fondamental croyable et la
      fonction REFUSE plutôt que de rendre une cible fausse.
    """
    if perso["cibles"]:
        return perso["cibles"].get(role, perso["cibles"]["*"])
    grave = float(np.median([_part_grave(c) for c in clips]))
    if grave > 0.05:
        raise SystemExit(
            f"{grave:.1%} de l'énergie sous 150 Hz sur le rôle « {role} » : la F0 n'est plus "
            f"un fondamental croyable, la cible de contrôle serait fausse. Étalonner au "
            f"barycentre (`voix_personnage.py etalonner`) et écrire la cible dans "
            f"PERSONNAGES[...]['cibles'], comme pour Arthur.")
    f0 = [d["f0_median"] for d in (mesures._descripteurs(c) for c in clips)
          if d["f0_median"] > 0]
    return float(np.median(f0))


def _douteux(perso: dict, clips_roles: list, mesures) -> tuple:
    """Les clips dont l'énergie n'est pas là où elle devrait, à rôle comparable.

    Seuil RELATIF à la médiane, pas absolu : la part d'énergie dans la bande dépend du timbre
    et du texte, et un seuil fixe rejetterait tout le lot ou aucun clip. Médiane calculée PAR
    RÔLE — narration et réplique parlée n'ont ni la même cible ni la même distribution, les
    mélanger ferait juger les unes à l'aune des autres.
    """
    mauvais, medianes, cibles = [], {}, {}
    for role in sorted({r for _, r in clips_roles}):
        duRole = [c for c, r in clips_roles if r == role]
        if not duRole:
            continue
        cible = _cible(perso, role, duRole, mesures)
        parts = [(_part_bande(c, cible), c) for c in duRole]
        mediane = float(np.median([p for p, _ in parts]))
        medianes[role], cibles[role] = mediane, cible
        mauvais += [(p, c) for p, c in parts if p < 0.5 * mediane]
    return sorted(mauvais), medianes, cibles


def _clips_presents(perso: dict, lignes: list) -> list:
    """(chemin, rôle) des clips réellement sur le disque, pour les seules répliques attendues."""
    return [(perso["sortie"] / f"{l['clip']}.ogg", l["role"]) for l in lignes
            if (perso["sortie"] / f"{l['clip']}.ogg").exists()]


# --- commandes ----------------------------------------------------------------

def _numero_chapitre(etiquette: str):
    """Numéro de chapitre d'une étiquette, ou None si elle n'en porte pas.

    Ancré sur le préfixe `ch`, comme dans `extraire_repliques._numero` : une étiquette d'arc
    secondaire (`gates_design_01`) contient elle aussi un nombre, et « le premier nombre
    trouvé » en tirerait 1.
    """
    m = re.fullmatch(r"ch(\d+)[a-z]*", etiquette)
    return int(m.group(1)) if m else None


def livrer(cle: str, limite: int = 0, max_chapitre: int = None) -> int:
    """Génère ce qui manque, et RIEN d'autre.

    `max_chapitre` borne la TRAME, pas le lot : une histoire secondaire n'est datée d'aucun
    chapitre, elle n'est donc jamais « au-delà » d'une borne et reste toujours produite. C'est
    la sémantique voulue — on repousse la fin du récit sans repousser les arcs, qui sont un
    contenu à part et complet en lui-même. Pour ne produire QUE la trame, il faudrait une autre
    option ; personne n'en a eu besoin.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    perso = _perso(cle)
    lignes = _lignes(perso, max_chapitre)
    if max_chapitre is not None:
        print(f"borne ch{max_chapitre} : {len(_lignes(perso)) - len(lignes)} clips écartés "
              f"(arcs secondaires conservés, ils ne portent pas de chapitre)")
    perso["sortie"].mkdir(parents=True, exist_ok=True)
    def _absent(ligne: dict) -> bool:
        c = perso["sortie"] / f"{ligne['clip']}.ogg"
        return not c.exists() or c.stat().st_size == 0

    a_faire = [l for l in lignes if _absent(l)]
    if limite:
        a_faire = a_faire[:limite]
    print(f"{perso['nom']} · timbre {perso['timbre']} · aucun prompt d'âge")
    print(f"{len(lignes)} clips attendus, {len(lignes) - len(a_faire)} déjà produits, "
          f"{len(a_faire)} à générer vers {perso['sortie'].relative_to(MEDIA)}", flush=True)
    if not a_faire:
        return 0

    modele = qwen3tts._charge("customvoice")
    grave = perso.get("grave_demi_tons", 0.0)
    relances, debut = 0, time.time()
    for i, ligne in enumerate(a_faire):
        cible = perso["sortie"] / f"{ligne['clip']}.ogg"
        onde, essais = qwen3tts._genere(
            modele, "customvoice", ligne["texte"], _instruct(qwen3tts, ligne, perso),
            perso["timbre"],
            # Graine dérivée de l'IDENTIFIANT, pas du rang dans le lot. Le rang change dès
            # qu'une réplique est ajoutée en amont : le même clip regénéré plus tard sortirait
            # d'une autre graine, donc d'une autre prise. Reprendre un lot doit redonner le
            # même son.
            seed=qwen3tts._seed_de(ligne["clip"], 2000), temperature=0.7)
        relances += essais
        qwen3tts._ecrit(_traite(onde, perso, modele.sample_rate), modele.sample_rate,
                        cible, "ogg")
        if (i + 1) % 25 == 0 or i + 1 == len(a_faire):
            ecoule = time.time() - debut
            reste = ecoule / (i + 1) * (len(a_faire) - i - 1)
            print(f"    {i + 1}/{len(a_faire)}  ({ecoule / 60:.0f} min, {relances} relances, "
                  f"reste ~{reste / 3600:.1f} h)", flush=True)
    del modele

    rapport = {"personnage": perso["nom"], "timbre": perso["timbre"], "prompt_age": False,
               "clips_attendus": len(lignes), "clips_generes": len(a_faire),
               "relances": relances, "secondes": round(time.time() - debut, 1)}
    # Dans la FORGE, pas dans `voices/<perso>/` : `build_pack._declaree` filtre au dossier et
    # non au fichier, si bien que tout ce qui traîne dans un dossier de voix déclaré part dans
    # le pack public. Un rapport interne n'a rien à faire dans une archive distribuée.
    (perso["lignes"].parent / "rapport_livraison.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"\n{len(a_faire)} clips en {rapport['secondes'] / 3600:.2f} h, {relances} relances")
    print(f"Contrôler AVANT d'intégrer : tools/voix_personnage.py verifier {cle}")
    return 0


CANDIDATES_CIBLE = [110, 132, 150, 175, 205, 240, 270, 300, 340, 380, 440]


def etalonner(cle: str, limite: int = 40) -> int:
    """Balaie des cibles candidates et rend, PAR RÔLE, celle qui capte le plus d'énergie.

    C'est la seule façon honnête de choisir cette valeur, et elle vient d'une erreur déjà
    payée. Deux grandeurs traînent dans ce dépôt et NE SONT PAS la cible :

    - la **F0** par autocorrélation, qui divise le fondamental par deux sur les répliques
      parlées d'Arthur (~140 Hz annoncés quand la bande dominante est bien plus haut) ;
    - le **barycentre spectral**, qui est une moyenne pondérée sur toute la bande vocale, donc
      tirée vers le haut par les harmoniques et les sifflantes. Il vaut 231 Hz sur des
      narrations dont la cible validée est 132 : excellent pour comparer deux lots entre eux,
      inutilisable comme centre de bande.

    Ce que `_part_bande` utilise est un centre de bande [0,6·c ; 1,4·c]. On mesure donc
    directement ce qui l'intéresse : pour chaque cible candidate, la part médiane d'énergie
    captée — le critère exact que la note de `voix_age_arthur._cible` appliquait à la main
    (« recentrer la bande sur cette valeur faisait tomber l'énergie captée de 45 % à 28 % »).

    ⚠️ **Cette part brute NE PEUT PAS servir de critère de choix**, et la première version de
    cette fonction s'y est laissé prendre. La bande vaut 0,8·c de large : elle s'ÉLARGIT avec la
    cible, donc une cible haute en capte mécaniquement plus. Le balayage brut « retenait » ainsi
    175 Hz pour la narration d'Arthur (contre 132 validée) et 340 Hz pour Tessia (dont la F0
    mesurée est 217) — c'est-à-dire la cible la plus large avant que la bande ne sorte de la
    voix, pas celle qui est centrée dessus. On divise donc par la largeur relative de la bande :
    ce qui est comparable, c'est la CONCENTRATION d'énergie, pas son total. Ainsi normalisées,
    les deux valeurs déjà validées à l'oreille redeviennent les gagnantes. Ne génère rien.
    """
    import random

    perso = _perso(cle)
    clips_roles = _clips_presents(perso, _lignes(perso))
    if not clips_roles:
        print(f"aucun clip dans {perso['sortie']}", file=sys.stderr)
        return 1
    random.seed(11)
    par_role = {}
    for c, r in clips_roles:
        par_role.setdefault(r, []).append(c)

    # Bande d'analyse de `_part_bande`, celle par rapport à laquelle la part est calculée.
    largeur_analyse = 2000.0 - 60.0
    print(f"{perso['nom']} — concentration d'énergie par cible candidate "
          f"({limite} clips max par rôle ; part captée ÷ largeur relative de la bande)")
    print(f"{'rôle':11s}" + "".join(f"{c:>7d}" for c in CANDIDATES_CIBLE) + "    retenue")
    for role, chemins in sorted(par_role.items()):
        ech = random.sample(chemins, min(limite, len(chemins)))
        parts = [float(np.median([_part_bande(c, cible) for c in ech]))
                 for cible in CANDIDATES_CIBLE]
        densites = [p / (0.8 * c / largeur_analyse) for p, c in zip(parts, CANDIDATES_CIBLE)]
        meilleure = CANDIDATES_CIBLE[int(np.argmax(densites))]
        declaree = (perso["cibles"] or {}).get(role, (perso["cibles"] or {}).get("*"))
        etat = "" if declaree is None else (
            " = déclarée" if declaree == meilleure else f" ≠ DÉCLARÉE {declaree:.0f}")
        print(f"{role:11s}" + "".join(f"{d:6.1f} " for d in densites)
              + f"  {meilleure} Hz{etat}")
    return 0


def verifier(cle: str) -> int:
    """Contrôle qualité du lot, sans rien régénérer."""
    import bench_qwen3tts as mesures

    perso = _perso(cle)
    clips_roles = _clips_presents(perso, _lignes(perso))
    if not clips_roles:
        print(f"aucun clip dans {perso['sortie']}", file=sys.stderr)
        return 1
    mauvais, medianes, cibles = _douteux(perso, clips_roles, mesures)
    detail = ", ".join(f"{r} {m:.0%} (cible {cibles[r]:.0f} Hz)"
                       for r, m in sorted(medianes.items()))
    print(f"{len(clips_roles)} clips — médiane d'énergie par rôle : {detail} — "
          f"{len(mauvais)} douteux ({len(mauvais) / len(clips_roles):.1%})")
    for part, c in mauvais[:60]:
        print(f"    {c.stem:22s} {part:5.1%}")
    if len(mauvais) > 60:
        print(f"    … et {len(mauvais) - 60} autres")
    return 0


def reprendre(cle: str, essais: int = 4) -> int:
    """Régénère les clips douteux sur d'autres graines, en gardant le meilleur essai.

    « Meilleur » au sens du critère d'énergie, pas de la F0 : c'est lui qui a détecté le
    défaut, c'est lui qui valide la reprise. On garde le meilleur essai même s'il reste sous le
    seuil — un clip amélioré vaut mieux qu'un clip cassé conservé par principe — et on
    journalise ceux qui n'ont pas pu être sauvés.
    """
    import bench_qwen3tts as mesures
    import qwen3tts

    perso = _perso(cle)
    lignes = _lignes(perso)
    par_clip = {l["clip"]: l for l in lignes}
    clips_roles = _clips_presents(perso, lignes)
    mauvais, medianes, cibles = _douteux(perso, clips_roles, mesures)
    role_par_clip = {c: r for c, r in clips_roles}
    print(f"{len(mauvais)} clips à reprendre sur {len(clips_roles)}", flush=True)
    if not mauvais:
        return 0

    modele = qwen3tts._charge("customvoice")
    sauves, restants = 0, []
    for part0, chemin in mauvais:
        ligne = par_clip.get(chemin.stem)
        if ligne is None:
            print(f"    {chemin.stem:22s} absent de lines.json — ignoré", flush=True)
            continue
        role = role_par_clip[chemin]
        cible, seuil = cibles[role], 0.5 * medianes[role]
        meilleur, meilleure_part = None, part0
        for essai in range(essais):
            onde, _ = qwen3tts._genere(modele, "customvoice", ligne["texte"],
                                       _instruct(qwen3tts, ligne, perso), perso["timbre"],
                                       seed=7000 + essai * 613, temperature=0.7)
            onde = _traite(onde, perso, modele.sample_rate)
            tmp = chemin.with_suffix(".essai.ogg")
            qwen3tts._ecrit(onde, modele.sample_rate, tmp, "ogg")
            part = _part_bande(tmp, cible)
            if part > meilleure_part:
                meilleur, meilleure_part = onde, part
            tmp.unlink()
            if meilleure_part >= seuil:
                break
        if meilleur is not None:
            qwen3tts._ecrit(meilleur, modele.sample_rate, chemin, "ogg")
        if meilleure_part >= seuil:
            sauves += 1
        else:
            restants.append(chemin.stem)
        print(f"    {chemin.stem:22s} {part0:5.1%} -> {meilleure_part:5.1%}  "
              f"{'OK' if meilleure_part >= seuil else 'encore douteux'}", flush=True)
    del modele

    print(f"\n{sauves}/{len(mauvais)} récupérés"
          + (f", restants : {', '.join(restants)}" if restants else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commande", choices=["livrer", "verifier", "reprendre", "etalonner"])
    ap.add_argument("personnage", choices=sorted(PERSONNAGES))
    ap.add_argument("--limite", type=int, default=0,
                    help="ne traiter que N clips (livrer), N par rôle (etalonner)")
    ap.add_argument("--max-chapitre", type=int, default=None,
                    help="borner la TRAME à ce chapitre ; les histoires secondaires, qui ne "
                         "portent pas de numéro, sont produites quoi qu'il arrive")
    args = ap.parse_args()

    if args.commande == "livrer":
        return livrer(args.personnage, args.limite, args.max_chapitre)
    if args.commande == "verifier":
        return verifier(args.personnage)
    if args.commande == "etalonner":
        return etalonner(args.personnage, args.limite or 40)
    return reprendre(args.personnage)


if __name__ == "__main__":
    sys.exit(main())
