"""Exportar/importar um time como texto, num formato parecido com o do
Pokémon Showdown — dá pra compartilhar uma build sem mandar o savegame.json
inteiro. A parte de texto (formatar/interpretar) é pura e não toca rede; só
`build_from_spec`, que precisa buscar a espécie e os golpes na PokeAPI pra
montar um Pokemon de verdade, depende de `roster`.

`trade.py` (troca entre dois saves) reaproveita `pokemon_to_spec` e
`build_from_spec` daqui pro mesmo formato de "ficha" de um único Pokémon —
exportar/importar time e trocar um Pokémon são, na prática, a mesma
serialização aplicada a 1 ou a 6 Pokémon.
"""

import random
import re
from typing import Any

from . import roster

_STAT_ABBR = {"HP": "hp", "Atk": "attack", "Def": "defense", "SpA": "sp_atk", "SpD": "sp_def", "Spe": "speed"}
_STAT_ABBR_ORDER = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
_STAT_NAMES = list(_STAT_ABBR.values())


def pokemon_to_spec(pokemon) -> dict[str, Any]:
    """Serializa um Pokemon já montado numa "ficha" simples (dict só com
    tipos primitivos), pronta pra virar texto ou JSON."""
    species = getattr(pokemon, "species", None) or pokemon.name.lower().replace(" ", "-")
    nickname = pokemon.name if pokemon.name != roster.display_name(species) else None
    return {
        "species": species,
        "nickname": nickname,
        "level": pokemon.level,
        "ivs": dict(pokemon.ivs),
        "evs": dict(pokemon.evs),
        "nature": pokemon.nature,
        "held_item": getattr(pokemon, "held_item", None),
        "moves": [move.name for move in pokemon.moves],
    }


def _format_mon(spec: dict[str, Any]) -> str:
    species_display = roster.display_name(spec["species"])
    nickname = spec.get("nickname")
    header = f"{nickname} ({species_display})" if nickname and nickname != species_display else species_display
    if spec.get("held_item"):
        header += f" @ {spec['held_item']}"

    lines = [header, f"Level: {spec.get('level', roster.LEVEL)}", f"Nature: {spec.get('nature', 'Hardy')}"]

    ivs = spec.get("ivs") or {}
    iv_parts = [f"{ivs[stat]} {abbr}" for abbr, stat in _STAT_ABBR.items() if stat in ivs]
    if iv_parts:
        lines.append("IVs: " + " / ".join(iv_parts))

    evs = spec.get("evs") or {}
    ev_parts = [f"{evs[stat]} {abbr}" for abbr, stat in _STAT_ABBR.items() if evs.get(stat)]
    if ev_parts:
        lines.append("EVs: " + " / ".join(ev_parts))

    lines.extend(f"- {move}" for move in spec.get("moves") or [])
    return "\n".join(lines)


def team_to_text(team: list) -> str:
    return "\n\n".join(_format_mon(pokemon_to_spec(pokemon)) for pokemon in team)


def _slugify_species(text: str) -> str:
    return text.strip().lower().replace(" ", "-").replace("'", "").replace(".", "")


def _slugify_move(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("'", "")


def _parse_stat_line(text: str) -> dict[str, int]:
    result = {}
    for part in text.split("/"):
        part = part.strip()
        if not part:
            continue
        value_str, _, abbr = part.partition(" ")
        stat = _STAT_ABBR.get(abbr.strip())
        if stat and value_str.strip().lstrip("-").isdigit():
            result[stat] = int(value_str.strip())
    return result


def _parse_mon(block: str) -> dict[str, Any]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Bloco de Pokémon vazio no texto do time.")

    header = lines[0]
    name_part, _, item_part = header.partition(" @ ")
    name_part = name_part.strip()

    match = re.match(r"^(?P<nick>.*)\((?P<species>[^()]+)\)\s*$", name_part)
    if match:
        nickname = match.group("nick").strip() or None
        species = _slugify_species(match.group("species"))
    else:
        nickname = None
        species = _slugify_species(name_part)

    spec: dict[str, Any] = {
        "species": species,
        "nickname": nickname,
        "level": roster.LEVEL,
        "nature": "Hardy",
        "ivs": {stat: 31 for stat in _STAT_NAMES},
        "evs": {stat: 0 for stat in _STAT_NAMES},
        "held_item": item_part.strip() or None,
        "moves": [],
    }

    for line in lines[1:]:
        if line.startswith("-"):
            spec["moves"].append(line[1:].strip())
        elif line.lower().startswith("level:"):
            value = line.split(":", 1)[1].strip()
            if value.isdigit():
                spec["level"] = int(value)
        elif line.lower().startswith("nature:"):
            spec["nature"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("ivs:"):
            spec["ivs"].update(_parse_stat_line(line.split(":", 1)[1]))
        elif line.lower().startswith("evs:"):
            spec["evs"].update(_parse_stat_line(line.split(":", 1)[1]))
        # "Ability:" é só informativo no texto — a habilidade real vem da
        # espécie de verdade na PokeAPI quando o time é remontado.

    return spec


def text_to_specs(text: str) -> list[dict[str, Any]]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    return [_parse_mon(block) for block in blocks]


def build_from_spec(spec: dict[str, Any], rng=random):
    """Materializa uma ficha em um Pokemon de verdade — a única parte deste
    módulo que precisa da PokeAPI (via `roster`)."""
    pokemon = roster.build_pokemon(
        spec["species"], level=spec.get("level", roster.LEVEL), rng=rng,
        ivs=spec.get("ivs"), nature=spec.get("nature"),
    )
    if spec.get("nickname"):
        pokemon.name = spec["nickname"]
    if spec.get("evs"):
        for stat, value in spec["evs"].items():
            if stat in pokemon.evs:
                pokemon.evs[stat] = max(0, min(252, value))
        pokemon._recalculate_stats(full_heal=True)
    if spec.get("held_item"):
        pokemon.held_item = spec["held_item"]
    move_names = spec.get("moves") or []
    if move_names:
        pokemon.moves = [roster._build_move(_slugify_move(name)) for name in move_names]
    return pokemon


def build_team_from_text(text: str, rng=random) -> list:
    return [build_from_spec(spec, rng=rng) for spec in text_to_specs(text)]
