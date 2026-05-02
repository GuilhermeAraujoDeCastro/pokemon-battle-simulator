"""Testes de pokebattle/nuzlocke.py — regra pura, sem tocar main_gui.py."""

from pokebattle import nuzlocke
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon(name, fainted=False):
    stats = {"hp": 100, "attack": 50, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}
    mon = Pokemon(name, ["normal"], 50, stats, [Move("Tackle", "normal", 40, "physical")])
    if fainted:
        mon.current_hp = 0
    return mon


def test_surviving_team_filters_out_the_fainted():
    alive = make_pokemon("Vivo")
    fainted = make_pokemon("Caido", fainted=True)

    assert nuzlocke.surviving_team([alive, fainted]) == [alive]


def test_released_members_is_the_complement_of_surviving_team():
    alive = make_pokemon("Vivo")
    fainted = make_pokemon("Caido", fainted=True)

    assert nuzlocke.released_members([alive, fainted]) == [fainted]


def test_can_use_revive_is_false_only_when_nuzlocke_is_on():
    assert nuzlocke.can_use_revive(nuzlocke_enabled=False) is True
    assert nuzlocke.can_use_revive(nuzlocke_enabled=True) is False
