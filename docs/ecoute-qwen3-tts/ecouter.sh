#!/bin/bash
# Écoute guidée des voix d'Arthur. Usage : bash ecouter.sh [1|2|3]
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
