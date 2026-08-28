"""Génération du rapport Markdown et des graphiques du README.

Ce module constitue l'interface publique de la génération du README.
Les fonctions historiques restent dans ``stats_cli`` pour préserver les
imports internes et les tests, mais ne doivent plus être lancées directement.
"""

from .stats_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
