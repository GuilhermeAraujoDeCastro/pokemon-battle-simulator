"""Catálogo de itens da PokéMart e a lógica de usar um item em batalha.

Fica de fora de battle.py de propósito: o motor de batalha só entende "curar
X HP em alguém do time" (a tupla ("item", ...) de Battle.take_turn); este
módulo é quem decide QUANTO cada item cura e SE ele pode ser usado num
Pokémon específico (item de cura normal não funciona em quem desmaiou,
Revive só funciona em quem desmaiou).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    price: int
    description: str
    revive: bool = False  # True só pra Revive: cura quem desmaiou, com metade do HP
    heal_amount: int = 0  # HP curado (ignorado quando revive=True)


CATALOG: list[Item] = [
    Item("potion", "Poção", 300, "Cura 20 HP.", heal_amount=20),
    Item("super_potion", "Super Poção", 700, "Cura 50 HP.", heal_amount=50),
    Item("hyper_potion", "Hiper Poção", 1200, "Cura 120 HP.", heal_amount=120),
    Item("revive", "Revive", 1500, "Revive um Pokémon desmaiado com metade do HP.", revive=True),
]

_BY_ID = {item.id: item for item in CATALOG}


def get_item(item_id: str) -> Item:
    return _BY_ID[item_id]


def can_use_on(item_id: str, pokemon) -> bool:
    """Se esse item faz sentido usar nesse Pokémon agora (Revive só em quem
    desmaiou, cura normal só em quem não desmaiou)."""
    item = get_item(item_id)
    return pokemon.is_fainted if item.revive else not pokemon.is_fainted


def heal_amount_for(item_id: str, pokemon) -> int:
    """Quanto HP esse item aplica nesse Pokémon especificamente — Revive
    depende do HP máximo de quem está sendo revivido."""
    item = get_item(item_id)
    if item.revive:
        return max(1, pokemon.max_hp // 2)
    return item.heal_amount
