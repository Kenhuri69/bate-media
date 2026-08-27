#!/usr/bin/env python3
"""Attribue une voix à CHAQUE personnage qui parle, y compris les figurants.

    python3 tools/casting_troupe.py --dry-run
    python3 tools/casting_troupe.py
    python3 tools/casting_troupe.py --selftest

LE CADRE, POSÉ PAR LA MESURE. `catalogue_voix.py` a mesuré 759 voix candidates (mélanges à deux,
trois et quatre timbres × sept décalages) et n'en a trouvé que **17 réellement distinctes** en plus
des 17 en service — 10 masculines, 7 féminines. Il y a 119 personnages à doubler sur les cent
premiers chapitres et les arcs. Le plafond n'est donc pas une opinion : une voix propre par
personnage est impossible, et l'espace des mélanges ne le change pas.

LA RÈGLE RETENUE. Voix PROPRE aux personnages de trente répliques ou plus ; les autres partagent un
petit nombre de voix d'ARCHÉTYPE. Chaque personnage garde la même voix du premier au dernier
chapitre — c'est la seule chose qui ne se négocie pas, parce qu'un figurant qui change de timbre
entre deux scènes se lit comme un bug, alors que deux figurants qui partagent un timbre passent
inaperçus (c'est la pratique du doublage : les petits rôles sont tenus par les mêmes comédiens).

CE QUE CET OUTIL NE DEVINE PAS. Le genre d'un personnage ne s'invente pas : il est déduit de
preuves LOCALES — un titre accordé dans le libellé (« Doyenne », « Roi nain »), un motif non
ambigu dans les timelines (« la directrice Goodsky », « Rinia, elle »). Faute de preuve, le
personnage est marqué `genre: "?"` et reçoit une voix neutre de son archétype le plus proche, avec
la mention explicite. Mieux vaut un doute déclaré qu'un genre inventé.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

RACINE = Path.home() / "workspace"
MEDIA = Path(__file__).resolve().parent.parent
JEU = RACINE / "bate"
SORTIE = MEDIA / "resources" / "casting_troupe.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from empreinte import clip_id, dossier_de_voix, role_du_locuteur  # noqa: E402

SEUIL_VOIX_PROPRE = 30

# LA CIBLE D'ÉNERGIE EST PAR ARCHÉTYPE, et c'est le contrôle qui l'exige : `_cible` refuse de
# juger un lot dont plus de 5 % de l'énergie passe sous 150 Hz, parce qu'à ce moment la F0
# mesurée n'est plus un fondamental croyable et qu'une cible fausse signale des clips sains.
# Trente-quatre des quatre-vingt-treize voix de troupe étaient dans ce cas — toutes les graves.
#
# Une cible par archétype et non par personnage : les personnages d'un même archétype partagent
# LA MÊME voix, donc la même bande. Étalonner quatre-vingt-treize fois aurait mesuré douze fois
# la même chose, avec l'imprécision d'échantillons parfois réduits à trois clips.
#
# Les valeurs viennent de `etalonner` sur un représentant par archétype (celui qui a le plus de
# clips). Ce n'est PAS la F0 : c'est la bande qui capte le plus d'énergie sur le lot réel, et
# c'est exactement ce qu'un contrôle relatif à la médiane doit viser. Sur les voix aiguës les
# deux coïncident ; sur les graves l'étalonnage pointe une harmonique, ce qui reste un repère
# valide tant qu'il est le même pour tout le lot.
#
# Les archétypes de troupe, pris TELS QUELS dans les places neuves mesurées par
# `catalogue_voix.py` — aucune spec inventée ici. Les candidats dont la plage dépassait 60 Hz
# ont été écartés : une voix qui saute d'une réplique à l'autre ne fait pas un personnage, et
# c'est la leçon payée sur Sylvie (98 Hz livrés, lot refait).
ARCHETYPES = {
    # masculins, du plus grave au plus clair
    "m_grave":    {"timbre": "aiden:0.8+uncle_fu:0.2",              "decalage": 2.0,  "f0": 136, "cible": 150},
    "m_pose":     {"timbre": "aiden:0.5+uncle_fu:0.3+ryan:0.2",     "decalage": -3.0, "f0": 151, "cible": 150},
    "m_clair":    {"timbre": "aiden:0.8+uncle_fu:0.2",              "decalage": -3.0, "f0": 179, "cible": 205},
    "m_rugueux":  {"timbre": "uncle_fu:0.65+ryan:0.35",             "decalage": 1.0,  "f0": 180, "cible": 300},
    "m_quelconque": {"timbre": "uncle_fu:0.8+aiden:0.2",            "decalage": 0.0,  "f0": 188, "cible": 340},
    "m_jeune":    {"timbre": "uncle_fu:0.65+ryan:0.35",             "decalage": -2.0, "f0": 211, "cible": 340},
    # féminins, du plus grave au plus clair
    "f_autorite": {"timbre": "sohee:0.65+serena:0.35",              "decalage": 3.0,  "f0": 176, "cible": 175},
    "f_mure":     {"timbre": "serena:0.4+vivian:0.4+sohee:0.2",     "decalage": 3.0,  "f0": 216, "cible": 175},
    "f_adulte":   {"timbre": "serena:0.4+vivian:0.4+sohee:0.2",     "decalage": 1.0,  "f0": 243, "cible": 300},
    "f_jeune":    {"timbre": "ono_anna:0.65+vivian:0.35",           "decalage": -2.0, "f0": 268, "cible": 380},
    "f_claire":   {"timbre": "serena:0.5+sohee:0.3+ono_anna:0.2",   "decalage": -3.0, "f0": 289, "cible": 240},
    "f_enfant":   {"timbre": "ono_anna:0.8+sohee:0.2",              "decalage": -3.0, "f0": 298, "cible": 440},
}

# Indices d'âge et d'autorité lus dans le LIBELLÉ du locuteur. Ils ne devinent rien : « Roi nain »
# porte son registre, « Élève » aussi. Un libellé muet retombe sur la répartition par empreinte.
INDICES = [
    (r"\b(roi|doyen|ancien|vieil|vieux|patriarche|ma[îi]tre|seigneur|chancelier)\b", "m_grave"),
    (r"\b(doyenne|reine|matriarche|directrice|gardienne|professeure|instructrice)\b", "f_autorite"),
    (r"\b(capitaine|officier|g[eé]n[eé]ral|commandant|chef|intendant|juge|h[eé]raut)\b", "m_pose"),
    (r"\b([eé]l[eè]ve|enfant|gamin|apprenti|novice|petit)\b", "m_jeune"),
    (r"\b(serveuse|examinatrice|r[eé]ceptionniste|domestique|fermi[eè]re)\b", "f_adulte"),
    (r"\b(ivrogne|pillard|bandit|assaillant|inc?endiaire|ren[eé]gat|crieur|tenancier)\b",
     "m_quelconque"),
]

# Genre porté par le libellé lui-même : le mot EST la preuve, aucune sonde nécessaire.
GENRE_LIBELLE = [
    (r"\b(doyenne|reine|directrice|gardienne|professeure|instructrice|serveuse|examinatrice"
     r"|femme|fille|m[eè]re|s[oœ]ur|dame|princesse|comtesse|paysanne|fermi[eè]re)\b", "f"),
    (r"\b(roi|doyen|seigneur|prince|comte|ma[îi]tre|homme|gar[çc]on|p[eè]re|fr[eè]re|monsieur"
     r"|capitaine|g[eé]n[eé]ral|chancelier|h[eé]raut|crieur|tenancier|ivrogne|fermier"
     r"|aventurier|intendant|officier|guetteur|meneur|assaillant|renegat|ren[eé]gat)\b", "m"),
]

MOTIFS_GENRE = [
    (r"\b(la|La) (directrice|g[eé]n[eé]rale|professeure|conseill[eè]re|dame|reine|princesse)\s+{N}", "f"),
    (r"\b(le|Le) (directeur|g[eé]n[eé]ral|professeur|conseiller|seigneur|roi|prince)\s+{N}", "m"),
    (r"{N}[^.!?]{{0,40}}\b(est|était|s'est|semblait) (arriv[eé]e|partie|entr[eé]e|venue|rest[eé]e)", "f"),
    (r"{N}[^.!?]{{0,40}}\b(est|était|s'est|semblait) (arriv[eé]|parti|entr[eé]|venu|rest[eé])\b", "m"),
    (r"{N}\s*,\s*(elle|Elle)\b", "f"),
    (r"{N}\s*,\s*(il|Il)\b", "m"),
    (r"\b(Madame|Dame|Lady)\s+{N}", "f"),
    (r"\b(Monsieur|Sire|Seigneur)\s+{N}", "m"),
    (r"{N}\s+(elle-m[eê]me|toute seule)", "f"),
    (r"{N}\s+(lui-m[eê]me|tout seul)", "m"),
]

# Personnages dont plusieurs libellés désignent la même personne. Le jeu déduit le dossier de voix
# du PREMIER MOT du locuteur : « Directrice Goodsky » ne cherche pas dans `goodsky/`, il faut donc
# le déclarer — et c'est aussi vrai pour la production, sinon le clip naît au mauvais nom.
MEME_PERSONNE = {
    "Elijah Knight": "Elijah", "Directrice Goodsky": "Goodsky", "Professeur Gideon": "Gideon",
    "Général Varay": "Varay", "Elder Rinia": "Rinia", "Blaine Glayder": "Blaine",
    "Alduin Eralith": "Alduin", "Merial Eralith": "Merial", "Kathlyn Glayder": "Kathyln",
    "Chloe": "Chloé", "Curtis Glayder": "Curtis", "Claire Bladeheart": "Claire",
    "Tessia Eralith": "Tessia", "Virion Eralith": "Virion", "Alice Leywin": "Alice",
    "Ellie Leywin": "Ellie", "Reynolds Leywin": "Reynolds", "Note": "Arthur",
    "narrator": "Arthur",
}

REPL = re.compile(r"^\s*([A-Za-zÀ-ÿ][\w '\-À-ÿ]*)\s*:\s*(.+)$")


def _timelines(max_chapitre: int = 100) -> list:
    """Les timelines du périmètre : la trame jusqu'au chapitre demandé, et TOUS les arcs."""
    fichiers = []
    for f in sorted((JEU / "dialogues").glob("chapter_*.dtl")):
        m = re.search(r"chapter_(\d+)", f.name)
        if m and int(m.group(1)) <= max_chapitre:
            fichiers.append(f)
    fichiers += sorted((JEU / "dialogues/side").rglob("*.dtl"))
    return fichiers


