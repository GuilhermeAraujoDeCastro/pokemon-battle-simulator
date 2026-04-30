"""Testes de pokebattle/held_items.py — lógica pura, sem tocar battle.py."""

from pokebattle import held_items
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon
from pokebattle.status import BURN, PARALYSIS


def make_pokemon(hp=100, held_item=None, status=None):
    stats = {"hp": hp, "attack": 50, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}
    mon = Pokemon("Testmon", ["normal"], 50, stats, [Move("Tackle", "normal", 40, "physical")])
    mon.held_item = held_item
    mon.status = status
    return mon


def test_end_of_turn_heal_leftovers_heals_one_sixteenth():
    mon = make_pokemon(hp=160, held_item="held_leftovers")
    mon.current_hp = 100
    expected_heal = mon.max_hp // 16

    message = held_items.end_of_turn_heal(mon)

    assert mon.current_hp == 100 + expected_heal
    assert "Leftovers" in message


def test_end_of_turn_heal_does_nothing_without_leftovers():
    mon = make_pokemon(hp=160)
    mon.current_hp = 100
    assert held_items.end_of_turn_heal(mon) is None
    assert mon.current_hp == 100


def test_end_of_turn_heal_does_nothing_at_full_hp():
    mon = make_pokemon(hp=160, held_item="held_leftovers")
    assert held_items.end_of_turn_heal(mon) is None


def test_power_modifier_boosts_physical_moves_with_choice_band():
    attacker = make_pokemon(held_item="held_choice_band")
    physical = Move("Tackle", "normal", 40, "physical")
    special = Move("Ember", "fire", 40, "special")

    assert held_items.power_modifier(attacker, physical) == 1.5
    assert held_items.power_modifier(attacker, special) == 1.0


def test_power_modifier_is_neutral_without_choice_band():
    attacker = make_pokemon()
    physical = Move("Tackle", "normal", 40, "physical")
    assert held_items.power_modifier(attacker, physical) == 1.0


def test_cheri_berry_cures_paralysis_and_is_consumed():
    mon = make_pokemon(held_item="held_cheri_berry")
    mon.status = PARALYSIS

    message = held_items.try_cure_status(mon, PARALYSIS)

    assert mon.status is None
    assert mon.held_item is None
    assert "Cheri" in message


def test_cheri_berry_does_not_cure_a_different_status():
    mon = make_pokemon(held_item="held_cheri_berry")
    mon.status = BURN

    assert held_items.try_cure_status(mon, BURN) is None
    assert mon.status == BURN
    assert mon.held_item == "held_cheri_berry"  # não foi consumida


def test_lum_berry_cures_any_status():
    for status in (BURN, PARALYSIS):
        mon = make_pokemon(held_item="held_lum_berry")
        mon.status = status
        message = held_items.try_cure_status(mon, status)
        assert mon.status is None
        assert message is not None


def test_try_cure_status_does_nothing_without_a_curing_berry():
    mon = make_pokemon(held_item="held_leftovers")
    mon.status = BURN
    assert held_items.try_cure_status(mon, BURN) is None
    assert mon.status == BURN
