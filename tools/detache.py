#!/usr/bin/env python3
"""Lance une commande dans sa PROPRE session, à l'abri du signal qui tue le groupe.

    tools/detache.py journal.log -- ../.venv-mlx/bin/python -u tools/voix_personnage.py livrer arthur

POURQUOI. `nohup cmd &` ne suffit pas ici : le process garde le groupe de son shell, et quand
l'outil qui a lancé ce shell atteint son délai, le SIGTERM part au GROUPE entier — le job détaché
meurt avec lui. Mesuré le 2026-08-26 : une reprise de trois clips s'est arrêtée au deuxième, sans
une ligne d'erreur, deux fois de suite. `setsid` réglerait le problème mais n'existe pas sur
macOS ; `os.setsid()` est dans la bibliothèque standard.

Rend le PID sur stdout, pour pouvoir suivre le job sans dépendre de `pgrep -f`, dont la ligne de
commande visible est tronquée bien avant les arguments (même journée, même leçon).
"""
import os
import sys
from pathlib import Path


def main() -> int:
    if "--" not in sys.argv[2:] or len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    journal = Path(sys.argv[1])
    commande = sys.argv[sys.argv.index("--") + 1:]
    journal.parent.mkdir(parents=True, exist_ok=True)

    pid = os.fork()
    if pid:
        print(pid)
        return 0
    os.setsid()                                   # nouvelle session : plus de groupe partagé
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    os.execvp(commande[0], commande)
    return 1                                      # inatteignable


if __name__ == "__main__":
    sys.exit(main())
