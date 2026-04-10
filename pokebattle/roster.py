"""Monta um Pokemon pronto pra batalha a partir dos dados reais da PokeAPI,
escolhendo golpes de verdade — incluindo golpes de status — em vez de usar o
roster fixo de pokebattle/data.py.

Fica separado de data.py de propósito: data.py continua sendo o roster
estático (41 Pokémon, só dano direto) que o modo texto (main.py) e os testes
usam sem precisar de internet; esse módulo é o que alimenta o modo gráfico
(main_gui.py), que depende da PokeAPI pra ter acesso a todos os Pokémon.
"""

import random
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from . import pokeapi, sprites
from .moves import Move
from .natures import random_nature
from .pokemon import Pokemon
from .status import CONFUSION, MAJOR_STATUSES

LEVEL = 50
_STAT_NAMES = ("hp", "attack", "defense", "sp_atk", "sp_def", "speed")

# Quantos golpes candidatos buscar na API pra escolher os 4 finais. Maior =
# moveset mais variado, mas mais chamadas de rede na primeira vez que um
# Pokémon aparece (ficam em cache depois disso).
MAX_MOVE_CANDIDATES = 12

SUPPORTED_AILMENTS = set(MAJOR_STATUSES) | {CONFUSION}

# PokeAPI usa "special-attack"/"special-defense"; o resto do projeto usa
# "sp_atk"/"sp_def".
_STAT_KEYS = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_atk",
    "special-defense": "sp_def",
    "speed": "speed",
}

# Nomes que o "nome.replace('-', ' ').title()" sozinho não acerta bem.
_DISPLAY_OVERRIDES = {
    "farfetchd": "Farfetch'd",
    "mr-mime": "Mr. Mime",
    "mime-jr": "Mime Jr.",
    "ho-oh": "Ho-Oh",
    "porygon-z": "Porygon-Z",
    "nidoran-f": "Nidoran♀",
    "nidoran-m": "Nidoran♂",
    "type-null": "Type: Null",
}


def display_name(species: str) -> str:
    key = species.lower()
    if key in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[key]
    return species.replace("-", " ").title()


def list_all_species() -> list[str]:
    """Todos os nomes de Pokémon (e formas alternativas) da PokeAPI."""
    return pokeapi.list_all_species_names()


def list_all_species_with_dex_numbers() -> list[tuple[int, str]]:
    """Todos os Pokémon com o número da Pokédex — usado pela tela de Pokédex."""
    return pokeapi.list_all_species_with_dex_numbers()


def list_species_starting_with(letter: str, species: Optional[list[str]] = None) -> list[str]:
    """Filtro por letra, igual ao de data.py, mas sobre a lista completa da API."""
    all_species = species if species is not None else list_all_species()
    letter = letter.strip().lower()
    if not letter:
        return all_species
    return [s for s in all_species if s.lower().startswith(letter)]


def _pick_ability(pokemon_data: dict) -> Optional[str]:
    """Escolhe uma habilidade "normal" (não oculta) pra combinar com o que
    mais aparece nos jogos; se só tiver oculta mesmo, usa essa."""
    entries = pokemon_data.get("abilities") or []
    if not entries:
        return None
    normal = [e for e in entries if not e.get("is_hidden")]
    chosen = (normal or entries)[0]
    return chosen["ability"]["name"]


def _prettify_move_name(name: str) -> str:
    return name.replace("-", " ").title()


# Nome do golpe (na PokeAPI) -> clima que ele estabelece. A API não expõe um
# campo "clima" direto num golpe, só o nome mesmo, por isso é uma lista
# curada em vez de algo genérico (igual abilities.py faz com habilidades).
_WEATHER_BY_MOVE_NAME = {
    "sunny-day": "sun",
    "rain-dance": "rain",
    "sandstorm": "sandstorm",
    "hail": "hail",
}

# PokeAPI usa "special-attack"/"special-defense"/"accuracy"/"evasion"; só os
# 5 stats de _STAT_KEYS têm estágio implementado aqui (accuracy/evasion não).
_STAT_STAGE_KEYS = {
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_atk",
    "special-defense": "sp_def",
    "speed": "speed",
}


def _build_stat_changes(move_json: dict) -> tuple:
    changes = []
    for entry in move_json.get("stat_changes") or []:
        stat_name = _STAT_STAGE_KEYS.get(entry["stat"]["name"])
        if stat_name and entry["change"]:
            changes.append((stat_name, entry["change"]))
    return tuple(changes)


