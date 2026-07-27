#!/usr/bin/env python3
"""Pipeline de création de voix : une description en français → la voix d'Hermès.

    voice-agent forge propose "une voix féminine chaleureuse, débit vif" -n 5
    voice-agent forge listen  <slug>            # écoute les candidats
    voice-agent forge select  <slug> 3          # retient le candidat n°3
    voice-agent forge produce <slug>            # dataset + fine-tune + export (long)
    voice-agent forge status  [slug]

Chaîne complète, entièrement locale :

  1. **Descriptions** — le LLM local (`config.AGENT_MODEL`) traduit la demande française
     en N descriptions ANGLAISES au format attendu par Parler-TTS, en les faisant varier
     (timbre, débit, chaleur). Parler-TTS n'accepte que l'anglais pour décrire un timbre.
  2. **Candidats** — Parler-TTS génère un extrait par description (seed fixée, donc
     reproductible). C'est le seul des moteurs disponibles qui fabrique une voix depuis
     un texte descriptif : Kokoro n'a que des voix figées, Chatterbox clone un audio.
  3. **Choix humain** — écoute puis `select`. Rien ne s'entraîne sans validation.
  4. **Production** — Chatterbox multilingue clone le candidat retenu et relit tout le
     corpus français : audio plus propre que Parler-TTS, donc meilleur matériau. Repli
     automatique sur Parler-TTS si Chatterbox manque.
  5. **Entraînement** — `auto_pipeline.sh` (warmstart siwis, reprise sur crash, deadline)
     puis export ONNX vers un NOUVEAU fichier : la voix en service n'est jamais écrasée.
     La bascule reste une décision manuelle.

Chaque étape est reprenable et l'état vit dans `training/forge/<slug>/`.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent          # ~/workspace/voice-agent
FORGE = RACINE / "training" / "forge"
PY_VOICEDESIGN = RACINE / ".venv-voicedesign/bin/python"
PY_CHATTERBOX = RACINE / ".venv-chatterbox/bin/python"
PY_PROJET = RACINE / ".venv/bin/python"
# Qwen3-TTS tourne dans le venv MLX partagé du poste (mlx-audio y est déjà), pas dans un
# venv dédié : c'est le même interpréteur qui sert les autres modèles MLX.
PY_MLX = RACINE.parent / ".venv-mlx/bin/python"

TEXTE_AUDITION = ("Bonjour, je suis Hermès, votre assistant vocal. "
                  "Il est quinze heures, et il fait beau à Brindas.")

# Descriptions de repli si le LLM local est indisponible : ces axes de variation sont
# ceux qui s'entendent le plus (hauteur, débit, chaleur, proximité du micro).
VARIANTES_REPLI = [
    "A female speaker with a warm, friendly voice, speaking at a lively pace, very clear "
    "and close-sounding, no background noise.",
    "A female speaker with a bright, energetic voice, speaking quickly and cheerfully, "
    "very clear and close-sounding, no background noise.",
    "A female speaker with a low, warm, calm voice, speaking at a moderate pace, very "
    "clear and close-sounding, no background noise.",
    "A young female speaker with a soft, gentle voice, speaking at a lively pace, very "
    "clear recording, no background noise.",
    "A female speaker with a confident, expressive voice, speaking briskly with a smiling "
    "tone, very clear and close-sounding, no background noise.",
]


def _slugifie(texte: str) -> str:
    sans_accent = "".join(c for c in unicodedata.normalize("NFKD", texte)
                          if not unicodedata.combining(c))
    mots = re.findall(r"[a-z0-9]+", sans_accent.lower())[:4]
    return "-".join(mots) or "voix"


def _dossier(slug: str) -> Path:
    return FORGE / slug


def _lit_json(chemin: Path) -> dict:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ecrit_json(chemin: Path, donnees: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")


# --- 1) descriptions anglaises via le LLM local -------------------------------
def _descriptions_llm(demande: str, n: int) -> list:
    """Demande n descriptions Parler-TTS au LLM local. Liste vide si indisponible.

    Appel HTTP en `urllib` de la bibliothèque standard, pas en `requests` : ce script
    est lancé par le python SYSTÈME (3.9) parce qu'il ne fait qu'orchestrer des
    sous-process, chaque étape ayant son propre venv. Aucune dépendance externe ici.
    """
    import urllib.error
    import urllib.request

    sys.path.insert(0, str(RACINE / "scripts"))
    try:
        import config          # ne dépend que de os/pathlib, donc importable en 3.9
    except ImportError:
        return []

    consigne = (
        "Tu écris des descriptions de voix pour le modèle Parler-TTS. Une description est "
        "UNE phrase en ANGLAIS qui décrit un timbre : genre, hauteur, chaleur, débit, "
        "émotion, et se termine toujours par « very clear and close-sounding, no background "
        "noise. ». Ne décris JAMAIS le contenu parlé, seulement la voix.\n"
        f"Demande de l'utilisateur (en français) : « {demande} »\n"
        f"Produis exactement {n} variantes nettement DIFFÉRENTES les unes des autres "
        "(fais varier hauteur, débit, chaleur, âge), toutes fidèles à la demande.\n"
        "Réponds uniquement par un tableau JSON de chaînes, sans commentaire."
    )
    charge = json.dumps({
        "model": config.AGENT_MODEL, "stream": False, "think": False,
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "messages": [{"role": "user", "content": consigne}],
    }).encode("utf-8")
    requete = urllib.request.Request(config.OLLAMA_URL, data=charge,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=180) as reponse:
            brut = (json.load(reponse)["message"].get("content") or "").strip()
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        print(f"[forge] LLM indisponible ({e.__class__.__name__}), descriptions de repli",
              file=sys.stderr)
        return []
    # Le modèle encadre parfois le JSON de texte : on isole le premier tableau.
    m = re.search(r"\[.*\]", brut, re.S)
    if not m:
        return []
    try:
        liste = json.loads(m.group(0))
    except ValueError:
        return []
    return [str(x).strip() for x in liste if str(x).strip()][:n]


def cmd_propose(args) -> int:
    n = args.nombre
    descriptions = _descriptions_llm(args.demande, n)
    origine = "LLM local"
    if len(descriptions) < n:
        manque = n - len(descriptions)
        descriptions += VARIANTES_REPLI[:manque]
        origine = f"{origine} + repli" if descriptions else "repli"
    descriptions = descriptions[:n]

    slug = args.nom or f"{_slugifie(args.demande)}-{dt.datetime.now():%m%d-%H%M}"
    dossier = _dossier(slug)
    dossier.mkdir(parents=True, exist_ok=True)
    _ecrit_json(dossier / "request.json", {
        "demande": args.demande, "texte_audition": args.texte, "nombre": n,
        "cree": dt.datetime.now().isoformat(timespec="seconds"), "descriptions_via": origine,
    })

    print(f"[forge] {slug} — {n} candidats ({origine})")
    candidats = []
    for i, description in enumerate(descriptions, start=1):
        wav = dossier / f"cand_{i:02d}.wav"
        graine = 1000 + i          # graine déterministe : le candidat est reproductible
        print(f"\n[forge] candidat {i}/{n} (seed {graine})\n        {description}")
        if wav.exists() and wav.stat().st_size > 1000 and not args.force:
            print("        (déjà généré, ignoré)")
        else:
            code = subprocess.call([
                str(PY_VOICEDESIGN), str(RACINE / "training/voicedesign.py"), "--sample",
                "--description", description, "--text", args.texte,
                "--out", str(wav), "--seed", str(graine),
            ])
            if code != 0:
                print(f"        ÉCHEC (code {code})", file=sys.stderr)
                continue
        candidats.append({"n": i, "description": description, "seed": graine,
                          "wav": str(wav.relative_to(RACINE))})
    _ecrit_json(dossier / "candidates.json", {"slug": slug, "candidats": candidats})
    print(f"\n[forge] {len(candidats)} candidats prêts dans {dossier.relative_to(RACINE)}")
    print(f"[forge] écouter : voice-agent forge listen {slug}")
    print(f"[forge] choisir : voice-agent forge select {slug} <n>")
    return 0 if candidats else 1


# --- 2) écoute ----------------------------------------------------------------
def cmd_listen(args) -> int:
    dossier = _dossier(args.slug)
    donnees = _lit_json(dossier / "candidates.json")
    candidats = donnees.get("candidats") or []
    if not candidats:
        print(f"aucun candidat pour {args.slug}", file=sys.stderr)
        return 1
    voulus = [c for c in candidats if args.numero in (None, c["n"])]
    for c in voulus:
        print(f"\n▶ candidat {c['n']} (seed {c['seed']})\n  {c['description']}")
        # afplay sort sur le périphérique par défaut : l'enceinte du salon.
        subprocess.call(["afplay", str(RACINE / c["wav"])])
    print(f"\n[forge] retenir : voice-agent forge select {args.slug} <n>")
    return 0


def cmd_select(args) -> int:
    dossier = _dossier(args.slug)
    donnees = _lit_json(dossier / "candidates.json")
    choisi = next((c for c in donnees.get("candidats", []) if c["n"] == args.numero), None)
    if not choisi:
        print(f"candidat {args.numero} inconnu pour {args.slug}", file=sys.stderr)
        return 1
    _ecrit_json(dossier / "choice.json",
                {**choisi, "valide": dt.datetime.now().isoformat(timespec="seconds")})
    print(f"[forge] candidat {args.numero} retenu pour {args.slug}")
    print(f"[forge] produire la voix : voice-agent forge produce {args.slug}")
    return 0


# --- 3) production (dataset -> fine-tune -> export) ---------------------------
def cmd_produce(args) -> int:
    dossier = _dossier(args.slug)
    choix = _lit_json(dossier / "choice.json")
    if not choix:
        print(f"aucun candidat validé pour {args.slug} "
              f"(voice-agent forge select {args.slug} <n>)", file=sys.stderr)
        return 1

    reference = RACINE / choix["wav"]
    dataset = dossier / "dataset"
    sortie = args.sortie or f"models/tts/{args.voix}.onnx"
    if (RACINE / sortie).exists() and not args.force:
        print(f"{sortie} existe déjà — choisir --voix autrement, ou --force", file=sys.stderr)
        return 1

    moteur = args.moteur
    if moteur == "chatterbox" and not PY_CHATTERBOX.exists():
        print("[forge] Chatterbox absent, repli sur Parler-TTS", file=sys.stderr)
        moteur = "parler"

    dossier.mkdir(parents=True, exist_ok=True)
    journal = dossier / "produce.log"
    _ecrit_json(dossier / "production.json", {
        "moteur": moteur, "voix": args.voix, "sortie": sortie,
        "reference": choix["wav"], "lance": dt.datetime.now().isoformat(timespec="seconds"),
        "journal": str(journal.relative_to(RACINE)),
    })

    if moteur == "chatterbox":
        etape_dataset = [str(PY_CHATTERBOX), str(RACINE / "training/chatterbox_dataset.py"),
                         "--reference", str(reference), "--prompts", args.prompts,
                         "--out-dir", str(dataset)]
    else:
        etape_dataset = [str(PY_VOICEDESIGN), str(RACINE / "training/voicedesign.py"),
                         "--make-dataset", args.prompts, "--description", choix["description"],
                         "--seed", str(choix["seed"]), "--out-dir", str(dataset)]
    if args.limite and moteur == "chatterbox":
        etape_dataset += ["--limit", str(args.limite)]

    # L'entraînement dure des heures : tout est enchaîné dans un shell détaché, avec
    # un journal unique. `auto_pipeline.sh` est piloté par les variables FORGE_*, dont
    # FORGE_ONNX qui écrit la voix AILLEURS que sur celle en service.
    env_pipeline = " ".join([
        f"FORGE_DATASET={dataset.relative_to(RACINE)}",
        f"FORGE_PROMPTS={args.prompts}",
        f"FORGE_VOICE={args.voix}",
        f"FORGE_ONNX={sortie}",
        f"FORGE_LOGDIR={dossier.relative_to(RACINE)}",
        f"FORGE_DEADLINE_S={args.deadline * 3600}",
        f"FORGE_LOG={journal.relative_to(RACINE)}",
    ])
    script = (
        f"cd {RACINE} && "
        f"echo '===== FORGE {args.slug} : dataset ({moteur}) =====' >> {journal} && "
        f"{' '.join(etape_dataset)} >> {journal} 2>&1 && "
        f"echo '===== FORGE {args.slug} : entraînement =====' >> {journal} && "
        f"{env_pipeline} bash training/auto_pipeline.sh"
    )
    if args.dry_run:
        print(script)
        return 0

    subprocess.Popen(["nohup", "bash", "-c", script],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    print(f"[forge] production lancée en tâche de fond ({moteur} -> {sortie})")
    print(f"[forge] suivre  : tail -f {journal}")
    print(f"[forge] état    : voice-agent forge status {args.slug}")
    print(f"[forge] la voix en service n'est PAS touchée ; test à la fin :\n"
          f"        VA_VOICE={RACINE}/{sortie} ./voice-agent text \"Bonjour, voici ma nouvelle voix.\"")
    return 0


# --- 3 bis) répliques de personnage (voix de jeu) -----------------------------
def _extrait_repliques(dossier_dialogues: Path, personnage: str) -> list:
    """Répliques d'un personnage dans des timelines Dialogic (`Perso: texte`).

    Un personnage de jeu a un texte fini : on génère un fichier par réplique plutôt que
    d'entraîner une voix Piper (6 h) dont on n'a pas besoin en temps réel.
    """
    motif = re.compile(rf"^\s*{re.escape(personnage)}\s*:\s*(.+?)\s*$")
    repliques = []
    for timeline in sorted(dossier_dialogues.glob("*.dtl")):
        chapitre = re.search(r"(\d+)", timeline.stem)
        etiquette = f"ch{chapitre.group(1)}" if chapitre else timeline.stem
        n = 0
        for ligne in timeline.read_text(encoding="utf-8").splitlines():
            m = motif.match(ligne)
            if not m:
                continue
            texte = m.group(1).strip()
            # Les timelines contiennent des marqueurs Dialogic ([portrait], {var}…) :
            # ils ne doivent pas être prononcés.
            texte = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", texte)
            texte = re.sub(r"\s{2,}", " ", texte).strip()
            if not texte:
                continue
            n += 1
            repliques.append({"id": f"{_slugifie(personnage)}_{etiquette}_{n:02d}",
                              "chapitre": etiquette, "texte": texte,
                              "role": personnage, "source": timeline.name})
    return repliques


def cmd_lines(args) -> int:
    dossier = _dossier(args.slug)
    choix = _lit_json(dossier / "choice.json")
    # Qwen3-TTS part d'un timbre premium nommé, pas d'un WAV cloné : il n'a donc pas
    # besoin du candidat validé. Chatterbox, lui, ne peut rien faire sans référence.
    if not choix and args.moteur == "chatterbox":
        print(f"aucun candidat validé pour {args.slug} "
              f"(voice-agent forge select {args.slug} <n>)", file=sys.stderr)
        return 1
    if args.moteur == "chatterbox" and not PY_CHATTERBOX.exists():
        print("Chatterbox requis pour les répliques (venv .venv-chatterbox absent)",
              file=sys.stderr)
        return 1
    if args.moteur == "qwen3" and not PY_MLX.exists():
        print(f"Qwen3-TTS requis le venv MLX ({PY_MLX} absent)", file=sys.stderr)
        return 1

    dialogues = Path(args.dialogues).expanduser()
    repliques = [{**r, **_expressivite(args.personnage)}
                 for r in _extrait_repliques(dialogues, args.personnage)]
    if not repliques:
        print(f"aucune réplique de « {args.personnage} » dans {dialogues}", file=sys.stderr)
        return 1
    chapitres = sorted({r["chapitre"] for r in repliques})
    print(f"[forge] {len(repliques)} répliques de {args.personnage} "
          f"dans {len(chapitres)} timelines")

    fichier_lignes = dossier / f"lines_{_slugifie(args.personnage)}.json"
    fichier_lignes.write_text(json.dumps(repliques, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    sortie = Path(args.out_dir).expanduser() if args.out_dir else \
        dossier / f"lines_{_slugifie(args.personnage)}"

    if args.moteur == "qwen3":
        commande = [str(PY_MLX), str(RACINE / "training/qwen3tts.py"),
                    "--lines", str(fichier_lignes), "--out-dir", str(sortie),
                    "--speaker", args.speaker, "--format", args.format]
    else:
        commande = [str(PY_CHATTERBOX), str(RACINE / "training/character_lines.py"),
                    "--reference", str(RACINE / choix["wav"]),
                    "--lines", str(fichier_lignes), "--out-dir", str(sortie),
                    "--format", args.format]
    if args.limite:
        # Les deux moteurs n'ont pas nommé l'option pareil, et character_lines.py est
        # appelé ailleurs : on s'adapte au lieu de renommer une option publique.
        commande += ["--limite" if args.moteur == "qwen3" else "--limit", str(args.limite)]
    if args.dry_run:
        print(" ".join(commande))
        return 0

    journal = dossier / f"lines_{_slugifie(args.personnage)}.log"
    print(f"[forge] génération en tâche de fond -> {sortie}")
    print(f"[forge] suivre : tail -f {journal}")
    with journal.open("a", encoding="utf-8") as flux:
        subprocess.Popen(commande, stdout=flux, stderr=subprocess.STDOUT,
                         start_new_session=True)
    return 0


# --- 3 ter) distribution complète d'un jeu ------------------------------------
# « Note » est le pseudonyme d'Arthur et `narrator` sa voix intérieure (le jeu est
# narré à la première personne) : ces rôles doivent partager SA voix, sinon le même
# personnage parle avec trois timbres différents.
ALIAS_DEFAUT = {"Note": "Arthur", "narrator": "Arthur"}

# Expressivité Chatterbox par RÔLE, pas par personnage : Arthur parle en dialogue ET en
# narration, et l'introspection supporte mal l'emphase d'une scène d'action. Les deux
# paramètres se règlent ensemble — `cfg_weight` bride la liberté prosodique, donc monter
# `exaggeration` sans le baisser donne une voix forte mais raide.
# Validé à l'écoute le 2026-07-26 : sobre pour le narrateur, passionné pour les dialogues
# du héros. Les autres personnages restent sur le réglage sobre : ils n'ont pas été
# auditionnés dans ce registre, et exalter toute la distribution serait un choix non validé.
EXPRESSIVITE_SOBRE = {"exaggeration": 0.6, "cfg_weight": 0.5}
EXPRESSIVITE_PASSIONNEE = {"exaggeration": 0.85, "cfg_weight": 0.35}
EXPRESSIVITE_PAR_ROLE = {
    "narrator": EXPRESSIVITE_SOBRE,        # voix intérieure d'Arthur
    "Arthur": EXPRESSIVITE_PASSIONNEE,     # ses répliques parlées
    "Note": EXPRESSIVITE_PASSIONNEE,       # même personnage, sous pseudonyme
}

# Qwen3-TTS ne se règle pas par curseurs mais par une consigne de jeu nommée (voir
# REGISTRES dans qwen3tts.py). Le registre est écrit à côté des curseurs Chatterbox,
# dans la même réplique : chaque moteur y lit ce qu'il comprend, et changer de moteur ne
# demande pas de régénérer les fichiers de répliques.
REGISTRE_PAR_ROLE = {"narrator": "narration", "Arthur": "dialogue", "Note": "dialogue"}
REGISTRE_SOBRE = "narration"


def _expressivite(role: str) -> dict:
    return {**EXPRESSIVITE_PAR_ROLE.get(role, EXPRESSIVITE_SOBRE),
            "registre": REGISTRE_PAR_ROLE.get(role, REGISTRE_SOBRE),
            "role": role}


# Les neuf timbres premium de Qwen3-TTS CustomVoice, et le défaut retenu pour Arthur
# (mesuré : le seul des quatre masculins à tenir la cohésion de timbre sans clip
# dégénéré). La liste doit rester alignée sur SPEAKERS dans qwen3tts.py.
SPEAKERS_QWEN3 = ["aiden", "dylan", "eric", "ryan", "uncle_fu",
                  "serena", "vivian", "ono_anna", "sohee"]
SPEAKER_DEFAUT = "aiden"
# Genre entendu à l'audition (`qwen3tts.py --auditionne-speakers`). Sert uniquement à
# avertir : le tour de rôle ne SAIT pas qu'Alice est une fille, et donnait `eric`.
GENRE_TIMBRE = {"aiden": "M", "dylan": "M", "eric": "M", "ryan": "M", "uncle_fu": "M",
                "serena": "F", "vivian": "F", "ono_anna": "F", "sohee": "F"}
# Déclarés dialectaux dans la config du modèle (`spk_is_dialect` : sichuanais, pékinois).
# Ce sont eux qui ont produit les clips dégénérés en français : écartés du tour de rôle.
SPEAKERS_DIALECTAUX = {"eric", "dylan"}


def _parse_poids(spec: str) -> dict:
    """« aiden » ou « aiden:0.7+serena:0.3 » -> {nom: poids}. Miroir de qwen3tts.py."""
    poids = {}
    for part in spec.split("+"):
        nom, _, valeur = part.strip().partition(":")
        if nom.strip():
            poids[nom.strip().lower()] = float(valeur) if valeur.strip() else 1.0
    return poids


def _genre_melange(spec: str) -> str:
    """Genre entendu d'un timbre, mélange compris : M, F, ou « M+F » s'il est mixte."""
    genres = {GENRE_TIMBRE.get(n, "?") for n in _parse_poids(spec)}
    return "+".join(sorted(genres))


def _timbres_explicites(forces: list) -> dict:
    attribution = {}
    for paire in forces:
        if "=" in paire:
            role, timbre = paire.split("=", 1)
            attribution[role.strip()] = timbre.strip()
    return attribution


def _moteur_du_role(voix: str, timbres: dict, moteur: str) -> str:
    """En hybride, avoir un timbre fixé décide : Qwen3 pour ce rôle, Chatterbox sinon."""
    if moteur != "hybride":
        return moteur
    return "qwen3" if voix in timbres else "chatterbox"


def _attribue_timbres(recensement: dict, explicites: dict, defaut: str) -> dict:
    """Un timbre par personnage, du plus bavard au moins.

    Les neuf timbres premium ne suffisent pas à une distribution de trente rôles, mais
    ils se **mélangent** : une combinaison pondérée de leurs embeddings donne un timbre
    intermédiaire réel (`aiden:0.7+serena:0.3`), donc l'espace des voix est continu et la
    limite n'est plus le nombre de timbres. Ce tour de rôle ne fait que remplir avec des
    timbres purs — il ne sait rien du genre ni de l'âge des personnages. Les rôles qui
    comptent se fixent à la main, éventuellement en mélange.
    """
    attribution = dict(explicites)
    libres = [t for t in SPEAKERS_QWEN3
              if t not in attribution.values() and t not in SPEAKERS_DIALECTAUX] \
        or [t for t in SPEAKERS_QWEN3 if t not in SPEAKERS_DIALECTAUX]
    i = 0
    for voix in recensement:                      # déjà trié par nombre de répliques
        if voix in attribution:
            continue
        attribution[voix] = libres[i % len(libres)]
        i += 1
    return attribution


def _recense(dossier_dialogues: Path, alias: dict) -> dict:
    """Compte les répliques par voix (alias résolus). Rend {voix: [rôles]} et le total."""
    compte, roles = {}, {}
    motif = re.compile(r"^\s*([A-Za-zÀ-ÿ' -]{2,25}?)\s*:\s*\S")
    for timeline in sorted(dossier_dialogues.glob("*.dtl")):
        for ligne in timeline.read_text(encoding="utf-8").splitlines():
            m = motif.match(ligne)
            if not m:
                continue
            role = m.group(1).strip()
            voix = alias.get(role, role)
            compte[voix] = compte.get(voix, 0) + 1
            roles.setdefault(voix, set()).add(role)
    return {v: {"repliques": n, "roles": sorted(roles[v])}
            for v, n in sorted(compte.items(), key=lambda kv: -kv[1])}


def _description_personnage(nom: str, extraits: list) -> str:
    """Fait déduire au LLM local une description de voix depuis les répliques du rôle."""
    import urllib.error
    import urllib.request

    sys.path.insert(0, str(RACINE / "scripts"))
    try:
        import config
    except ImportError:
        return ""
    echantillon = "\n".join(f"- « {t} »" for t in extraits[:6])
    consigne = (
        "Tu écris UNE description de voix en ANGLAIS pour le modèle Parler-TTS, à partir "
        "des répliques d'un personnage de jeu vidéo (adaptation du roman The Beginning "
        "After The End).\n"
        f"Personnage : {nom}\nRépliques :\n{echantillon}\n\n"
        "Déduis le genre, l'âge approximatif, le timbre et le tempérament. La description "
        "fait UNE phrase, en anglais, décrit SEULEMENT la voix (jamais le contenu), et "
        "finit par « very clear and close-sounding, no background noise. »\n"
        "Réponds uniquement par cette phrase."
    )
    charge = json.dumps({
        "model": config.AGENT_MODEL, "stream": False, "think": False,
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "messages": [{"role": "user", "content": consigne}],
    }).encode("utf-8")
    requete = urllib.request.Request(config.OLLAMA_URL, data=charge,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=180) as reponse:
            texte = (json.load(reponse)["message"].get("content") or "").strip()
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return ""
    # Le modèle ajoute parfois des guillemets ou une phrase d'introduction.
    texte = texte.strip().strip('"').strip()
    return texte.splitlines()[-1].strip().strip('"') if texte else ""


def cmd_cast(args) -> int:
    dialogues = Path(args.dialogues).expanduser()
    alias = dict(ALIAS_DEFAUT)
    for paire in (args.alias or []):
        if "=" in paire:
            role, voix = paire.split("=", 1)
            alias[role.strip()] = voix.strip()
    exclus = {x.strip() for x in (args.exclure or "").split(",") if x.strip()}

    recensement = _recense(dialogues, alias)
    retenus = [(v, d) for v, d in recensement.items()
               if d["repliques"] >= args.min_repliques and v not in exclus]
    if args.personnages:
        voulus = {x.strip() for x in args.personnages.split(",")}
        retenus = [(v, d) for v, d in retenus if v in voulus]
    if not retenus:
        print("aucun personnage retenu", file=sys.stderr)
        return 1
    # Après le filtrage, et pas avant : les timbres ne doivent pas être consommés par des
    # rôles que `--min-repliques` ou `--exclure` viennent d'écarter.
    explicites = _timbres_explicites(args.timbre or [])
    timbres = _attribue_timbres(dict(retenus), explicites, args.speaker) \
        if args.moteur == "qwen3" else dict(explicites)
    # En hybride, `--timbre` fait double emploi et c'est voulu : donner un timbre à un
    # rôle, c'est le confier à Qwen3 ; ne rien donner le laisse à Chatterbox. Une option
    # de plus pour dire la même chose n'aurait fait qu'ouvrir la porte aux contradictions.
    moteurs = {v: _moteur_du_role(v, timbres, args.moteur) for v, _ in retenus}

    print(f"[cast] {len(retenus)} voix à produire "
          f"({sum(d['repliques'] for _, d in retenus)} répliques au total)")
    for voix, d in retenus:
        autres = [r for r in d["roles"] if r != voix]
        suffixe = f"  (+ {', '.join(autres)})" if autres else ""
        if moteurs[voix] == "qwen3":
            etiquette = f"  [qwen3 {timbres[voix]} {_genre_melange(timbres[voix])}]"
        else:
            etiquette = "  [chatterbox]"
        print(f"   {d['repliques']:>4}  {voix}{etiquette}{suffixe}")
    en_qwen3 = [v for v in moteurs if moteurs[v] == "qwen3"]
    if en_qwen3:
        print(f"[cast] Qwen3-TTS : {len(en_qwen3)} rôle(s) — émotion par prompt, RTF 0,29")
        auto = [v for v in en_qwen3 if v not in explicites]
        if auto:
            print(f"[cast] timbre attribué automatiquement (le genre du rôle est IGNORÉ, "
                  f"vérifier la colonne M/F) : {', '.join(auto)}")
        print(f"[cast] timbres M : "
              f"{', '.join(t for t in SPEAKERS_QWEN3 if GENRE_TIMBRE[t] == 'M')}"
              f"  |  F : {', '.join(t for t in SPEAKERS_QWEN3 if GENRE_TIMBRE[t] == 'F')}"
              f"  |  mélange pondéré : « aiden:0.7+serena:0.3 »")
        dialectaux = [v for v in en_qwen3
                      if SPEAKERS_DIALECTAUX & set(_parse_poids(timbres[v]))]
        if dialectaux:
            print(f"[cast] ATTENTION : {', '.join(dialectaux)} utilise(nt) un timbre "
                  f"dialectal ({', '.join(sorted(SPEAKERS_DIALECTAUX))}) — c'est de là que "
                  f"venaient les clips dégénérés en français.")
    reste = [v for v in moteurs if moteurs[v] == "chatterbox"]
    if reste and args.moteur == "hybride":
        print(f"[cast] Chatterbox : {len(reste)} rôle(s) — un timbre cloné par personnage")
    if args.dry_run:
        return 0

    FORGE.mkdir(parents=True, exist_ok=True)
    # Un plan de répliques PAR MOTEUR : les deux ne peuvent pas tourner en même temps
    # (deux modèles lourds ne cohabitent pas en RAM) et n'ont pas les mêmes entrées.
    plan_candidats, plans, etat = [], {"qwen3": [], "chatterbox": []}, {}
    for index, (voix, detail) in enumerate(retenus):
        moteur_voix = moteurs[voix]
        slug = f"bate-{_slugifie(voix)}"
        dossier = _dossier(slug)
        dossier.mkdir(parents=True, exist_ok=True)

        # Répliques de TOUS les rôles de cette voix (Arthur + Note + narrator…),
        # dans un seul fichier : c'est une seule voix à générer.
        repliques = []
        for role in detail["roles"]:
            for replique in _extrait_repliques(dialogues, role):
                # L'expressivité voyage AVEC la réplique : c'est le seul niveau où le
                # registre est connu (dialogue ou narration, pour un même personnage).
                repliques.append({**replique, **_expressivite(role)})
        if args.max_repliques:
            repliques = repliques[:args.max_repliques]
        fichier_lignes = dossier / "lines.json"
        fichier_lignes.write_text(json.dumps(repliques, ensure_ascii=False, indent=2),
                                  encoding="utf-8")

        deja = _lit_json(dossier / "candidates.json")
        if moteur_voix == "qwen3":
            # Rien à auditionner par personnage : le timbre est un premium (ou un mélange
            # de premiums), entendu une fois pour toutes avec
            # `qwen3tts.py --auditionne-speakers`. L'étape candidats de Parler-TTS n'a
            # plus d'objet pour ce rôle.
            candidats = deja.get("candidats") or []
            _ecrit_json(dossier / "request.json", {
                "demande": f"personnage BATE : {voix}", "roles": detail["roles"],
                "repliques": len(repliques), "descriptions_via": "timbre Qwen3-TTS",
                "speaker": timbres.get(voix, SPEAKER_DEFAUT),
                "cree": dt.datetime.now().isoformat(timespec="seconds"),
            })
        elif deja.get("candidats") and not args.force:
            candidats = deja["candidats"]
            print(f"[cast] {voix} : {len(candidats)} candidats déjà là")
        else:
            description = _description_personnage(voix, [r["texte"] for r in repliques])
            if not description:
                description = VARIANTES_REPLI[index % len(VARIANTES_REPLI)]
                print(f"[cast] {voix} : description de repli (LLM indisponible)",
                      file=sys.stderr)
            candidats = []
            for k in range(1, args.nombre + 1):
                # Graine décalée par personnage : deux rôles à description voisine ne
                # doivent pas tomber sur le même timbre.
                graine = 1000 + k * 7 + (abs(hash(voix)) % 400)
                wav = dossier / f"cand_{k:02d}.wav"
                candidats.append({"n": k, "description": description, "seed": graine,
                                  "wav": str(wav.relative_to(RACINE))})
                plan_candidats.append({
                    "description": description, "seed": graine, "out": str(wav),
                    "text": (repliques[0]["texte"] if repliques else TEXTE_AUDITION)[:200],
                })
            _ecrit_json(dossier / "candidates.json", {"slug": slug, "candidats": candidats})
            _ecrit_json(dossier / "request.json", {
                "demande": f"personnage BATE : {voix}", "roles": detail["roles"],
                "repliques": len(repliques), "descriptions_via": "LLM local",
                "cree": dt.datetime.now().isoformat(timespec="seconds"),
            })

        # En qwen3 il n'y a pas de candidat à retenir, donc rien à attendre : les
        # répliques peuvent partir tout de suite. `--auto-select` ne gouverne que la
        # chaîne Chatterbox, où il faut d'abord fixer le WAV de référence.
        if moteur_voix == "qwen3" or args.auto_select:
            choisi = None
            if moteur_voix != "qwen3":
                # Un choix validé À L'OREILLE ne doit jamais être écrasé par un choix
                # automatique : `--auto-select 1` avait ainsi ramené Arthur sur le
                # candidat 1 alors que le 2 avait été retenu après écoute.
                existant = _lit_json(dossier / "choice.json")
                if existant and not existant.get("auto"):
                    choisi = existant
                    print(f"[cast] {voix} : candidat {choisi['n']} conservé (choix manuel)")
                else:
                    choisi = next((c for c in candidats if c["n"] == args.auto_select),
                                  candidats[0])
                    _ecrit_json(dossier / "choice.json",
                                {**choisi, "valide": "auto", "auto": True})
            # Même convention de chemin que `forge lines`, pour ne pas générer deux fois
            # les mêmes répliques dans deux dossiers différents.
            sortie = Path(args.out_root).expanduser() / _slugifie(voix) if args.out_root \
                else dossier / f"lines_{_slugifie(voix)}"
            tache = {"nom": voix, "lines": str(fichier_lignes), "out_dir": str(sortie),
                     "repliques": len(repliques)}
            if moteur_voix == "qwen3":
                tache["speaker"] = timbres.get(voix, SPEAKER_DEFAUT)
            else:
                tache["reference"] = str(RACINE / choisi["wav"])
            plans[moteur_voix].append(tache)
        etat[voix] = {"slug": slug, "repliques": len(repliques), "roles": detail["roles"],
                      "moteur": moteur_voix,
                      "timbre": timbres.get(voix) if moteur_voix == "qwen3" else None}

    _ecrit_json(FORGE / "cast.json", {
        "cree": dt.datetime.now().isoformat(timespec="seconds"),
        "auto_select": args.auto_select, "voix": etat,
    })
    journal = FORGE / "cast.log"
    etapes = []
    if plan_candidats:
        f = FORGE / "cast_candidats.json"
        f.write_text(json.dumps(plan_candidats, ensure_ascii=False, indent=2), encoding="utf-8")
        etapes.append((f"candidats ({len(plan_candidats)})",
                       f"{PY_VOICEDESIGN} training/voicedesign.py --batch {f}"))
    # Qwen3 d'abord : il tient 1600 répliques en une demi-heure là où Chatterbox y passe
    # la nuit, donc les rôles qui lui sont confiés sont écoutables tout de suite.
    for moteur_plan in ("qwen3", "chatterbox"):
        plan = plans[moteur_plan]
        if not plan:
            continue
        # Du plus court au plus long : les rôles secondaires sont écoutables au bout de
        # quelques minutes, au lieu d'attendre les trois heures du personnage principal.
        plan.sort(key=lambda t: t.get("repliques", 0))
        f = FORGE / f"cast_repliques_{moteur_plan}.json"
        f.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        if moteur_plan == "qwen3":
            commande = f"{PY_MLX} training/qwen3tts.py --jobs {f} --format {args.format}"
        else:
            commande = (f"{PY_CHATTERBOX} training/character_lines.py --jobs {f} "
                        f"--format {args.format}")
        # Reprise sur arrêt brutal : une production Chatterbox de plusieurs heures se fait
        # tuer par la pression mémoire de macOS (mesuré — swap saturé, process supprimé
        # sans trace Python), et le générateur rend aussi la main volontairement tous les
        # N clips (code 2) pour repartir d'un process neuf. Dans les deux cas la reprise
        # est la bonne réponse, puisque chaque clip produit est conservé. La limite de 40
        # passes couvre largement 1645 répliques, tout en empêchant une erreur permanente
        # de boucler indéfiniment. Qwen3 n'a pas cette fuite (MLX rend sa mémoire), mais
        # la boucle ne coûte rien et couvre les mêmes arrêts subis.
        etapes.append((
            f"répliques {moteur_plan} ({len(plan)} rôles, "
            f"{sum(t['repliques'] for t in plan)} répliques)",
            f"for essai in $(seq 1 40); do {commande} && break; "
            f"echo \"[cast] passe $essai terminée sans tout finir, reprise\"; "
            f"sleep 15; done"))
    if not etapes:
        print("[cast] rien à générer")
        return 0

    # Séquentiel et détaché : deux modèles lourds ne doivent pas cohabiter en RAM,
    # et la production complète dure des heures.
    script = f"cd {RACINE} && " + " && ".join(
        f"echo '===== {libelle} =====' >> {journal} && {commande} >> {journal} 2>&1"
        for libelle, commande in etapes)
    subprocess.Popen(["nohup", "bash", "-c", script], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    print(f"\n[cast] lancé en tâche de fond : {len(plan_candidats)} candidats"
          + (f", puis {len(plan_repliques)} rôles à doubler" if plan_repliques else ""))
    print(f"[cast] suivre : tail -f {journal}")
    print(f"[cast] état   : voice-agent forge status")
    return 0


# --- 4) état ------------------------------------------------------------------
def _pipeline_actif(motif: str) -> bool:
    """Vrai si un travail de forge tourne pour ce motif, hors shell orchestrateur.

    `pgrep -f` seul est trompeur : le shell détaché porte TOUTE la chaîne de commandes
    dans sa ligne d'appel, donc il matche l'étape 2 alors que l'étape 1 tourne encore.
    On écarte donc les shells — et on ne peut PAS se fier à la colonne `comm` de ps,
    que macOS tronque à 16 caractères (`/opt/homebrew/Ce`, où « python » a disparu).
    """
    ENVELOPPES = {"bash", "zsh", "sh", "dash", "nohup", "env", "timeout"}
    sortie = subprocess.run(["ps", "-Ao", "pid=,args="],
                            capture_output=True, text=True).stdout
    for ligne in sortie.splitlines():
        if motif not in ligne:
            continue
        morceaux = ligne.split(None, 1)
        if len(morceaux) < 2 or not morceaux[1].strip():
            continue
        executable = Path(morceaux[1].split()[0]).name
        if executable not in ENVELOPPES:
            return True
    return False


def _etape_en_cours(journal: Path) -> str:
    """Dernière étape annoncée dans un journal de forge (source de vérité)."""
    try:
        etapes = [l for l in journal.read_text(encoding="utf-8").splitlines()
                  if l.startswith("=====")]
    except OSError:
        return "—"
    return etapes[-1].strip("= ").strip() if etapes else "—"
def cmd_status(args) -> int:
    if not FORGE.exists():
        print("aucune forge lancée")
        return 0
    cast = _lit_json(FORGE / "cast.json")
    if cast and not args.slug:
        journal = FORGE / "cast.log"
        candidats = sum(1 for l in journal.read_text(encoding="utf-8").splitlines()
                        if l.startswith("[batch") and "✓" in l) if journal.exists() else 0
        print(f"=== distribution ({len(cast.get('voix', {}))} voix) ===")
        print(f"  étape       : {_etape_en_cours(journal)}")
        print(f"  candidats   : {candidats} générés")
        print(f"  Parler-TTS  : {'actif' if _pipeline_actif('voicedesign.py') else 'inactif'}")
        print(f"  Chatterbox  : {'actif' if _pipeline_actif('character_lines.py') else 'inactif'}")
    slugs = [args.slug] if args.slug else sorted(d.name for d in FORGE.iterdir() if d.is_dir())
    for slug in slugs:
        d = _dossier(slug)
        req, cand = _lit_json(d / "request.json"), _lit_json(d / "candidates.json")
        choix, prod = _lit_json(d / "choice.json"), _lit_json(d / "production.json")
        clips = len(list((d / "dataset/wavs").glob("*.wav"))) if (d / "dataset/wavs").exists() else 0
        print(f"\n=== {slug} ===")
        print(f"  demande     : {req.get('demande', '?')}")
        print(f"  candidats   : {len(cand.get('candidats', []))}")
        print(f"  choix       : {('n°' + str(choix['n'])) if choix else '— (à valider)'}")
        if prod:
            onnx = RACINE / prod["sortie"]
            etat = "prête" if onnx.exists() else "en cours"
            print(f"  production  : {prod['moteur']} -> {prod['sortie']} ({etat})")
            print(f"  dataset     : {clips} clips")
            print(f"  processus   : {'actif' if _pipeline_actif(slug) else 'inactif'}")
            if onnx.exists():
                print(f"  tester      : VA_VOICE={onnx} ./voice-agent text \"Bonjour.\"")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="voice-agent forge", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("propose", help="générer N voix candidates depuis une description")
    p.add_argument("demande", help="description en français (ex. « féminine chaleureuse, vive »)")
    p.add_argument("-n", "--nombre", type=int, default=5)
    p.add_argument("--texte", default=TEXTE_AUDITION, help="phrase prononcée par les candidats")
    p.add_argument("--nom", help="slug du dossier (défaut : dérivé de la demande + horodatage)")
    p.add_argument("--force", action="store_true", help="régénérer les candidats existants")
    p.set_defaults(fn=cmd_propose)

    p = sub.add_parser("listen", help="écouter les candidats")
    p.add_argument("slug")
    p.add_argument("numero", nargs="?", type=int, help="un seul candidat")
    p.set_defaults(fn=cmd_listen)

    p = sub.add_parser("select", help="retenir un candidat")
    p.add_argument("slug")
    p.add_argument("numero", type=int)
    p.set_defaults(fn=cmd_select)

    p = sub.add_parser("produce", help="dataset + fine-tune + export (heures, en fond)")
    p.add_argument("slug")
    p.add_argument("--moteur", choices=["chatterbox", "parler"], default="chatterbox")
    p.add_argument("--voix", default="fr_hermes_v2", help="nom de la voix produite")
    p.add_argument("--sortie", help="chemin ONNX (défaut models/tts/<voix>.onnx)")
    p.add_argument("--prompts", default="training/prompts_fr.txt")
    p.add_argument("--deadline", type=float, default=6, help="heures d'entraînement max")
    p.add_argument("--limite", type=int, default=0, help="limiter le dataset (essai rapide)")
    p.add_argument("--force", action="store_true", help="accepter d'écraser la sortie")
    p.add_argument("--dry-run", action="store_true", help="afficher la commande sans lancer")
    p.set_defaults(fn=cmd_produce)

    p = sub.add_parser("lines", help="générer les répliques d'un personnage (voix de jeu)")
    p.add_argument("slug")
    p.add_argument("--moteur", choices=["chatterbox", "qwen3"], default="chatterbox",
                   help="qwen3 : émotion par prompt et timbre premium (3× plus rapide) ; "
                        "chatterbox : timbre cloné du candidat retenu (défaut)")
    p.add_argument("--speaker", default=SPEAKER_DEFAUT,
                   help=f"timbre en --moteur qwen3 : un nom premium ou un mélange pondéré "
                        f"(« aiden:0.7+serena:0.3 »). Défaut {SPEAKER_DEFAUT}")
    p.add_argument("--personnage", required=True, help="nom exact dans les timelines, ex. Alice")
    p.add_argument("--dialogues", default=str(Path.home() / "workspace/bate/dialogues"),
                   help="dossier des timelines Dialogic (*.dtl)")
    p.add_argument("--out-dir", help="défaut : training/forge/<slug>/lines_<personnage>/")
    p.add_argument("--format", default="ogg", choices=["ogg", "wav"])
    p.add_argument("--limite", type=int, default=0, help="n'en générer que N (essai)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_lines)

    p = sub.add_parser("cast", help="distribution complète d'un jeu (tous les personnages)")
    p.add_argument("--dialogues", default=str(Path.home() / "workspace/bate/dialogues"))
    p.add_argument("--moteur", choices=["chatterbox", "qwen3", "hybride"],
                   default="chatterbox",
                   help="qwen3 : tous les rôles en Qwen3-TTS (émotion par prompt) ; "
                        "hybride : Qwen3 pour les rôles ayant un --timbre, Chatterbox "
                        "pour les autres ; chatterbox : tout en clonage (défaut)")
    p.add_argument("--speaker", default=SPEAKER_DEFAUT,
                   help=f"timbre de repli en --moteur qwen3 (défaut {SPEAKER_DEFAUT})")
    p.add_argument("--timbre", action="append", metavar="ROLE=TIMBRE",
                   help="fixer le timbre d'un rôle : un nom premium (Tessia=serena) ou un "
                        "MÉLANGE pondéré (Arthur=aiden:0.7+serena:0.3). En --moteur "
                        "hybride, donner un timbre confie le rôle à Qwen3")
    p.add_argument("--min-repliques", type=int, default=5,
                   help="ignorer les rôles en dessous (défaut 5)")
    p.add_argument("--personnages", help="liste explicite, séparée par des virgules")
    p.add_argument("--exclure", default="", help="voix à ignorer, séparées par des virgules")
    p.add_argument("--alias", action="append",
                   help="rôle=voix (défaut : Note=Arthur, narrator=Arthur)")
    p.add_argument("-n", "--nombre", type=int, default=3, help="candidats par voix")
    p.add_argument("--auto-select", type=int, default=0, metavar="N",
                   help="retenir d'office le candidat N et enchaîner les répliques")
    p.add_argument("--max-repliques", type=int, default=0,
                   help="plafonner les répliques par voix (essai)")
    p.add_argument("--out-root", help="racine des sorties audio (défaut : dans forge/)")
    p.add_argument("--format", default="ogg", choices=["ogg", "wav"])
    p.add_argument("--force", action="store_true", help="regénérer les candidats existants")
    p.add_argument("--dry-run", action="store_true", help="afficher la distribution et sortir")
    p.set_defaults(fn=cmd_cast)

    p = sub.add_parser("status", help="état des forges")
    p.add_argument("slug", nargs="?")
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    os.chdir(RACINE)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
