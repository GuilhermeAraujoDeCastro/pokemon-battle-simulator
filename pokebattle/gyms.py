"""Ginásios: sequência fixa de líderes com times reais (mesma essência dos
jogos originais, região de Kanto), nos mesmos moldes de nível/recompensa.

O progresso (quais insígnias já foram conquistadas) vive em pokebattle/save.py.
Os ginásios são sempre enfrentados na ordem da lista — só o próximo ainda não
vencido fica disponível pra desafiar.
"""

import random
from dataclasses import dataclass

from . import roster


@dataclass
class GymTrainer:
    species: str
    level: int


@dataclass
class Gym:
    id: str
    city: str
    leader: str
    gym_type: str
    team: list[GymTrainer]
    badge_name: str
    reward_money: int
    personality: str = "aggressive"  # como a IA do líder escolhe golpe — ver pokebattle/ai.py


GYMS: list[Gym] = [
    Gym("pewter", "Pewter City", "Brock", "rock",
        [GymTrainer("geodude", 12), GymTrainer("onix", 14)],
        "Insígnia Rocha", 1400, personality="defensive"),
    Gym("cerulean", "Cerulean City", "Misty", "water",
        [GymTrainer("staryu", 18), GymTrainer("starmie", 21)],
        "Insígnia Cascata", 2100, personality="strategic"),
    Gym("vermilion", "Vermilion City", "Lt. Surge", "electric",
        [GymTrainer("voltorb", 21), GymTrainer("pikachu", 18), GymTrainer("raichu", 24)],
        "Insígnia Trovão", 2400, personality="aggressive"),
    Gym("celadon", "Celadon City", "Erika", "grass",
        [GymTrainer("victreebel", 29), GymTrainer("tangela", 24), GymTrainer("vileplume", 29)],
        "Insígnia Arco-íris", 2900, personality="defensive"),
    Gym("fuchsia", "Fuchsia City", "Koga", "poison",
        [GymTrainer("koffing", 37), GymTrainer("muk", 39), GymTrainer("koffing", 37), GymTrainer("weezing", 43)],
        "Insígnia Alma", 4300, personality="strategic"),
    Gym("saffron", "Saffron City", "Sabrina", "psychic",
        [GymTrainer("kadabra", 38), GymTrainer("mr-mime", 37), GymTrainer("venomoth", 38), GymTrainer("alakazam", 43)],
        "Insígnia Pântano", 4300, personality="strategic"),
    Gym("cinnabar", "Cinnabar Island", "Blaine", "fire",
        [GymTrainer("growlithe", 42), GymTrainer("ponyta", 40), GymTrainer("rapidash", 42), GymTrainer("arcanine", 47)],
        "Insígnia Vulcão", 4700, personality="aggressive"),
    Gym("viridian", "Viridian City", "Giovanni", "ground",
        [GymTrainer("rhyhorn", 45), GymTrainer("dugtrio", 42), GymTrainer("nidoqueen", 44),
         GymTrainer("nidoking", 45), GymTrainer("rhydon", 50)],
        "Insígnia Terra", 5000, personality="aggressive"),
]

_GYMS_BY_ID = {gym.id: gym for gym in GYMS}


def get_gym(gym_id: str) -> Gym:
    return _GYMS_BY_ID[gym_id]


def next_gym(badges: list[str]):
    """Primeiro ginásio da sequência que ainda não foi vencido, ou None se
    todos já caíram."""
    for gym in GYMS:
        if gym.id not in badges:
            return gym
    return None


def build_gym_team(gym: Gym, rng=random):
    """Monta o time do ginásio com pokebattle.roster.build_pokemon, cada
    integrante no nível fixado pra esse ginásio (não no LEVEL padrão)."""
    return [roster.build_pokemon(trainer.species, level=trainer.level, rng=rng) for trainer in gym.team]
