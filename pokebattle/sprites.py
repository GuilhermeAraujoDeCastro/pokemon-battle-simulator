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


def best_sprite_url(pokemon_data: dict[str, Any]) -> Optional[str]:
    sprites = pokemon_data.get("sprites") or {}
    artwork = (
        sprites.get("other", {})
        .get("official-artwork", {})
        .get("front_default")
    )
    return artwork or sprites.get("front_default")


def get_sprite_path(pokemon_data: dict[str, Any]) -> Optional[Path]:
    """Devolve o caminho local da imagem do Pokémon, baixando se preciso.

    Devolve None se a PokeAPI não tiver nenhuma imagem pra esse Pokémon, ou
    se o download falhar (o chamador decide o que mostrar no lugar).
    """
    url = best_sprite_url(pokemon_data)
    if not url:
        return None

    local_path = SPRITE_CACHE_DIR / f"{pokemon_data['id']}.png"
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
