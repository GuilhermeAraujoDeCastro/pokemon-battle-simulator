"""Testes de pokebattle/replay.py — gravação/leitura de replay em JSON,
sem tocar Tkinter nem a Battle de verdade."""

from pokebattle import replay
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon():
    stats = {"hp": 100, "attack": 50, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}
    return Pokemon("Testmon", ["normal"], 50, stats, [Move("Tackle", "normal", 40, "physical")])


def test_snapshot_captures_the_essentials_without_a_live_reference():
    mon = make_pokemon()
    mon.species = "testmon"
    snap = replay.snapshot(mon)

    assert snap == {
        "name": "Testmon", "species": "testmon", "level": 50,
        "current_hp": mon.max_hp, "max_hp": mon.max_hp, "status": None,
    }


def test_record_turn_bundles_everything_needed_to_play_it_back():
    player_snap = replay.snapshot(make_pokemon())
    enemy_snap = replay.snapshot(make_pokemon())

    turn = replay.record_turn(1, "Jogador usou Tackle", ["Testmon usou Tackle!"], player_snap, enemy_snap)

    assert turn["turn"] == 1
    assert turn["log"] == ["Testmon usou Tackle!"]
    assert turn["player"] == player_snap


def test_save_and_load_replay_round_trip(tmp_path):
    path = tmp_path / "replay1.json"
    turns = [replay.record_turn(1, "desc", ["log"], replay.snapshot(make_pokemon()), replay.snapshot(make_pokemon()))]

    replay.save_replay(path, {"result": "vitoria"}, turns)
    loaded = replay.load_replay(path)

    assert loaded["metadata"] == {"result": "vitoria"}
    assert loaded["turns"] == turns


def test_list_replays_orders_newest_first(tmp_path):
    import time

    older = tmp_path / "a.json"
    newer = tmp_path / "b.json"
    replay.save_replay(older, {}, [])
    time.sleep(0.01)
    replay.save_replay(newer, {}, [])

    files = replay.list_replays(tmp_path)
    assert files[0] == newer
    assert files[1] == older


def test_list_replays_on_a_missing_directory_is_empty(tmp_path):
    assert replay.list_replays(tmp_path / "does_not_exist") == []
