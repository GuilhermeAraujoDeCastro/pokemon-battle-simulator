"""Cliente simples da PokeAPI (https://pokeapi.co), com cache em disco.

Cada resposta é salva como um .json dentro de CACHE_DIR (nomeado pelo hash da
URL), então jogar de novo não repete nenhuma chamada de rede pra um Pokémon
ou golpe que já foi usado antes — só a primeira vez que cada um aparece
precisa de internet.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://pokeapi.co/api/v2"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".pokecache"
TIMEOUT = 10

# Sessão compartilhada (mantém a conexão HTTP viva entre chamadas) — como o
# roster.py busca vários golpes em paralelo, isso evita reabrir uma conexão
# nova TCP/TLS a cada requisição.
_session = requests.Session()


class PokeApiError(Exception):
    """Erro ao falar com a PokeAPI (rede fora do ar, Pokémon inexistente etc.)."""


def _cache_path(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _get(url: str) -> dict[str, Any]:
    cache_file = _cache_path(url)
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    try:
        response = _session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PokeApiError(
            f"Não consegui acessar a PokeAPI ({url}). Verifique sua internet.\nDetalhe: {exc}"
        ) from exc

    data = response.json()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return data


def list_all_species_names() -> list[str]:
    """Nomes de todos os Pokémon (e formas) conhecidos pela PokeAPI."""
    data = _get(f"{BASE_URL}/pokemon?limit=100000&offset=0")
    return [entry["name"] for entry in data["results"]]


def list_all_species_with_dex_numbers() -> list[tuple[int, str]]:
    """Igual a list_all_species_names, mas com o número da Pokédex de cada
    um — extraído da própria URL da lista, sem precisar de mais uma chamada
    de rede por Pokémon. Mesma URL que list_all_species_names, então usa o
    mesmo arquivo de cache."""
    data = _get(f"{BASE_URL}/pokemon?limit=100000&offset=0")
    result = []
    for entry in data["results"]:
        try:
            dex_id = int(entry["url"].rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            dex_id = 0
        result.append((dex_id, entry["name"]))
    return result


def get_pokemon(name_or_id) -> dict[str, Any]:
    key = str(name_or_id).lower().strip()
    return _get(f"{BASE_URL}/pokemon/{key}")


def get_move(name: str) -> dict[str, Any]:
    key = name.lower().strip()
    return _get(f"{BASE_URL}/move/{key}")


def get_species(name_or_id) -> dict[str, Any]:
    """Dados de "espécie" (separados de /pokemon): é aqui que mora o link
    pra cadeia de evolução."""
    key = str(name_or_id).lower().strip()
    return _get(f"{BASE_URL}/pokemon-species/{key}")


def get_ability(name: str) -> dict[str, Any]:
    key = name.lower().strip()
    return _get(f"{BASE_URL}/ability/{key}")


def get_by_url(url: str) -> dict[str, Any]:
    """Busca um recurso pela URL completa que outra resposta da API já deu
    (ex: species["evolution_chain"]["url"]) — evita remontar o endpoint."""
    return _get(url)