def _build_move(move_name: str) -> Move:
    move_json = pokeapi.get_move(move_name)
    meta = move_json.get("meta") or {}
    raw_ailment = (meta.get("ailment") or {}).get("name", "none")
    raw_chance = meta.get("ailment_chance") or 0

    ailment = raw_ailment if raw_ailment in SUPPORTED_AILMENTS else None
    # Golpe de status "puro" costuma vir com ailment_chance=0 na API, o que
    # ali significa "sempre acontece", não "nunca" — só golpes de dano com
    # efeito colateral (ex: 10% de queimar) trazem uma porcentagem real.
    ailment_chance = 100 if (ailment and raw_chance == 0) else raw_chance

    target_name = (move_json.get("target") or {}).get("name", "")
    category_meta = meta.get("category") or {}

    return Move(
        name=_prettify_move_name(move_json["name"]),
        type=move_json["type"]["name"],
        power=move_json.get("power") or 0,
        category=move_json["damage_class"]["name"],
        accuracy=move_json.get("accuracy") or 100,
        ailment=ailment,
        ailment_chance=ailment_chance,
        priority=move_json.get("priority") or 0,
        drain=meta.get("drain") or 0,
        stat_changes=_build_stat_changes(move_json),
        stat_change_target="self" if target_name == "user" else "target",
        weather=_WEATHER_BY_MOVE_NAME.get(move_json["name"]),
        is_charge_move=category_meta.get("name") == "damage+charge",
    )


def _level_up_candidates(pokemon_data: dict, level: int) -> list[str]:
    """Nomes de golpes aprendidos por nível até `level`, do mais recente pro
    mais antigo (golpes aprendidos mais tarde tendem a ser os mais fortes).

    Usa a primeira versão do jogo que listar o golpe como "level-up" — pode
    variar um pouco o nível exato entre gerações, o que é uma simplificação
    aceitável aqui (o ponto é ter um moveset real e variado, não reproduzir
    a progressão exata de um jogo específico).
    """
    learned = []
    for entry in pokemon_data["moves"]:
        for detail in entry["version_group_details"]:
            if detail["move_learn_method"]["name"] != "level-up":
                continue
            learned_at = detail["level_learned_at"]
            if 0 < learned_at <= level:
                learned.append((learned_at, entry["move"]["name"]))
            break

    learned.sort(key=lambda item: item[0], reverse=True)
    seen = set()
    names = []
    for _, name in learned:
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _build_moves(move_names: list[str]) -> list[Move]:
    """Busca vários golpes em paralelo — sequencial seria lento (cada golpe é
    uma chamada de rede na primeira vez que aparece)."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_build_move, move_names))


def _pick_moveset(pokemon_data: dict, types: list[str], level: int) -> list[Move]:
    candidate_names = _level_up_candidates(pokemon_data, level)[:MAX_MOVE_CANDIDATES]
    if not candidate_names:
        # Caso raro (algumas formas especiais não têm golpe de nível):
        # usa qualquer golpe conhecido como último recurso.
        candidate_names = [m["move"]["name"] for m in pokemon_data["moves"]][:MAX_MOVE_CANDIDATES]

    candidates = _build_moves(candidate_names)

    stab_damaging = [m for m in candidates if m.power > 0 and m.type in types]
    other_damaging = [m for m in candidates if m.power > 0 and m.type not in types]
    status_moves = [m for m in candidates if m.power == 0 and (m.ailment or m.stat_changes or m.weather)]

    chosen: list[Move] = []
    if stab_damaging:
        chosen.append(max(stab_damaging, key=lambda m: m.power))
    if other_damaging:
        chosen.append(max(other_damaging, key=lambda m: m.power))
    if status_moves:
        chosen.append(status_moves[0])

    remaining = [m for m in candidates if m not in chosen and m.power > 0]
    remaining.sort(key=lambda m: m.power, reverse=True)
    for move in remaining:
        if len(chosen) >= 4:
            break
        chosen.append(move)

    if not chosen:
        chosen.append(Move("Struggle", "normal", 50, "physical"))

    return chosen[:4]


def random_ivs(rng=random) -> dict:
    return {stat: rng.randint(0, 31) for stat in _STAT_NAMES}


def build_pokemon(species: str, level: int = LEVEL, rng=random) -> Pokemon:
    """Busca um Pokémon na PokeAPI e monta um Pokemon pronto pra batalha, já
    com IVs aleatórios, natureza aleatória e o sprite em `pokemon.sprite_path`.

    Cada Pokémon do modo gráfico é um indivíduo (IV/natureza próprios), do
    jeito que os jogos fazem — diferente do roster fixo do modo texto, que
    usa IV/EV neutros de propósito (ver pokemon.py).
    """
    pokemon_data = pokeapi.get_pokemon(species)

    types = [t["type"]["name"] for t in sorted(pokemon_data["types"], key=lambda t: t["slot"])]
    base_stats = {
        _STAT_KEYS[s["stat"]["name"]]: s["base_stat"]
        for s in pokemon_data["stats"]
        if s["stat"]["name"] in _STAT_KEYS
    }
    moves = _pick_moveset(pokemon_data, types, level)

    pokemon = Pokemon(
        display_name(pokemon_data["name"]), types, level, base_stats, moves,
        ivs=random_ivs(rng), nature=random_nature(rng),
    )
    pokemon.species = pokemon_data["name"]
    pokemon.pokedex_id = pokemon_data["id"]
    pokemon.sprite_path = sprites.get_sprite_path(pokemon_data)
    pokemon.ability = _pick_ability(pokemon_data)
    return pokemon
