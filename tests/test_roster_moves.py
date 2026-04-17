"""Testes de pokebattle/roster._build_move e _build_stat_changes — extração
dos campos novos (prioridade, dreno, mudança de stat, clima, carga) dos
dados crus da PokeAPI, sem tocar rede de verdade."""

from pokebattle import pokeapi, roster


def _base_move_json(**overrides):
    data = {
        "name": "tackle",
        "type": {"name": "normal"},
        "power": 40,
        "accuracy": 100,
        "damage_class": {"name": "physical"},
        "meta": {"ailment": {"name": "none"}, "ailment_chance": 0},
        "priority": 0,
        "target": {"name": "selected-pokemon"},
    }
    data.update(overrides)
    return data


def test_build_move_reads_priority(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_move", lambda name: _base_move_json(priority=1))
    move = roster._build_move("quick-attack")
    assert move.priority == 1


def test_build_move_reads_positive_drain(monkeypatch):
    json_data = _base_move_json(meta={"ailment": {"name": "none"}, "ailment_chance": 0, "drain": 50})
    monkeypatch.setattr(pokeapi, "get_move", lambda name: json_data)
    move = roster._build_move("giga-drain")
    assert move.drain == 50


def test_build_move_reads_negative_drain_as_recoil(monkeypatch):
    json_data = _base_move_json(meta={"ailment": {"name": "none"}, "ailment_chance": 0, "drain": -25})
    monkeypatch.setattr(pokeapi, "get_move", lambda name: json_data)
    move = roster._build_move("double-edge")
    assert move.drain == -25


def test_build_move_reads_self_targeted_stat_changes(monkeypatch):
    json_data = _base_move_json(
        power=0, category="status", damage_class={"name": "status"},
        target={"name": "user"},
        stat_changes=[{"change": 2, "stat": {"name": "attack"}}],
    )
    monkeypatch.setattr(pokeapi, "get_move", lambda name: json_data)
    move = roster._build_move("swords-dance")
    assert move.stat_changes == (("attack", 2),)
    assert move.stat_change_target == "self"


def test_build_move_ignores_accuracy_and_evasion_stat_changes(monkeypatch):
    json_data = _base_move_json(
        power=0, damage_class={"name": "status"},
        stat_changes=[
            {"change": -1, "stat": {"name": "accuracy"}},
            {"change": -1, "stat": {"name": "defense"}},
        ],
    )
    monkeypatch.setattr(pokeapi, "get_move", lambda name: json_data)
    move = roster._build_move("growl")
    assert move.stat_changes == (("defense", -1),)


def test_build_move_recognizes_a_curated_weather_move_by_name(monkeypatch):
    json_data = _base_move_json(name="rain-dance", power=0, damage_class={"name": "status"})
    monkeypatch.setattr(pokeapi, "get_move", lambda name: json_data)
    move = roster._build_move("rain-dance")
    assert move.weather == "rain"


def test_build_move_flags_a_two_turn_charge_move(monkeypatch):
    json_data = _base_move_json(
        name="solar-beam", power=120, damage_class={"name": "special"},
        meta={"ailment": {"name": "none"}, "ailment_chance": 0, "category": {"name": "damage+charge"}},
    )
    monkeypatch.setattr(pokeapi, "get_move", lambda name: json_data)
    move = roster._build_move("solar-beam")
    assert move.is_charge_move is True


def test_build_move_defaults_are_all_neutral(monkeypatch):
    monkeypatch.setattr(pokeapi, "get_move", lambda name: _base_move_json())
    move = roster._build_move("tackle")
    assert move.priority == 0
    assert move.drain == 0
    assert move.stat_changes == ()
    assert move.weather is None
    assert move.is_charge_move is False
