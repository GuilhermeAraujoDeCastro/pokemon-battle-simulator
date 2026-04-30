"""Testes de pokebattle/abilities.py: só o conjunto curado tem efeito
mecânico de verdade (Static, Flame Body, Poison Point, Levitate, Intimidate,
Guts, Rough Skin, Sturdy) — o resto das habilidades só aparece na tela."""

import pytest

from pokebattle import abilities
from pokebattle.battle import Battle, calculate_damage
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon
from pokebattle.status import BURN, PARALYSIS


class FixedRNG:
    """Sempre acerta a chance de porcentagem que estiver testando (uniform)
    e nunca crítico (random)."""

    def __init__(self, percent_roll=0.0):
        self.percent_roll = percent_roll

    def uniform(self, a, b):
        return self.percent_roll if b > 2 else 1.0

    def random(self):
        return 1.0

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]


def make_pokemon(name="Testmon", types=None, level=50, ability=None, **stat_overrides):
    stats = {"hp": 60, "attack": 60, "defense": 60, "sp_atk": 60, "sp_def": 60, "speed": 60}
    stats.update(stat_overrides)
    mon = Pokemon(name, types or ["normal"], level, stats, [Move("Tackle", "normal", 40, "physical")])
    mon.ability = ability
    return mon


def test_display_name_uses_the_curated_pretty_name_or_titlecases_the_rest():
    assert abilities.display_name("flame-body") == "Flame Body"
    assert abilities.display_name("chlorophyll") == "Chlorophyll"
    assert abilities.display_name(None) == "—"


def test_static_has_a_chance_to_paralyze_on_a_physical_hit():
    attacker = make_pokemon("Atacante")
    defender = make_pokemon("Defensor", ability="static")
    move = Move("Tackle", "normal", 40, "physical")

    message = abilities.on_contact_defended(defender, attacker, move, rng=FixedRNG(percent_roll=0.0))

    assert attacker.status == PARALYSIS
    assert "Static" in message


def test_static_does_nothing_on_a_special_move():
    attacker = make_pokemon("Atacante")
    defender = make_pokemon("Defensor", ability="static")
    move = Move("Ember", "fire", 40, "special")

    message = abilities.on_contact_defended(defender, attacker, move, rng=FixedRNG(percent_roll=0.0))

    assert message is None
    assert attacker.status is None


def test_levitate_grants_full_immunity_to_ground_moves():
    attacker = make_pokemon("Atacante")
    defender = make_pokemon("Defensor", ability="levitate")
    move = Move("Earthquake", "ground", 100, "physical")

    result = calculate_damage(attacker, defender, move, rng=FixedRNG())

    assert result.effectiveness == 0.0
    assert result.damage == 0


def test_intimidate_lowers_the_opponents_attack_stage_on_switch_in():
    intimidator = make_pokemon("Intimidador", ability="intimidate")
    opponent = make_pokemon("Alvo")

    message = abilities.on_switch_in(intimidator, opponent)

    assert opponent.stat_stages["attack"] == -1
    assert message is not None


def test_battle_applies_intimidate_from_whoever_starts_with_it():
    intimidator = make_pokemon("Intimidador", ability="intimidate")
    opponent = make_pokemon("Alvo")

    battle = Battle(intimidator, opponent)

    assert opponent.stat_stages["attack"] == -1
    assert battle.intro_log  # tem pelo menos a mensagem do Intimidate


def test_guts_boosts_attack_and_ignores_the_burn_penalty():
    healthy = make_pokemon("Saudavel", ability="guts")
    burned = make_pokemon("Queimado", ability="guts")
    burned.status = BURN

    assert burned.effective_attack > healthy.effective_attack


