"""Funções de apresentação usadas pelo main.py: barra de HP em ASCII e banners."""


def render_hp_bar(current: int, max_hp: int, width: int = 20) -> str:
    ratio = 0.0 if max_hp <= 0 else max(0.0, min(1.0, current / max_hp))
    filled = round(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{max_hp} HP"


def print_banner(text: str) -> None:
    line = "=" * (len(text) + 4)
    print(line)
    print(f"  {text}")
    print(line)
