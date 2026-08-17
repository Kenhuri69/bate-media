#!/usr/bin/env python3
"""Descente de voix à durée constante — le seul traitement du signal de la chaîne.

Importé par `voix_personnage.py` (production) et `bench_grave.py` (banc d'écoute). Il vit à
part parce qu'un chemin de production ne doit pas importer un banc : le banc explore, la
production livre, et c'est la production qui commande.

POURQUOI CE TRAITEMENT EXISTE. Le modèle ne sait pas descendre une voix. Six consignes
« vieil homme » mesurées sur Virion montent TOUTES la F0 (+1 à +16 Hz) — demander « rauque et
usé » fait forcer la voix, donc la monte — et les trois timbres masculins de CustomVoice
tiennent tous entre 130 et 175 Hz. Sans ce filtre, un personnage de plusieurs siècles parle
exactement à la hauteur d'Arthur, quinze ans.
"""
import numpy as np


def _comprimer_wsola(x: np.ndarray, facteur: float, sr: int,
                     taille_s: float = 0.040, recherche_s: float = 0.010) -> np.ndarray:
    """Ramène `x` à `facteur` fois sa durée, SANS toucher à sa hauteur (WSOLA).

    Overlap-add à recouvrement synchronisé : chaque trame de sortie est prise à la position
    d'analyse qui CORRÈLE LE MIEUX avec ce que la trame précédente laisse attendre, cherchée
    dans une fenêtre de ±10 ms. C'est ce recalage qui distingue WSOLA d'un simple overlap-add :
    sans lui, les périodes du fondamental se recollent au hasard, et une voix devient
    métallique et hachée — l'artefact classique du « robot » sur la parole.

    Trame de 40 ms : il faut au moins deux ou trois périodes de fondamental pour que la
    corrélation ait un sens, et une voix d'homme à 110 Hz a des périodes de 9 ms.
    """
    n = int(taille_s * sr)
    n += n % 2
    hs = n // 2                                   # saut de synthèse, recouvrement 50 %
    ha = max(1, int(round(hs / facteur)))         # saut d'analyse
    delta = int(recherche_s * sr)
    fenetre = np.hanning(n).astype(np.float64)

    sortie = np.zeros(int(len(x) * facteur) + n, dtype=np.float64)
    poids = np.zeros_like(sortie)
    attendu = x[:n].astype(np.float64)            # ce que la trame précédente prolonge
    pos_a, pos_s = 0, 0
    while pos_a + n + delta < len(x):
        # Recalage : on cherche le décalage qui maximise la corrélation avec `attendu`.
        debut = max(0, pos_a - delta)
        fin = min(len(x) - n, pos_a + delta)
        if fin <= debut:
            best = pos_a
        else:
            bloc = np.lib.stride_tricks.sliding_window_view(x[debut:fin + n], n)
            best = debut + int(np.argmax(bloc.astype(np.float64) @ attendu))
        trame = x[best:best + n].astype(np.float64)
        sortie[pos_s:pos_s + n] += trame * fenetre
        poids[pos_s:pos_s + n] += fenetre
        # La suite attendue est la continuation naturelle de la trame qu'on vient de poser.
        attendu = x[best + hs:best + hs + n].astype(np.float64)
        if len(attendu) < n:
            break
        pos_a += ha
        pos_s += hs
    utile = poids > 1e-6
    sortie[utile] /= poids[utile]
    return sortie[:int(len(x) * facteur)].astype(x.dtype)


def descendre(onde: np.ndarray, demi_tons: float, sr: int = 24000,
              garder_duree: bool = True) -> np.ndarray:
    """Descend `onde` de `demi_tons` — hauteur ET formants — à durée inchangée par défaut.

    Deux étapes, et la seconde n'est pas un raffinement mais la demande elle-même :

    1. rééchantillonnage au rapport 2^(n/12). Descend la hauteur, descend AUSSI les formants
       (ce qu'un décalage « propre » à formants préservés éviterait) et rallonge d'autant. Des
       formants plus bas s'entendent comme un conduit vocal plus grand, donc un corps plus
       vieux : ici l'effet de bord va dans le sens voulu, on le garde ;
    2. compression WSOLA du même rapport, qui rend la durée d'origine sans remonter la hauteur.

    `garder_duree=False` s'arrête à l'étape 1 — plus grave ET plus lent. Gardé pour pouvoir
    réécouter le compromis, pas pour être livré : ralentir a été refusé explicitement.
    """
    from scipy.signal import resample_poly

    if demi_tons <= 0:
        return onde
    rapport = 2 ** (demi_tons / 12)
    # Fraction rationnelle proche du rapport : 1000 au dénominateur suffit (0,1 % d'erreur,
    # soit moins de deux millièmes de demi-ton).
    plus_grave = resample_poly(onde, int(round(rapport * 1000)), 1000).astype(onde.dtype)
    if not garder_duree:
        return plus_grave
    return _comprimer_wsola(plus_grave, 1 / rapport, sr)
