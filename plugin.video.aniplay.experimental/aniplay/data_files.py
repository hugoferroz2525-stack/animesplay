"""Leitura dos índices distribuídos com o addon."""
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / 'resources' / 'data'


def load(filename):
    with (DIRECTORY / filename).open(encoding='utf-8') as stream:
        return json.load(stream)
