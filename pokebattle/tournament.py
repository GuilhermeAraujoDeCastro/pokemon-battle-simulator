"""Modo torneio: bracket de eliminação simples até sair um campeão.
Reaproveita Battle (o motor de turnos) e ai.choose_move (pra decidir os
golpes de qualquer lado controlado por IA) em vez de reimplementar batalha.

O bracket só entende "nomes de participante" — quem é o jogador e quem é o
time de cada participante fica por conta de quem chama (main_gui.py). Isso
mantém a lógica de avanço de fase pura e testável sem precisar montar
Pokémon de verdade pra cada teste.

Simplificação consciente: o número de participantes precisa ser uma
potência de 2 (4, 8, 16...) — nada de "bye" pra número ímpar, porque não
acrescenta nada à experiência de jogar esse simulador e só complicaria o
bracket.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from . import ai
from .battle import Battle

MAX_SIMULATED_TURNS = 300  # trava de segurança: evita loop infinito em confrontos só de golpe de status


@dataclass
class Tournament:
    entrants: list[str]
    results: dict[int, dict[int, str]] = field(default_factory=dict)

    def __post_init__(self):
        count = len(self.entrants)
        if count < 2 or (count & (count - 1)) != 0:
            raise ValueError(f"Número de participantes precisa ser uma potência de 2 (2, 4, 8...); recebi {count}.")

    @property
    def total_rounds(self) -> int:
        return len(self.entrants).bit_length() - 1

    def _round_participants(self, round_index: int) -> list[str]:
        if round_index == 0:
            return list(self.entrants)
        previous = self._round_participants(round_index - 1)
        previous_results = self.results.get(round_index - 1, {})
        if len(previous_results) < len(previous) // 2:
            return []  # a rodada anterior ainda não terminou: ninguém entra aqui ainda
        return [previous_results[match] for match in range(len(previous) // 2)]

    def pairings(self, round_index: int) -> list[tuple[str, str]]:
        participants = self._round_participants(round_index)
        return [(participants[i], participants[i + 1]) for i in range(0, len(participants), 2)]

    def record_result(self, round_index: int, match_index: int, winner: str) -> None:
        pairing = self.pairings(round_index)[match_index]
        if winner not in pairing:
            raise ValueError(f"{winner!r} não está nesse confronto: {pairing!r}")
        self.results.setdefault(round_index, {})[match_index] = winner

    def is_round_complete(self, round_index: int) -> bool:
        pairings = self.pairings(round_index)
        if not pairings:
            return False  # a rodada nem começou de verdade ainda (a anterior não terminou)
        return len(self.results.get(round_index, {})) == len(pairings)

    @property
    def is_complete(self) -> bool:
        return self.is_round_complete(self.total_rounds - 1)

    @property
    def champion(self) -> Optional[str]:
        if not self.is_complete:
            return None
        return self.results[self.total_rounds - 1][0]

    def current_round(self) -> int:
        """Primeira rodada ainda não completa (ou a última, se o torneio já
        acabou)."""
        for round_index in range(self.total_rounds):
            if not self.is_round_complete(round_index):
                return round_index
        return self.total_rounds - 1


def simulate_ai_battle(team_a, team_b, difficulty_a="normal", personality_a="aggressive",
                        difficulty_b="normal", personality_b="aggressive", rng=random) -> int:
    """Simula uma batalha inteira entre dois times controlados por IA, turno
    a turno, até sobrar só um lado. Devolve 0 se team_a venceu, 1 se team_b
    venceu — usado pra resolver confrontos do bracket em que o jogador não
    está envolvido."""
    battle = Battle(list(team_a), list(team_b), rng=rng)

    for _ in range(MAX_SIMULATED_TURNS):
        if battle.is_over:
            break
        if battle.needs_switch("player"):
            battle.switch("player", _first_alive_index(battle.player_team))
            continue
        if battle.needs_switch("enemy"):
            battle.switch("enemy", _first_alive_index(battle.enemy_team))
            continue
        move_a = ai.choose_move(battle.player, battle.enemy, difficulty_a, personality_a, rng=rng)
        move_b = ai.choose_move(battle.enemy, battle.player, difficulty_b, personality_b, rng=rng)
        battle.take_turn(("move", move_a), move_b)

    if battle.winner == "player":
        return 0
    if battle.winner == "enemy":
        return 1
    return _tiebreak(battle)  # bateu o teto de turnos: decide por HP total restante


def _first_alive_index(team) -> int:
    for index, pokemon in enumerate(team):
        if not pokemon.is_fainted:
            return index
    raise ValueError("Nenhum Pokémon vivo pra trocar.")


def _tiebreak(battle: Battle) -> int:
    player_hp = sum(p.current_hp for p in battle.player_team)
    enemy_hp = sum(p.current_hp for p in battle.enemy_team)
    return 0 if player_hp >= enemy_hp else 1
