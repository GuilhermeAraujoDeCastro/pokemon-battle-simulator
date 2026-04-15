"""Testes de pokebattle/progression.py com a PokeAPI trocada por dados
falsos (via monkeypatch) — nada aqui toca a rede de verdade."""

import pytest

from pokebattle import pokeapi, progression
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon

FAKE_CHARMANDER = {
    "name": "charmander",
    "id": 4,
    "base_experience": 62,
    "types": [{"slot": 1, "type": {"name": "fire"}}],
    "stats": [
        {"base_stat": 39, "stat": {"name": "hp"}},
        {"base_stat": 52, "stat": {"name": "attack"}},
        {"base_stat": 43, "stat": {"name": "defense"}},
        {"base_stat": 60, "stat": {"name": "special-attack"}},
        {"base_stat": 50, "stat": {"name": "special-defense"}},
        {"base_stat": 65, "stat": {"name": "speed"}},
    ],
    "moves": [
        {
            "move": {"name": "ember"},
            "version_group_details": [
                {"move_learn_method": {"name": "level-up"}, "level_learned_at": 51}
            ],
        },
    ],
    "sprites": {"front_default": None, "other": {"official-artwork": {"front_default": None}}},
}

FAKE_CHARMELEON = {
    **FAKE_CHARMANDER,
    "name": "charmeleon",
    "id": 5,
    "stats": [
        {"base_stat": 58, "stat": {"name": "hp"}},
        {"base_stat": 64, "stat": {"name": "attack"}},
        {"base_stat": 58, "stat": {"name": "defense"}},
        {"base_stat": 80, "stat": {"name": "special-attack"}},
        {"base_stat": 65, "stat": {"name": "special-defense"}},
        {"base_stat": 80, "stat": {"name": "speed"}},
    ],
}

FAKE_EMBER_MOVE = {
    "name": "ember",
    "type": {"name": "fire"},
    "power": 40,
    "accuracy": 100,
    "damage_class": {"name": "special"},
    "meta": {"ailment": {"name": "burn"}, "ailment_chance": 10},
}

FAKE_EVOLUTION_CHAIN = {
    "chain": {
        "species": {"name": "charmander"},
        "evolves_to": [
            {
                "species": {"name": "charmeleon"},
                "evolution_details": [{"trigger": {"name": "level-up"}, "min_level": 16}],
                "evolves_to": [],
            }
        ],
    }
}


def _raise_no_network(*_args, **_kwargs):
    raise pokeapi.PokeApiError("sem rede nesse teste")


def make_pokemon(species="charmander", level=50):
    stats = {"hp": 39, "attack": 52, "defense": 43, "sp_atk": 60, "sp_def": 50, "speed": 65}
    mon = Pokemon("Charmander", ["fire"], level, stats, [Move("Scratch", "normal", 40, "physical")])
    mon.species = species
    mon.pokedex_id = 4
    mon.sprite_path = None
    return mon


def test_experience_for_win_applies_the_trainer_battle_multiplier():
    data = {"base_experience": 70}
    trainer_xp = progression.experience_for_win(data, defeated_level=20, is_trainer_battle=True)
    wild_xp = progression.experience_for_win(data, defeated_level=20, is_trainer_battle=False)
    assert trainer_xp == int(70 * 20 * 1.5 / 7)
    assert wild_xp == int(70 * 20 / 7)
    assert trainer_xp > wild_xp


def test_xp_to_next_level_follows_the_cube_curve():
    assert progression.xp_to_next_level(10) == 11 ** 3


def test_gain_ev_from_victory_targets_the_defeated_highest_stat():
    winner = make_pokemon()
    defeated_data = {
        "stats": [
            {"base_stat": 50, "stat": {"name": "attack"}},
            {"base_stat": 154, "stat": {"name": "special-attack"}},
            {"base_stat": 90, "stat": {"name": "defense"}},
        ]
    }
    message = progression.gain_ev_from_victory(winner, defeated_data)
    assert winner.evs["sp_atk"] == 1
    assert "Sp Atk" in message


def test_gain_ev_from_victory_returns_none_when_the_stat_is_already_capped():
    winner = make_pokemon()
    winner.evs["sp_atk"] = 252
    defeated_data = {"stats": [{"base_stat": 154, "stat": {"name": "special-attack"}}]}
    assert progression.gain_ev_from_victory(winner, defeated_data) is None


def test_apply_level_up_gains_a_level_and_learns_the_exact_move(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_pokemon", lambda name: FAKE_CHARMANDER)
    monkeypatch.setattr(pokeapi, "get_move", lambda name: FAKE_EMBER_MOVE)
    monkeypatch.setattr(pokeapi, "get_species", _raise_no_network)  # sem evolução nesse teste

    mon = make_pokemon(level=50)
    mon.experience = progression.xp_to_next_level(50)

    result = progression.apply_level_up(mon)

    assert result["levels_gained"] == 1
    assert mon.level == 51
    assert [m.name for m in result["new_moves"]] == ["Ember"]
    assert result["evolved_into"] is None


def test_apply_level_up_does_nothing_without_enough_experience(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_species", _raise_no_network)
    mon = make_pokemon(level=50)
    mon.experience = 0

    result = progression.apply_level_up(mon)

    assert result["levels_gained"] == 0
    assert mon.level == 50


def test_apply_level_up_can_trigger_evolution(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_pokemon", lambda name: FAKE_CHARMANDER)
    monkeypatch.setattr(pokeapi, "get_move", lambda name: FAKE_EMBER_MOVE)
    monkeypatch.setattr(pokeapi, "get_species", lambda name: {"evolution_chain": {"url": "fake-url"}})
    monkeypatch.setattr(pokeapi, "get_by_url", lambda url: FAKE_EVOLUTION_CHAIN)

    mon = make_pokemon(level=15)
    mon.experience = progression.xp_to_next_level(15)  # sobe pro 16: bate o min_level da cadeia

    result = progression.apply_level_up(mon)

    assert mon.level == 16
    assert result["evolved_into"] == "charmeleon"


def test_learn_move_appends_when_there_is_room():
    mon = make_pokemon()
    assert len(mon.moves) == 1
    new_move = Move("Ember", "fire", 40, "special")

    progression.learn_move(mon, new_move)

    assert mon.moves[-1] is new_move


def test_learn_move_replaces_the_chosen_slot_when_full():
    mon = make_pokemon()
    mon.moves = [Move(f"Golpe{i}", "normal", 40, "physical") for i in range(4)]
    new_move = Move("Ember", "fire", 40, "special")

    progression.learn_move(mon, new_move, forget_index=2)

    assert mon.moves[2] is new_move
    assert len(mon.moves) == 4


def test_learn_move_does_nothing_when_full_and_no_slot_chosen():
    mon = make_pokemon()
    original_moves = [Move(f"Golpe{i}", "normal", 40, "physical") for i in range(4)]
    mon.moves = list(original_moves)

    progression.learn_move(mon, Move("Ember", "fire", 40, "special"), forget_index=None)

    assert mon.moves == original_moves


def test_evolve_pokemon_updates_species_type_stats_and_keeps_level_and_moves(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_pokemon", lambda name: FAKE_CHARMELEON)

    mon = make_pokemon(level=16)
    original_moves = list(mon.moves)
    original_ivs = dict(mon.ivs)

    progression.evolve_pokemon(mon, "charmeleon")

    assert mon.species == "charmeleon"
    assert mon.name == "Charmeleon"
    assert mon.types == ["fire"]
    assert mon.base_stats["attack"] == 64
    assert mon.level == 16
    assert mon.moves == original_moves
    assert mon.ivs == original_ivs
