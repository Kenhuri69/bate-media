#!/usr/bin/env python3
"""Banc d'essai Qwen3-TTS pour la voix d'Arthur (BATE) — à lancer avec .venv-mlx.

Trois questions, et une seule mérite du code : le reste s'entend.

  1. STABILITÉ DU TIMBRE — c'est le risque du mode VoiceDesign. Chaque réplique est
     une génération indépendante : rien ne garantit que la voix d'Arthur au chapitre 3
     soit la même qu'au chapitre 40. Chatterbox tenait cette promesse en clonant un WAV
     de référence ; VoiceDesign ne part que d'une description. On mesure donc la dérive,
     au lieu de l'espérer.
  2. EXPRESSIVITÉ — le `instruct` par réplique change-t-il VRAIMENT la prosodie, ou
     seulement le prompt ? Deux sliders Chatterbox (exaggeration/cfg_weight) faisaient
     déjà quelque chose : le remplaçant doit faire mieux, pas juste « différemment ».
  3. VITESSE — mesurée en RTF, pour comparer aux heures de Chatterbox sur MPS.

La mesure ne remplace pas l'oreille : elle écarte les candidats objectivement mauvais
(voix qui change d'âge entre deux répliques, émotions indiscernables) pour ne soumettre
à l'écoute que ce qui tient debout. Le choix final reste humain — convention de la forge.
"""
import json
import sys
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
import soundfile as sf
from scipy.fftpack import dct
from scipy.signal import get_window

RACINE = Path.home() / "workspace"
SORTIE = RACINE / "scratch" / "q3tts-arthur"
VOICEDESIGN = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit"
CUSTOMVOICE = "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"

# La description retenue à l'oreille le 2026-07-26 pour Arthur (choice.json), traduite :
# Qwen3-TTS accepte le français dans l'instruct, contrairement à Parler-TTS qui imposait
# l'anglais. On garde le sens exact du candidat validé plutôt que d'en réinventer un.
TIMBRE_ARTHUR = ("Voix de garçon d'environ seize ans, calme et introspective, timbre doux "
                 "et chaud, légèrement hésitante mais déterminée, avec une profondeur "
                 "émotionnelle discrète. Enregistrement très net, sans bruit de fond.")

# Registres = ce que les deux sliders Chatterbox tentaient d'approcher, plus ce qu'ils ne
# pouvaient pas exprimer du tout (peur, colère). Un registre par intention de jeu.
REGISTRES = {
    "narration": "Ton posé de narrateur intérieur, sobre, presque murmuré, sans emphase.",
    "dialogue": "Ton naturel de conversation, engagé et vivant.",
    "emu": "Ton ému, la voix se serre, hésitante, au bord des larmes.",
    "colere": "Ton de colère contenue, mâchoires serrées, débit dur et tranchant.",
    "peur": "Ton apeuré, souffle court, voix tremblante et pressée.",
}

# Les quatre timbres masculins des neuf voix premium de CustomVoice : les seuls
# candidats plausibles pour un garçon de seize ans.
SPEAKERS_MASCULINS = ["aiden", "dylan", "ryan", "eric"]


