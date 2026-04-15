"""Teste de pokebattle/roster._pick_ability — lógica pura, sem tocar a
PokeAPI de verdade."""

from pokebattle import roster


def test_pick_ability_prefers_a_normal_ability_over_a_hidden_one():
    data = {
        "abilities": [
            {"ability": {"name": "insomnia"}, "is_hidden": True, "slot": 3},
            {"ability": {"name": "overgrow"}, "is_hidden": False, "slot": 1},
        ]
    }
    assert roster._pick_ability(data) == "overgrow"


def test_pick_ability_falls_back_to_hidden_when_thats_all_there_is():
    data = {"abilities": [{"ability": {"name": "insomnia"}, "is_hidden": True, "slot": 3}]}
    assert roster._pick_ability(data) == "insomnia"


def test_pick_ability_returns_none_without_ability_data():
    assert roster._pick_ability({}) is None
    assert roster._pick_ability({"abilities": []}) is None
