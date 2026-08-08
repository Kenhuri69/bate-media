#!/bin/bash
# Écoute guidée des essais Qwen3-TTS pour Arthur. Usage : bash ecouter.sh [1|2|3|4|5|5b]
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
# Les timbres du lot 5, du moins dispersé au plus dispersé — l'ordre du verdict.
TOURNOI="aiden-0-5_serena-0-5 aiden-0-7_serena-0-3 aiden-0-9_vivian-0-1 aiden \
         aiden-0-8_vivian-0-2 aiden-0-6_serena-0-3_vivian-0-1 aiden-0-7_vivian-0-3"
if [ "$lot" = 5 ] || [ "$lot" = 0 ]; then
  # La même réplique enchaînée sur les 7 timbres : c'est la comparaison qui s'entend.
  # Deux répliques, parce qu'un timbre peut tenir sur l'une et s'écrouler sur l'autre —
  # c'est exactement ce que mesure la plage F0 (138 Hz sur l'une, 296 Hz sur l'autre).
  echo "=== 5. TOURNOI : 7 timbres, du plus stable au plus dispersé"
  for id in arthur_ch04_02 narrator_ch00_01; do
    echo "  --- $id"
    for t in $TOURNOI; do echo "     [$t]"; jouer "5-tournoi-arthur/$t/$id.ogg"; done
  done
fi
if [ "$lot" = 5b ]; then
  echo "=== 5b. TIMBRE RETENU (aiden:0.5+serena:0.5) sur les 8 répliques"
  echo "    reste-t-il le même personnage entre « Prêt. » et 14 s de narration ?"
  for f in 5-tournoi-arthur/aiden-0-5_serena-0-5/*.ogg; do jouer "$f"; done
fi
if [ "$lot" = 6 ] || [ "$lot" = 0 ]; then
  # Dans l'ordre de la VIE d'Arthur, pas dans celui des dossiers : le prologue est
  # chronologiquement premier (King Grey meurt) et vocalement le plus grave.
  echo "=== 6. ÂGES : la voix d'Arthur stade par stade, base aiden:0.5+ryan:0.5"
  echo "    131 Hz -> 245 -> 226 -> 225 -> 194   (enfant et ado sortent pareil : le défaut)"
  for s in prologue s02_toddler s03_child s04_teen s05_academy; do
    echo "  --- $s"
    for f in 6-ages-arthur/$s/*.ogg; do jouer "$f"; done
  done
fi
