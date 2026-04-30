"""Testes dos hooks aditivos da Fase C em battle.py: itens segurados (held
items) e clima fixo de arena (locations). Mesmo padrão de RNG falso de
test_battle_mechanics.py."""

from pokebattle.battle import Battle, calculate_damage
from pokebattle.locations import get_location
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon
from pokebattle.status import PARALYSIS


class FixedRNG:
    def __init__(self, hits=True):
        self.hits = hits

    def uniform(self, a, b):
        if b > 2:
            return 0.0 if self.hits else 101.0
        return 1.0

    def random(self):
        return 1.0

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]


def make_pokemon(name, types=None, held_item=None, **stat_overrides):
    stats = {"hp": 200, "attack": 60, "defense": 60, "sp_atk": 60, "sp_def": 60, "speed": 60}
    stats.update(stat_overrides)
    mon = Pokemon(name, types or ["normal"], 50, stats, [Move("Tackle", "normal", 40, "physical")])
    mon.held_item = held_item
    return mon


# ---------- itens segurados ----------

def test_choice_band_boosts_physical_damage():
    attacker = make_pokemon("SemItem")
    boosted_attacker = make_pokemon("ComChoiceBand", held_item="held_choice_band")
    defender = make_pokemon("Alvo")
    move = Move("Tackle", "normal", 40, "physical")

    plain = calculate_damage(attacker, defender, move, rng=FixedRNG())
    boosted = calculate_damage(boosted_attacker, defender, move, rng=FixedRNG())
    assert boosted.damage > plain.damage


def test_leftovers_heals_at_the_end_of_the_turn():
    attacker = make_pokemon("ComLeftovers", held_item="held_leftovers", hp=200)
    defender = make_pokemon("Alvo", speed=1)
    attacker.current_hp = 100
    expected_heal = attacker.max_hp // 16
    battle = Battle(attacker, defender, rng=FixedRNG())

    log = battle._apply_residual_damage()

    assert attacker.current_hp == 100 + expected_heal
    assert any("Leftovers" in line for line in log)


def test_a_curing_berry_cures_the_status_it_applies_and_is_consumed():
    attacker = make_pokemon("Paralisante")
    defender = make_pokemon("ComCheri", held_item="held_cheri_berry")
    battle = Battle(attacker, defender, rng=FixedRNG())
    move = Move("Thunder Wave", "electric", 0, "status", ailment=PARALYSIS, ailment_chance=100)

    battle._act(attacker, defender, move)

    assert defender.status is None
    assert defender.held_item is None


# ---------- clima fixo de arena (locations) ----------

def test_a_battle_at_a_location_starts_with_its_fixed_weather():
    battle = Battle(make_pokemon("A"), make_pokemon("B"), rng=FixedRNG(), location=get_location("volcano"))
    assert battle.weather == "sun"
    assert battle.weather_turns is None


def test_the_fixed_weather_never_expires_on_its_own():
    battle = Battle(make_pokemon("A"), make_pokemon("B"), rng=FixedRNG(), location=get_location("lake"))
    for _ in range(20):
        battle._tick_weather()
    assert battle.weather == "rain"


def test_a_weather_move_temporarily_overrides_the_fixed_weather_then_reverts():
    battle = Battle(make_pokemon("A"), make_pokemon("B"), rng=FixedRNG(), location=get_location("volcano"))
    assert battle.weather == "sun"

    battle._set_weather("rain")  # golpe de clima sobrepõe o clima da arena
    assert battle.weather == "rain"
    assert battle.weather_turns == 5

    for _ in range(5):
        battle._tick_weather()
    assert battle.weather == "sun"  # voltou pro clima fixo do vulcão
    assert battle.weather_turns is None


def test_a_battle_without_a_location_behaves_like_before():
    battle = Battle(make_pokemon("A"), make_pokemon("B"), rng=FixedRNG())
    assert battle.weather is None
    assert battle.weather_turns == 0
