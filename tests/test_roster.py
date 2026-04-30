"""Testes de pokebattle/roster.build_pokemon: shiny (1/4096) e os overrides
opcionais de ivs/nature usados por teamcodec.py — com a PokeAPI trocada por
dados falsos (via monkeypatch), no mesmo molde de test_progression.py."""

from pokebattle import pokeapi, roster
from pokebattle.natures import NATURES

FAKE_PIKACHU = {
    "name": "pikachu", "id": 25,
    "abilities": [{"ability": {"name": "static"}, "is_hidden": False}],
    "types": [{"slot": 1, "type": {"name": "electric"}}],
    "stats": [
        {"base_stat": 35, "stat": {"name": "hp"}},
        {"base_stat": 55, "stat": {"name": "attack"}},
        {"base_stat": 40, "stat": {"name": "defense"}},
        {"base_stat": 50, "stat": {"name": "special-attack"}},
        {"base_stat": 50, "stat": {"name": "special-defense"}},
        {"base_stat": 90, "stat": {"name": "speed"}},
    ],
    "moves": [
        {
            "move": {"name": "thunderbolt"},
            "version_group_details": [{"move_learn_method": {"name": "level-up"}, "level_learned_at": 26}],
        },
    ],
    "sprites": {
        "front_default": None, "front_shiny": None,
        "other": {"official-artwork": {"front_default": None, "front_shiny": None}},
    },
}

FAKE_THUNDERBOLT = {
    "name": "thunderbolt", "type": {"name": "electric"}, "power": 90, "accuracy": 100,
    "damage_class": {"name": "special"}, "meta": {"ailment": {"name": "none"}, "ailment_chance": 0},
    "priority": 0, "target": {"name": "selected-pokemon"},
}


class FixedRollRNG:
    """randint sempre devolve o mesmo valor combinado (usado pro sorteio de
    shiny e, se ivs=None, pro sorteio de IV também); choice sempre o
    primeiro item (natureza)."""

    def __init__(self, randint_value):
        self.randint_value = randint_value

    def randint(self, a, b):
        return self.randint_value

    def choice(self, seq):
        return seq[0]


def _patch_pokeapi(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_pokemon", lambda name: FAKE_PIKACHU)
    monkeypatch.setattr(pokeapi, "get_move", lambda name: FAKE_THUNDERBOLT)


def test_build_pokemon_is_shiny_when_the_roll_hits_one(monkeypatch):
    _patch_pokeapi(monkeypatch)
    mon = roster.build_pokemon("pikachu", rng=FixedRollRNG(1))
    assert mon.is_shiny is True


def test_build_pokemon_is_not_shiny_on_any_other_roll(monkeypatch):
    _patch_pokeapi(monkeypatch)
    mon = roster.build_pokemon("pikachu", rng=FixedRollRNG(2))
    assert mon.is_shiny is False


def test_build_pokemon_accepts_fixed_ivs_and_nature(monkeypatch):
    _patch_pokeapi(monkeypatch)
    fixed_ivs = {"hp": 31, "attack": 31, "defense": 31, "sp_atk": 31, "sp_def": 31, "speed": 31}

    mon = roster.build_pokemon("pikachu", rng=FixedRollRNG(2), ivs=fixed_ivs, nature="Adamant")

    assert mon.ivs == fixed_ivs
    assert mon.nature == "Adamant"


def test_build_pokemon_without_overrides_still_randomizes(monkeypatch):
    _patch_pokeapi(monkeypatch)
    mon = roster.build_pokemon("pikachu", rng=FixedRollRNG(7))
    assert all(0 <= iv <= 31 for iv in mon.ivs.values())
    assert mon.nature in NATURES


def test_build_pokemon_starts_without_a_held_item(monkeypatch):
    _patch_pokeapi(monkeypatch)
    mon = roster.build_pokemon("pikachu", rng=FixedRollRNG(2))
    assert mon.held_item is None
