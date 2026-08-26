#!/bin/bash
# Écoute guidée des voix de BATE. Usage : bash ecouter.sh [1|2|3|4|5|6|6b|7|8|9]
#
# Ne restent ici que les clips qui documentent une décision ENCORE EN VIGUEUR : la voix
# en service, la comparaison qui a fait changer de moteur, et le repère de mesure. Les
# variantes écartées (9 timbres du premier balayage, 7 du tournoi, les 5 stades produits
# par dilution, les prompts perdants) ont été supprimées le 2026-08-08 — leurs mesures
# restent dans les README et les rapports JSON, et `git log` les rend si besoin.
cd "$(dirname "$0")"
lot=${1:-0}
jouer() { echo "  ▶ $1"; afplay "$1"; sleep 0.4; }

if [ "$lot" = 1 ] || [ "$lot" = 0 ]; then
  echo "=== 1. LA VOIX D'ARTHUR — aiden:0.5+ryan:0.5, timbre en service (~131 Hz)"
  jouer 4-melanges/aiden_0-5-ryan_0-5.wav
  echo "  --- le même timbre sur les répliques du stade toddler, sans prompt d'âge"
  for f in 7-age-par-prompt/nu/*.ogg; do jouer "$f"; done
fi

if [ "$lot" = 2 ] || [ "$lot" = 0 ]; then
  echo "=== 2. L'ÂGE PAR LE PROMPT — même timbre, « enfant-insistant » (164 Hz)"
  echo "    à comparer au lot 1 : c'est la seule différence, le timbre est identique"
  for f in 7-age-par-prompt/enfant-insistant/*.ogg; do jouer "$f"; done
fi

if [ "$lot" = 3 ] || [ "$lot" = 0 ]; then
  echo "=== 3. A/B MOTEUR : A = Chatterbox, B = Qwen3-TTS — ce qui a fait basculer"
  for f in 3-ab/*_A-chatterbox.ogg; do
    id=$(basename "$f" _A-chatterbox.ogg)
    echo "  --- $id"; jouer "$f"; jouer "3-ab/${id}_B-qwen3.ogg"
  done
fi

if [ "$lot" = 4 ] || [ "$lot" = 0 ]; then
  echo "=== 4. LES SIX ÂGES D'ARTHUR — même timbre, un prompt d'âge par stade"
  echo "    QUESTION POSÉE : entend-on un enfant qui grandit, ou un adulte qui parle plus haut ?"
  echo "    Mesuré : 289-308 Hz en parlé contre 209-214 en narration ; les stades, eux,"
  echo "    ne se distinguent pas entre eux. Détail : 8-ages-par-prompt/README.md"
  for d in prologue s02_toddler s03_road s03_child s04_teen s05_academy; do
    [ -d "8-ages-par-prompt/$d" ] || continue
    echo "  --- $d"
    for f in 8-ages-par-prompt/"$d"/*.ogg; do jouer "$f"; done
  done
fi

if [ "$lot" = 5 ] || [ "$lot" = 0 ]; then
  echo "=== 5. CASTING DE TESSIA — les 4 timbres féminins sur ses vraies répliques"
  echo "    Chaque timbre dit d'abord l'enfant de 5 ans (ch10-18), puis l'adolescente (ch44-60)."
  for t in serena vivian ono_anna sohee; do
    [ -d "9-casting-tessia/$t" ] || continue
    echo "  --- $t"
    for f in 9-casting-tessia/"$t"/*.ogg; do jouer "$f"; done
  done
fi

# Les mélanges du lot 10 : sohee et ono_anna sont repris tels quels du lot 5 (mêmes graines,
# mêmes clips), donc les entendre ici à côté des mélanges est une comparaison honnête.
MELANGES="sohee ono_anna sohee-0-7_ono_anna-0-3 sohee-0-5_ono_anna-0-5 sohee-0-3_ono_anna-0-7 \
sohee-0-8_serena-0-2 ono_anna-0-8_serena-0-2"

if [ "$lot" = 6 ] || [ "$lot" = 0 ]; then
  echo "=== 6. MÉLANGES POUR TESSIA — la MÊME réplique enchaînée sur les 7 doses"
  echo "    C'est l'ordre qui compte : deux timbres ne se comparent qu'à texte identique."
  echo "    D'abord l'enfant de 5 ans, puis l'adolescente. Aucun prompt d'âge : ce qui"
  echo "    bouge entre les deux, c'est le TEXTE qui le fait bouger."
  for id in tessia_ch11_09 tessia_ch45_03; do
    echo "  --- réplique $id"
    for t in $MELANGES; do
      [ -f "10-melanges-tessia/$t/$id.ogg" ] || continue
      echo "    · $t"; jouer "10-melanges-tessia/$t/$id.ogg"
    done
  done
  echo "    Puis : bash ecouter.sh 6b <dose>  — les 8 répliques d'une seule dose,"
  echo "    pour entendre si elle reste la même personne d'un « ...Je ne sais pas » à"
  echo "    un discours de 14 s. Doses : $MELANGES"
fi

if [ "$lot" = 6b ]; then
  t=${2:?usage : bash ecouter.sh 6b <dose>   (ex. sohee-0-5_ono_anna-0-5)}
  [ -d "10-melanges-tessia/$t" ] || { echo "dose inconnue : $t"; echo "→ $MELANGES"; exit 1; }
  echo "=== 6b. $t sur les 8 répliques — 4 enfant (ch11-14) puis 4 adolescente (ch45-50)"
  for f in 10-melanges-tessia/"$t"/*.ogg; do jouer "$f"; done
fi

if [ "$lot" = 7 ] || [ "$lot" = 0 ]; then
  echo "=== 7. CASTING DE VIRION — 3 timbres masculins, et Arthur en dit deux"
  echo "    La question n'est pas « lequel lui va » mais « lequel ne sera pas pris pour"
  echo "    Arthur » : CustomVoice n'a que trois voix d'homme utilisables et le mélange"
  echo "    d'Arthur en consomme deux (aiden + ryan). Écouter chaque réplique DANS LA"
  echo "    FOULÉE de la référence : c'est la confusion qu'on juge, pas le timbre seul."
  for f in "11-casting-virion/uncle_fu:0.5+aiden:0.5"/*.ogg; do
    id=$(basename "$f")
    echo "  --- réplique ${id%.ogg}"
    echo "    · ARTHUR (référence)"; jouer "11-casting-virion/_reference-arthur/$id"
    echo "    · TESSIA (référence)"; jouer "11-casting-virion/_reference-tessia/$id"
    echo "    · VIRION retenu"; jouer "$f"
  done
  echo "    uncle_fu PUR a été produit (350 clips) puis écarté : F0 201,7 Hz, soit 14 Hz de"
  echo "    Tessia, et 79 Hz de dispersion — le pire lot des quatre voix. Le mélange retenu"
  echo "    tombe à 130 Hz et 47 Hz. Détail : 11-casting-virion/README.md"
fi

if [ "$lot" = 9 ] || [ "$lot" = 0 ]; then
  echo "=== 9. VIRION PLUS GRAVE — la MÊME prise, descendue par rééchantillonnage"
  echo "    Le modèle ne sait pas descendre une voix : les six consignes « vieil homme »"
  echo "    essayées MONTENT toutes la F0 (+1 à +16 Hz). On descend donc le signal, en"
  echo "    rattrapant la durée par compression WSOLA : plus grave, PAS plus lent."
  echo "    Repères : Arthur parlé 131 Hz, Arthur narration 119 Hz, Tessia 216 Hz."
  for f in 13-grave-virion/temoin/*.ogg; do
    id=$(basename "$f")
    echo "  --- réplique ${id%.ogg}"
    for p in temoin moins2v0st moins3v0st moins4v0st; do
      [ -f "13-grave-virion/$p/$id" ] || continue
      echo "    · $p"; jouer "13-grave-virion/$p/$id"
    done
  done
  echo "    TRANCHÉ : -3 demi-tons. Vérifié sur les 350 clips livrés, clip par clip :"
  echo "    132 -> 114 Hz, dispersion inchangée, durée tenue à -0,02 %."
fi

if [ "$lot" = 8 ] || [ "$lot" = 0 ]; then
  echo "=== 8. CASTING DE SYLVIE — sa référence est TESSIA, pas Arthur"
  echo "    Deux voix féminines jeunes qui partagent la plupart de leurs scènes : c'est"
  echo "    entre elles deux que la confusion coûte, pas avec le narrateur."
  for f in "11-casting-sylvie/ono_anna:0.5+serena:0.5"/*.ogg; do
    id=$(basename "$f")
    echo "  --- réplique ${id%.ogg}"
    echo "    · TESSIA (référence)"; jouer "11-casting-sylvie/_reference-tessia/$id"
    echo "    · SYLVIE retenue"; jouer "$f"
  done
  echo "    vivian:0.7+serena:0.3 avait gagné le casting puis livré 98 Hz de dispersion."
  echo "    Le lot d'audition prend les répliques les PLUS LONGUES : sa plage sous-estime"
  echo "    celle du lot réel. Détail : 11-casting-sylvie/README.md"
fi

if [ "$lot" = 10 ] || [ "$lot" = 0 ]; then
  echo "=== 10. LUNA ET LISE — le couple que la mesure désigne, à valider à l'oreille"
  echo
  echo "    Luna = ono_anna:0.8+vivian:0.2  descendue de 2 demi-tons"
  echo "           237 Hz · plage 53 Hz · ambitus 3,2 st · Tessia 0,932"
  echo "    Lise = vivian:0.8+ono_anna:0.2  sans décalage"
  echo "           262 Hz · plage 39 Hz · ambitus 3,7 st · Tessia 0,903"
  echo
  echo "    Deux mélanges INVERSES des deux mêmes timbres. Aucun pur : les quatre féminins de"
  echo "    CustomVoice sont déjà pris (Tessia sohee, Alice vivian) ou trop proches de Tessia."
  echo "    Lise évite serena, qui est le second composant d'ELLIE (0,970 de cosinus) —"
  echo "    et Ellie sort désormais à 270 Hz, donc juste au-dessus de Lise."
  echo
  echo "    La hauteur place les quatre voix féminines jeunes sans en coller deux :"
  echo "      Tessia 213  <  LUNA 237  <  LISE 262  <  Ellie 270"
  echo
  echo "  --- A. LA PAIRE, chacune sur ses propres répliques, Tessia en tête"
  for f in "16-doses20-luna/_reference-tessia"/*.ogg; do
    echo "    · TESSIA (la voix à ne pas confondre)"; jouer "$f"; break
  done
  n=0
  for f in 20-hauteur-luna/luna-moins2st/*.ogg; do
    n=$((n+1)); [ $n -gt 3 ] && break
    echo "    · LUNA — ono_anna:0.8+vivian:0.2, -2 st"; jouer "$f"
  done
  n=0
  for f in "19-melanges20-lise/vivian:0.8+ono_anna:0.2"/*.ogg; do
    n=$((n+1)); [ $n -gt 3 ] && break
    echo "    · LISE — vivian:0.8+ono_anna:0.2"; jouer "$f"
  done

  echo
  echo "  --- B. LA HAUTEUR DE LUNA, seul point que la mesure ne tranche pas seule"
  echo "    Sans décalage elle sort à 265 Hz, soit 3 Hz de Lise : indistinguables. Descendre"
  echo "    la place entre Tessia et Lise, mais trop bas elle rejoint Tessia (piège déjà payé"
  echo "    sur Virion, qui fuyait Arthur par le haut et atterrissait sur Tessia)."
  echo "      sans shift 265 Hz  ·  -1 st 250  ·  -2 st 237 (proposé)  ·  -3 st 223"
  for f in 20-hauteur-luna/luna-sans-shift/*.ogg; do
    id=$(basename "$f")
    echo "    --- ${id%.ogg}"
    for v in luna-sans-shift luna-moins1st luna-moins2st luna-moins3st; do
      echo "      · $v"; jouer "20-hauteur-luna/$v/$id"
    done
  done
fi
