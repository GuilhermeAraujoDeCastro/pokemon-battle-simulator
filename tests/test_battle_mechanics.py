"""Testes das mecânicas novas de battle.py: prioridade, recuo/dreno, golpes
que mudam stat, clima e golpes de 2 turnos. Tudo lógica pura, RNG falso."""

import pytest

from pokebattle.battle import Battle, calculate_damage
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


class FixedRNG:
    """Sempre acerta e nunca crítico, com variação de dano fixa em 1.0
    (o máximo); uniform(0,100) só cobre a checagem de precisão/ailment, a de
    variação (0.85-1.0) é distinguida pelo teto do intervalo, igual o padrão
    usado em test_damage.py."""

    def __init__(self, hits=True):
        self.hits = hits

    def uniform(self, a, b):
        if b > 2:  # faixa 0-100: precisão/ailment
            return 0.0 if self.hits else 101.0
        return 1.0  # faixa 0.85-1.0: variação de dano no teto

    def random(self):
        return 1.0

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]


def make_pokemon(name, types=None, level=50, speed=60, **stat_overrides):
    stats = {"hp": 200, "attack": 60, "defense": 60, "sp_atk": 60, "sp_def": 60, "speed": speed}
    stats.update(stat_overrides)
    return Pokemon(name, types or ["normal"], level, stats, [Move("Tackle", "normal", 40, "physical")])


# ---------- prioridade ----------

def test_a_higher_priority_move_goes_first_even_when_slower():
    slow_priority = make_pokemon("Lento", speed=10)
    fast_normal = make_pokemon("Rapido", speed=200)
    battle = Battle(slow_priority, fast_normal, rng=FixedRNG())

    priority_move = Move("Investida Rápida", "normal", 20, "physical", priority=1)
    normal_move = Move("Golpe", "normal", 20, "physical", priority=0)

    order = battle._order(priority_move, normal_move)
    assert order[0][0] is slow_priority  # quem tem o golpe de prioridade age primeiro


def test_equal_priority_falls_back_to_speed():
    slow = make_pokemon("Lento", speed=10)
    fast = make_pokemon("Rapido", speed=200)
    battle = Battle(slow, fast, rng=FixedRNG())

    move = Move("Golpe", "normal", 20, "physical")
    order = battle._order(move, move)
    assert order[0][0] is fast


# ---------- recuo e dreno ----------

def test_a_move_with_positive_drain_heals_the_attacker():
    attacker = make_pokemon("Sugador", attack=80)
    defender = make_pokemon("Alvo", defense=30)
    attacker.current_hp = 10
    battle = Battle(attacker, defender, rng=FixedRNG())
    drain_move = Move("Giga Dreno", "grass", 60, "special", drain=50)

    log = battle._act(attacker, defender, drain_move)

    assert attacker.current_hp > 10
    assert any("recuperou" in line for line in log)


def test_a_move_with_negative_drain_hurts_the_attacker_with_recoil():
    attacker = make_pokemon("Kamikaze", attack=80)
    defender = make_pokemon("Alvo", defense=30, hp=500)
    battle = Battle(attacker, defender, rng=FixedRNG())
    recoil_move = Move("Fúria Dupla", "normal", 100, "physical", drain=-25)
    hp_before = attacker.current_hp

    log = battle._act(attacker, defender, recoil_move)

    assert attacker.current_hp < hp_before
    assert any("recuo" in line for line in log)


# ---------- golpes que mudam stat ----------

def test_a_self_targeted_stat_move_raises_the_users_own_stage():
    user = make_pokemon("Dançarino")
    opponent = make_pokemon("Alvo")
    battle = Battle(user, opponent, rng=FixedRNG())
    move = Move("Dança das Espadas", "normal", 0, "status", stat_changes=(("attack", 2),), stat_change_target="self")

    battle._act(user, opponent, move)

    assert user.stat_stages["attack"] == 2
    assert opponent.stat_stages["attack"] == 0


