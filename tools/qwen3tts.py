#!/usr/bin/env python3
"""Qwen3-TTS (MLX) — répliques de personnage avec une ÉMOTION donnée par prompt.

Remplace le couple Parler-TTS (candidats) + Chatterbox (répliques) de la forge :

    # auditionner des timbres libres, décrits en français (mode voicedesign)
    .venv-mlx/bin/python training/qwen3tts.py --sample \
        --description "Voix de garçon de seize ans, calme et introspective" \
        --texte "Papa, comment on sait qu'on a réussi ?" --out /tmp/essai.wav

    # auditionner les neuf timbres premium (mode customvoice)
    .venv-mlx/bin/python training/qwen3tts.py --auditionne-speakers \
        --texte "Papa, comment on sait qu'on a réussi ?"

    # produire les répliques d'un personnage
    .venv-mlx/bin/python training/qwen3tts.py --lines forge/bate-arthur/lines.json \
        --out-dir forge/bate-arthur/lines_arthur --speaker aiden --format ogg

    # plusieurs rôles en une passe (un seul chargement)
    .venv-mlx/bin/python training/qwen3tts.py --jobs forge/cast_repliques.json

Ce que ce moteur change, et pourquoi il remplace les deux précédents
-------------------------------------------------------------------
Chatterbox réglait l'expressivité avec deux nombres (`exaggeration`, `cfg_weight`) :
un curseur d'intensité, pas une émotion. On pouvait rendre Arthur « plus emphatique »,
jamais « au bord des larmes » ni « en colère contenue ». Ici, l'émotion est une PHRASE
en français attachée à la réplique (`instruct`) — c'est le registre de jeu qui est dit,
pas son amplitude. Et le français est natif : plus besoin de rédiger les descriptions
en anglais comme l'imposait Parler-TTS.

Deux modes, et le choix n'est pas celui qu'on croit (mesuré, voir scratch/bench_qwen3tts.py)
-------------------------------------------------------------------------------------------
`voicedesign` décrit un timbre en toute liberté, mais ne le REPRODUIT pas d'une réplique
à l'autre : cohésion de timbre 0,83 en moyenne et jusqu'à 0,52 sur la pire paire, contre
0,94 pour Chatterbox. Sur les quatre-vingt-dix chapitres d'un personnage, la voix dérive.
Il décrivait aussi mal ce qu'on lui demandait — « garçon de seize ans » sortait à 300 Hz,
soit une voix d'enfant ou de femme. Réservé, donc, à l'exploration de timbres.

`customvoice` part d'un des neuf timbres premium (choix contraint) et n'accepte le prompt
QUE pour le style. C'est le mode de production : cohésion 0,94 — à parité avec Chatterbox
— et une expressivité supérieure (ambitus 4,2 à 5,9 demi-tons selon le registre, contre
2,3 à 3,4 pour voicedesign). Le prompt d'émotion fonctionne mieux sur un timbre figé que
sur un timbre lui-même décrit par prompt.

Vitesse : RTF 0,29, soit trois fois plus rapide que le temps réel — les mille six cent
quarante-cinq répliques de la distribution BATE passent d'une nuit à une demi-heure.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent          # ~/workspace/voice-agent
OGGENC = shutil.which("oggenc")

DEPOTS = {
    "customvoice": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "voicedesign": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
}
# Les neuf timbres premium. Les quatre masculins ont été mesurés pour Arthur : `aiden`
# est le seul à tenir la cohésion de timbre (0,939) SANS produire de clip dégénéré —
# `dylan` (0,904) a rendu un quasi-silence de 23 s sur le registre ému, `ryan` monte à
# 300 Hz en dialogue, `eric` plafonne à 0,873.
SPEAKERS = ["serena", "vivian", "uncle_fu", "ryan", "aiden", "ono_anna", "sohee",
            "eric", "dylan"]
SPEAKER_DEFAUT = "aiden"
# `eric` et `dylan` sont déclarés dialectaux dans la config du modèle (`spk_is_dialect` :
# sichuanais et pékinois). C'est ce qui explique leurs scores : ce sont eux qui ont produit
# les clips dégénérés en français. À éviter hors chinois.
SPEAKERS_DIALECTAUX = {"eric", "dylan"}

# Registres de jeu, en remplacement des deux curseurs Chatterbox. Une phrase par
# intention : c'est ce que le modèle sait interpréter, là où un nombre ne disait rien.
REGISTRES = {
    "narration": "Ton posé de narrateur intérieur, sobre, presque murmuré, sans emphase.",
    "dialogue": "Ton naturel de conversation, engagé et vivant.",
    "emu": "Ton ému, la voix se serre, hésitante, au bord des larmes.",
    "colere": "Ton de colère contenue, mâchoires serrées, débit dur et tranchant.",
    "peur": "Ton apeuré, souffle court, voix tremblante et pressée.",
    "joie": "Ton joyeux et léger, sourire dans la voix.",
    "determination": "Ton ferme et résolu, appuyé, sans hésitation.",
}
# Correspondance rôle -> registre, reprise de l'intention de EXPRESSIVITE_PAR_ROLE dans
# voice_forge.py : Arthur narre à la première personne, et son introspection ne se joue
# pas comme ses répliques parlées.
REGISTRE_PAR_ROLE = {"narrator": "narration", "Arthur": "dialogue", "Note": "dialogue"}
REGISTRE_DEFAUT = "dialogue"

# Une réplique sans lettre ni chiffre (« ... ») n'a rien à prononcer — même raison que
# dans character_lines.py, où Chatterbox levait une IndexError dessus.
_PRONONCABLE = re.compile(r"[0-9A-Za-zÀ-ÿ]")

CODE_INCOMPLET = 2      # convention héritée de character_lines.py : relancer


# --- garde-fou anti-dégénérescence -------------------------------------------
# Le test a produit deux clips manifestement cassés sur soixante (23 s de quasi-silence
# pour une phrase de 2 s ; une réplique de 1,9 s étirée à 7,4 s). Sur mille six cents
# répliques ça se compte en dizaines, et personne ne réécoute mille six cents fichiers :
# le filtre doit être dans la boucle, pas dans l'oreille de la personne qui relit.
def _suspect(onde, sr: int, texte: str) -> str:
    """Rend la raison si le clip est aberrant, sinon une chaîne vide.

    Trois symptômes, tous observés : durée sans rapport avec le texte, niveau si bas
    que le clip est vide, et absence de trames voisées (du souffle, pas de la parole).
    """
    import numpy as np

    duree = len(onde) / sr
    # ~14 caractères par seconde en français parlé ; la borne est LARGE (3× + 5 s) car
    # elle ne doit attraper que l'aberration franche, pas un débit lent volontaire.
    attendue = max(0.6, len(texte) / 14)
    if duree > 3 * attendue + 5:
        return f"durée {duree:.1f}s pour ~{attendue:.1f}s attendues"
    rms_db = 20 * math.log10(float(np.sqrt(np.mean(onde ** 2))) + 1e-10)
    if rms_db < -38:
        return f"niveau {rms_db:.0f} dB (clip quasi muet)"
    # Énergie par trame de 20 ms : une réplique parlée en a largement plus de 10 %
    # au-dessus du plancher. Sous ce seuil il n'y a pas de voix dans le fichier.
    trame = int(0.02 * sr)
    if trame and len(onde) >= trame:
        trames = onde[:len(onde) // trame * trame].reshape(-1, trame)
        actives = float(np.mean(np.sqrt(np.mean(trames ** 2, axis=1)) > 1e-3))
        if actives < 0.10:
            return f"{actives:.0%} de trames actives (souffle)"
    return ""


# --- moteur -------------------------------------------------------------------
def _charge(mode: str):
    from mlx_audio.tts.utils import load

    depot = DEPOTS[mode]
    print(f"[q3tts] chargement {depot}…", flush=True)
    t0 = time.time()
    modele = load(depot)
    print(f"[q3tts] prêt en {time.time() - t0:.1f}s (sr={modele.sample_rate}, mode={mode})",
          flush=True)
    return modele


# --- mélange de timbres -------------------------------------------------------
# Le timbre premium n'est pas une voix figée mais un TOKEN de la table d'embedding du
# talker (`spk_id` : aiden=2861, ryan=3061…). Une combinaison pondérée de ces vecteurs
# donne un timbre intermédiaire réel : aiden seul sort à 188 Hz, ryan à 161, et
# « aiden 0.5 + ryan 0.5 » à 155 — sans dégénérescence, durée et niveau normaux. Cela
# lève la limite des neuf timbres : l'espace des voix devient continu.
def _parse_timbre(spec: str) -> dict:
    """« aiden » ou « aiden:0.7+serena:0.3 » -> {nom: poids}. Poids implicite = 1."""
    poids = {}
    for part in spec.split("+"):
        part = part.strip()
        if not part:
            continue
        nom, _, valeur = part.partition(":")
        nom = nom.strip().lower()
        if nom not in SPEAKERS:
            raise ValueError(f"timbre inconnu : {nom} (parmi {', '.join(SPEAKERS)})")
        poids[nom] = float(valeur) if valeur.strip() else 1.0
    if not poids:
        raise ValueError(f"timbre vide : {spec!r}")
    return poids


class _ProxyTimbre:
    """Substitue le vecteur de timbre au SEUL premier appel de forme (1,1).

    Dans `_prepare_generation_inputs`, l'embedding du speaker est le premier accès de
    forme (1,1) à la table du talker ; les autres accès y sont de forme (1,2) à (1,4).
    Le « une seule fois » est essentiel : la boucle de génération réclame ensuite des
    `code_0_embed` de forme (1,1) elle aussi, et les détourner fait boucler le modèle
    (mesuré : 318 s d'audio pour une phrase de 4,6 s). Le proxy délègue tout le reste.
    """

    def __init__(self, vrai, vecteur):
        self.vrai, self.vecteur, self.servi = vrai, vecteur, False

    def __call__(self, ids):
        if not self.servi and ids.shape == (1, 1):
            self.servi = True
            return self.vecteur.reshape(1, 1, -1)
        return self.vrai(ids)

    def __getattr__(self, nom):
        return getattr(self.vrai, nom)


def _vecteur_timbre(modele, poids: dict):
    """Combinaison pondérée (normalisée) des embeddings de timbre, dans le dtype du modèle."""
    import mlx.core as mx

    table = modele.talker.get_input_embeddings()
    spk_id = modele.config.talker_config.spk_id
    total = sum(poids.values())
    vecteurs = table(mx.array([[spk_id[nom] for nom in poids]]))[0]
    parts = mx.array([[poids[nom] / total] for nom in poids]).astype(vecteurs.dtype)
    return (vecteurs * parts).sum(axis=0).astype(vecteurs.dtype)


def _genere_brut(modele, mode: str, texte: str, instruct: str, speaker: str,
                 seed: int, temperature: float):
    import mlx.core as mx
    import numpy as np

    mx.random.seed(seed)
    kw = {"instruct": instruct} if instruct else {}
    poids = None
    if mode == "customvoice":
        poids = _parse_timbre(speaker)
        # `generate_custom_voice` valide le nom du timbre : on lui donne le composant
        # dominant, dont le vecteur sera de toute façon remplacé par le mélange.
        kw["voice"] = max(poids, key=poids.get)

    if poids and len(poids) == 1:
        poids = None            # timbre pur : aucune raison de passer par le proxy
    if poids is None:
        morceaux = list(modele.generate(text=texte, lang_code="french",
                                        temperature=temperature, **kw))
        return np.array(mx.concatenate([m.audio for m in morceaux]))

    table = modele.talker.model.codec_embedding
    modele.talker.model.codec_embedding = _ProxyTimbre(table,
                                                       _vecteur_timbre(modele, poids))
    try:
        morceaux = list(modele.generate(text=texte, lang_code="french",
                                        temperature=temperature, **kw))
        return np.array(mx.concatenate([m.audio for m in morceaux]))
    finally:
        # Restaurer même en cas d'erreur : un proxy laissé en place corromprait toutes
        # les répliques suivantes du même processus.
        modele.talker.model.codec_embedding = table


def _genere(modele, mode: str, texte: str, instruct: str, speaker: str, seed: int,
            temperature: float, essais: int = 3):
    """Génère une réplique, en relançant sur une autre graine si le clip est aberrant.

    La graine change à chaque essai : rejouer la même donnerait exactement le même clip
    cassé. Au bout des essais, on rend le dernier obtenu avec un avertissement — un clip
    douteux signalé vaut mieux qu'un trou dans la distribution.
    """
    onde, raison = None, ""
    for essai in range(essais):
        onde = _genere_brut(modele, mode, texte, instruct, speaker,
                            seed + essai * 977, temperature)
        raison = _suspect(onde, modele.sample_rate, texte)
        if not raison:
            return onde, essai
        print(f"        clip suspect ({raison}) — nouvelle graine", flush=True)
    print(f"        ATTENTION : {essais} essais suspects, dernier conservé ({raison})",
          file=sys.stderr, flush=True)
    return onde, essais


def _ecrit(onde, sr: int, cible: Path, format_: str) -> None:
    import soundfile as sf

    cible.parent.mkdir(parents=True, exist_ok=True)
    if format_ == "wav":
        sf.write(str(cible), onde, sr)
        return
    # Godot lit l'Ogg Vorbis nativement (convention BATE : assets/audio/*.ogg). Le ffmpeg
    # de Homebrew est construit sans libvorbis, d'où `oggenc` en premier — même contrainte
    # que dans character_lines.py.
    tmp = cible.with_suffix(".tmp.wav")
    sf.write(str(tmp), onde, sr)
    try:
        if OGGENC:
            subprocess.run([OGGENC, "-Q", "-q", "5", "-o", str(cible), str(tmp)], check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                            "-c:a", "vorbis", "-strict", "-2", "-q:a", "5", str(cible)],
                           check=True)
    finally:
        tmp.unlink(missing_ok=True)


def _instruct_replique(replique: dict, travail: dict, args) -> str:
    """Consigne de jeu d'une réplique. L'ordre de priorité va du plus précis au moins.

    `instruct` explicite dans la réplique > registre nommé dans la réplique > registre
    du rôle > registre du travail > défaut. Une réplique peut ainsi être jouée à part
    (un cri, un aveu) sans sortir du registre général du personnage.
    """
    if replique.get("instruct"):
        return replique["instruct"]
    nom = (replique.get("registre")
           or REGISTRE_PAR_ROLE.get(replique.get("role", ""))
           or travail.get("registre") or args.registre)
    return REGISTRES.get(nom, REGISTRES[REGISTRE_DEFAUT])


def _seed_de(identifiant: str, base: int) -> int:
    """Graine reproductible dérivée de l'id : régénérer une réplique redonne le clip.

    `hash()` est randomisé par processus en Python 3, donc inutilisable ici : deux
    exécutions donneraient deux voix. On somme les octets, c'est stable et suffisant.
    """
    return base + sum(identifiant.encode("utf-8")) % 10_000


# --- production de répliques ---------------------------------------------------
def cmd_lines(args) -> int:
    if args.jobs:
        travaux = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    else:
        nom = Path(args.out_dir).name
        travaux = [{"nom": nom[len("lines_"):] if nom.startswith("lines_") else nom,
                    "lines": args.lines, "out_dir": args.out_dir}]

    modele = _charge(args.mode)
    total, relances, suspects = 0, 0, 0
    for numero, travail in enumerate(travaux, start=1):
        nom = travail.get("nom", f"role{numero}")
        repliques = json.loads(Path(travail["lines"]).read_text(encoding="utf-8"))
        if args.limite:
            repliques = repliques[:args.limite]
        sortie = Path(travail["out_dir"])
        sortie.mkdir(parents=True, exist_ok=True)
        speaker = travail.get("speaker") or args.speaker
        # En voicedesign, le timbre vient de la description : elle doit accompagner
        # CHAQUE réplique, préfixée au registre, sinon la voix change de personnage.
        timbre = travail.get("description") or args.description or ""
        print(f"\n=== [{numero}/{len(travaux)}] {nom} : {len(repliques)} répliques "
              f"({args.mode}" + (f", {speaker}" if args.mode == "customvoice" else "")
              + ") ===", flush=True)

        manifeste, faits, ignores = [], 0, 0
        t0 = time.time()
        for i, replique in enumerate(repliques, start=1):
            cible = sortie / f"{replique['id']}.{args.format}"
            entree = {"id": replique["id"], "texte": replique["texte"],
                      "fichier": cible.name}
            if cible.exists() and cible.stat().st_size > 500 and not args.force:
                manifeste.append(entree)
                continue
            if not _PRONONCABLE.search(replique["texte"]):
                print(f"  [{i}/{len(repliques)}] {replique['id']} ignoré "
                      f"(rien à prononcer : {replique['texte']!r})", flush=True)
                ignores += 1
                continue
            consigne = _instruct_replique(replique, travail, args)
            instruct = f"{timbre} {consigne}".strip() if timbre else consigne
            onde, essais = _genere(modele, args.mode, replique["texte"], instruct,
                                   speaker, _seed_de(replique["id"], args.seed),
                                   args.temperature)
            _ecrit(onde, modele.sample_rate, cible, args.format)
            relances += essais
            if essais >= 3:
                suspects += 1
            duree = len(onde) / modele.sample_rate
            entree["instruct"] = consigne
            manifeste.append(entree)
            faits += 1
            total += 1
            print(f"  [{i}/{len(repliques)}] {replique['id']} ✓ {duree:4.1f}s  "
                  f"«{replique['texte'][:44]}»", flush=True)

        (sortie / "manifest.json").write_text(
            json.dumps({"personnage": nom, "mode": args.mode,
                        "speaker": speaker if args.mode == "customvoice" else None,
                        "description": timbre or None, "repliques": manifeste},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        ecoule = time.time() - t0
        print(f"  → {faits} produites, {len(manifeste) - faits} déjà là, "
              f"{ignores} sans texte  ({ecoule / 60:.1f} min)", flush=True)

    print(f"\n[q3tts] {total} répliques générées, {relances} relances, "
          f"{suspects} clips restés suspects")
    return 0


# --- auditions ----------------------------------------------------------------
def cmd_sample(args) -> int:
    """Un clip unique, pour entendre un timbre ou un registre avant de lancer la masse."""
    modele = _charge(args.mode)
    consigne = REGISTRES.get(args.registre, args.registre)
    instruct = f"{args.description} {consigne}".strip() if args.description else consigne
    onde, _ = _genere(modele, args.mode, args.texte, instruct, args.speaker,
                      args.seed, args.temperature)
    out = Path(args.out)
    _ecrit(onde, modele.sample_rate, out, "wav" if out.suffix == ".wav" else args.format)
    print(f"✅ {out}  ({len(onde) / modele.sample_rate:.1f}s)")
    subprocess.call(["afplay", str(out)])
    return 0


def cmd_auditionne_speakers(args) -> int:
    """Les neuf timbres premium sur la même phrase : le choix du timbre est une écoute."""
    modele = _charge("customvoice")
    dossier = Path(args.out_dir or (RACINE / "training/forge/_auditions"))
    dossier.mkdir(parents=True, exist_ok=True)
    consigne = REGISTRES.get(args.registre, args.registre)
    for speaker in SPEAKERS:
        cible = dossier / f"speaker_{speaker}.wav"
        onde, _ = _genere(modele, "customvoice", args.texte, consigne, speaker,
                          args.seed, args.temperature)
        _ecrit(onde, modele.sample_rate, cible, "wav")
        print(f"▶ {speaker:9s} {len(onde) / modele.sample_rate:4.1f}s  {cible}", flush=True)
        if not args.silencieux:
            subprocess.call(["afplay", str(cible)])
    print(f"\n[q3tts] clips dans {dossier}")
    return 0


def cmd_auditionne_registres(args) -> int:
    """Le même texte dans tous les registres : vérifie que le jeu porte, avant la masse."""
    modele = _charge(args.mode)
    dossier = Path(args.out_dir or (RACINE / "training/forge/_auditions"))
    dossier.mkdir(parents=True, exist_ok=True)
    for nom, consigne in REGISTRES.items():
        cible = dossier / f"registre_{nom}.wav"
        instruct = f"{args.description} {consigne}".strip() if args.description else consigne
        onde, _ = _genere(modele, args.mode, args.texte, instruct, args.speaker,
                          args.seed, args.temperature)
        _ecrit(onde, modele.sample_rate, cible, "wav")
        print(f"▶ {nom:14s} {len(onde) / modele.sample_rate:4.1f}s  {cible}", flush=True)
        if not args.silencieux:
            subprocess.call(["afplay", str(cible)])
    print(f"\n[q3tts] clips dans {dossier}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["customvoice", "voicedesign"], default="customvoice",
                    help="customvoice = timbre premium stable (production) ; "
                         "voicedesign = timbre libre décrit par prompt (exploration)")
    ap.add_argument("--speaker", default=SPEAKER_DEFAUT,
                    help=f"timbre en mode customvoice : un nom ({', '.join(SPEAKERS)}) ou "
                         f"un MÉLANGE pondéré, ex. « aiden:0.7+serena:0.3 » "
                         f"(défaut {SPEAKER_DEFAUT})")
    ap.add_argument("--description", default="",
                    help="description du timbre, en français (mode voicedesign)")
    ap.add_argument("--registre", default=REGISTRE_DEFAUT,
                    help=f"registre de jeu par défaut : {', '.join(REGISTRES)} "
                         "(ou une phrase libre)")
    ap.add_argument("--temperature", type=float, default=0.7,
                    help="0.7 : assez bas pour tenir le timbre, assez haut pour jouer")
    ap.add_argument("--seed", type=int, default=1000, help="base des graines (reproductible)")
    ap.add_argument("--format", default="ogg", choices=["ogg", "wav"])

    ap.add_argument("--lines", metavar="JSON", help="répliques [{id, texte, role}]")
    ap.add_argument("--out-dir", help="dossier de sortie des répliques")
    ap.add_argument("--jobs", metavar="JSON",
                    help="plusieurs rôles en une passe : [{nom, lines, out_dir, speaker}]")
    ap.add_argument("--limite", type=int, default=0, help="ne traiter que N répliques")
    ap.add_argument("--force", action="store_true", help="regénérer les clips existants")

    ap.add_argument("--sample", action="store_true", help="un seul clip d'audition")
    ap.add_argument("--texte", default="Papa, comment on sait qu'on a réussi ?",
                    help="phrase prononcée en audition")
    ap.add_argument("--out", default="/tmp/q3tts_sample.wav", help="fichier (--sample)")
    ap.add_argument("--auditionne-speakers", action="store_true",
                    help="les neuf timbres premium sur la même phrase")
    ap.add_argument("--auditionne-registres", action="store_true",
                    help="tous les registres sur la même phrase")
    ap.add_argument("--silencieux", action="store_true", help="ne pas jouer les clips")
    args = ap.parse_args()

    os.chdir(RACINE)
    if args.auditionne_speakers:
        return cmd_auditionne_speakers(args)
    if args.auditionne_registres:
        return cmd_auditionne_registres(args)
    if args.sample:
        return cmd_sample(args)
    if args.jobs or (args.lines and args.out_dir):
        return cmd_lines(args)
    ap.error("il faut --sample, --auditionne-speakers, --auditionne-registres, "
             "--jobs, ou --lines + --out-dir")


if __name__ == "__main__":
    sys.exit(main())
