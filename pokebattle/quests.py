"""Sistema de missões: NPCs fixos, cada um com uma fala e um objetivo
simples (derrotar N treinadores, ver N espécies na Pokédex, ou vencer um
ginásio específico), com recompensa em dinheiro ao cumprir.

Fica de fora do main_gui.py de propósito — toda a lógica aqui só lê o dict
do save.py, então dá pra testar sem abrir nenhuma janela.
"""

from dataclasses import dataclass
from typing import Any, Union

GOAL_DEFEAT_TRAINERS = "defeat_trainers"
GOAL_SEE_POKEMON = "see_pokemon"
GOAL_WIN_GYM = "win_gym"


@dataclass(frozen=True)
class Quest:
    id: str
    npc_name: str
    dialogue: str  # fala do NPC ao apresentar a missão
    goal_type: str
    goal_target: Union[int, str]  # contagem (defeat_trainers/see_pokemon) ou id do ginásio (win_gym)
    reward_money: int


QUESTS: list[Quest] = [
    Quest(
        "first_wins", "Enfermeira Joy",
        "Bem-vindo(a) à sua jornada! Volte aqui depois de vencer 3 batalhas "
        "— quero ver do que você é capaz.",
        GOAL_DEFEAT_TRAINERS, 3, 500,
    ),
    Quest(
        "rock_badge", "Brock",
        "Antes de sair por aí se achando treinador, prove seu valor: vença "
        "minha Insígnia Rocha.",
        GOAL_WIN_GYM, "pewter", 300,
    ),
    Quest(
        "young_researcher", "Professor Carvalho",
        "Um bom treinador conhece muitos Pokémon. Registre 10 espécies "
        "diferentes na sua Pokédex.",
        GOAL_SEE_POKEMON, 10, 800,
    ),
    Quest(
        "veteran_trainer", "Treinador Ambicioso",
        "Já ouvi falar das suas vitórias por aí. Aposto que você ainda não "
        "chegou a 10 batalhas vencidas!",
        GOAL_DEFEAT_TRAINERS, 10, 1500,
    ),
    Quest(
        "pokedex_master", "Professor Carvalho",
        "Impressionante progresso! Mas a jornada de verdade é registrar 30 "
        "espécies na Pokédex.",
        GOAL_SEE_POKEMON, 30, 2000,
    ),
    Quest(
        "champion_challenge", "Giovanni",
        "Se você chegou até aqui, já deve imaginar: vença o meu ginásio e "
        "prove que é campeão.",
        GOAL_WIN_GYM, "viridian", 3000,
    ),
]

_BY_ID = {quest.id: quest for quest in QUESTS}


def get_quest(quest_id: str) -> Quest:
    return _BY_ID[quest_id]


def progress_for(quest: Quest, save_data: dict[str, Any]) -> int:
    """Progresso atual do jogador nessa missão. Pra "vencer ginásio X" isso
    vira 0 ou 1 (não tem meio-termo)."""
    if quest.goal_type == GOAL_DEFEAT_TRAINERS:
        return save_data.get("trainers_defeated", 0)
    if quest.goal_type == GOAL_SEE_POKEMON:
        return len(save_data.get("pokedex_seen", []))
    if quest.goal_type == GOAL_WIN_GYM:
        return 1 if quest.goal_target in save_data.get("badges", []) else 0
    return 0


def target_for(quest: Quest) -> int:
    """Alvo numérico da missão — pras de ginásio isso é sempre 1, pra
    mostrar "0/1" ou "1/1" do mesmo jeito que as de contagem."""
    return 1 if quest.goal_type == GOAL_WIN_GYM else quest.goal_target


def is_complete(quest: Quest, save_data: dict[str, Any]) -> bool:
    return progress_for(quest, save_data) >= target_for(quest)


def is_claimed(quest: Quest, save_data: dict[str, Any]) -> bool:
    return quest.id in save_data.get("quests_completed", [])


def is_claimable(quest: Quest, save_data: dict[str, Any]) -> bool:
    """Pronta pra resgatar: já foi cumprida e ainda não foi resgatada."""
    return is_complete(quest, save_data) and not is_claimed(quest, save_data)
