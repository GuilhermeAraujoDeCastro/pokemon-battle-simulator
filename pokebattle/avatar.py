"""Avatar do treinador no modo gráfico: nada de sprite de terceiro, só um
círculo colorido com a inicial do nome (já coletado no onboarding) — a
mesma decisão de design de main_gui.py hoje (sem asset visual de fora da
PokeAPI). A cor é escolhida uma vez, junto do nome/inicial, e fica salva.

Fica separado de main_gui.py de propósito: essa função é só "qual cor e qual
letra", pura e testável; quem desenha o círculo no Canvas é o modo gráfico.
"""

from typing import Optional

PALETTE = {
    "red": "#e34b4b",
    "blue": "#4b7be3",
    "green": "#59c135",
    "yellow": "#ffcb05",
    "purple": "#a45ee5",
}

DEFAULT_COLOR = "red"


def initial_for(trainer_name: str) -> str:
    name = (trainer_name or "").strip()
    return name[0].upper() if name else "?"


def color_hex(color_id: Optional[str]) -> str:
    return PALETTE.get(color_id, PALETTE[DEFAULT_COLOR])


def avatar_spec(trainer_name: str, color_id: Optional[str]) -> dict:
    """Tudo que o Canvas precisa pra desenhar o avatar: a letra e a cor."""
    return {
        "initial": initial_for(trainer_name),
        "color": color_hex(color_id),
        "color_id": color_id if color_id in PALETTE else DEFAULT_COLOR,
    }
