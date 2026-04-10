"""Representa um golpe (movimento) que um Pokémon pode usar em batalha."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Move:
    name: str
    type: str
    power: int
    category: str  # "physical", "special" ou "status"
    accuracy: int = 100  # chance de acerto, em %

    # Efeito de status secundário (ex: Thunderbolt tem 10% de chance de
    # paralisar). None = golpe sem efeito de status nenhum.
    ailment: Optional[str] = None
    ailment_chance: int = 100  # chance (%) de aplicar o ailment quando acerta

    priority: int = 0  # golpes de prioridade alta agem antes, mesmo mais lentos
    drain: int = 0  # % do dano causado devolvido a quem atacou; negativo = recuo

    # Golpes de status que sobem/descem estágio de stat (Growl, Swords Dance).
    stat_changes: tuple = ()  # ((nome_do_stat, delta), ...)
    stat_change_target: str = "target"  # "self" (o próprio usuário) ou "target"

    weather: Optional[str] = None  # clima que esse golpe estabelece ("sun"/"rain"/"sandstorm"/"hail")
    is_charge_move: bool = False  # golpe de 2 turnos: carrega, depois bate (ex: Solar Beam)

    def __post_init__(self):
        if self.category not in ("physical", "special", "status"):
            raise ValueError(f"Categoria de golpe inválida: {self.category!r}")
        if not (0 <= self.accuracy <= 100):
            raise ValueError(f"Precisão fora do intervalo 0-100: {self.accuracy}")
        if not (0 <= self.ailment_chance <= 100):
            raise ValueError(f"Chance de status fora do intervalo 0-100: {self.ailment_chance}")
        if not (-100 <= self.drain <= 100):
            raise ValueError(f"Dreno/recuo fora do intervalo -100 a 100: {self.drain}")
        if self.stat_change_target not in ("self", "target"):
            raise ValueError(f"Alvo de mudança de stat inválido: {self.stat_change_target!r}")
