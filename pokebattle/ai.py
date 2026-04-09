"""IA do treinador adversário: decide qual golpe usar a cada turno,
considerando a dificuldade escolhida pelo jogador e a personalidade do
treinador. Fica fora de battle.py de propósito — o motor de batalha só
entende "execute esse Move"; este módulo é quem decide QUAL.

Dificuldades (guardadas no save.py, escolhidas na tela de time):
    easy   — golpe aleatório entre TODOS os golpes, sem lógica nenhuma.
    normal — evita golpes fracos contra o tipo do adversário e segue a
             personalidade, mas só olhando o poder bruto do golpe.
    hard   — a personalidade calcula um "dano esperado" de verdade (poder x
             efetividade de tipo x STAB), bem mais afiada que o normal.

Personalidades (curadas por ginásio em gyms.py; aleatória fora de ginásio):
    aggressive  — sempre o golpe com maior dano esperado.
    defensive   — com o HP baixo, prefere um golpe de status (cura/buff) em
                  vez de atacar.
    strategic   — prioriza o melhor multiplicador de tipo, mesmo que o
                  poder bruto do golpe seja menor.
"""

import random

from .types_chart import effectiveness

DIFFICULTIES = ["easy", "normal", "hard"]
DIFFICULTY_LABELS = {"easy": "Fácil", "normal": "Normal", "hard": "Difícil"}

PERSONALITIES = ["aggressive", "defensive", "strategic"]
PERSONALITY_LABELS = {
    "aggressive": "Agressivo",
    "defensive": "Defensivo",
    "strategic": "Estratégico",
}

_LOW_HP_RATIO = 0.4  # abaixo disso, o perfil defensivo troca ataque por golpe de status


def _expected_damage(move, attacker, defender) -> float:
    stab = 1.5 if move.type in attacker.types else 1.0
    return move.power * effectiveness(move.type, defender.types) * stab


def choose_move(attacker, defender, difficulty="normal", personality="aggressive", rng=random):
    """Devolve o Move que a IA escolhe usar nesse turno."""
    if difficulty not in DIFFICULTIES:
        difficulty = "normal"
    if personality not in PERSONALITIES:
        personality = "aggressive"

    moves = attacker.moves
    if difficulty == "easy":
        return rng.choice(moves)

    damaging = [m for m in moves if m.power > 0]
    status_moves = [m for m in moves if m.power == 0]
    pool = damaging or moves

    if personality == "defensive" and status_moves and attacker.current_hp <= attacker.max_hp * _LOW_HP_RATIO:
        return rng.choice(status_moves)

    if difficulty == "normal":
        if personality == "strategic":
            return max(pool, key=lambda m: effectiveness(m.type, defender.types) * m.power)
        return max(pool, key=lambda m: m.power)  # aggressive, e defensive com HP OK: bate com o mais forte

    # difficulty == "hard": todo mundo calcula dano esperado de verdade
    return max(pool, key=lambda m: _expected_damage(m, attacker, defender))
