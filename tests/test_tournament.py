"""Testes de pokebattle/tournament.py: o bracket (Tournament) é testado só
com nomes de participante, sem precisar de Pokémon de verdade; a simulação
de partida IA-vs-IA (simulate_ai_battle) usa Pokemon de verdade com RNG
determinístico (random.Random com seed fixa)."""

import random

import pytest

from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon
from pokebattle.tournament import Tournament, simulate_ai_battle


def make_team(name, attack=50, defense=50, hp=100, moves=None):
    stats = {"hp": hp, "attack": attack, "defense": defense, "sp_atk": 50, "sp_def": 50, "speed": 50}
    default_moves = moves or [Move("Tackle", "normal", 40, "physical")]
    return [Pokemon(name, ["normal"], 50, stats, default_moves)]


# ---------- bracket ----------

def test_rejects_a_non_power_of_two_entrant_count():
    with pytest.raises(ValueError):
        Tournament(["a", "b", "c"])


def test_first_round_pairings_are_sequential():
    tournament = Tournament(["a", "b", "c", "d"])
    assert tournament.pairings(0) == [("a", "b"), ("c", "d")]


def test_recording_a_result_outside_the_pairing_is_rejected():
    tournament = Tournament(["a", "b", "c", "d"])
    with pytest.raises(ValueError):
        tournament.record_result(0, 0, "c")  # "c" não está nesse confronto


def test_advances_to_the_next_round_once_the_current_one_is_complete():
    tournament = Tournament(["a", "b", "c", "d"])
    assert tournament.current_round() == 0

    tournament.record_result(0, 0, "a")
    assert tournament.current_round() == 0  # ainda falta o outro confronto da rodada 0
    tournament.record_result(0, 1, "d")
    assert tournament.current_round() == 1
    assert tournament.pairings(1) == [("a", "d")]


def test_champion_is_none_until_the_final_is_resolved():
    tournament = Tournament(["a", "b", "c", "d"])
    tournament.record_result(0, 0, "a")
    tournament.record_result(0, 1, "d")
    assert tournament.champion is None

    tournament.record_result(1, 0, "a")
    assert tournament.champion == "a"
    assert tournament.is_complete is True


def test_eight_entrant_bracket_has_three_rounds():
    tournament = Tournament([f"p{i}" for i in range(8)])
    assert tournament.total_rounds == 3


# ---------- simulação IA vs IA ----------

def test_a_clearly_stronger_team_wins_the_simulation():
    strong = make_team("Forte", attack=200, defense=200, hp=300)
    weak = make_team("Fraco", attack=5, defense=5, hp=20)

    winner = simulate_ai_battle(strong, weak, rng=random.Random(1))
    assert winner == 0


def test_the_simulation_is_deterministic_with_the_same_seed():
    team_a = make_team("A", attack=60, defense=60, hp=120)
    team_b = make_team("B", attack=60, defense=60, hp=120)

    first = simulate_ai_battle(team_a, team_b, rng=random.Random(7))
    team_a2 = make_team("A", attack=60, defense=60, hp=120)
    team_b2 = make_team("B", attack=60, defense=60, hp=120)
    second = simulate_ai_battle(team_a2, team_b2, rng=random.Random(7))

    assert first == second


def test_the_simulation_always_terminates_even_with_only_status_moves():
    harmless_move = Move("Rugido", "normal", 0, "status")
    team_a = make_team("A", moves=[harmless_move])
    team_b = make_team("B", moves=[harmless_move])

    winner = simulate_ai_battle(team_a, team_b, rng=random.Random(3))
    assert winner in (0, 1)
