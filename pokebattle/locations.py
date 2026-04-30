"""Local de batalha: cada arena favorece um tipo de golpe, do mesmo jeito que
o clima já favorece (battle.py) — na prática, um "clima fixo" da arena, que
não expira com o passar dos turnos (diferente do clima normal, que dura 5
turnos e depois volta ao normal).

Vulcão favorece Fogo, lago favorece Água, caverna e deserto favorecem Pedra/
Terra/Aço (tempestade de areia), e uma geleira favorece Gelo (granizo). Nem
toda batalha acontece num desses lugares especiais — "campo aberto" é a
opção neutra, sem efeito nenhum, e continua sendo a mais comum.
"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    weather: Optional[str]  # None ou "sun"/"rain"/"sandstorm"/"hail", igual a battle.WEATHER_LABELS


CATALOG: list[Location] = [
    Location("open_field", "Campo Aberto", None),
    Location("volcano", "Vulcão", "sun"),
    Location("lake", "Lago", "rain"),
    Location("cave", "Caverna", "sandstorm"),
    Location("glacier", "Geleira", "hail"),
]

_BY_ID = {location.id: location for location in CATALOG}

# Peso maior pro campo aberto — a maioria das batalhas continua sem efeito de
# ambiente nenhum, e os locais especiais são a exceção (ginásio de tipo Fogo,
# torneio numa arena vulcânica etc.), não a regra.
_RANDOM_WEIGHTS = {"open_field": 4, "volcano": 1, "lake": 1, "cave": 1, "glacier": 1}


def get_location(location_id: str) -> Location:
    return _BY_ID[location_id]


def location_for_type(pokemon_type: str) -> Optional[Location]:
    """Arena "natural" pra um tipo, usada pra combinar ginásio com local
    (ex: ginásio de Fogo acontece no Vulcão). None se não tiver uma óbvia."""
    by_type = {
        "fire": "volcano", "water": "lake", "rock": "cave", "ground": "cave", "ice": "glacier",
    }
    location_id = by_type.get(pokemon_type)
    return _BY_ID[location_id] if location_id else None


def random_location(rng=random) -> Location:
    ids = list(_RANDOM_WEIGHTS.keys())
    weights = list(_RANDOM_WEIGHTS.values())
    return _BY_ID[rng.choices(ids, weights=weights, k=1)[0]]
