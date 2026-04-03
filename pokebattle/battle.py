"""Lógica pura da batalha 1x1 por turnos.

De propósito, esse módulo não faz nenhum print() nem input() — quem cuida
da tela e da entrada do jogador é o main.py. Isso é o que permite testar a
fórmula de dano e as regras de turno sem precisar simular teclado, e é a
mesma separação (lógica x interface) que vale a pena levar pra qualquer
projeto maior.
"""

import random
from dataclasses import dataclass
from typing import Optional

from .types_chart import effectiveness


@dataclass
class DamageResult:
    damage: int
    hit: bool
    effectiveness: float
    is_crit: bool


def _base_power(level: float, power: int, atk_stat: int, def_stat: int) -> float:
    """Núcleo da fórmula oficial de dano, antes de STAB/tipo/crítico/variação."""
    return (((2 * level / 5 + 2) * power * atk_stat / def_stat) / 50) + 2


def calculate_damage(attacker, defender, move, rng=random) -> DamageResult:
    hit = rng.uniform(0, 100) <= move.accuracy
    if not hit:
        return DamageResult(damage=0, hit=False, effectiveness=1.0, is_crit=False)

    type_eff = effectiveness(move.type, defender.types)
    if type_eff == 0.0:
        return DamageResult(damage=0, hit=True, effectiveness=0.0, is_crit=False)

    if move.category == "physical":
        atk_stat, def_stat = attacker.attack, defender.defense
    else:
        atk_stat, def_stat = attacker.sp_atk, defender.sp_def

    base = _base_power(attacker.level, move.power, atk_stat, def_stat)

    is_crit = rng.random() < (1 / 16)
    stab = 1.5 if move.type in attacker.types else 1.0
    crit_mult = 1.5 if is_crit else 1.0
    variance = rng.uniform(0.85, 1.0)

    damage = int(base * stab * type_eff * crit_mult * variance)
    damage = max(1, damage)
    return DamageResult(damage=damage, hit=True, effectiveness=type_eff, is_crit=is_crit)


class Battle:
    def __init__(self, player, enemy, rng=random):
        self.player = player
        self.enemy = enemy
        self.rng = rng
        self.turn_count = 0

    @property
    def is_over(self) -> bool:
        return self.player.is_fainted or self.enemy.is_fainted

    @property
    def winner(self) -> Optional[str]:
        if self.enemy.is_fainted and not self.player.is_fainted:
            return "player"
        if self.player.is_fainted and not self.enemy.is_fainted:
            return "enemy"
        return None

    def _order(self, player_move, enemy_move):
        """Decide quem ataca primeiro pela Velocidade (empate = sorteio)."""
        if self.player.speed > self.enemy.speed:
            first, second = "player", "enemy"
        elif self.enemy.speed > self.player.speed:
            first, second = "enemy", "player"
        else:
            first = self.rng.choice(["player", "enemy"])
            second = "enemy" if first == "player" else "player"

        actors = {
            "player": (self.player, self.enemy, player_move),
            "enemy": (self.enemy, self.player, enemy_move),
        }
        return [actors[first], actors[second]]

    def execute_turn(self, player_move, enemy_move) -> list[str]:
        """Aplica os dois ataques do turno, em ordem de velocidade.

        Retorna a lista de mensagens de log daquele turno, prontas pra exibir.
        """
        self.turn_count += 1
        log = []
        for attacker, defender, move in self._order(player_move, enemy_move):
            if attacker.is_fainted:
                continue

            log.append(f"{attacker.name} usou {move.name}!")
            result = calculate_damage(attacker, defender, move, rng=self.rng)

            if not result.hit:
                log.append("O ataque errou!")
                continue
            if result.effectiveness == 0.0:
                log.append(f"Não afetou {defender.name}...")
                continue

            defender.take_damage(result.damage)
            if result.is_crit:
                log.append("Acerto crítico!")
            if result.effectiveness > 1.0:
                log.append("É super efetivo!")
            elif result.effectiveness < 1.0:
                log.append("Não é muito eficaz...")
            log.append(
                f"{defender.name} sofreu {result.damage} de dano "
                f"({defender.current_hp}/{defender.max_hp} HP)."
            )

            if defender.is_fainted:
                log.append(f"{defender.name} desmaiou!")
                break
        return log
