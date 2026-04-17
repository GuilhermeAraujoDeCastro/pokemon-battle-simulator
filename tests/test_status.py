from pokebattle.pokemon import Pokemon
from pokebattle.status import (
    BURN,
    FREEZE,
    PARALYSIS,
    POISON,
    SLEEP,
    apply_status,
    check_can_act,
    residual_damage,
    try_confuse,
)


class StubRNG:
    """RNG determinístico: toda chamada devolve um valor fixo escolhido no teste."""

    def __init__(self, random_value=0.0, randint_value=1):
        self.random_value = random_value
        self.randint_value = randint_value

    def random(self):
        return self.random_value

    def uniform(self, a, b):
        return self.random_value

    def randint(self, a, b):
        return self.randint_value


def make_pokemon(name="Testmon", types=None, hp=100, attack=50, defense=50):
    stats = {"hp": hp, "attack": attack, "defense": defense, "sp_atk": 50, "sp_def": 50, "speed": 50}
    return Pokemon(name, types or ["normal"], level=50, base_stats=stats, moves=[])


def test_apply_status_sets_status_and_returns_message():
    mon = make_pokemon()
    message = apply_status(mon, POISON)
    assert mon.status == POISON
    assert "envenenado" in message


def test_apply_status_does_nothing_if_already_has_a_status():
    mon = make_pokemon()
    apply_status(mon, POISON)
    message = apply_status(mon, BURN)
    assert message is None
    assert mon.status == POISON


def test_fire_types_cannot_be_burned_or_frozen():
    mon = make_pokemon(types=["fire"])
    assert apply_status(mon, BURN) is None
    assert apply_status(mon, FREEZE) is None
    assert mon.status is None


def test_electric_types_cannot_be_paralyzed():
    assert apply_status(make_pokemon(types=["electric"]), PARALYSIS) is None


def test_poison_and_steel_types_cannot_be_poisoned():
    assert apply_status(make_pokemon(types=["poison"]), POISON) is None
    assert apply_status(make_pokemon(types=["steel"]), POISON) is None


def test_sleep_sets_a_turn_counter():
    mon = make_pokemon()
    apply_status(mon, SLEEP, rng=StubRNG(randint_value=2))
    assert mon.status == SLEEP
    assert mon.sleep_turns == 2


def test_try_confuse_sets_counter_and_does_not_stack():
    mon = make_pokemon()
    message = try_confuse(mon, rng=StubRNG(randint_value=3))
    assert mon.confusion_turns == 3
    assert "confuso" in message
    assert try_confuse(mon) is None  # já estava confuso


def test_sleeping_pokemon_wakes_up_and_can_act_when_counter_reaches_zero():
    mon = make_pokemon()
    apply_status(mon, SLEEP, rng=StubRNG(randint_value=1))

    check = check_can_act(mon, rng=StubRNG())
    assert check.can_act is True
    assert mon.status is None


def test_sleeping_pokemon_cannot_act_while_counter_is_still_running():
    mon = make_pokemon()
    apply_status(mon, SLEEP, rng=StubRNG(randint_value=2))

    check = check_can_act(mon, rng=StubRNG())
    assert check.can_act is False
    assert mon.status == SLEEP
    assert mon.sleep_turns == 1


def test_frozen_pokemon_stays_frozen_when_thaw_roll_fails():
    mon = make_pokemon()
    mon.status = FREEZE
    check = check_can_act(mon, rng=StubRNG(random_value=0.9))
    assert check.can_act is False
    assert mon.status == FREEZE


def test_frozen_pokemon_thaws_when_roll_succeeds():
    mon = make_pokemon()
    mon.status = FREEZE
    check = check_can_act(mon, rng=StubRNG(random_value=0.0))
    assert check.can_act is True
    assert mon.status is None


def test_paralyzed_pokemon_sometimes_cannot_act():
    mon = make_pokemon()
    mon.status = PARALYSIS
    assert check_can_act(mon, rng=StubRNG(random_value=0.1)).can_act is False


def test_paralyzed_pokemon_can_still_act_most_of_the_time():
    mon = make_pokemon()
    mon.status = PARALYSIS
    assert check_can_act(mon, rng=StubRNG(random_value=0.9)).can_act is True


def test_confused_pokemon_sometimes_hits_itself():
    mon = make_pokemon(attack=100, defense=50)
    mon.confusion_turns = 2
    check = check_can_act(mon, rng=StubRNG(random_value=0.0))
    assert check.can_act is False
    assert check.self_hit_damage > 0
    assert mon.confusion_turns == 1


def test_confusion_wears_off_after_its_turn_counter_ends():
    mon = make_pokemon()
    mon.confusion_turns = 1
    check_can_act(mon, rng=StubRNG(random_value=0.9))
    assert mon.confusion_turns == 0


def test_burn_residual_damage_is_one_sixteenth_of_max_hp():
    mon = make_pokemon()
    mon.max_hp = 160
    mon.status = BURN
    damage, message = residual_damage(mon)
    assert damage == 10
    assert "queimadura" in message


def test_poison_residual_damage_is_one_eighth_of_max_hp():
    mon = make_pokemon()
    mon.max_hp = 160
    mon.status = POISON
    damage, message = residual_damage(mon)
    assert damage == 20
    assert "veneno" in message


def test_healthy_pokemon_has_no_residual_damage():
    assert residual_damage(make_pokemon()) is None
