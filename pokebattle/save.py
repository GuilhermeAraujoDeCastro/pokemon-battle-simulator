"""Save game local do modo gráfico: Pokédex vista e insígnias conquistadas,
num JSON do lado do projeto. Fica de fora do git (é progresso de cada
jogador, não faz sentido versionar) e é lido/escrito por completo a cada
chamada, porque o arquivo é pequeno e isso evita bugs de estado desatualizado
entre a tela de batalha e a tela de Pokédex/ginásios.
"""

import copy
import json
from pathlib import Path
from typing import Any

SAVE_PATH = Path(__file__).resolve().parent.parent / "savegame.json"

_DEFAULT_SAVE = {
    "pokedex_seen": [],  # nomes de espécie (formato da PokeAPI) já vistos em batalha
    "badges": [],  # ids dos ginásios já vencidos, na ordem em que foram vencidos
    "money": 0,  # dinheiro do jogo (recompensa de ginásio), nada a ver com dinheiro de verdade
    "items": {"potion": 3},  # inventário da PokéMart (cura, revive, EV, itens segurados); começa com 3 Poções
    "trainer_name": "",  # perguntado uma vez, na primeira tela do jogo
    "starter": "",  # espécie do Pokémon inicial (formato da PokeAPI), escolhido uma vez
    "difficulty": "normal",  # "easy" | "normal" | "hard" — ver pokebattle/ai.py
    "trainers_defeated": 0,  # total de batalhas vencidas (comuns + ginásio) — usado pelas missões
    "quests_completed": [],  # ids de missões já resgatadas — ver pokebattle/quests.py
    "battles_lost": 0,  # usado pela IA adaptativa (ai.adaptive_personality) e por conquistas
    "avatar_color": "red",  # cor do avatar do treinador — ver pokebattle/avatar.py
    "nuzlocke": False,  # modo Nuzlocke ligado/desligado — ver pokebattle/nuzlocke.py
    "achievements_unlocked": [],  # ids de conquistas já desbloqueadas — ver pokebattle/achievements.py
    "owned_pokemon": [],  # espécies compradas na loja de Pokémon da PokéMart (fora do time atual)
}


def load() -> dict[str, Any]:
    if not SAVE_PATH.exists():
        return copy.deepcopy(_DEFAULT_SAVE)
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(_DEFAULT_SAVE)
    # Um save antigo sem um campo novo (ex: de antes dos ginásios existirem)
    # ganha o valor padrão em vez de quebrar. copy.deepcopy porque os valores
    # são listas: um dict(_DEFAULT_SAVE) raso deixaria "data" e o default
    # global compartilhando a MESMA lista, e um data["badges"].append(...)
    # em algum lugar acabaria vazando pro default de todo mundo.
    merged = copy.deepcopy(_DEFAULT_SAVE)
    merged.update(data)
    return merged


def write(data: dict[str, Any]) -> None:
    SAVE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def mark_seen(species_names) -> dict[str, Any]:
    """Adiciona uma ou mais espécies à Pokédex vista."""
    if isinstance(species_names, str):
        species_names = [species_names]
    data = load()
    seen = set(data["pokedex_seen"])
    seen.update(species_names)
    data["pokedex_seen"] = sorted(seen)
    write(data)
    return data


def add_badge(gym_id: str) -> dict[str, Any]:
    data = load()
    if gym_id not in data["badges"]:
        data["badges"].append(gym_id)
        write(data)
    return data


def set_trainer_name(name: str) -> dict[str, Any]:
    data = load()
    data["trainer_name"] = name
    write(data)
    return data


def set_starter(species: str) -> dict[str, Any]:
    data = load()
    data["starter"] = species
    write(data)
    return data


def set_difficulty(level: str) -> dict[str, Any]:
    data = load()
    data["difficulty"] = level
    write(data)
    return data


def increment_trainers_defeated(amount: int = 1) -> dict[str, Any]:
    data = load()
    data["trainers_defeated"] += amount
    write(data)
    return data


def add_completed_quest(quest_id: str) -> dict[str, Any]:
    data = load()
    if quest_id not in data["quests_completed"]:
        data["quests_completed"].append(quest_id)
        write(data)
    return data


def add_money(amount: int) -> dict[str, Any]:
    data = load()
    data["money"] += amount
    write(data)
    return data


def spend_money(amount: int) -> bool:
    """Tenta gastar dinheiro. Devolve False sem mudar nada se não tiver o
    suficiente."""
    data = load()
    if data["money"] < amount:
        return False
    data["money"] -= amount
    write(data)
    return True


def add_item(item_id: str, qty: int = 1) -> dict[str, Any]:
    data = load()
    data["items"][item_id] = data["items"].get(item_id, 0) + qty
    write(data)
    return data


def remove_item(item_id: str, qty: int = 1) -> bool:
    """Tenta gastar `qty` unidades de um item. Devolve False sem mudar nada
    se não tiver o suficiente."""
    data = load()
    have = data["items"].get(item_id, 0)
    if have < qty:
        return False
    data["items"][item_id] = have - qty
    write(data)
    return True


def increment_battles_lost(amount: int = 1) -> dict[str, Any]:
    data = load()
    data["battles_lost"] += amount
    write(data)
    return data


def set_avatar_color(color_id: str) -> dict[str, Any]:
    data = load()
    data["avatar_color"] = color_id
    write(data)
    return data


def set_nuzlocke(enabled: bool) -> dict[str, Any]:
    data = load()
    data["nuzlocke"] = bool(enabled)
    write(data)
    return data


def add_achievement(achievement_id: str) -> dict[str, Any]:
    data = load()
    if achievement_id not in data["achievements_unlocked"]:
        data["achievements_unlocked"].append(achievement_id)
        write(data)
    return data


def add_owned_pokemon(species: str) -> dict[str, Any]:
    data = load()
    data["owned_pokemon"].append(species)
    write(data)
    return data


def remove_owned_pokemon(species: str) -> bool:
    """Tenta remover uma espécie comprada (ex: depois de adicioná-la ao
    time). Devolve False se não tiver nenhuma sobrando pra remover."""
    data = load()
    if species not in data["owned_pokemon"]:
        return False
    data["owned_pokemon"].remove(species)
    write(data)
    return True
