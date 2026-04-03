import pytest

from pokebattle.battle import _base_power, calculate_damage
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon, calc_hp, calc_stat


class FixedRNG:
    """RNG determinístico pra teste: acerta sempre e fixa variação/crítico.

    A checagem de precisão usa uniform(0, 100) e a variação de dano usa
    uniform(0.85, 1.0) — como os dois têm faixas bem diferentes, usamos o
    limite superior (b) pra saber qual delas está sendo chamada.
    """

    def __init__(self, variance=1.0, crit=False, hits=True):
        self.variance = variance
        self.crit = crit
        self.hits = hits

    def uniform(self, a, b):
        if b > 2:
            # faixa 0-100: devolve um valor acima de qualquer precisão
            # possível (100) pra garantir o erro quando hits=False
            return 0.0 if self.hits else 101.0
        return self.variance

    def random(self):
        return 0.0 if self.crit else 1.0


def make_pokemon(name, types, level=50, hp=45, attack=49, defense=49,
                  sp_atk=65, sp_def=65, speed=45):
    stats = {"hp": hp, "attack": attack, "defense": defense,
             "sp_atk": sp_atk, "sp_def": sp_def, "speed": speed}
    return Pokemon(name, types, level, stats, [])


def test_base_power_matches_official_formula():
    expected = (((2 * 50 / 5 + 2) * 40 * 50 / 50) / 50) + 2
    assert _base_power(50, 40, 50, 50) == pytest.approx(expected)


def test_calc_stat_formulas_use_neutral_iv_ev():
    assert calc_hp(45, 50) == (2 * 45 * 50) // 100 + 50 + 10
    assert calc_stat(49, 50) == (2 * 49 * 50) // 100 + 5


def test_immune_type_deals_zero_damage():
    attacker = make_pokemon("Gastly", ["ghost", "poison"])
    defender = make_pokemon("Snorlax", ["normal"])
    ghost_move = Move("Lick", "ghost", 30, "physical")

    result = calculate_damage(attacker, defender, ghost_move, rng=FixedRNG())
    assert result.hit is True
    assert result.effectiveness == 0.0
    assert result.damage == 0


def test_miss_deals_zero_damage():
    attacker = make_pokemon("Charmander", ["fire"])
    defender = make_pokemon("Bulbasaur", ["grass", "poison"])
    move = Move("Ember", "fire", 40, "special")

    result = calculate_damage(attacker, defender, move, rng=FixedRNG(hits=False))
    assert result.hit is False
    assert result.damage == 0


def test_super_effective_deals_more_damage_than_neutral():
    attacker = make_pokemon("Charmander", ["fire"], attack=52, sp_atk=60)
    grass_defender = make_pokemon("Bulbasaur", ["grass", "poison"])
    normal_defender = make_pokemon("Eevee", ["normal"])
    move = Move("Ember", "fire", 40, "special")

    vs_grass = calculate_damage(attacker, grass_defender, move, rng=FixedRNG())
    vs_normal = calculate_damage(attacker, normal_defender, move, rng=FixedRNG())

    assert vs_grass.effectiveness == 2.0
    assert vs_normal.effectiveness == 1.0
    assert vs_grass.damage > vs_normal.damage


def test_stab_increases_damage():
    move = Move("Investida de Fogo", "fire", 40, "physical")
    fire_type = make_pokemon("Charmander", ["fire"], attack=52)
    non_fire_type = make_pokemon("SemSTAB", ["normal"], attack=52)
    defender = make_pokemon("Alvo", ["normal"])

    with_stab = calculate_damage(fire_type, defender, move, rng=FixedRNG())
    without_stab = calculate_damage(non_fire_type, defender, move, rng=FixedRNG())

    assert with_stab.damage > without_stab.damage


def test_critical_hit_multiplies_damage():
    attacker = make_pokemon("Machop", ["fighting"], attack=80)
    defender = make_pokemon("Snorlax", ["normal"])
    move = Move("Golpe", "fighting", 50, "physical")

    normal_hit = calculate_damage(attacker, defender, move, rng=FixedRNG(crit=False))
    crit_hit = calculate_damage(attacker, defender, move, rng=FixedRNG(crit=True))

    assert crit_hit.is_crit is True
    assert crit_hit.damage > normal_hit.damage


def test_damage_is_never_less_than_one_when_it_hits_and_is_effective():
    attacker = make_pokemon("Fraco", ["normal"], attack=1)
    defender = make_pokemon("Tanque", ["normal"], defense=999)
    move = Move("Investida", "normal", 10, "physical")

    result = calculate_damage(attacker, defender, move, rng=FixedRNG(variance=0.85))
    assert result.damage >= 1