def test_without_guts_burn_still_halves_attack():
    burned = make_pokemon("Queimado")
    burned.status = BURN

    assert burned.effective_attack == max(1, burned.attack // 2)


def test_rough_skin_deals_recoil_to_the_attacker():
    attacker = make_pokemon("Atacante")
    defender = make_pokemon("Defensor", ability="rough-skin")
    move = Move("Tackle", "normal", 40, "physical")
    hp_before = attacker.current_hp

    message = abilities.on_contact_defended(defender, attacker, move, rng=FixedRNG())

    assert attacker.current_hp < hp_before
    assert "Rough Skin" in message


def test_sturdy_survives_a_lethal_hit_from_full_hp_with_one_hp_left():
    defender = make_pokemon("Robusto", ability="sturdy", hp=60)
    assert abilities.survives_with_sturdy(defender, incoming_damage=999)


def test_sturdy_does_not_save_when_not_at_full_hp():
    defender = make_pokemon("Robusto", ability="sturdy", hp=60)
    defender.current_hp -= 1

    assert not abilities.survives_with_sturdy(defender, incoming_damage=999)


def test_stage_multiplier_matches_the_official_table():
    from pokebattle.pokemon import stage_multiplier

    assert stage_multiplier(0) == 1.0
    assert stage_multiplier(1) == pytest.approx(1.5)
    assert stage_multiplier(-1) == pytest.approx(2 / 3)
    assert stage_multiplier(6) == 4.0
    assert stage_multiplier(-6) == 0.25


def test_modify_stage_clamps_between_minus_six_and_six():
    mon = make_pokemon()
    for _ in range(10):
        mon.modify_stage("attack", -1)
    assert mon.stat_stages["attack"] == -6

    changed = mon.modify_stage("attack", -1)
    assert changed == 0


# ---------- Wonder Guard, Speed Boost, Sand Veil, Water/Volt Absorb, Poison Heal ----------

def test_wonder_guard_blocks_non_super_effective_damage():
    defender = make_pokemon("Guardiao", ability="wonder-guard", types=["normal"])
    move = Move("Tackle", "normal", 40, "physical")  # 1x — não é super efetivo
    assert abilities.blocks_non_supereffective(defender, type_effectiveness=1.0, move_category=move.category)


def test_wonder_guard_lets_super_effective_moves_through():
    defender = make_pokemon("Guardiao", ability="wonder-guard", types=["grass"])
    move = Move("Ember", "fire", 40, "special")  # 2x contra Grass
    assert not abilities.blocks_non_supereffective(defender, type_effectiveness=2.0, move_category=move.category)


def test_wonder_guard_never_blocks_status_moves():
    defender = make_pokemon("Guardiao", ability="wonder-guard")
    assert not abilities.blocks_non_supereffective(defender, type_effectiveness=1.0, move_category="status")


def test_calculate_damage_deals_zero_through_wonder_guard():
    attacker = make_pokemon("Atacante")
    defender = make_pokemon("Guardiao", ability="wonder-guard", types=["normal"])
    move = Move("Tackle", "normal", 40, "physical")

    result = calculate_damage(attacker, defender, move, rng=FixedRNG())
    assert result.damage == 0


def test_speed_boost_raises_speed_stage_at_turn_end():
    mon = make_pokemon("Veloz", ability="speed-boost")
    message = abilities.on_turn_end(mon)
    assert mon.stat_stages["speed"] == 1
    assert message is not None


def test_speed_boost_does_nothing_without_the_ability():
    mon = make_pokemon("Normal")
    assert abilities.on_turn_end(mon) is None
    assert mon.stat_stages["speed"] == 0


def test_sand_veil_lowers_accuracy_in_a_sandstorm():
    defender = make_pokemon("Escondido", ability="sand-veil")
    assert abilities.accuracy_multiplier(defender, weather="sandstorm") < 1.0
    assert abilities.accuracy_multiplier(defender, weather=None) == 1.0
    assert abilities.accuracy_multiplier(defender, weather="rain") == 1.0


def test_water_absorb_blocks_water_damage_and_heals():
    attacker = make_pokemon("Aquatico")
    defender = make_pokemon("Esponja", ability="water-absorb")
    defender.current_hp = 10
    move = Move("Water Gun", "water", 40, "special")

    result = calculate_damage(attacker, defender, move, rng=FixedRNG())
    assert result.damage == 0

    message = abilities.on_absorb(defender, "water")
    assert defender.current_hp > 10
    assert message is not None


def test_water_absorb_does_nothing_for_a_different_type():
    defender = make_pokemon("Esponja", ability="water-absorb")
    assert abilities.on_absorb(defender, "fire") is None


def test_volt_absorb_grants_immunity_to_electric_moves():
    attacker = make_pokemon("Eletrico")
    defender = make_pokemon("Esponja", ability="volt-absorb")
    move = Move("Thunderbolt", "electric", 90, "special")

    result = calculate_damage(attacker, defender, move, rng=FixedRNG())
    assert result.effectiveness == 0.0
    assert result.damage == 0


def test_poison_heal_heals_instead_of_taking_poison_damage():
    from pokebattle.status import POISON

    mon = make_pokemon("Curado", ability="poison-heal", hp=160)
    mon.status = POISON
    mon.current_hp = 100
    expected_heal = mon.max_hp // 8

    message = abilities.poison_heal_tick(mon)

    assert mon.current_hp == 100 + expected_heal
    assert message is not None


def test_poison_heal_does_nothing_without_poison_status():
    mon = make_pokemon("Saudavel", ability="poison-heal")
    assert abilities.poison_heal_tick(mon) is None
