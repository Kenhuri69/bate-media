#!/bin/bash
# Écoute guidée des essais Qwen3-TTS pour Arthur. Usage : bash ecouter.sh [1|2|3]
cd "$(dirname "$0")"
lot=${1:-0}
jouer() { echo "  ▶ $1"; afplay "$1"; sleep 0.4; }
if [ "$lot" = 1 ] || [ "$lot" = 0 ]; then
  echo "=== 1. TIMBRES : « Je... je le sens. C'est comme une petite flamme, tout au fond. »"
  echo "    (les 4 masculins d'abord — les 5 autres sont féminins/âgés)"
  for s in aiden dylan eric ryan; do jouer 1-timbres/speaker_$s.wav; done
fi
if [ "$lot" = 2 ] || [ "$lot" = 0 ]; then
  echo "=== 2. REGISTRES sur aiden : « Papa, comment on sait qu'on a réussi ? »"
  for r in narration dialogue emu colere peur joie determination; do
    jouer 2-registres/registre_$r.wav; done
fi
if [ "$lot" = 3 ] || [ "$lot" = 0 ]; then
  echo "=== 3. A/B : A = Chatterbox actuel, B = Qwen3-TTS (aiden)"
  for f in 3-ab/*_A-chatterbox.ogg; do
    id=$(basename "$f" _A-chatterbox.ogg)
    echo "  --- $id"; jouer "$f"; jouer "3-ab/${id}_B-qwen3.ogg"
  done
fi
if [ "$lot" = 4 ] || [ "$lot" = 0 ]; then
  echo "=== 4. MÉLANGES de timbres : « Je... je le sens. C'est comme une petite flamme... »"
  echo "    cohésion mesurée : aiden 0,948 | +serena.3 0,959 (la meilleure)"
  echo "                       +ryan.5 0,926 | +vivian.2 0,899 (mais la plus proche en hauteur)"
  for f in 4-melanges/*.wav; do jouer "$f"; done
  echo "  --- les 7 registres sur aiden:0.7+serena:0.3"
  for r in narration dialogue emu colere peur joie determination; do
    jouer "4-melanges/registres/registre_$r.wav"; done
fi
