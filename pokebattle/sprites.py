"""Baixa e cacheia localmente a imagem de um Pokémon.

Prioriza a "official artwork" da PokeAPI (a ilustração grande e bonita usada
nos jogos e no site oficial) em vez do sprite pixelado de 96x96, porque é a
diferença visual que dá pra perceber de verdade numa janela grande.
"""

from pathlib import Path
from typing import Any, Optional

import requests

SPRITE_CACHE_DIR = Path(__file__).resolve().parent.parent / ".pokecache" / "sprites"
TIMEOUT = 10


def best_sprite_url(pokemon_data: dict[str, Any], shiny: bool = False) -> Optional[str]:
    sprites = pokemon_data.get("sprites") or {}
    if shiny:
        shiny_artwork = sprites.get("other", {}).get("official-artwork", {}).get("front_shiny")
        return shiny_artwork or sprites.get("front_shiny") or best_sprite_url(pokemon_data, shiny=False)
    artwork = (
        sprites.get("other", {})
        .get("official-artwork", {})
        .get("front_default")
    )
    return artwork or sprites.get("front_default")


def get_sprite_path(pokemon_data: dict[str, Any], shiny: bool = False) -> Optional[Path]:
    """Devolve o caminho local da imagem do Pokémon, baixando se preciso.

    Devolve None se a PokeAPI não tiver nenhuma imagem pra esse Pokémon, ou
    se o download falhar (o chamador decide o que mostrar no lugar).
    `shiny=True` busca a variante rara (1/4096, ver roster.py), cacheada
    separada da normal.
    """
    url = best_sprite_url(pokemon_data, shiny=shiny)
    if not url:
        return None

    suffix = "_shiny" if shiny else ""
    local_path = SPRITE_CACHE_DIR / f"{pokemon_data['id']}{suffix}.png"
    if local_path.exists():
        return local_path

    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        return None

    SPRITE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(response.content)
    return local_path