# --- mesures acoustiques ------------------------------------------------------
# Pas de librosa dans .venv-mlx, et l'installer pour trois descripteurs serait payer
# 200 Mo de dépendances : numpy + scipy suffisent.
def _f0(x: np.ndarray, sr: int, fmin=60, fmax=400) -> np.ndarray:
    """F0 par autocorrélation, trame par trame. Rend les trames voisées seulement.

    Les trames non voisées (silences, consonnes sourdes) n'ont pas de hauteur : les
    inclure ferait tendre toutes les moyennes vers le même bruit et masquerait
    précisément l'écart qu'on cherche à mesurer.
    """
    taille, saut = int(0.04 * sr), int(0.01 * sr)
    fenetre = get_window("hann", taille)
    lag_min, lag_max = int(sr / fmax), int(sr / fmin)
    sorties = []
    for debut in range(0, len(x) - taille, saut):
        trame = x[debut:debut + taille] * fenetre
        energie = np.sqrt(np.mean(trame ** 2))
        if energie < 1e-3:
            continue
        trame = trame - trame.mean()
        ac = np.correlate(trame, trame, mode="full")[taille - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        zone = ac[lag_min:lag_max]
        if len(zone) == 0:
            continue
        pic = int(np.argmax(zone)) + lag_min
        # Un pic d'autocorrélation faible = trame non périodique : ce n'est pas de la
        # voix, c'est du souffle. 0.3 écarte le bruit sans couper les fins de phrase.
        if ac[pic] < 0.3:
            continue
        sorties.append(sr / pic)
    return np.array(sorties)


def _mfcc_moyen(x: np.ndarray, sr: int, n_mel=40, n_cep=13) -> np.ndarray:
    """MFCC moyennés = empreinte grossière du timbre, indépendante du texte prononcé.

    Proxy assumé : un vrai encodeur de locuteur (ECAPA-TDNN) serait plus fin, mais il
    n'est livré qu'avec la variante Base. Les MFCC suffisent pour ce qu'on cherche —
    détecter qu'une voix a changé d'âge ou de genre entre deux répliques, pas certifier
    l'identité vocale.
    """
    taille, saut = int(0.025 * sr), int(0.010 * sr)
    fenetre = get_window("hann", taille)
    # Banc de filtres mel
    def hz2mel(f): return 2595 * np.log10(1 + f / 700)
    def mel2hz(m): return 700 * (10 ** (m / 2595) - 1)
    bords = mel2hz(np.linspace(hz2mel(50), hz2mel(min(8000, sr / 2)), n_mel + 2))
    bins = np.floor((taille + 1) * bords / sr).astype(int)
    banc = np.zeros((n_mel, taille // 2 + 1))
    for m in range(1, n_mel + 1):
        g, c, d = bins[m - 1], bins[m], bins[m + 1]
        if c == g or d == c:
            continue
        banc[m - 1, g:c] = (np.arange(g, c) - g) / (c - g)
        banc[m - 1, c:d] = (d - np.arange(c, d)) / (d - c)
    ceps = []
    for debut in range(0, len(x) - taille, saut):
        trame = x[debut:debut + taille] * fenetre
        if np.sqrt(np.mean(trame ** 2)) < 1e-3:
            continue
        spectre = np.abs(np.fft.rfft(trame)) ** 2
        ceps.append(dct(np.log(banc @ spectre + 1e-10), type=2, norm="ortho")[:n_cep])
    return np.mean(ceps, axis=0) if ceps else np.zeros(n_cep)


def _descripteurs(chemin: Path) -> dict:
    x, sr = sf.read(str(chemin))
    if x.ndim > 1:
        x = x.mean(axis=1)
    f0 = _f0(x, sr)
    voises = len(f0)
    return {
        "duree": len(x) / sr,
        "f0_median": float(np.median(f0)) if voises else 0.0,
        # L'écart-type de F0 EN DEMI-TONS, pas en Hz : en Hz, une voix aiguë paraît
        # toujours plus variable qu'une grave à expressivité égale. C'est l'ambitus
        # perçu qui dit si la réplique est jouée ou récitée.
        "f0_ambitus_st": float(np.std(12 * np.log2(f0 / np.median(f0)))) if voises else 0.0,
        "rms_db": float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-10)),
        # Part de trames voisées : un ton apeuré et haletant en a moins (souffle,
        # pauses) qu'une narration posée. Approxime le débit sans aligner de phonèmes.
        "voise": voises / max(1, len(x) // int(0.010 * sr)),
        "mfcc": _mfcc_moyen(x, sr),
    }


def _cosinus(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def _dispersion_timbre(chemins: list) -> dict:
    """Cohésion du timbre sur un lot de clips : cosinus moyen des MFCC deux à deux."""
    empreintes = [_descripteurs(c)["mfcc"] for c in chemins]
    paires = [_cosinus(empreintes[i], empreintes[j])
              for i in range(len(empreintes)) for j in range(i + 1, len(empreintes))]
    return {"cohesion_moyenne": float(np.mean(paires)),
            "cohesion_min": float(np.min(paires)), "paires": len(paires)}


# --- génération ---------------------------------------------------------------
def _genere(modele, cible: Path, texte: str, seed: int, **kw) -> float:
    cible.parent.mkdir(parents=True, exist_ok=True)
    mx.random.seed(seed)
    t0 = time.time()
    morceaux = list(modele.generate(text=texte, lang_code="french", temperature=0.7, **kw))
    onde = mx.concatenate([m.audio for m in morceaux])
    duree = onde.shape[0] / modele.sample_rate
    sf.write(str(cible), np.array(onde), modele.sample_rate)
    return time.time() - t0, duree


def main() -> int:
    from mlx_audio.tts.utils import load

    # Vraies répliques d'Arthur : évaluer sur des phrases inventées dirait comment le
    # modèle lit du texte quelconque, pas comment il joue CE personnage.
    lignes = json.loads((RACINE / "voice-agent/training/forge/bate-arthur/lines.json")
                        .read_text(encoding="utf-8"))
    dialogues = [l for l in lignes if l["role"] == "Arthur"][:6]
    narrations = [l for l in lignes if l["role"] == "narrator"][:2]
    SORTIE.mkdir(parents=True, exist_ok=True)
    rapport = {"repliques": [d["id"] for d in dialogues]}

    # --- 1) VoiceDesign : stabilité sur 6 répliques, en conditions de prod ---------
    print("=== VoiceDesign : 6 répliques (stabilité du timbre) ===", flush=True)
    modele = load(VOICEDESIGN)
    temps, duree_totale, faits = 0.0, 0.0, []
    for i, ligne in enumerate(dialogues + narrations):
        registre = "narration" if ligne["role"] == "narrator" else "dialogue"
        cible = SORTIE / "vd-stabilite" / f"{ligne['id']}.wav"
        # Seed variable = ce qui se passera en production, une réplique par appel.
        t, d = _genere(modele, cible, ligne["texte"], seed=2000 + i,
                       instruct=f"{TIMBRE_ARTHUR} {REGISTRES[registre]}")
        temps, duree_totale = temps + t, duree_totale + d
        faits.append(cible)
        print(f"  {ligne['id']:22s} {d:4.1f}s  ({registre})", flush=True)
    rapport["voicedesign"] = {"rtf": temps / duree_totale, **_dispersion_timbre(faits)}

    # --- 2) VoiceDesign : les 5 registres sur UNE réplique -----------------------
    print("\n=== VoiceDesign : 5 registres sur une réplique ===", flush=True)
    phrase = dialogues[1]["texte"]
    rapport["registres_vd"] = {}
    for nom, consigne in REGISTRES.items():
        cible = SORTIE / "vd-registres" / f"{nom}.wav"
        _genere(modele, cible, phrase, seed=1060, instruct=f"{TIMBRE_ARTHUR} {consigne}")
        d = _descripteurs(cible)
        rapport["registres_vd"][nom] = {k: v for k, v in d.items() if k != "mfcc"}
        print(f"  {nom:10s} F0 {d['f0_median']:5.0f} Hz  ambitus {d['f0_ambitus_st']:4.1f} st"
              f"  {d['rms_db']:6.1f} dB  voisé {d['voise']:.2f}  {d['duree']:.1f}s", flush=True)
    del modele

    # --- 3) CustomVoice : les 4 timbres masculins -------------------------------
    print("\n=== CustomVoice : 4 timbres masculins (audition) ===", flush=True)
    modele = load(CUSTOMVOICE)
    for spk in SPEAKERS_MASCULINS:
        cible = SORTIE / "cv-speakers" / f"{spk}.wav"
        _genere(modele, cible, phrase, seed=1060, voice=spk,
                instruct=REGISTRES["dialogue"])
        d = _descripteurs(cible)
        print(f"  {spk:8s} F0 {d['f0_median']:5.0f} Hz  {d['duree']:.1f}s", flush=True)

    # --- 4) CustomVoice : stabilité + registres sur le timbre de référence -------
    reference = SPEAKERS_MASCULINS[0]
    print(f"\n=== CustomVoice ({reference}) : stabilité + registres ===", flush=True)
    faits, temps, duree_totale = [], 0.0, 0.0
    for i, ligne in enumerate(dialogues + narrations):
        registre = "narration" if ligne["role"] == "narrator" else "dialogue"
        cible = SORTIE / "cv-stabilite" / f"{ligne['id']}.wav"
        t, d = _genere(modele, cible, ligne["texte"], seed=2000 + i, voice=reference,
                       instruct=REGISTRES[registre])
        temps, duree_totale = temps + t, duree_totale + d
        faits.append(cible)
    rapport["customvoice"] = {"speaker": reference, "rtf": temps / duree_totale,
                              **_dispersion_timbre(faits)}
    rapport["registres_cv"] = {}
    for nom, consigne in REGISTRES.items():
        cible = SORTIE / "cv-registres" / f"{nom}.wav"
        _genere(modele, cible, phrase, seed=1060, voice=reference, instruct=consigne)
        d = _descripteurs(cible)
        rapport["registres_cv"][nom] = {k: v for k, v in d.items() if k != "mfcc"}
        print(f"  {nom:10s} F0 {d['f0_median']:5.0f} Hz  ambitus {d['f0_ambitus_st']:4.1f} st"
              f"  {d['rms_db']:6.1f} dB  voisé {d['voise']:.2f}", flush=True)
    del modele

    # --- 5) Baseline : ce que Chatterbox a réellement produit -------------------
    # Comparer à la production existante, pas à une idée de la production existante :
    # c'est cette voix-là qu'il faut battre pour justifier de changer de moteur.
    print("\n=== Baseline Chatterbox (fichiers déjà produits) ===", flush=True)
    voix_actuelles = sorted((RACINE / "bate-media/voices/arthur").glob("arthur_ch0*.ogg"))[:8]
    if voix_actuelles:
        rapport["chatterbox"] = _dispersion_timbre(voix_actuelles)
        rapport["chatterbox"]["clips"] = len(voix_actuelles)
        for c in voix_actuelles[:3]:
            d = _descripteurs(c)
            print(f"  {c.name:22s} F0 {d['f0_median']:5.0f} Hz  "
                  f"ambitus {d['f0_ambitus_st']:4.1f} st  {d['duree']:.1f}s", flush=True)

    (SORTIE / "rapport.json").write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    # --- verdict mesurable ------------------------------------------------------
    print("\n" + "=" * 66)
    print("COHÉSION DU TIMBRE (cosinus MFCC ; 1.0 = timbre identique)")
    for cle, libelle in [("chatterbox", "Chatterbox (actuel)"),
                         ("voicedesign", "Qwen3 VoiceDesign"),
                         ("customvoice", "Qwen3 CustomVoice")]:
        if cle in rapport:
            r = rapport[cle]
            print(f"  {libelle:22s} moyenne {r['cohesion_moyenne']:.3f}   "
                  f"pire paire {r['cohesion_min']:.3f}")
    print("\nÉCART ENTRE REGISTRES (étendue sur les 5 registres)")
    for cle, libelle in [("registres_vd", "VoiceDesign"), ("registres_cv", "CustomVoice")]:
        vals = rapport[cle]
        f0 = [v["f0_median"] for v in vals.values()]
        amb = [v["f0_ambitus_st"] for v in vals.values()]
        print(f"  {libelle:22s} F0 {min(f0):.0f}–{max(f0):.0f} Hz "
              f"(étendue {max(f0) - min(f0):.0f})   ambitus {min(amb):.1f}–{max(amb):.1f} st")
    print(f"\nVITESSE  VoiceDesign RTF {rapport['voicedesign']['rtf']:.2f}   "
          f"CustomVoice RTF {rapport['customvoice']['rtf']:.2f}   (< 1 = plus vite que le réel)")
    print(f"\nClips à écouter dans {SORTIE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
