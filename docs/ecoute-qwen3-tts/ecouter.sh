#!/bin/bash
# Écoute guidée des voix de BATE. Usage : bash ecouter.sh [1|2|3|4|5|6|6b]
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
