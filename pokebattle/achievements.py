"""Sistema de conquistas: catálogo fixo, checado contra o dict do save.py
(mesmo molde de quests.py), mais um "contexto" pontual pra marcos que não dá
pra calcular só olhando o save (ex: "venceu sem perder ninguém" — isso quem
sabe é a BattleScreen, no momento em que a batalha termina).

Diferente de missões (quests.py), conquistas não têm botão de "reivindicar":
desbloqueiam sozinhas assim que a condição bate, e quem chama newly_unlocked
persiste o resultado no save.py.
"""

from dataclasses import dataclass
from typing import Any, Optional, Union

GOAL_POKEDEX_SEEN = "pokedex_seen_at_least"
GOAL_BADGES = "badges_at_least"
GOAL_WINS = "trainers_defeated_at_least"
GOAL_FLAG = "flag"  # goal_target é uma chave booleana dentro do "context"


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    goal_type: str
    goal_target: Union[int, str]


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first_win", "Primeira Vitória", "Vença sua primeira batalha.", GOAL_WINS, 1),
    Achievement("veteran", "Veterano", "Vença 25 batalhas.", GOAL_WINS, 25),
    Achievement("flawless_victory", "Vitória Impecável", "Vença uma batalha sem perder nenhum Pokémon.",
                GOAL_FLAG, "no_faint_win"),
    Achievement("shiny_hunter", "Caçador de Shiny", "Encontre seu primeiro Pokémon shiny.",
                GOAL_FLAG, "found_shiny"),
    Achievement("young_researcher", "Jovem Pesquisador", "Registre 10 espécies na Pokédex.", GOAL_POKEDEX_SEEN, 10),
    Achievement("pokedex_master", "Mestre da Pokédex", "Registre 50 espécies na Pokédex.", GOAL_POKEDEX_SEEN, 50),
    Achievement("champion", "Campeão", "Vença os 8 ginásios.", GOAL_BADGES, 8),
    Achievement("mega_trainer", "Treinador Mega", "Mega evolua um Pokémon numa batalha.",
                GOAL_FLAG, "mega_evolved"),
    Achievement("tournament_champion", "Campeão de Torneio", "Vença um torneio inteiro.",
                GOAL_FLAG, "tournament_champion"),
    Achievement("nuzlocke_survivor", "Sobrevivente Nuzlocke", "Vença uma batalha no modo Nuzlocke.",
                GOAL_FLAG, "nuzlocke_win"),
]

def is_unlocked(achievement: Achievement, save_data: dict[str, Any]) -> bool:
    return achievement.id in save_data.get("achievements_unlocked", [])


def is_satisfied(achievement: Achievement, save_data: dict[str, Any], context: Optional[dict] = None) -> bool:
    context = context or {}
    if achievement.goal_type == GOAL_POKEDEX_SEEN:
        return len(save_data.get("pokedex_seen", [])) >= achievement.goal_target
    if achievement.goal_type == GOAL_BADGES:
        return len(save_data.get("badges", [])) >= achievement.goal_target
    if achievement.goal_type == GOAL_WINS:
        return save_data.get("trainers_defeated", 0) >= achievement.goal_target
    if achievement.goal_type == GOAL_FLAG:
        return bool(context.get(achievement.goal_target))
    return False


def newly_unlocked(save_data: dict[str, Any], context: Optional[dict] = None) -> list[Achievement]:
    """Conquistas que acabaram de ser satisfeitas mas ainda não estão salvas
    como desbloqueadas. Quem chama decide o que fazer (persistir + avisar o
    jogador)."""
    return [
        achievement for achievement in ACHIEVEMENTS
        if not is_unlocked(achievement, save_data) and is_satisfied(achievement, save_data, context)
    ]
