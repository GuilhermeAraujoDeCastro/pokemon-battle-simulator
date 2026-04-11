"""Efeitos de status de batalha: queimadura, veneno, paralisia, congelamento,
sono e confusão.

Cada Pokémon guarda no máximo um status "maior" (burn/poison/paralysis/freeze/
sleep) por vez, igual nos jogos oficiais. Confusão é tratada à parte porque ela
é "volátil": não conta como status maior e pode acontecer junto com um deles.

Esse módulo não importa nada de pokemon.py/battle.py de propósito (só recebe
os objetos Pokemon já prontos), pra não criar dependência circular.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

BURN = "burn"
POISON = "poison"
PARALYSIS = "paralysis"
FREEZE = "freeze"
SLEEP = "sleep"
CONFUSION = "confusion"  # não é um status "maior", ver módulo acima

MAJOR_STATUSES = (BURN, POISON, PARALYSIS, FREEZE, SLEEP)

# Sigla mostrada do lado do nome do Pokémon, igual nos jogos oficiais.
SHORT_LABEL = {
    BURN: "QMD",
    POISON: "VEN",
    PARALYSIS: "PAR",
    FREEZE: "CGL",
    SLEEP: "SON",
}

_LABEL_PT = {
    BURN: "queimado",
    POISON: "envenenado",
    PARALYSIS: "paralisado",
    FREEZE: "congelado",
    SLEEP: "dormindo",
}

# Tipos imunes a cada status maior (regra oficial: Fogo não queima nem
# congela, Veneno/Aço não envenena, Elétrico não paralisa, Gelo não congela).
_IMMUNE_TYPES = {
    BURN: {"fire"},
    POISON: {"poison", "steel"},
    PARALYSIS: {"electric"},
    FREEZE: {"ice", "fire"},
}


@dataclass
class ActionCheck:
    """Resultado de checar se um Pokémon consegue agir no turno."""

    can_act: bool
    self_hit_damage: int = 0
    log: list = field(default_factory=list)


def apply_status(pokemon, status: str, rng=random) -> Optional[str]:
    """Tenta aplicar um status maior a um Pokémon.

    Devolve a mensagem de log, ou None se não aplicou (já tinha status, ou o
    tipo do Pokémon é imune a esse status).
    """
    if pokemon.status is not None:
        return None
    if pokemon.is_fainted:
        return None
    if any(t in _IMMUNE_TYPES.get(status, set()) for t in pokemon.types):
        return None

    pokemon.status = status
    if status == SLEEP:
        pokemon.sleep_turns = rng.randint(1, 3)
    return f"{pokemon.name} ficou {_LABEL_PT[status]}!"


def try_confuse(pokemon, rng=random) -> Optional[str]:
    """Tenta deixar um Pokémon confuso. Devolve a mensagem, ou None se já estava."""
    if pokemon.confusion_turns > 0 or pokemon.is_fainted:
        return None
    pokemon.confusion_turns = rng.randint(2, 5)
    return f"{pokemon.name} ficou confuso!"


def _confusion_self_damage(pokemon, rng) -> int:
    """Dano que a confusão causa no próprio Pokémon.

    Mesma fórmula-base de calculate_damage (battle.py), mas com um golpe
    físico fixo de 40 de poder contra si mesmo, sem STAB, tipo ou crítico —
    é assim que o jogo oficial calcula esse dano.
    """
    base = (
        (2 * pokemon.level / 5 + 2) * 40 * pokemon.effective_attack / pokemon.defense
    ) / 50 + 2
    return max(1, int(base * rng.uniform(0.85, 1.0)))


def check_can_act(pokemon, rng=random) -> ActionCheck:
    """Verifica se o Pokémon consegue agir nesse turno.

    Atualiza os contadores de sono/congelamento/confusão como efeito
    colateral (é assim que os jogos oficiais fazem: a checagem em si já
    avança o efeito).
    """
    log = []

    if pokemon.status == SLEEP:
        pokemon.sleep_turns -= 1
        if pokemon.sleep_turns <= 0:
            pokemon.status = None
            log.append(f"{pokemon.name} acordou!")
        else:
            log.append(f"{pokemon.name} está dormindo.")
            return ActionCheck(False, log=log)

    elif pokemon.status == FREEZE:
        if rng.random() < 0.2:
            pokemon.status = None
            log.append(f"{pokemon.name} descongelou!")
        else:
            log.append(f"{pokemon.name} está congelado e não consegue se mover!")
            return ActionCheck(False, log=log)

    if pokemon.confusion_turns > 0:
        pokemon.confusion_turns -= 1
        if pokemon.confusion_turns <= 0:
            log.append(f"{pokemon.name} não está mais confuso.")
        elif rng.random() < (1 / 3):
            log.append(f"{pokemon.name} está confuso...")
            damage = _confusion_self_damage(pokemon, rng)
            return ActionCheck(False, self_hit_damage=damage, log=log)

    if pokemon.status == PARALYSIS and rng.random() < 0.25:
        log.append(f"{pokemon.name} está paralisado e não consegue se mexer!")
        return ActionCheck(False, log=log)

    return ActionCheck(True, log=log)


def residual_damage(pokemon) -> Optional[tuple[int, str]]:
    """Dano de fim de turno de queimadura/veneno, ou None se não tem nenhum."""
    if pokemon.status == BURN:
        dmg = max(1, pokemon.max_hp // 16)
        return dmg, f"{pokemon.name} sofreu {dmg} de dano da queimadura."
    if pokemon.status == POISON:
        dmg = max(1, pokemon.max_hp // 8)
        return dmg, f"{pokemon.name} sofreu {dmg} de dano do veneno."
    return None
