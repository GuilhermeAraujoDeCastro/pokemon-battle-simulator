"""Testes de pokebattle/trade.py: exportar/importar um Pokémon pra um
arquivo de troca. import_pokemon_from_file toca `roster` por baixo (via
teamcodec.build_from_spec), sempre com monkeypatch — nunca rede de verdade."""

import random

from pokebattle import roster, trade
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon():
    stats = {"hp": 78, "attack": 84, "defense": 78, "sp_atk": 109, "sp_def": 85, "speed": 100}
    mon = Pokemon("Charizard", ["fire", "flying"], 50, stats, [Move("Flamethrower", "fire", 90, "special")])
    mon.species = "charizard"
    mon.held_item = "held_leftovers"
    return mon


def test_export_writes_a_readable_json_spec(tmp_path):
    path = tmp_path / "trade.json"
    trade.export_pokemon_to_file(make_pokemon(), path)

    spec = trade.import_pokemon_spec_from_file(path)
    assert spec["species"] == "charizard"
    assert spec["held_item"] == "held_leftovers"
    assert spec["moves"] == ["Flamethrower"]


def test_import_pokemon_from_file_rebuilds_a_real_pokemon(tmp_path, monkeypatch):
    path = tmp_path / "trade.json"
    trade.export_pokemon_to_file(make_pokemon(), path)

    def fake_build_pokemon(species, level=roster.LEVEL, rng=random, ivs=None, nature=None):
        stats = {"hp": 78, "attack": 84, "defense": 78, "sp_atk": 109, "sp_def": 85, "speed": 100}
        mon = Pokemon("Charizard", ["fire", "flying"], level, stats,
                       [Move("Flamethrower", "fire", 90, "special")], ivs=ivs, nature=nature)
        mon.species = species
        mon.held_item = None
        return mon

    monkeypatch.setattr(roster, "build_pokemon", fake_build_pokemon)

    rebuilt = trade.import_pokemon_from_file(path)

    assert rebuilt.species == "charizard"
    assert rebuilt.held_item == "held_leftovers"
