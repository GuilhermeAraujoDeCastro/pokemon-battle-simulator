"""Lógica pura da batalha por turnos, agora com time (até 6 Pokémon por lado),
troca, fuga e os efeitos de status (queimadura, veneno, paralisia,
congelamento, sono e confusão).

De propósito, esse módulo não faz nenhum print() nem input() — quem cuida
da tela e da entrada do jogador é o main.py (modo texto) ou o main_gui.py
(modo gráfico). Isso é o que permite testar a fórmula de dano e as regras de
turno sem precisar simular teclado, e é a mesma separação (lógica x
interface) que vale a pena levar pra qualquer projeto maior.
"""

import random
from dataclasses import dataclass
from typing import Optional

from . import abilities
from .status import (
    CONFUSION,
    apply_status,
    check_can_act,
    residual_damage,
    try_confuse,
)
from .types_chart import effectiveness


@dataclass
class DamageResult:
    damage: int
    hit: bool
    effectiveness: float
    is_crit: bool


# Clima: nome interno -> (rótulo em português, tipo fortalecido, tipo enfraquecido)
WEATHER_LABELS = {
    "sun": "ensolarado",
    "rain": "chuvoso",
    "sandstorm": "com tempestade de areia",
    "hail": "com granizo",
}
_WEATHER_BOOST = {"sun": "fire", "rain": "water"}
_WEATHER_WEAKEN = {"sun": "water", "rain": "fire"}
# Tipos imunes ao dano residual de cada clima.
WEATHER_RESIDUAL_IMMUNE = {
    "sandstorm": {"rock", "ground", "steel"},
    "hail": {"ice"},
}
WEATHER_DURATION = 5  # turnos, igual aos jogos sem habilidade que estenda


def _base_power(level: float, power: int, atk_stat: int, def_stat: int) -> float:
    """Núcleo da fórmula oficial de dano, antes de STAB/tipo/crítico/variação."""
    return (((2 * level / 5 + 2) * power * atk_stat / def_stat) / 50) + 2


def calculate_damage(attacker, defender, move, rng=random, weather=None) -> DamageResult:
    hit = rng.uniform(0, 100) <= move.accuracy
    if not hit:
        return DamageResult(damage=0, hit=False, effectiveness=1.0, is_crit=False)

    type_eff = 0.0 if abilities.grants_type_immunity(defender, move.type) else effectiveness(move.type, defender.types)
    if type_eff == 0.0:
        return DamageResult(damage=0, hit=True, effectiveness=0.0, is_crit=False)

    if move.category == "physical":
        atk_stat, def_stat = attacker.effective_attack, defender.effective_defense
    else:
        atk_stat, def_stat = attacker.effective_sp_atk, defender.effective_sp_def

    base = _base_power(attacker.level, move.power, atk_stat, def_stat)

    is_crit = rng.random() < (1 / 16)
    stab = 1.5 if move.type in attacker.types else 1.0
    crit_mult = 1.5 if is_crit else 1.0
    variance = rng.uniform(0.85, 1.0)

    weather_mult = 1.0
    if weather and move.type == _WEATHER_BOOST.get(weather):
        weather_mult = 1.5
    elif weather and move.type == _WEATHER_WEAKEN.get(weather):
        weather_mult = 0.5

    damage = int(base * stab * type_eff * crit_mult * variance * weather_mult)
    damage = max(1, damage)
    return DamageResult(damage=damage, hit=True, effectiveness=type_eff, is_crit=is_crit)


