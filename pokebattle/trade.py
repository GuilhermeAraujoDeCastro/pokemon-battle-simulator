"""Troca de Pokémon entre dois saves: em vez de gerenciar dois
savegame.json ao mesmo tempo, um jogador exporta um Pokémon pra um arquivo
".json" de troca, manda pro amigo por fora (email, pendrive, o que for), e o
amigo importa esse arquivo — cada lado com seu próprio save intacto.

Reaproveita o mesmo formato de "ficha" de teamcodec.py (pokemon_to_spec /
build_from_spec): trocar 1 Pokémon é só ler/escrever uma ficha num arquivo
em vez de dentro de um bloco de texto de time inteiro.
"""

import json
import random
from pathlib import Path
from typing import Any

from . import teamcodec


def export_pokemon_to_file(pokemon, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    spec = teamcodec.pokemon_to_spec(pokemon)
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")


def import_pokemon_spec_from_file(path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def import_pokemon_from_file(path, rng=random):
    """Lê o arquivo de troca e já devolve um Pokemon de verdade (via
    teamcodec.build_from_spec, que busca a espécie na PokeAPI)."""
    spec = import_pokemon_spec_from_file(path)
    return teamcodec.build_from_spec(spec, rng=rng)
