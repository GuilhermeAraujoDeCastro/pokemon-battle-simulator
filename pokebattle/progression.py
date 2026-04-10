"""Progressão pós-batalha do modo gráfico: XP, EV, level up, golpe novo e
evolução. Fica fora de battle.py de propósito — o modo texto não usa nada
disso, é só o modo gráfico que chama essas funções depois que alguém vence.
"""

from typing import Optional

from . import pokeapi, roster, sprites
from .moves import Move

MAX_LEVEL = 100
EV_GAIN_PER_KO = 1  # simplificação: os jogos variam de 1 a 3 por espécie


def experience_for_win(defeated_pokemon_data: dict, defeated_level: int, is_trainer_battle: bool = True) -> int:
    """Fórmula oficial simplificada (sem Exp. Share, item de XP ou afeição).

    base_experience vem de verdade da PokeAPI; o multiplicador de 1.5x pra
    batalhas de treinador é o mesmo que os jogos aplicam.
    """
    base_xp = defeated_pokemon_data.get("base_experience") or 64
    multiplier = 1.5 if is_trainer_battle else 1.0
    return max(1, int(base_xp * defeated_level * multiplier / 7))


def xp_to_next_level(level: int) -> int:
    """XP acumulado total precisado pra alcançar `level + 1`.

    Usa a curva "medium fast" (n³) pra todo mundo. Os jogos variam a curva
    por espécie (rápida, lenta, "erratic" etc.), o que exigiria buscar o
    growth_rate de cada Pokémon na PokeAPI só pra isso — a curva única não
    muda a experiência de jogar esse projeto o suficiente pra justificar
    mais uma chamada de rede por Pokémon.
    """
    return (level + 1) ** 3


def gain_ev_from_victory(winner, defeated_data: dict) -> Optional[str]:
    """Regra oficial: quem vence ganha EV no stat mais alto do derrotado.
    Devolve uma mensagem de log, ou None se os tetos de EV já foram batidos.
    """
    stats = {
        roster._STAT_KEYS[s["stat"]["name"]]: s["base_stat"]
        for s in defeated_data["stats"]
        if s["stat"]["name"] in roster._STAT_KEYS
    }
    best_stat = max(stats, key=stats.get)
    gained = winner.gain_ev(best_stat, EV_GAIN_PER_KO)
    if gained <= 0:
        return None
    return f"{winner.name} ganhou pontos de esforço em {best_stat.replace('_', ' ').title()}!"


def apply_level_up(pokemon, parent=None) -> dict:
    """Sobe o nível de `pokemon` enquanto o XP acumulado permitir.

    Devolve um resumo: {"levels_gained": int, "new_moves": [Move, ...],
    "evolved_into": nome da espécie nova ou None}. Não decide sozinho o que
    fazer com "new_moves" nem com a evolução — quem chama (main_gui.py)
    decide como perguntar isso ao jogador.
    """
    result = {"levels_gained": 0, "new_moves": [], "evolved_into": None}
    if pokemon.level >= MAX_LEVEL:
        return result

    while pokemon.level < MAX_LEVEL and pokemon.experience >= xp_to_next_level(pokemon.level):
        pokemon.level += 1
        pokemon._recalculate_stats()
        result["levels_gained"] += 1
        result["new_moves"].extend(_moves_learned_at(pokemon, pokemon.level))

    evolved_species = _check_evolution(pokemon)
    if evolved_species:
        result["evolved_into"] = evolved_species

    return result


def _moves_learned_at(pokemon, level: int) -> list[Move]:
    species = getattr(pokemon, "species", None)
    if not species:
        return []
    pokemon_data = pokeapi.get_pokemon(species)

    names = []
    for entry in pokemon_data["moves"]:
        for detail in entry["version_group_details"]:
            if detail["move_learn_method"]["name"] == "level-up" and detail["level_learned_at"] == level:
                names.append(entry["move"]["name"])
                break

    unique_names = list(dict.fromkeys(names))
    return roster._build_moves(unique_names) if unique_names else []


def learn_move(pokemon, move: Move, forget_index: Optional[int] = None) -> None:
    """Ensina `move` ao Pokémon. Se já tiver 4 golpes, `forget_index` diz
    qual esquecer (None = não aprende, igual escolher "Não" nos jogos)."""
    if len(pokemon.moves) < 4:
        pokemon.moves.append(move)
        return
    if forget_index is not None:
        pokemon.moves[forget_index] = move


def _check_evolution(pokemon) -> Optional[str]:
    species = getattr(pokemon, "species", None)
    if not species:
        return None
    try:
        species_data = pokeapi.get_species(species)
        chain = pokeapi.get_by_url(species_data["evolution_chain"]["url"])
    except Exception:
        return None
    return _find_next_evolution(chain["chain"], species, pokemon.level)


def _find_next_evolution(node: dict, current_species: str, level: int) -> Optional[str]:
    if node["species"]["name"] == current_species:
        for evolution in node["evolves_to"]:
            for detail in evolution["evolution_details"]:
                min_level = detail.get("min_level")
                if detail["trigger"]["name"] == "level-up" and min_level and level >= min_level:
                    return evolution["species"]["name"]
        return None
    for child in node["evolves_to"]:
        found = _find_next_evolution(child, current_species, level)
        if found:
            return found
    return None


def evolve_pokemon(pokemon, new_species: str) -> None:
    """Transforma `pokemon` na evolução: nível, XP, IVs, EVs, natureza e
    golpes continuam os mesmos, só stats-base, tipo e sprite mudam.
    """
    new_data = pokeapi.get_pokemon(new_species)
    types = [t["type"]["name"] for t in sorted(new_data["types"], key=lambda t: t["slot"])]
    base_stats = {
        roster._STAT_KEYS[s["stat"]["name"]]: s["base_stat"]
        for s in new_data["stats"]
        if s["stat"]["name"] in roster._STAT_KEYS
    }

    pokemon.name = roster.display_name(new_data["name"])
    pokemon.species = new_data["name"]
    pokemon.pokedex_id = new_data["id"]
    pokemon.types = types
    pokemon.base_stats = base_stats
    pokemon._recalculate_stats()
    pokemon.sprite_path = sprites.get_sprite_path(new_data)
    pokemon.ability = roster._pick_ability(new_data)
