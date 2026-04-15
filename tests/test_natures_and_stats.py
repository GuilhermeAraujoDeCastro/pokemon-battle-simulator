import random

from pokebattle.moves import Move
from pokebattle.natures import NATURES, multiplier, random_nature
from pokebattle.pokemon import Pokemon, calc_hp, calc_stat


def test_calc_hp_and_calc_stat_default_to_the_old_neutral_numbers():
    # Sem passar iv/ev/nature, tem que dar exatamente a mesma conta de antes
    # (roster fixo do modo texto e testes antigos dependem disso).
    assert calc_hp(45, 50) == (2 * 45 * 50) // 100 + 50 + 10
    assert calc_stat(49, 50) == (2 * 49 * 50) // 100 + 5


def test_iv_and_ev_raise_the_stat():
    base = calc_stat(100, 50)
    with_iv = calc_stat(100, 50, iv=31)
    with_ev = calc_stat(100, 50, ev=252)
    assert with_iv > base
    assert with_ev > base


def test_nature_boosts_and_lowers_by_ten_percent():
    boosted = calc_stat(100, 50, nature="Adamant", stat_name="attack")
    lowered = calc_stat(100, 50, nature="Adamant", stat_name="sp_atk")
    neutral = calc_stat(100, 50, nature="Adamant", stat_name="defense")
    plain = calc_stat(100, 50)
    assert boosted > plain
    assert lowered < plain
    assert neutral == plain


def test_neutral_natures_never_change_anything():
    for nature in ("Hardy", "Docile", "Serious", "Bashful", "Quirky"):
        for stat in ("attack", "defense", "sp_atk", "sp_def", "speed"):
            assert multiplier(nature, stat) == 1.0


def test_every_nature_boosts_and_lowers_a_different_stat():
    for boosted, lowered in NATURES.values():
        if boosted is None:
            assert lowered is None
        else:
            assert boosted != lowered


def test_random_nature_always_returns_a_known_nature():
    assert random_nature(random.Random(1)) in NATURES


def make_pokemon(**overrides):
    stats = {"hp": 100, "attack": 100, "defense": 100, "sp_atk": 100, "sp_def": 100, "speed": 100}
    kwargs = dict(name="Testmon", types=["normal"], level=50, base_stats=stats, moves=[Move("Tackle", "normal", 40, "physical")])
    kwargs.update(overrides)
    return Pokemon(**kwargs)


def test_pokemon_without_ivs_evs_nature_behaves_like_before():
    mon = make_pokemon()
    assert mon.ivs == {"hp": 0, "attack": 0, "defense": 0, "sp_atk": 0, "sp_def": 0, "speed": 0}
    assert mon.nature == "Hardy"
    assert mon.attack == calc_stat(100, 50)


def test_pokemon_with_perfect_ivs_has_higher_stats():
    perfect = make_pokemon(ivs={stat: 31 for stat in ("hp", "attack", "defense", "sp_atk", "sp_def", "speed")})
    plain = make_pokemon()
    assert perfect.max_hp > plain.max_hp
    assert perfect.attack > plain.attack


def test_gain_ev_respects_the_stat_and_total_caps():
    mon = make_pokemon()
    gained = mon.gain_ev("attack", 300)  # acima do teto de 252 por stat
    assert gained == 252
    assert mon.evs["attack"] == 252

    second = mon.gain_ev("defense", 300)  # teto total de 510 já quase batido
    assert mon.evs["attack"] + second <= 510


def test_level_up_recalculates_stats_and_keeps_hp_delta_instead_of_full_healing():
    mon = make_pokemon(level=49)
    mon.current_hp = 1  # quase desmaiado
    hp_before = mon.max_hp

    mon.level = 50
    mon._recalculate_stats()

    assert mon.max_hp > hp_before
    # curou só o quanto o HP máximo subiu, não voltou pro máximo inteiro
    assert mon.current_hp == 1 + (mon.max_hp - hp_before)
