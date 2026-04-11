"""Testes de pokebattle/ai.py — escolha de golpe por dificuldade e
personalidade, tudo com RNG injetável e sem tocar em Tkinter/save.py."""

from pokebattle import ai
from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon


class FixedChoiceRNG:
    """rng.choice fixo: sempre devolve o item no índice combinado, pra
    provar que a IA "fácil" realmente delega a escolha pro RNG."""

    def __init__(self, index):
        self.index = index

    def choice(self, seq):
        return seq[self.index]


def make_pokemon(name="Testmon", types=None, hp=100, moves=None):
    stats = {"hp": hp, "attack": 50, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": 50}
    return Pokemon(name, types or ["normal"], 50, stats, moves or [Move("Tackle", "normal", 40, "physical")])


def test_easy_difficulty_delegates_to_rng_regardless_of_power():
    weak = Move("Fraco", "normal", 10, "physical")
    strong = Move("Forte", "normal", 90, "physical")
    attacker = make_pokemon(moves=[weak, strong])
    defender = make_pokemon()

    # index 0 = o golpe fraco: se a IA "fácil" olhasse pra poder, nunca ia escolher esse.
    move = ai.choose_move(attacker, defender, difficulty="easy", personality="aggressive", rng=FixedChoiceRNG(0))
    assert move is weak


def test_normal_aggressive_picks_highest_power_move():
    weak = Move("Fraco", "normal", 10, "physical")
    strong = Move("Forte", "normal", 90, "physical")
    attacker = make_pokemon(moves=[weak, strong])
    defender = make_pokemon()

    move = ai.choose_move(attacker, defender, difficulty="normal", personality="aggressive")
    assert move is strong


def test_normal_strategic_prefers_type_matchup_over_raw_power():
    # Golpe de Água mais fraco (score 50 x 2.0 = 100), mas super efetivo contra
    # um Pokémon de Fogo — bate o golpe Normal, mais forte só no poder bruto
    # (score 90 x 1.0 = 90, já que Normal não tem vantagem nem desvantagem
    # contra Fogo).
    weak_but_effective = Move("Jato d'Água", "water", 50, "special")
    strong_but_resisted = Move("Investida", "normal", 90, "physical")
    attacker = make_pokemon(moves=[weak_but_effective, strong_but_resisted])
    defender = make_pokemon(types=["fire"])

    move = ai.choose_move(attacker, defender, difficulty="normal", personality="strategic")
    assert move is weak_but_effective


def test_defensive_switches_to_status_move_when_hp_is_low():
    attack_move = Move("Investida", "normal", 90, "physical")
    heal_move = Move("Descanso", "normal", 0, "status")
    attacker = make_pokemon(moves=[attack_move, heal_move])
    attacker.current_hp = 10  # bem abaixo de 40% do HP máximo
    defender = make_pokemon()

    move = ai.choose_move(attacker, defender, difficulty="normal", personality="defensive")
    assert move is heal_move


def test_defensive_attacks_normally_when_hp_is_healthy():
    attack_move = Move("Investida", "normal", 90, "physical")
    heal_move = Move("Descanso", "normal", 0, "status")
    attacker = make_pokemon(moves=[attack_move, heal_move])
    defender = make_pokemon()

    move = ai.choose_move(attacker, defender, difficulty="normal", personality="defensive")
    assert move is attack_move


def test_hard_difficulty_accounts_for_stab_on_top_of_type_effectiveness():
    # Mesmo poder e mesma efetividade de tipo (1x); só um dos golpes recebe
    # STAB (o tipo do golpe bate com o tipo do próprio atacante).
    stab_move = Move("Chama", "fire", 50, "special")
    no_stab_move = Move("Investida", "normal", 50, "physical")
    attacker = make_pokemon(types=["fire"], moves=[no_stab_move, stab_move])
    defender = make_pokemon(types=["normal"])

    move = ai.choose_move(attacker, defender, difficulty="hard", personality="aggressive")
    assert move is stab_move


def test_unknown_difficulty_and_personality_fall_back_to_sane_defaults():
    weak = Move("Fraco", "normal", 10, "physical")
    strong = Move("Forte", "normal", 90, "physical")
    attacker = make_pokemon(moves=[weak, strong])
    defender = make_pokemon()

    # "difícil demais" e "aleatorio" não existem: cai em normal/aggressive.
    move = ai.choose_move(attacker, defender, difficulty="impossible", personality="aleatorio")
    assert move is strong
