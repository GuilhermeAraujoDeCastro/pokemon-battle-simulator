import random

from pokebattle.battle import Battle
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon(name, types, speed, hp=200, attack=100, defense=50, sp_atk=50, sp_def=50):
    stats = {"hp": hp, "attack": attack, "defense": defense,
             "sp_atk": sp_atk, "sp_def": sp_def, "speed": speed}
    moves = [Move("Investida", types[0], 40, "physical")]
    return Pokemon(name, types, level=50, base_stats=stats, moves=moves)


def test_faster_pokemon_attacks_first():
    fast = make_pokemon("Rapido", ["electric"], speed=200)
    slow = make_pokemon("Lento", ["rock"], speed=10)
    battle = Battle(fast, slow, rng=random.Random(1))

    log = battle.execute_turn(fast.moves[0], slow.moves[0])
    assert log[0].startswith("Rapido usou")


def test_battle_ends_when_one_side_faints():
    strong = make_pokemon("Forte", ["fighting"], speed=100, attack=999)
    weak = make_pokemon("Fraco", ["normal"], speed=10, hp=1, defense=1)
    battle = Battle(strong, weak, rng=random.Random(1))

    battle.execute_turn(strong.moves[0], weak.moves[0])

    assert battle.is_over is True
    assert battle.winner == "player"


def test_fainted_pokemon_does_not_attack_in_the_same_turn():
    strong = make_pokemon("Forte", ["fighting"], speed=200, attack=999)
    weak = make_pokemon("Fraco", ["normal"], speed=100, hp=1, defense=1)
    battle = Battle(strong, weak, rng=random.Random(1))

    log = battle.execute_turn(strong.moves[0], weak.moves[0])

    fainted_index = next(i for i, line in enumerate(log) if "desmaiou" in line)
    assert not any("Fraco usou" in line for line in log[fainted_index:])