def test_a_target_stat_move_lowers_the_opponents_stage():
    user = make_pokemon("Intimidador")
    opponent = make_pokemon("Alvo")
    battle = Battle(user, opponent, rng=FixedRNG())
    move = Move("Rugido", "normal", 0, "status", stat_changes=(("attack", -1),), stat_change_target="target")

    battle._act(user, opponent, move)

    assert opponent.stat_stages["attack"] == -1
    assert user.stat_stages["attack"] == 0


# ---------- clima ----------

def test_a_weather_move_sets_the_battles_weather_and_it_expires():
    user = make_pokemon("Chuveiro")
    opponent = make_pokemon("Alvo")
    battle = Battle(user, opponent, rng=FixedRNG())
    move = Move("Dança da Chuva", "water", 0, "status", weather="rain")

    battle._act(user, opponent, move)
    assert battle.weather == "rain"
    assert battle.weather_turns == 5

    for _ in range(5):
        battle._tick_weather()
    assert battle.weather is None


def test_rain_boosts_water_moves_and_weakens_fire_moves():
    attacker = make_pokemon("Aquatico", sp_atk=80)
    defender = make_pokemon("Alvo", sp_def=60)
    water_move = Move("Jato d'Água", "water", 60, "special")
    fire_move = Move("Ember", "fire", 60, "special")

    boosted = calculate_damage(attacker, defender, water_move, rng=FixedRNG(), weather="rain")
    normal = calculate_damage(attacker, defender, water_move, rng=FixedRNG(), weather=None)
    weakened = calculate_damage(attacker, defender, fire_move, rng=FixedRNG(), weather="rain")
    normal_fire = calculate_damage(attacker, defender, fire_move, rng=FixedRNG(), weather=None)

    assert boosted.damage > normal.damage
    assert weakened.damage < normal_fire.damage


def test_sandstorm_damages_non_immune_types_each_turn():
    victim = make_pokemon("Vitima", types=["normal"], hp=160)
    immune = make_pokemon("Imune", types=["rock"], hp=160)
    battle = Battle(victim, immune, rng=FixedRNG())
    battle.weather = "sandstorm"
    battle.weather_turns = 5

    hp_before_victim = victim.current_hp
    hp_before_immune = immune.current_hp
    battle._apply_weather_residual()

    assert victim.current_hp < hp_before_victim
    assert immune.current_hp == hp_before_immune


# ---------- golpes de 2 turnos ----------

def test_a_charge_move_does_not_attack_on_the_first_turn():
    attacker = make_pokemon("Carregador", sp_atk=999)
    defender = make_pokemon("Alvo", sp_def=1, hp=999)
    battle = Battle(attacker, defender, rng=FixedRNG())
    charge_move = Move("Solar Beam", "grass", 120, "special", is_charge_move=True)

    log = battle._act(attacker, defender, charge_move)

    assert defender.current_hp == defender.max_hp  # não tomou dano ainda
    assert attacker.charging_move is charge_move
    assert any("carregando" in line for line in log)


def test_a_charge_move_attacks_for_real_on_the_second_use():
    attacker = make_pokemon("Carregador", sp_atk=999)
    defender = make_pokemon("Alvo", sp_def=1, hp=999)
    battle = Battle(attacker, defender, rng=FixedRNG())
    charge_move = Move("Solar Beam", "grass", 120, "special", is_charge_move=True)

    battle._act(attacker, defender, charge_move)  # 1º turno: carrega
    battle._act(attacker, defender, charge_move)  # 2º turno: ataca de verdade

    assert defender.current_hp < defender.max_hp
    assert attacker.charging_move is None


def test_switching_the_move_cancels_a_pending_charge():
    attacker = make_pokemon("Carregador", sp_atk=999)
    defender = make_pokemon("Alvo", sp_def=1, hp=999)
    battle = Battle(attacker, defender, rng=FixedRNG())
    charge_move = Move("Solar Beam", "grass", 120, "special", is_charge_move=True)
    other_move = Move("Tackle", "normal", 40, "physical")

    battle._act(attacker, defender, charge_move)  # começa a carregar
    battle._act(attacker, defender, other_move)  # muda de ideia: cancela a carga

    assert attacker.charging_move is None
    assert defender.current_hp < defender.max_hp  # o Tackle bateu de verdade