def recense(max_chapitre: int = 100) -> tuple:
    """`{personnage: {libelles, repliques, manquants}}` et le texte joint des timelines."""
    voix = JEU / "assets/audio/voice"
    persos = {}
    textes = []
    for f in _timelines(max_chapitre):
        contenu = f.read_text(encoding="utf-8")
        textes.append(contenu)
        for ligne in contenu.splitlines():
            m = REPL.match(ligne)
            if not m:
                continue
            loc, texte = m.group(1).strip(), m.group(2).strip()
            ident = clip_id(loc, texte)
            if ident is None:
                continue
            nom = MEME_PERSONNE.get(loc, loc)
            e = persos.setdefault(nom, {"libelles": Counter(), "repliques": 0, "manquants": 0})
            e["libelles"][loc] += 1
            e["repliques"] += 1
            if not (voix / dossier_de_voix(role_du_locuteur(loc)) / f"{ident}.ogg").exists():
                e["manquants"] += 1
    return persos, "\n".join(textes)


# Prénoms rencontrés dans ce jeu, relevés dans les libellés eux-mêmes. Preuve FAIBLE — un prénom
# n'est pas un genre — mais infiniment meilleure que la répartition par défaut, qui envoyait
# Charlotte, Mary et Samantha en voix d'homme. Ne sert qu'après échec des preuves fortes.
PRENOMS_F = {"emily", "tabitha", "charlotte", "samantha", "mary", "priscilla", "myrtle",
             "chloé", "chloe", "doradrea", "solene", "maelis", "wenna", "perrine", "aldine",
             "claire", "sylvia", "nima", "alea", "glory", "kathyln", "kathlyn", "rinia",
             "varay", "merial", "goodsky", "cynthia", "helen", "angela", "lilia", "ellie",
             "alice", "tessia", "sylvie", "luna", "lise", "jasmine", "glaudera"}
