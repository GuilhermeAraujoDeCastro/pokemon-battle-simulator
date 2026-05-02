"""Testes de pokebattle/items.py — lógica pura, sem tocar save.py."""

from pokebattle import items
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon(hp=100):
    stats = {"hp": hp, "attack": 50, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}
    return Pokemon("Testmon", ["normal"], 50, stats, [Move("Tackle", "normal", 40, "physical")])


def test_catalog_has_the_healing_items_plus_the_ev_training_items():
    ids = [item.id for item in items.CATALOG]
    assert ids[:4] == ["potion", "super_potion", "hyper_potion", "revive"]
    assert items.EV_ITEM_IDS == {"hp_up", "protein", "iron", "calcium", "zinc", "carbos"}


def test_apply_ev_item_grants_the_right_stat():
    mon = make_pokemon()
    gained = items.apply_ev_item("protein", mon)
    assert gained == 10
    assert mon.evs["attack"] == 10


def test_apply_ev_item_respects_the_252_cap():
    mon = make_pokemon()
    mon.evs["attack"] = 250
    gained = items.apply_ev_item("protein", mon)
    assert gained == 2
    assert mon.evs["attack"] == 252


def test_can_use_a_healing_item_only_on_a_conscious_pokemon():
    healthy = make_pokemon()
    fainted = make_pokemon()
    fainted.current_hp = 0

    assert items.can_use_on("potion", healthy) is True
    assert items.can_use_on("potion", fainted) is False


def test_can_use_revive_only_on_a_fainted_pokemon():
    healthy = make_pokemon()
    fainted = make_pokemon()
    fainted.current_hp = 0

    assert items.can_use_on("revive", fainted) is True
    assert items.can_use_on("revive", healthy) is False


def test_heal_amount_for_a_potion_is_fixed():
    mon = make_pokemon()
    assert items.heal_amount_for("potion", mon) == 20
    assert items.heal_amount_for("super_potion", mon) == 50


def test_heal_amount_for_revive_is_half_max_hp():
    mon = make_pokemon(hp=200)
    assert items.heal_amount_for("revive", mon) == mon.max_hp // 2
