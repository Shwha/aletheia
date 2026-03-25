"""
Entry point for `python -m aletheia`.

Allows running the CLI as a module: python -m aletheia eval --model ...
"""

from aletheia.cli import app

app()