PRENOMS_M = {"theodore", "roland", "nicolas", "george", "sebastian", "reginald", "charles",
             "clive", "kai", "jarrod", "brald", "danek", "himes", "broznean", "draneeve",
             "kriol", "oliver", "jack", "lucas", "curtis", "kaspian", "perrin", "feyrith",
             "blaine", "alduin", "gideon", "windsom", "elijah", "aldir", "kordri", "adam",
             "durden", "vincent", "reynolds", "virion", "arthur", "térence", "terence",
             "hadrien", "ansel", "bren", "joss", "dawsid", "geist", "avius", "mayner",
             "drywell", "orwin", "sorne", "cabestan", "valcourt", "ferrand", "aurelle"}

# Pronom sujet dans la fenêtre qui SUIT la mention du nom. Indice et non preuve : « il » peut
# désigner un tiers. On ne l'utilise donc qu'au vote, et seulement si un camp domine nettement.
FENETRE = 90
PRON_F = re.compile(r"\b(elle|Elle)\b")
PRON_M = re.compile(r"\b(il|Il)\b")


def genre_de(nom: str, libelles, tout: str) -> tuple:
    """`(genre, méthode)` — « f », « m » ou « ? », et d'où vient la preuve.

    Trois niveaux, du plus sûr au plus faible, et le premier qui parle décide :

    1. **le libellé** — « Doyenne », « Roi nain » : le mot EST la preuve ;
    2. **un motif accordé dans les timelines** — « la directrice Goodsky », « Rinia, elle », un
       participe accordé. Sans ambiguïté possible ;
    3. **un vote** entre le pronom sujet qui suit les mentions du nom et une table de prénoms.
       C'est un indice, pas une preuve, et il est nommé comme tel dans le registre.

    Le niveau 3 a été ajouté après mesure : sans lui, 77 personnages sur 113 restaient
    indéterminés, et la répartition par défaut les envoyait tous sur des voix masculines —
    Charlotte, Mary et Samantha comprises. Un indice déclaré vaut mieux qu'un défaut silencieux.
    """
    for brut, g in GENRE_LIBELLE:
        if any(re.search(brut, l, re.I) for l in libelles):
            return g, "libellé"
    votes = Counter()
    for brut, g in MOTIFS_GENRE:
        for l in libelles:
            if re.search(brut.replace("{N}", re.escape(l)), tout):
                votes[g] += 1
    if len(votes) == 1:
        return next(iter(votes)), "timeline"
    if votes:
        gagnant, n = votes.most_common(1)[0]
        if n >= 2 * sum(v for g, v in votes.items() if g != gagnant):
            return gagnant, "timeline (majorité)"

    # Niveau 3 : le prénom, puis le pronom de voisinage.
    mots = {m.lower() for l in libelles for m in re.split(r"[ '\-]", l) if len(m) > 2}
    if mots & PRENOMS_F and not mots & PRENOMS_M:
        return "f", "prénom (indice)"
    if mots & PRENOMS_M and not mots & PRENOMS_F:
        return "m", "prénom (indice)"
    f_ = m_ = 0
    for l in libelles:
        for occurrence in re.finditer(re.escape(l), tout):
            suite = tout[occurrence.end():occurrence.end() + FENETRE]
            f_ += len(PRON_F.findall(suite))
            m_ += len(PRON_M.findall(suite))
    if f_ + m_ >= 3:
        if f_ >= 2 * max(1, m_):
            return "f", f"pronom de voisinage (indice, {f_}/{m_})"
        if m_ >= 2 * max(1, f_):
            return "m", f"pronom de voisinage (indice, {m_}/{f_})"
    return "?", "indéterminé"


