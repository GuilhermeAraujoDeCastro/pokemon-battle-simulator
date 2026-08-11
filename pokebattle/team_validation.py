"""Contrato compartilhado pela importação de texto e pelos slots locais."""
import re
from .natures import NATURES

STATS = ("hp", "attack", "defense", "sp_atk", "sp_def", "speed")


def validate_spec(spec, field="pokemon"):
    errors = []
    if not isinstance(spec, dict):
        raise ValueError(f"{field}: esperado objeto de Pokémon.")
    if not isinstance(spec.get("species"), str) or not re.fullmatch(r"[a-z0-9-]{1,80}", spec["species"]):
        errors.append(f"{field}.species: espécie inválida")
    level = spec.get("level", 50)
    if type(level) is not int or not 1 <= level <= 100:
        errors.append(f"{field}.level: informe inteiro de 1 a 100")
    for kind, maximum in [("ivs",31), ("evs",252)]:
        values = spec.get(kind, {})
        if not isinstance(values, dict):
            errors.append(f"{field}.{kind}: esperado objeto de atributos")
            continue
        for stat, value in values.items():
            if stat not in STATS or type(value) is not int or not 0 <= value <= maximum:
                errors.append(f"{field}.{kind}.{stat}: informe inteiro de 0 a {maximum}")
        if kind == "evs" and all(type(v) is int for v in values.values()) and sum(values.values()) > 510:
            errors.append(f"{field}.evs: soma máxima de 510")
    moves = spec.get("moves", [])
    if not isinstance(moves, list) or len(moves) > 4 or any(not isinstance(m,str) or not m.strip() or len(m)>80 for m in moves):
        errors.append(f"{field}.moves: até quatro nomes de golpes válidos")
    if not isinstance(spec.get("nature", "Hardy"),str) or spec.get("nature", "Hardy") not in NATURES:
        errors.append(f"{field}.nature: natureza desconhecida")
    nickname = spec.get("nickname")
    if nickname is not None and (not isinstance(nickname,str) or len(nickname)>50):
        errors.append(f"{field}.nickname: máximo de 50 caracteres")
    if errors:
        raise ValueError("; ".join(errors))
    return spec


def validate_team(specs):
    if not isinstance(specs,list) or not 1 <= len(specs) <= 6:
        raise ValueError("team: informe de um a seis Pokémon.")
    errors = []
    for index, spec in enumerate(specs):
        try:
            validate_spec(spec, f"team[{index+1}]")
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError("\n".join(errors))
    return specs
