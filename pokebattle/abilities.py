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

DISPLAY_NAMES = {
    "static": "Static",
    "flame-body": "Flame Body",
    "poison-point": "Poison Point",
    "levitate": "Levitate",
    "intimidate": "Intimidate",
    "guts": "Guts",
    "rough-skin": "Rough Skin",
    "sturdy": "Sturdy",
}


def display_name(ability: Optional[str]) -> str:
    if not ability:
        return "—"
    return DISPLAY_NAMES.get(ability, ability.replace("-", " ").title())


def has_ability(pokemon, ability_name: str) -> bool:
    return getattr(pokemon, "ability", None) == ability_name


def grants_type_immunity(defender, move_type: str) -> bool:
    """True se a habilidade do defensor anula esse tipo de golpe (Levitate)."""
    return TYPE_IMMUNITY_ABILITIES.get(getattr(defender, "ability", None)) == move_type


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
        recoil = max(1, defender.max_hp // 8)
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