class Battle:
    def __init__(self, player, enemy, rng=random):
        # Aceita tanto um único Pokemon (modo clássico 1x1) quanto uma lista
        # (time completo), pra não quebrar quem já chama Battle(p1, p2).
        self.player_team = player if isinstance(player, list) else [player]
        self.enemy_team = enemy if isinstance(enemy, list) else [enemy]
        self.player_active = 0
        self.enemy_active = 0
        self.rng = rng
        self.turn_count = 0
        self.fled = False
        self.weather = None  # None ou "sun"/"rain"/"sandstorm"/"hail"
        self.weather_turns = 0
        # Intimidate de quem começa a batalha em campo (trocas depois disso
        # passam por switch(), que já dispara isso sozinho).
        self.intro_log = [
            message for message in (
                abilities.on_switch_in(self.player, self.enemy),
                abilities.on_switch_in(self.enemy, self.player),
            ) if message
        ]

    @property
    def player(self):
        return self.player_team[self.player_active]

    @property
    def enemy(self):
        return self.enemy_team[self.enemy_active]

    @property
    def is_over(self) -> bool:
        if self.fled:
            return True
        return self._team_wiped(self.player_team) or self._team_wiped(self.enemy_team)

    @property
    def winner(self) -> Optional[str]:
        if self.fled:
            return "enemy"
        player_out = self._team_wiped(self.player_team)
        enemy_out = self._team_wiped(self.enemy_team)
        if enemy_out and not player_out:
            return "player"
        if player_out and not enemy_out:
            return "enemy"
        return None

    @staticmethod
    def _team_wiped(team) -> bool:
        return all(p.is_fainted for p in team)

    def needs_switch(self, side: str) -> bool:
        """True se o ativo desse lado desmaiou mas ainda tem reserva viva."""
        team = self.player_team if side == "player" else self.enemy_team
        active = self.player if side == "player" else self.enemy
        return active.is_fainted and any(not p.is_fainted for p in team)

    def switch(self, side: str, index: int) -> list[str]:
        team = self.player_team if side == "player" else self.enemy_team
        if team[index].is_fainted:
            raise ValueError("Não dá pra trocar pra um Pokémon desmaiado.")
        if side == "player":
            self.player_active = index
            incoming, opponent = self.player, self.enemy
        else:
            self.enemy_active = index
            incoming, opponent = self.enemy, self.player
        log = [f"Vai, {incoming.name}!"]
        intimidate_message = abilities.on_switch_in(incoming, opponent)
        if intimidate_message:
            log.append(intimidate_message)
        return log

    def flee(self) -> str:
        self.fled = True
        return "Você fugiu da batalha!"

    def _order(self, player_move, enemy_move):
        """Decide quem ataca primeiro: prioridade do golpe manda, e só empate
        de prioridade vai pra Velocidade efetiva (empate dos dois = sorteio)."""
        if player_move.priority != enemy_move.priority:
            first = "player" if player_move.priority > enemy_move.priority else "enemy"
            second = "enemy" if first == "player" else "player"
            actors = {
                "player": (self.player, self.enemy, player_move),
                "enemy": (self.enemy, self.player, enemy_move),
            }
            return [actors[first], actors[second]]

        player_speed = self.player.effective_speed
        enemy_speed = self.enemy.effective_speed

        if player_speed > enemy_speed:
            first, second = "player", "enemy"
        elif enemy_speed > player_speed:
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
        """Turno "clássico": os dois lados atacam. Mantido pro modo CLI 1x1."""
        return self.take_turn(("move", player_move), enemy_move)

    def take_turn(self, player_action, enemy_move=None) -> list[str]:
        """Executa um turno completo a partir da ação do jogador.

        player_action é uma tupla ("move", Move), ("switch", indice),
        ("item", quantidade_de_cura) ou ("flee", None). Trocar de Pokémon ou
        usar um item consome o turno do jogador, mas o oponente ainda ataca
        em seguida — só fugir encerra a batalha na hora.
        """
        self.turn_count += 1
        kind, payload = player_action
        log: list[str] = []

        if kind == "flee":
            log.append(self.flee())
            return log

        if kind == "switch":
            log.extend(self.switch("player", payload))
            if not self.enemy.is_fainted:
                log.extend(self._act(self.enemy, self.player, enemy_move))
            log.extend(self._apply_residual_damage())
            return log

        if kind == "item":
            healed = min(payload, self.player.max_hp - self.player.current_hp)
            self.player.heal(payload)
            log.append(f"{self.player.name} recuperou {healed} HP!")
            if not self.enemy.is_fainted:
                log.extend(self._act(self.enemy, self.player, enemy_move))
            log.extend(self._apply_residual_damage())
            return log

        player_move = payload
        for attacker, defender, move in self._order(player_move, enemy_move):
            if attacker.is_fainted or defender.is_fainted:
                continue
            log.extend(self._act(attacker, defender, move))

        log.extend(self._apply_residual_damage())
        return log

    def _act(self, attacker, defender, move) -> list[str]:
        """Resolve a ação de um único Pokémon no turno: status, golpe e efeito."""
        log = []

        check = check_can_act(attacker, rng=self.rng)
        log.extend(check.log)
        if check.self_hit_damage:
            attacker.take_damage(check.self_hit_damage)
            log.append(
                f"{attacker.name} sofreu {check.self_hit_damage} de dano "
                f"({attacker.current_hp}/{attacker.max_hp} HP)."
            )
            if attacker.is_fainted:
                log.append(f"{attacker.name} desmaiou!")
            return log
        if not check.can_act:
            return log

        # Golpe de 2 turnos: o primeiro turno só carrega, sem atacar. Trocar
        # de golpe no meio cancela a carga antiga (simplificação: os jogos
        # forçam o mesmo golpe até liberar; aqui só deixamos ir de novo).
        if attacker.charging_move is not None and attacker.charging_move is not move:
            attacker.charging_move = None
        if move.is_charge_move and attacker.charging_move is None:
            attacker.charging_move = move
            log.append(f"{attacker.name} usou {move.name}!")
            log.append(f"{attacker.name} está carregando energia!")
            return log
        attacker.charging_move = None

        log.append(f"{attacker.name} usou {move.name}!")

        if move.category == "status":
            hit = self.rng.uniform(0, 100) <= move.accuracy
            if not hit:
                log.append("O ataque errou!")
                return log
            if move.weather:
                log.append(self._set_weather(move.weather))
            log.extend(self._apply_stat_changes(move, attacker, defender))
            log.extend(self._apply_ailment(move, defender))
            return log

        result = calculate_damage(attacker, defender, move, rng=self.rng, weather=self.weather)

        if not result.hit:
            log.append("O ataque errou!")
            return log
        if result.effectiveness == 0.0:
            log.append(f"Não afetou {defender.name}...")
            return log

        sturdy_save = abilities.survives_with_sturdy(defender, result.damage)
        defender.take_damage(result.damage)
        if sturdy_save and defender.is_fainted:
            defender.current_hp = 1

        if result.is_crit:
            log.append("Acerto crítico!")
        if result.effectiveness > 1.0:
            log.append("É super efetivo!")
        elif result.effectiveness < 1.0:
            log.append("Não é muito eficaz...")
        log.append(
            f"{defender.name} sofreu {min(result.damage, defender.max_hp)} de dano "
            f"({defender.current_hp}/{defender.max_hp} HP)."
        )
        if sturdy_save and defender.current_hp == 1:
            log.append(f"{defender.name} aguentou o golpe graças a Sturdy!")

        log.extend(self._apply_drain(move, attacker, result.damage))

        contact_message = abilities.on_contact_defended(defender, attacker, move, rng=self.rng)
        if contact_message:
            log.append(contact_message)
        if attacker.is_fainted:
            log.append(f"{attacker.name} desmaiou!")

        if defender.is_fainted:
            log.append(f"{defender.name} desmaiou!")
            return log

        log.extend(self._apply_ailment(move, defender))
        return log

    def _apply_drain(self, move, attacker, damage_dealt: int) -> list[str]:
        """Dreno (drain > 0, cura o atacante) e recuo (drain < 0, machuca o
        atacante), os dois como % do dano que acabou de ser causado."""
        if not move.drain or attacker.is_fainted:
            return []
        amount = max(1, abs(damage_dealt) * abs(move.drain) // 100)
        if move.drain > 0:
            attacker.heal(amount)
            return [f"{attacker.name} recuperou HP ({amount})!"]
        attacker.take_damage(amount)
        log = [f"{attacker.name} sofreu {amount} de dano do recuo!"]
        if attacker.is_fainted:
            log.append(f"{attacker.name} desmaiou!")
        return log

    def _apply_stat_changes(self, move, attacker, defender) -> list[str]:
        if not move.stat_changes:
            return []
        target = attacker if move.stat_change_target == "self" else defender
        log = []
        for stat_name, delta in move.stat_changes:
            changed = target.modify_stage(stat_name, delta)
            log.append(_stat_change_message(target, stat_name, delta, changed))
        return log

    def _set_weather(self, weather: str) -> str:
        self.weather = weather
        self.weather_turns = WEATHER_DURATION
        return f"O tempo ficou {WEATHER_LABELS[weather]}!"

    def _apply_ailment(self, move, defender) -> list[str]:
        if not move.ailment:
            return []
        if self.rng.uniform(0, 100) > move.ailment_chance:
            return []
        if move.ailment == CONFUSION:
            message = try_confuse(defender, rng=self.rng)
        else:
            message = apply_status(defender, move.ailment, rng=self.rng)
        return [message] if message else []

    def _apply_residual_damage(self) -> list[str]:
        log = []
        for pokemon in (self.player, self.enemy):
            if pokemon.is_fainted:
                continue
            result = residual_damage(pokemon)
            if result is None:
                continue
            damage, message = result
            pokemon.take_damage(damage)
            log.append(message)
            if pokemon.is_fainted:
                log.append(f"{pokemon.name} desmaiou!")
        log.extend(self._apply_weather_residual())
        log.extend(self._tick_weather())
        return log

    def _apply_weather_residual(self) -> list[str]:
        """Areia e granizo causam 1/16 do HP máximo por turno em quem não é
        imune (Pedra/Terra/Aço na areia, Gelo no granizo)."""
        immune_types = WEATHER_RESIDUAL_IMMUNE.get(self.weather)
        if immune_types is None:
            return []
        log = []
        for pokemon in (self.player, self.enemy):
            if pokemon.is_fainted or any(t in immune_types for t in pokemon.types):
                continue
            damage = max(1, pokemon.max_hp // 16)
            pokemon.take_damage(damage)
            label = "da tempestade de areia" if self.weather == "sandstorm" else "do granizo"
            log.append(f"{pokemon.name} sofreu {damage} de dano {label}!")
            if pokemon.is_fainted:
                log.append(f"{pokemon.name} desmaiou!")
        return log

    def _tick_weather(self) -> list[str]:
        if self.weather is None:
            return []
        self.weather_turns -= 1
        if self.weather_turns <= 0:
            self.weather = None
            self.weather_turns = 0
            return ["O tempo voltou ao normal."]
        return []


def _stat_change_message(pokemon, stat_name: str, delta: int, changed: int) -> str:
    label = stat_name.replace("_", " ").title()
    if changed == 0:
        direction = "subir" if delta > 0 else "cair"
        return f"O {label} de {pokemon.name} não pode {direction} mais!"
    verb = "subiu" if delta > 0 else "caiu"
    intensity = " bastante" if abs(delta) >= 2 else ""
    return f"O {label} de {pokemon.name} {verb}{intensity}!"
