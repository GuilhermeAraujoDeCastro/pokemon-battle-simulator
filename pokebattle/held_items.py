"""Itens segurados (held items): um Pokémon pode carregar um item o tempo
todo, com efeito mecânico durante a batalha inteira — diferente dos itens da
Mochila (items.py), que são consumidos manualmente pelo jogador num turno.

Só um conjunto curado tem efeito de verdade aqui, no mesmo espírito de
abilities.py: Leftovers (cura no fim do turno), Choice Band (+50% de dano
físico, sem travar o Pokémon num único golpe — simplificação consciente: os
jogos travam o golpe até trocar, o que exigiria guardar mais estado por
Pokémon só pra isso) e berries que curam um status específico ao ser
aplicado, se consumindo no processo.

As Mega Stones (mega.py) também são itens segurados — o catálogo delas mora
aqui, e a ativação em mega.py.
"""

import random
from dataclasses import dataclass
from typing import Optional

from .status import BURN, FREEZE, PARALYSIS, POISON, SLEEP


@dataclass(frozen=True)
class HeldItem:
    id: str
    name: str
    price: int
    description: str


CATALOG: list[HeldItem] = [
    HeldItem("held_leftovers", "Leftovers", 3000, "Cura 1/16 do HP máximo no fim de cada turno."),
    HeldItem("held_choice_band", "Choice Band", 3500, "Golpes físicos causam 50% a mais de dano."),
    HeldItem("held_cheri_berry", "Mirtilo Cheri", 800, "Cura Paralisia sozinho, uma vez."),
    HeldItem("held_rawst_berry", "Mirtilo Rawst", 800, "Cura Queimadura sozinho, uma vez."),
    HeldItem("held_pecha_berry", "Mirtilo Pecha", 800, "Cura Veneno sozinho, uma vez."),
    HeldItem("held_aspear_berry", "Mirtilo Aspear", 800, "Cura Congelamento sozinho, uma vez."),
    HeldItem("held_chesto_berry", "Mirtilo Chesto", 800, "Cura Sono sozinho, uma vez."),
    HeldItem("held_lum_berry", "Mirtilo Lum", 2000, "Cura qualquer status sozinho, uma vez."),
]

_BY_ID = {item.id: item for item in CATALOG}

# Berry -> status que ela cura (ANY_STATUS = qualquer um, caso do Lum Berry).
ANY_STATUS = "any"
_CURE_BERRIES = {
    "held_cheri_berry": PARALYSIS,
    "held_rawst_berry": BURN,
    "held_pecha_berry": POISON,
    "held_aspear_berry": FREEZE,
    "held_chesto_berry": SLEEP,
    "held_lum_berry": ANY_STATUS,
}

LEFTOVERS = "held_leftovers"
CHOICE_BAND = "held_choice_band"


def get_item(item_id: str) -> HeldItem:
    return _BY_ID[item_id]


def display_name(item_id: Optional[str]) -> str:
    if not item_id:
        return "—"
    item = _BY_ID.get(item_id)
    return item.name if item else item_id


def held_item_of(pokemon) -> Optional[str]:
    return getattr(pokemon, "held_item", None)


def end_of_turn_heal(pokemon) -> Optional[str]:
    """Leftovers: cura 1/16 do HP máximo no fim do turno, se não estiver
    com HP cheio nem desmaiado. Devolve a mensagem de log, ou None."""
    if held_item_of(pokemon) != LEFTOVERS or pokemon.is_fainted or pokemon.current_hp >= pokemon.max_hp:
        return None
    amount = max(1, pokemon.max_hp // 16)
    pokemon.heal(amount)
    return f"{pokemon.name} recuperou {amount} HP com o Leftovers!"


def power_modifier(attacker, move) -> float:
    """Choice Band: golpes físicos causam 50% a mais de dano."""
    if held_item_of(attacker) == CHOICE_BAND and move.category == "physical":
        return 1.5
    return 1.0


def try_cure_status(pokemon, status: str, rng=random) -> Optional[str]:
    """Chamado logo depois que um status maior é aplicado: se o Pokémon
    segura uma berry que cura esse status (ou qualquer um, no caso do Lum
    Berry), cura na hora e consome o item. Devolve a mensagem, ou None."""
    item_id = held_item_of(pokemon)
    cured_status = _CURE_BERRIES.get(item_id)
    if cured_status is None or (cured_status != ANY_STATUS and cured_status != status):
        return None
    item_name = display_name(item_id)
    pokemon.cure_status()
    pokemon.held_item = None
    return f"{pokemon.name} curou o status com o {item_name}!"
