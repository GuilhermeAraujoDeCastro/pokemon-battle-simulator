"""Habilidades (abilities) dos Pokémon.

Todo Pokémon mostra sua habilidade de verdade (nome vindo da PokeAPI, em
pokemon.ability), mas só um conjunto curado das mais conhecidas tem efeito
mecânico real aqui — implementar as ~300 habilidades da API de forma
genérica não vale o esforço pra esse projeto. As demais só aparecem na tela,
sem mudar a batalha.

Simplificação: golpe físico == golpe de contato. A PokeAPI marca contato por
golpe (não por categoria), mas a grande maioria dos golpes físicos realmente
toca o alvo — a diferença não muda a experiência de jogar esse projeto o
suficiente pra justificar mais uma chamada de rede por golpe.
"""

import random
from typing import Optional

from .status import BURN, PARALYSIS, POISON, apply_status

# Habilidade -> status que ela tenta causar em quem acerta um golpe físico
# no dono dela (Static, Flame Body, Poison Point).
ON_CONTACT_STATUS = {
    "static": PARALYSIS,
    "flame-body": BURN,
    "poison-point": POISON,
}
ON_CONTACT_CHANCE = 30  # % — mesma chance dos jogos

# Habilidade -> tipo de golpe ao qual ela dá imunidade total (Levitate).
TYPE_IMMUNITY_ABILITIES = {
    "levitate": "ground",
}

# Habilidade -> tipo de golpe que ela absorve: além da imunidade de
# TYPE_IMMUNITY_ABILITIES, ainda cura 1/4 do HP máximo (Water Absorb, Volt
# Absorb).
TYPE_ABSORB_ABILITIES = {
    "water-absorb": "water",
    "volt-absorb": "electric",
}
ABSORB_HEAL_FRACTION = 4  # cura 1/4 do HP máximo

WONDER_GUARD = "wonder-guard"
SPEED_BOOST = "speed-boost"
SAND_VEIL = "sand-veil"
POISON_HEAL = "poison-heal"
SAND_VEIL_ACCURACY_MULTIPLIER = 0.8  # golpes contra quem tem Sand Veil, na areia, erram mais

DISPLAY_NAMES = {
    "static": "Static",
    "flame-body": "Flame Body",
    "poison-point": "Poison Point",
    "levitate": "Levitate",
    "intimidate": "Intimidate",
    "guts": "Guts",
    "rough-skin": "Rough Skin",
    "sturdy": "Sturdy",
    "wonder-guard": "Wonder Guard",
    "speed-boost": "Speed Boost",
    "sand-veil": "Sand Veil",
    "water-absorb": "Water Absorb",
    "volt-absorb": "Volt Absorb",
    "poison-heal": "Poison Heal",
}


def display_name(ability: Optional[str]) -> str:
    if not ability:
        return "—"
    return DISPLAY_NAMES.get(ability, ability.replace("-", " ").title())


def has_ability(pokemon, ability_name: str) -> bool:
    return getattr(pokemon, "ability", None) == ability_name


def grants_type_immunity(defender, move_type: str) -> bool:
    """True se a habilidade do defensor anula esse tipo de golpe (Levitate,
    e também Water Absorb/Volt Absorb — a cura deles é tratada à parte por
    on_absorb, já que calculate_damage só calcula, não cura ninguém)."""
    ability = getattr(defender, "ability", None)
    if TYPE_IMMUNITY_ABILITIES.get(ability) == move_type:
        return True
    return TYPE_ABSORB_ABILITIES.get(ability) == move_type


