import random

import pytest

from pokebattle.battle import Battle
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


def make_pokemon(name, hp=50, speed=50, attack=50):
    stats = {"hp": hp, "attack": attack, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": speed}
    moves = [Move("Tackle", "normal", 40, "physical")]
    return Pokemon(name, ["normal"], level=50, base_stats=stats, moves=moves)


def test_battle_still_accepts_a_single_pokemon_per_side():
    player = make_pokemon("Solo")
    enemy = make_pokemon("Rival")
    battle = Battle(player, enemy)
    assert battle.player is player
    assert battle.enemy is enemy


def test_switching_changes_the_active_pokemon_and_the_enemy_still_attacks():
    bench = make_pokemon("Banco", hp=100)
    active = make_pokemon("Titular", hp=1)
    enemy = make_pokemon("Inimigo", attack=999)

    battle = Battle([active, bench], enemy, rng=random.Random(1))
    log = battle.take_turn(("switch", 1), enemy.moves[0])

    assert battle.player is bench
    assert any("Banco" in line for line in log)
    assert any("Banco sofreu" in line for line in log)


def test_cannot_switch_to_a_fainted_pokemon():
    fainted = make_pokemon("Caido")
    fainted.current_hp = 0
    active = make_pokemon("Ativo")
    battle = Battle([active, fainted], make_pokemon("Inimigo"))

    with pytest.raises(ValueError):
        battle.switch("player", 1)


def test_needs_switch_is_true_only_when_active_fainted_and_reserve_alive():
    bench = make_pokemon("Banco")
    active = make_pokemon("Titular")
    battle = Battle([active, bench], make_pokemon("Inimigo"))

    assert battle.needs_switch("player") is False
    active.current_hp = 0
    assert battle.needs_switch("player") is True


def test_fleeing_ends_the_battle_immediately():
    battle = Battle(make_pokemon("Fujao"), make_pokemon("Inimigo"))
    log = battle.take_turn(("flee", None))

    assert battle.is_over is True
    assert battle.winner == "enemy"
    assert "fugiu" in log[0]


def test_item_action_heals_and_still_lets_the_enemy_attack():
    player = make_pokemon("Curado", hp=100)
    player.current_hp = 50
    enemy = make_pokemon("Inimigo")

    battle = Battle(player, enemy, rng=random.Random(1))
    log = battle.take_turn(("item", 20), enemy.moves[0])

    assert any("recuperou 20 HP" in line for line in log)  # curou...
    assert any("Curado sofreu" in line for line in log)  # ...e só depois apanhou
    assert 0 < player.current_hp < 100


def test_team_is_only_defeated_when_every_member_has_fainted():
    alive = make_pokemon("Vivo")
    fainted = make_pokemon("Morto")
    fainted.current_hp = 0
    battle = Battle([fainted, alive], make_pokemon("Inimigo"))

    assert battle.is_over is False
