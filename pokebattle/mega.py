"""Mega evolução: curada a um punhado de espécies bem conhecidas — o mesmo
raciocínio de abilities.py (implementar as dezenas de formas mega da PokeAPI
de forma genérica não vale o esforço pra esse projeto).

Ativa quando o Pokémon segura a Mega Stone certa (um item segurado, ver
held_items.py) e é temporária: some no fim da batalha, do jeito que
acontece nos jogos. A transformação em si segue o mesmo molde de
progression.evolve_pokemon (troca tipo/base stats/sprite a partir de dados
já buscados na PokeAPI), mas guarda uma cópia de antes pra poder reverter.
"""

from typing import Any, Optional

from . import roster

# espécie base -> (id do item segurado que ativa, nome da forma mega na PokeAPI)
MEGA_FORMS: dict[str, tuple[str, str]] = {
    "charizard": ("held_mega_stone_charizardite_x", "charizard-mega-x"),
    "mewtwo": ("held_mega_stone_mewtwonite_x", "mewtwo-mega-x"),
    "gyarados": ("held_mega_stone_gyaradosite", "gyarados-mega"),
    "lucario": ("held_mega_stone_lucarionite", "lucario-mega"),
    "alakazam": ("held_mega_stone_alakazite", "alakazam-mega"),
}


def mega_stone_for(species: Optional[str]) -> Optional[str]:
    entry = MEGA_FORMS.get(species)
    return entry[0] if entry else None


def mega_species_for(species: Optional[str]) -> Optional[str]:
    entry = MEGA_FORMS.get(species)
    return entry[1] if entry else None


def can_mega_evolve(pokemon) -> Optional[str]:
    """Se esse Pokémon pode mega evoluir agora (espécie curada + segura a
    Mega Stone certa), devolve o nome da forma mega. Senão, None."""
    species = getattr(pokemon, "species", None)
    stone = mega_stone_for(species)
    if stone is None or getattr(pokemon, "held_item", None) != stone:
        return None
    if getattr(pokemon, "is_mega", False):
        return None  # já está mega evoluído
    return mega_species_for(species)


def apply_mega_form(pokemon, mega_data: dict[str, Any]) -> None:
    """Transforma `pokemon` na forma mega a partir dos dados já buscados na
    PokeAPI, guardando uma cópia do estado original pra revert_mega_form."""
    pokemon._mega_backup = {
        "species": pokemon.species,
        "pokedex_id": getattr(pokemon, "pokedex_id", None),
        "types": list(pokemon.types),
        "base_stats": dict(pokemon.base_stats),
        "sprite_path": getattr(pokemon, "sprite_path", None),
    }
    types = [t["type"]["name"] for t in sorted(mega_data["types"], key=lambda t: t["slot"])]
    base_stats = {
        roster._STAT_KEYS[s["stat"]["name"]]: s["base_stat"]
        for s in mega_data["stats"] if s["stat"]["name"] in roster._STAT_KEYS
    }
    pokemon.types = types
    pokemon.base_stats = base_stats
    pokemon._recalculate_stats()
    pokemon.is_mega = True


def revert_mega_form(pokemon) -> None:
    """Desfaz a mega evolução no fim da batalha — sem efeito se o Pokémon
    não estava mega evoluído."""
    backup = getattr(pokemon, "_mega_backup", None)
    if backup is None:
        return
    pokemon.species = backup["species"]
    pokemon.pokedex_id = backup["pokedex_id"]
    pokemon.types = backup["types"]
    pokemon.base_stats = backup["base_stats"]
    pokemon.sprite_path = backup["sprite_path"]
    pokemon._recalculate_stats()
    pokemon.is_mega = False
    del pokemon._mega_backup


def try_mega_evolve(pokemon) -> Optional[str]:
    """Busca a forma mega na PokeAPI (se aplicável) e aplica. Devolve a
    mensagem de log, ou None se esse Pokémon não pode mega evoluir agora."""
    mega_species = can_mega_evolve(pokemon)
    if mega_species is None:
        return None
    from . import pokeapi
    try:
        mega_data = pokeapi.get_pokemon(mega_species)
    except pokeapi.PokeApiError:
        return None
    apply_mega_form(pokemon, mega_data)
    return f"{pokemon.name} mega evoluiu!"