def archetype_de(nom: str, libelles, genre: str) -> tuple:
    """`(archétype, raison)`. Un indice de libellé décide ; sinon la répartition est STABLE.

    Stable et non aléatoire : l'archétype dérive du SHA-256 du nom, donc un même personnage
    retrouve sa voix à chaque exécution, y compris si de nouveaux personnages entrent au registre.
    Un tirage au sort aurait redistribué toute la troupe à chaque relance — et un figurant qui
    change de voix entre deux versions du pack s'entend comme un défaut.
    """
    for brut, arch in INDICES:
        if any(re.search(brut, l, re.I) for l in libelles):
            if genre == "?" or arch[0] == genre:
                return arch, "indice de libellé"
            jumeau = ("f" if genre == "f" else "m") + arch[1:]
            if jumeau in ARCHETYPES:
                return jumeau, "indice de libellé, transposé au genre"
    prefixe = "f_" if genre == "f" else "m_"
    dispo = sorted(a for a in ARCHETYPES if a.startswith(prefixe))
    n = int(hashlib.sha256(nom.encode("utf-8")).hexdigest()[:8], 16)
    return dispo[n % len(dispo)], "répartition stable par empreinte du nom"


def construire(max_chapitre: int = 100) -> dict:
    import voix_personnage

    persos, tout = recense(max_chapitre)
    # LES VOIX ÉCRITES EN CODE SEULEMENT. `PERSONNAGES` contient aussi, depuis le chargement du
    # registre, les figurants que CET outil a produits au tour précédent : les exclure ferait
    # rétrécir le registre à chaque exécution — mesuré, il tombait de 113 personnages à 31, et
    # les 82 disparus n'auraient plus jamais été produits. Une sortie qui devient une entrée
    # doit être retirée de l'entrée.
    deja = {p["nom"] for cle, p in voix_personnage.PERSONNAGES.items()
            if cle not in voix_personnage._TROUPE_AJOUTEE}
    fiches = {}
    for nom, e in sorted(persos.items(), key=lambda kv: -kv[1]["repliques"]):
        if nom in deja:
            continue                                  # voix propre déjà déclarée en code
        genre, methode = genre_de(nom, list(e["libelles"]), tout)
        fiche = {"roles": sorted(e["libelles"]), "repliques": e["repliques"],
                 "manquants": e["manquants"], "genre": genre, "genre_source": methode}
        if e["repliques"] >= SEUIL_VOIX_PROPRE:
            fiche["voix"] = "À CASTER"                # individuel : casting_timbre.py décide
        else:
            arch, raison = archetype_de(nom, list(e["libelles"]), genre)
            fiche.update({"archetype": arch, "archetype_source": raison,
                          "timbre": ARCHETYPES[arch]["timbre"],
                          "decalage": ARCHETYPES[arch]["decalage"]})
        fiches[nom] = fiche
    return {"version": "casting-troupe-1.0",
            "regle": f"voix propre au-dessus de {SEUIL_VOIX_PROPRE} répliques, archétype en dessous",
            "archetypes": ARCHETYPES, "personnages": fiches}


