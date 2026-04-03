"""Representa um golpe (movimento) que um Pokémon pode usar em batalha."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    name: str
    type: str
    power: int
    category: str  # "physical" ou "special"
    accuracy: int = 100  # chance de acerto, em %

    def __post_init__(self):
        if self.category not in ("physical", "special"):
            raise ValueError(f"Categoria de golpe inválida: {self.category!r}")
        if not (0 <= self.accuracy <= 100):
            raise ValueError(f"Precisão fora do intervalo 0-100: {self.accuracy}")
