"""Replay de batalha: grava o log de ações turno a turno num JSON e lê de
volta, pra uma tela reproduzir a luta depois. Fica de fora de battle.py de
propósito — a gravação é responsabilidade de quem chama take_turn()
(main_gui.py), não da lógica de batalha em si, que continua sem saber que
está sendo observada.

Cada turno gravado guarda só dados simples (nome, nível, espécie, HP, status
— nunca o objeto Pokemon inteiro), pra ser 100% serializável em JSON e pra
não prender referência viva a nada da batalha original.
"""

import json
from pathlib import Path
from typing import Any, Optional

REPLAY_DIR = Path(__file__).resolve().parent.parent / "replays"


def snapshot(pokemon) -> dict[str, Any]:
    """Retrato de um Pokémon num instante da batalha — só o que a tela de
    replay precisa pra desenhar, sem nenhuma referência ao objeto real."""
    return {
        "name": pokemon.name,
        "species": getattr(pokemon, "species", None),
        "level": pokemon.level,
        "current_hp": pokemon.current_hp,
        "max_hp": pokemon.max_hp,
        "status": pokemon.status,
    }


def record_turn(turn_number: int, description: str, log_lines: list[str],
                 player_snapshot: dict, enemy_snapshot: dict) -> dict[str, Any]:
    return {
        "turn": turn_number,
        "description": description,
        "log": list(log_lines),
        "player": player_snapshot,
        "enemy": enemy_snapshot,
    }


def save_replay(path, metadata: dict[str, Any], turns: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "turns": turns}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_replay(path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_replays(directory: Optional[Path] = None) -> list[Path]:
    """Replays salvos, do mais recente pro mais antigo."""
    directory = Path(directory) if directory is not None else REPLAY_DIR
    if not directory.exists():
        return []
    files = list(directory.glob("*.json"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
