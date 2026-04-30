"""Testes de pokebattle/mega.py — a transformação em si (apply_mega_form/
revert_mega_form) é pura sobre dados já buscados, no mesmo molde de
test_progression.py. Só try_mega_evolve toca a PokeAPI de verdade (via
monkeypatch aqui também, nunca rede real)."""

from pokebattle import mega, pokeapi
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon

FAKE_MEGA_CHARIZARD_X = {
    "name": "charizard-mega-x",
    "id": 10034,
    "types": [{"slot": 1, "type": {"name": "fire"}}, {"slot": 2, "type": {"name": "dragon"}}],
    "stats": [
        {"base_stat": 78, "stat": {"name": "hp"}},
        {"base_stat": 130, "stat": {"name": "attack"}},
        {"base_stat": 111, "stat": {"name": "defense"}},
        {"base_stat": 130, "stat": {"name": "special-attack"}},
        {"base_stat": 85, "stat": {"name": "special-defense"}},
        {"base_stat": 100, "stat": {"name": "speed"}},
    ],
    "sprites": {"front_default": None, "other": {"official-artwork": {"front_default": None}}},
}


def make_charizard(held_item=None):
    stats = {"hp": 78, "attack": 84, "defense": 78, "sp_atk": 109, "sp_def": 85, "speed": 100}
    mon = Pokemon("Charizard", ["fire", "flying"], 50, stats, [Move("Flamethrower", "fire", 90, "special")])
    mon.species = "charizard"
    mon.pokedex_id = 6
    mon.sprite_path = None
    mon.held_item = held_item
    return mon


def test_mega_stone_for_a_curated_species():
    assert mega.mega_stone_for("charizard") == "held_mega_stone_charizardite_x"
    assert mega.mega_species_for("charizard") == "charizard-mega-x"


def test_mega_stone_for_an_uncurated_species_is_none():
    assert mega.mega_stone_for("rattata") is None


def test_can_mega_evolve_requires_the_right_stone():
    without_stone = make_charizard()
    with_wrong_item = make_charizard(held_item="held_leftovers")
    with_stone = make_charizard(held_item="held_mega_stone_charizardite_x")

    assert mega.can_mega_evolve(without_stone) is None
    assert mega.can_mega_evolve(with_wrong_item) is None
    assert mega.can_mega_evolve(with_stone) == "charizard-mega-x"


def test_can_mega_evolve_is_none_once_already_mega():
    mon = make_charizard(held_item="held_mega_stone_charizardite_x")
    mon.is_mega = True
    assert mega.can_mega_evolve(mon) is None


def test_apply_mega_form_swaps_types_and_stats_and_keeps_a_backup():
    mon = make_charizard(held_item="held_mega_stone_charizardite_x")
    original_types = list(mon.types)
    original_base_stats = dict(mon.base_stats)

    mega.apply_mega_form(mon, FAKE_MEGA_CHARIZARD_X)

    assert mon.types == ["fire", "dragon"]
    assert mon.base_stats["attack"] == 130
    assert mon.is_mega is True
    assert mon._mega_backup["types"] == original_types
    assert mon._mega_backup["base_stats"] == original_base_stats


def test_revert_mega_form_restores_the_original_pokemon():
    mon = make_charizard(held_item="held_mega_stone_charizardite_x")
    original_types = list(mon.types)
    original_attack = mon.attack

    mega.apply_mega_form(mon, FAKE_MEGA_CHARIZARD_X)
    mega.revert_mega_form(mon)

    assert mon.types == original_types
    assert mon.attack == original_attack
    assert mon.is_mega is False
    assert not hasattr(mon, "_mega_backup")


def test_revert_mega_form_is_a_no_op_when_never_mega_evolved():
    mon = make_charizard()
    mega.revert_mega_form(mon)  # não pode levantar
    assert getattr(mon, "is_mega", False) is False


def test_try_mega_evolve_uses_the_pokeapi_and_applies(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_pokemon", lambda name: FAKE_MEGA_CHARIZARD_X)
    mon = make_charizard(held_item="held_mega_stone_charizardite_x")

    message = mega.try_mega_evolve(mon)

    assert message is not None
    assert mon.is_mega is True


def test_try_mega_evolve_returns_none_without_the_stone():
    mon = make_charizard()
    assert mega.try_mega_evolve(mon) is None
