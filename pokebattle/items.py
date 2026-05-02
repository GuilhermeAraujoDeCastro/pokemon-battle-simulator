"""Catálogo de itens da PokéMart e a lógica de usar um item em batalha.

Fica de fora de battle.py de propósito: o motor de batalha só entende "curar
X HP em alguém do time" (a tupla ("item", ...) de Battle.take_turn); este
módulo é quem decide QUANTO cada item cura e SE ele pode ser usado num
Pokémon específico (item de cura normal não funciona em quem desmaiou,
Revive só funciona em quem desmaiou).

Os itens de treino de EV (Proteína e companhia) moram no mesmo catálogo —
são itens da Mochila como os outros — mas `ev_stat` os diferencia: eles não
aparecem na Mochila de batalha (`can_use_on` só olha pra cura/revive), só na
tela de time, aplicados fora de combate com `apply_ev_item`.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    price: int
    description: str
    revive: bool = False  # True só pra Revive: cura quem desmaiou, com metade do HP
    heal_amount: int = 0  # HP curado (ignorado quando revive=True)
    ev_stat: Optional[str] = None  # setado só nos itens de treino de EV
    ev_amount: int = 0  # quanto EV o item de treino concede (ignorado fora dos itens de EV)


CATALOG: list[Item] = [
    Item("potion", "Poção", 300, "Cura 20 HP.", heal_amount=20),
    Item("super_potion", "Super Poção", 700, "Cura 50 HP.", heal_amount=50),
    Item("hyper_potion", "Hiper Poção", 1200, "Cura 120 HP.", heal_amount=120),
    Item("revive", "Revive", 1500, "Revive um Pokémon desmaiado com metade do HP.", revive=True),
    Item("hp_up", "HP Up", 2000, "Treino: +10 EV de HP.", ev_stat="hp", ev_amount=10),
    Item("protein", "Proteína", 2000, "Treino: +10 EV de Ataque.", ev_stat="attack", ev_amount=10),
    Item("iron", "Ferro", 2000, "Treino: +10 EV de Defesa.", ev_stat="defense", ev_amount=10),
    Item("calcium", "Cálcio", 2000, "Treino: +10 EV de Ataque Especial.", ev_stat="sp_atk", ev_amount=10),
    Item("zinc", "Zinco", 2000, "Treino: +10 EV de Defesa Especial.", ev_stat="sp_def", ev_amount=10),
    Item("carbos", "Carboidrato", 2000, "Treino: +10 EV de Velocidade.", ev_stat="speed", ev_amount=10),
]

EV_ITEM_IDS = frozenset(item.id for item in CATALOG if item.ev_stat)

_BY_ID = {item.id: item for item in CATALOG}


def get_item(item_id: str) -> Item:
    return _BY_ID[item_id]


def apply_ev_item(item_id: str, pokemon) -> int:
    """Aplica um item de treino de EV a um Pokémon do time (fora de
    batalha). Devolve quanto EV realmente foi ganho (Pokemon.gain_ev já
    respeita os tetos oficiais de 252 por stat / 510 no total)."""
    item = get_item(item_id)
    return pokemon.gain_ev(item.ev_stat, item.ev_amount)


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