def _selftest() -> int:
    ok = True

    def check(nom, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'OK ' if cond else 'ECHEC'}] {nom}")

    g, m = genre_de("Doyenne de Loriande", ["Doyenne de Loriande"], "")
    check("le libellé « Doyenne » prouve le genre sans sonde", (g, m) == ("f", "libellé"))
    g, _ = genre_de("Goodsky", ["Goodsky", "Directrice Goodsky"], "")
    check("« Directrice Goodsky » vaut pour Goodsky", g == "f")
    g, m = genre_de("Xyz", ["Xyz"], "Xyz, il entra. Xyz, il repartit.")
    check("un motif non ambigu de timeline tranche", (g, m)[0] == "m")
    g, m = genre_de("Abc", ["Abc"], "Abc marchait. On parlait de Abc.")
    check("sans preuve, le genre reste « ? »", (g, m) == ("?", "indéterminé"))
    a1, _ = archetype_de("Roi nain", ["Roi nain"], "m")
    check("« Roi » va au registre grave", a1 == "m_grave")
    a2, r2 = archetype_de("Élève", ["Élève"], "f")
    check("un indice masculin se transpose au genre féminin", a2.startswith("f_") and "transpos" in r2)
    stable = {archetype_de("Jarrod", ["Jarrod"], "m")[0] for _ in range(5)}
    check("la répartition est stable d'un appel à l'autre", len(stable) == 1)
    check("tout archétype existe dans la table",
          all(archetype_de(n, [n], "m")[0] in ARCHETYPES for n in ("Kai", "Brald", "Danek")))
    check("les archétypes ne reprennent que des specs mesurées",
          all("+" in a["timbre"] for a in ARCHETYPES.values()))
    print("auto-test casting_troupe :", "OK" if ok else "ECHEC")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-chapitre", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    registre = construire(args.max_chapitre)
    fiches = registre["personnages"]
    a_caster = {n: f for n, f in fiches.items() if f.get("voix") == "À CASTER"}
    troupe = {n: f for n, f in fiches.items() if "archetype" in f}
    inconnus = [n for n, f in fiches.items() if f["genre"] == "?"]
    print(f"{len(fiches)} personnages sans voix · {sum(f['manquants'] for f in fiches.values())} "
          f"clips à produire")
    print(f"  {len(a_caster)} à caster individuellement (≥ {SEUIL_VOIX_PROPRE} répliques, "
          f"{sum(f['manquants'] for f in a_caster.values())} clips)")
    print(f"  {len(troupe)} en troupe sur {len(ARCHETYPES)} archétypes "
          f"({sum(f['manquants'] for f in troupe.values())} clips)")
    print(f"  {len(inconnus)} au genre indéterminé, déclaré tel quel\n")
    print("=== À CASTER ===")
    for n, f in sorted(a_caster.items(), key=lambda kv: -kv[1]["repliques"]):
        print(f"  {f['repliques']:4d}  {n:22s} genre {f['genre']} ({f['genre_source']})")
    print("\n=== TROUPE, par archétype ===")
    par_arch = {}
    for n, f in troupe.items():
        par_arch.setdefault(f["archetype"], []).append((f["repliques"], n))
    for arch in sorted(par_arch):
        lot = sorted(par_arch[arch], reverse=True)
        print(f"  {arch:12s} {ARCHETYPES[arch]['f0']:3d} Hz · {len(lot):2d} personnages · "
              f"{sum(r for r, _ in lot):4d} répliques")
        print(f"       {', '.join(n for _, n in lot[:8])}"
              + (f" … +{len(lot) - 8}" if len(lot) > 8 else ""))
    if args.dry_run:
        print("\n(dry-run) rien écrit")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(registre, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nécrit : {SORTIE.relative_to(MEDIA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