def on_absorb(defender, move_type: str) -> Optional[str]:
    """Water Absorb/Volt Absorb: além da imunidade (já aplicada em
    grants_type_immunity), cura 1/4 do HP máximo do defensor. Devolve a
    mensagem de log, ou None se a habilidade não é essa ou o tipo não bate."""
    ability = getattr(defender, "ability", None)
    if TYPE_ABSORB_ABILITIES.get(ability) != move_type or defender.is_fainted:
        return None
    if defender.current_hp >= defender.max_hp:
        return f"{defender.name} tem {display_name(ability)}, mas já está com o HP cheio!"
    amount = max(1, defender.max_hp // ABSORB_HEAL_FRACTION)
    defender.heal(amount)
    return f"{defender.name} absorveu o golpe com {display_name(ability)} e recuperou HP!"


def blocks_non_supereffective(defender, type_effectiveness: float, move_category: str) -> bool:
    """Wonder Guard: golpes de dano só acertam se forem super efetivos
    (multiplicador > 1). Golpes de status continuam passando normalmente."""
    return (
        has_ability(defender, WONDER_GUARD)
        and move_category != "status"
        and type_effectiveness <= 1.0
    )


def accuracy_multiplier(defender, weather: Optional[str]) -> float:
    """Sand Veil: na tempestade de areia, golpes contra esse Pokémon erram
    mais (na prática, uma evasão extra)."""
    if has_ability(defender, SAND_VEIL) and weather == "sandstorm":
        return SAND_VEIL_ACCURACY_MULTIPLIER
    return 1.0


def on_turn_end(pokemon) -> Optional[str]:
    """Speed Boost: sobe 1 estágio de Velocidade no fim de cada turno em que
    esse Pokémon está em campo, sem precisar de gatilho nenhum."""
    if not has_ability(pokemon, SPEED_BOOST) or pokemon.is_fainted:
        return None
    changed = pokemon.modify_stage("speed", 1)
    if changed == 0:
        return None
    return f"A Velocidade de {pokemon.name} subiu com Speed Boost!"


def poison_heal_tick(pokemon) -> Optional[str]:
    """Poison Heal: em vez de tomar o dano residual normal do veneno, cura
    1/8 do HP máximo no fim do turno. Quem chama deve pular o
    status.residual_damage normal pra esse Pokémon quando isso devolve uma
    mensagem."""
    if not has_ability(pokemon, POISON_HEAL) or pokemon.status != POISON or pokemon.is_fainted:
        return None
    if pokemon.current_hp >= pokemon.max_hp:
        return None
    amount = max(1, pokemon.max_hp // 8)
    pokemon.heal(amount)
    return f"{pokemon.name} recuperou {amount} HP com Poison Heal!"


def survives_with_sturdy(defender, incoming_damage: int) -> bool:
    """Sturdy: de HP cheio, um golpe que mataria deixa 1 HP em vez de 0."""
    return (
        has_ability(defender, "sturdy")
        and defender.current_hp == defender.max_hp
        and incoming_damage >= defender.current_hp
    )


def on_contact_defended(defender, attacker, move, rng=random) -> Optional[str]:
    """Reação da habilidade do defensor a ser atingido por um golpe físico:
    Static/Flame Body/Poison Point (chance de status no atacante) ou Rough
    Skin (dano de recuo). Devolve a mensagem de log, ou None."""
    if move.category != "physical" or attacker.is_fainted:
        return None
    ability = getattr(defender, "ability", None)

    if ability in ON_CONTACT_STATUS:
        if rng.uniform(0, 100) > ON_CONTACT_CHANCE:
            return None
        message = apply_status(attacker, ON_CONTACT_STATUS[ability], rng=rng)
        if not message:
            return None
        return f"{defender.name} tem {display_name(ability)}! {message}"

    if ability == "rough-skin":
        recoil = max(1, attacker.max_hp // 8)  # 1/8 do HP máximo de quem encostou
        attacker.take_damage(recoil)
        return f"Rough Skin feriu {attacker.name} em {recoil} de dano!"

    return None


def on_switch_in(pokemon, opponent) -> Optional[str]:
    """Intimidate: ao entrar em campo, baixa 1 estágio de Ataque do
    oponente ativo. Devolve a mensagem de log, ou None se a habilidade não
    é essa."""
    if not has_ability(pokemon, "intimidate") or opponent.is_fainted:
        return None
    changed = opponent.modify_stage("attack", -1)
    if changed == 0:
        return f"{pokemon.name} tenta intimidar, mas o Ataque de {opponent.name} já não pode cair mais!"
    return f"{pokemon.name} intimida {opponent.name}! O Ataque caiu."
