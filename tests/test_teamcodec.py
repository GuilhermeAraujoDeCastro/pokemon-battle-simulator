"""Testes de pokebattle/teamcodec.py: o texto (formatar/interpretar) é puro
e é o grosso da cobertura aqui; só build_from_spec toca `roster` (via
monkeypatch, nunca rede de verdade), no mesmo molde de test_gyms.py."""

import random

from pokebattle import roster, teamcodec
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon(name="Charizard", species="charizard", nickname_differs=False, held_item=None):
    stats = {"hp": 78, "attack": 84, "defense": 78, "sp_atk": 109, "sp_def": 85, "speed": 100}
    ivs = {"hp": 31, "attack": 31, "defense": 20, "sp_atk": 31, "sp_def": 31, "speed": 31}
    evs = {"hp": 0, "attack": 252, "defense": 0, "sp_atk": 0, "sp_def": 4, "speed": 252}
    moves = [Move("Flamethrower", "fire", 90, "special"), Move("Dragon Claw", "dragon", 80, "physical")]
    mon = Pokemon("Draco" if nickname_differs else name, ["fire", "flying"], 50, stats, moves,
                   ivs=ivs, evs=evs, nature="Timid")
    mon.species = species
    mon.held_item = held_item
    return mon


# ---------- serialização pura (sem tocar roster/rede) ----------

def test_pokemon_to_spec_captures_everything_needed_to_rebuild():
    mon = make_pokemon(held_item="held_leftovers")
    spec = teamcodec.pokemon_to_spec(mon)

    assert spec["species"] == "charizard"
    assert spec["nickname"] is None  # nome igual ao nome de exibição da espécie
    assert spec["nature"] == "Timid"
    assert spec["held_item"] == "held_leftovers"
    assert spec["moves"] == ["Flamethrower", "Dragon Claw"]


def test_pokemon_to_spec_keeps_a_real_nickname():
    mon = make_pokemon(nickname_differs=True)
    spec = teamcodec.pokemon_to_spec(mon)
    assert spec["nickname"] == "Draco"


def test_team_to_text_round_trips_through_text_to_specs():
    team = [make_pokemon(held_item="held_leftovers"), make_pokemon(nickname_differs=True, species="charizard")]
    text = teamcodec.team_to_text(team)
    specs = teamcodec.text_to_specs(text)

    assert len(specs) == 2
    assert specs[0]["species"] == "charizard"
    assert specs[0]["held_item"] == "held_leftovers"
    assert specs[0]["nature"] == "Timid"
    assert specs[0]["ivs"]["defense"] == 20
    assert specs[0]["evs"]["attack"] == 252
    assert specs[0]["moves"] == ["Flamethrower", "Dragon Claw"]
    assert specs[1]["nickname"] == "Draco"


def test_text_to_specs_handles_a_mon_without_a_held_item_or_nickname():
    text = "Pikachu\nLevel: 25\nNature: Jolly\n- Thunderbolt"
    specs = teamcodec.text_to_specs(text)

    assert specs[0]["species"] == "pikachu"
    assert specs[0]["nickname"] is None
    assert specs[0]["held_item"] is None
    assert specs[0]["level"] == 25
    assert specs[0]["moves"] == ["Thunderbolt"]


def test_text_to_specs_handles_multiple_mons_separated_by_blank_lines():
    text = "Pikachu\n- Thunderbolt\n\nBulbasaur\n- Vine Whip"
    specs = teamcodec.text_to_specs(text)
    assert [s["species"] for s in specs] == ["pikachu", "bulbasaur"]


# ---------- build_from_spec (toca roster, sempre via monkeypatch) ----------

def test_build_from_spec_forwards_species_level_ivs_and_nature(monkeypatch):
    captured = {}

    def fake_build_pokemon(species, level=roster.LEVEL, rng=random, ivs=None, nature=None):
        captured.update(species=species, level=level, ivs=ivs, nature=nature)
        stats = {"hp": 100, "attack": 100, "defense": 100, "sp_atk": 100, "sp_def": 100, "speed": 100}
        mon = Pokemon("Charizard", ["fire", "flying"], level, stats,
                       [Move("Tackle", "normal", 40, "physical")], ivs=ivs, nature=nature)
        mon.species = species
        mon.held_item = None
        return mon

    monkeypatch.setattr(roster, "build_pokemon", fake_build_pokemon)

    spec = {
        "species": "charizard", "nickname": "Draco", "level": 55, "nature": "Adamant",
        "ivs": {"hp": 31, "attack": 31, "defense": 31, "sp_atk": 31, "sp_def": 31, "speed": 31},
        "evs": {}, "held_item": "held_leftovers", "moves": [],
    }
    mon = teamcodec.build_from_spec(spec)

    assert captured["species"] == "charizard"
    assert captured["level"] == 55
    assert captured["nature"] == "Adamant"
    assert mon.name == "Draco"
    assert mon.held_item == "held_leftovers"


def test_build_from_spec_rebuilds_the_exact_moves(monkeypatch):
    def fake_build_pokemon(species, level=roster.LEVEL, rng=random, ivs=None, nature=None):
        stats = {"hp": 100, "attack": 100, "defense": 100, "sp_atk": 100, "sp_def": 100, "speed": 100}
        mon = Pokemon("Pikachu", ["electric"], level, stats, [Move("Tackle", "normal", 40, "physical")])
        mon.species = species
        mon.held_item = None
        return mon

    def fake_build_move(name):
        return Move("Thunderbolt", "electric", 90, "special")

    monkeypatch.setattr(roster, "build_pokemon", fake_build_pokemon)
    monkeypatch.setattr(roster, "_build_move", fake_build_move)

    spec = {"species": "pikachu", "nickname": None, "level": 50, "nature": "Timid",
            "ivs": {}, "evs": {}, "held_item": None, "moves": ["Thunderbolt"]}
    mon = teamcodec.build_from_spec(spec)

    assert [m.name for m in mon.moves] == ["Thunderbolt"]
