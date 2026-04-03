"""Roster do jogo: Pokémon (nível 50) com base stats e movesets reais dos
jogos, prontos pra batalha. Sem sprites nem imagens — o projeto é 100%
texto, então não usa nenhum asset visual da franquia.

Todo golpe listado aqui é um golpe de dano direto de verdade (nome, tipo,
poder e precisão reais), mas nenhum reproduz efeito secundário, status,
recuo, prioridade ou mecânica de dois turnos — o battle.py só sabe aplicar
dano na hora, então um golpe como Sludge Bomb aqui causa dano normalmente,
só sem a chance de envenenar. É a mesma simplificação que o projeto já
usava nos 6 Pokémon originais (por exemplo o Iron Tail do Pikachu, sem a
chance de baixar Defesa).
"""

from .moves import Move
from .pokemon import Pokemon

LEVEL = 50

_SPECIES = {
    "bulbasaur": {
        "types": ["grass", "poison"],
        "stats": {"hp": 45, "attack": 49, "defense": 49, "sp_atk": 65, "sp_def": 65, "speed": 45},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Vine Whip", "grass", 45, "physical"),
            Move("Razor Leaf", "grass", 55, "physical", accuracy=95),
            Move("Sludge", "poison", 65, "special", accuracy=100),
        ],
    },
    "charmander": {
        "types": ["fire"],
        "stats": {"hp": 39, "attack": 52, "defense": 43, "sp_atk": 60, "sp_def": 50, "speed": 65},
        "moves": [
            Move("Scratch", "normal", 40, "physical"),
            Move("Ember", "fire", 40, "special"),
            Move("Fire Fang", "fire", 65, "physical", accuracy=95),
            Move("Slash", "normal", 70, "physical", accuracy=100),
        ],
    },
    "squirtle": {
        "types": ["water"],
        "stats": {"hp": 44, "attack": 48, "defense": 65, "sp_atk": 50, "sp_def": 64, "speed": 43},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Water Gun", "water", 40, "special"),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Aqua Tail", "water", 90, "physical", accuracy=90),
        ],
    },
    "pikachu": {
        "types": ["electric"],
        "stats": {"hp": 35, "attack": 55, "defense": 40, "sp_atk": 50, "sp_def": 50, "speed": 90},
        "moves": [
            Move("Quick Attack", "normal", 40, "physical"),
            Move("Thunder Shock", "electric", 40, "special"),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
            Move("Iron Tail", "steel", 100, "physical", accuracy=75),
        ],
    },
    "machop": {
        "types": ["fighting"],
        "stats": {"hp": 70, "attack": 80, "defense": 50, "sp_atk": 35, "sp_def": 35, "speed": 35},
        "moves": [
            Move("Karate Chop", "fighting", 50, "physical"),
            Move("Low Kick", "fighting", 50, "physical"),
            Move("Cross Chop", "fighting", 100, "physical", accuracy=80),
            Move("Rock Tomb", "rock", 60, "physical", accuracy=95),
        ],
    },
    "gastly": {
        "types": ["ghost", "poison"],
        "stats": {"hp": 30, "attack": 35, "defense": 30, "sp_atk": 100, "sp_def": 35, "speed": 80},
        "moves": [
            Move("Lick", "ghost", 30, "physical", accuracy=100),
            Move("Shadow Ball", "ghost", 80, "special", accuracy=100),
            Move("Sludge Bomb", "poison", 90, "special", accuracy=100),
            Move("Psychic", "psychic", 90, "special", accuracy=100),
        ],
    },
    "venusaur": {
        "types": ["grass", "poison"],
        "stats": {"hp": 80, "attack": 82, "defense": 83, "sp_atk": 100, "sp_def": 100, "speed": 80},
        "moves": [
            Move("Vine Whip", "grass", 45, "physical"),
            Move("Razor Leaf", "grass", 55, "physical", accuracy=95),
            Move("Sludge Bomb", "poison", 90, "special", accuracy=100),
            Move("Giga Drain", "grass", 75, "special", accuracy=100),
        ],
    },
    "charizard": {
        "types": ["fire", "flying"],
        "stats": {"hp": 78, "attack": 84, "defense": 78, "sp_atk": 109, "sp_def": 85, "speed": 100},
        "moves": [
            Move("Wing Attack", "flying", 60, "physical"),
            Move("Fire Fang", "fire", 65, "physical", accuracy=95),
            Move("Flamethrower", "fire", 90, "special", accuracy=100),
            Move("Slash", "normal", 70, "physical", accuracy=100),
        ],
    },
    "blastoise": {
        "types": ["water"],
        "stats": {"hp": 79, "attack": 83, "defense": 100, "sp_atk": 85, "sp_def": 105, "speed": 78},
        "moves": [
            Move("Water Gun", "water", 40, "special"),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Aqua Tail", "water", 90, "physical", accuracy=90),
            Move("Hydro Pump", "water", 110, "special", accuracy=80),
        ],
    },
    "raichu": {
        "types": ["electric"],
        "stats": {"hp": 60, "attack": 90, "defense": 55, "sp_atk": 90, "sp_def": 80, "speed": 110},
        "moves": [
            Move("Quick Attack", "normal", 40, "physical"),
            Move("Thunder Shock", "electric", 40, "special"),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
            Move("Iron Tail", "steel", 100, "physical", accuracy=75),
        ],
    },
    "nidoking": {
        "types": ["poison", "ground"],
        "stats": {"hp": 81, "attack": 92, "defense": 77, "sp_atk": 85, "sp_def": 75, "speed": 85},
        "moves": [
            Move("Poison Jab", "poison", 80, "physical", accuracy=100),
            Move("Horn Attack", "normal", 65, "physical", accuracy=100),
            Move("Earthquake", "ground", 100, "physical", accuracy=100),
            Move("Megahorn", "bug", 120, "physical", accuracy=85),
        ],
    },
    "clefairy": {
        "types": ["fairy"],
        "stats": {"hp": 70, "attack": 45, "defense": 48, "sp_atk": 60, "sp_def": 65, "speed": 35},
        "moves": [
            Move("Pound", "normal", 40, "physical"),
            Move("Body Slam", "normal", 85, "physical", accuracy=100),
            Move("Moonblast", "fairy", 95, "special", accuracy=100),
            Move("Ice Punch", "ice", 75, "physical", accuracy=100),
        ],
    },
    "vulpix": {
        "types": ["fire"],
        "stats": {"hp": 38, "attack": 41, "defense": 40, "sp_atk": 50, "sp_def": 65, "speed": 65},
        "moves": [
            Move("Ember", "fire", 40, "special"),
            Move("Quick Attack", "normal", 40, "physical"),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Flamethrower", "fire", 90, "special", accuracy=100),
        ],
    },
    "jigglypuff": {
        "types": ["normal", "fairy"],
        "stats": {"hp": 115, "attack": 45, "defense": 20, "sp_atk": 45, "sp_def": 25, "speed": 20},
        "moves": [
            Move("Pound", "normal", 40, "physical"),
            Move("Body Slam", "normal", 85, "physical", accuracy=100),
            Move("Disarming Voice", "fairy", 40, "special"),
            Move("Dazzling Gleam", "fairy", 80, "special", accuracy=100),
        ],
    },
    "meowth": {
        "types": ["normal"],
        "stats": {"hp": 40, "attack": 45, "defense": 35, "sp_atk": 40, "sp_def": 40, "speed": 90},
        "moves": [
            Move("Scratch", "normal", 40, "physical"),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Slash", "normal", 70, "physical", accuracy=100),
            Move("Play Rough", "fairy", 90, "physical", accuracy=90),
        ],
    },
    "psyduck": {
        "types": ["water"],
        "stats": {"hp": 50, "attack": 52, "defense": 48, "sp_atk": 65, "sp_def": 50, "speed": 55},
        "moves": [
            Move("Water Gun", "water", 40, "special"),
            Move("Confusion", "psychic", 50, "special"),
            Move("Zen Headbutt", "psychic", 80, "physical", accuracy=90),
            Move("Aqua Tail", "water", 90, "physical", accuracy=90),
        ],
    },
    "growlithe": {
        "types": ["fire"],
        "stats": {"hp": 55, "attack": 70, "defense": 45, "sp_atk": 70, "sp_def": 50, "speed": 60},
        "moves": [
            Move("Ember", "fire", 40, "special"),
            Move("Flame Wheel", "fire", 60, "physical"),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Flamethrower", "fire", 90, "special", accuracy=100),
        ],
    },
    "poliwag": {
        "types": ["water"],
        "stats": {"hp": 40, "attack": 50, "defense": 40, "sp_atk": 40, "sp_def": 40, "speed": 90},
        "moves": [
            Move("Water Gun", "water", 40, "special"),
            Move("Mud Shot", "ground", 55, "special", accuracy=95),
            Move("Bubble Beam", "water", 65, "special"),
            Move("Body Slam", "normal", 85, "physical", accuracy=100),
        ],
    },
    "alakazam": {
        "types": ["psychic"],
        "stats": {"hp": 55, "attack": 50, "defense": 45, "sp_atk": 135, "sp_def": 95, "speed": 120},
        "moves": [
            Move("Confusion", "psychic", 50, "special"),
            Move("Psybeam", "psychic", 65, "special"),
            Move("Psychic", "psychic", 90, "special", accuracy=100),
            Move("Focus Blast", "fighting", 120, "special", accuracy=70),
        ],
    },
    "geodude": {
        "types": ["rock", "ground"],
        "stats": {"hp": 40, "attack": 80, "defense": 100, "sp_atk": 30, "sp_def": 30, "speed": 20},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Rock Throw", "rock", 50, "physical", accuracy=90),
            Move("Rock Slide", "rock", 75, "physical", accuracy=90),
            Move("Earthquake", "ground", 100, "physical", accuracy=100),
        ],
    },
    "magnemite": {
        "types": ["electric", "steel"],
        "stats": {"hp": 25, "attack": 35, "defense": 70, "sp_atk": 95, "sp_def": 55, "speed": 45},
        "moves": [
            Move("Thunder Shock", "electric", 40, "special"),
            Move("Tri Attack", "normal", 80, "special", accuracy=100),
            Move("Flash Cannon", "steel", 80, "special", accuracy=100),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
        ],
    },
    "farfetchd": {
        "types": ["normal", "flying"],
        "stats": {"hp": 52, "attack": 65, "defense": 55, "sp_atk": 58, "sp_def": 62, "speed": 60},
        "moves": [
            Move("Peck", "flying", 35, "physical"),
            Move("Aerial Ace", "flying", 60, "physical", accuracy=100),
            Move("Slash", "normal", 70, "physical", accuracy=100),
            Move("Air Slash", "flying", 75, "special", accuracy=95),
        ],
    },
    "slowpoke": {
        "types": ["water", "psychic"],
        "stats": {"hp": 90, "attack": 65, "defense": 65, "sp_atk": 40, "sp_def": 40, "speed": 15},
        "moves": [
            Move("Water Gun", "water", 40, "special"),
            Move("Confusion", "psychic", 50, "special"),
            Move("Zen Headbutt", "psychic", 80, "physical", accuracy=90),
            Move("Psychic", "psychic", 90, "special", accuracy=100),
        ],
    },
    "onix": {
        "types": ["rock", "ground"],
        "stats": {"hp": 35, "attack": 45, "defense": 160, "sp_atk": 30, "sp_def": 45, "speed": 70},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Rock Throw", "rock", 50, "physical", accuracy=90),
            Move("Rock Slide", "rock", 75, "physical", accuracy=90),
            Move("Earthquake", "ground", 100, "physical", accuracy=100),
        ],
    },
    "voltorb": {
        "types": ["electric"],
        "stats": {"hp": 40, "attack": 30, "defense": 50, "sp_atk": 55, "sp_def": 55, "speed": 100},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Charge Beam", "electric", 50, "special", accuracy=90),
            Move("Thunder Shock", "electric", 40, "special"),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
        ],
    },
    "cubone": {
        "types": ["ground"],
        "stats": {"hp": 50, "attack": 50, "defense": 95, "sp_atk": 40, "sp_def": 50, "speed": 35},
        "moves": [
            Move("Bone Club", "ground", 65, "physical", accuracy=85),
            Move("Mud Shot", "ground", 55, "special", accuracy=95),
            Move("Headbutt", "normal", 70, "physical", accuracy=100),
            Move("Earthquake", "ground", 100, "physical", accuracy=100),
        ],
    },
    "scyther": {
        "types": ["bug", "flying"],
        "stats": {"hp": 70, "attack": 110, "defense": 80, "sp_atk": 55, "sp_def": 80, "speed": 105},
        "moves": [
            Move("Quick Attack", "normal", 40, "physical"),
            Move("Wing Attack", "flying", 60, "physical"),
            Move("Slash", "normal", 70, "physical", accuracy=100),
            Move("X-Scissor", "bug", 80, "physical", accuracy=100),
        ],
    },
    "electabuzz": {
        "types": ["electric"],
        "stats": {"hp": 65, "attack": 83, "defense": 57, "sp_atk": 95, "sp_def": 85, "speed": 105},
        "moves": [
            Move("Thunder Shock", "electric", 40, "special"),
            Move("Thunder Punch", "electric", 75, "physical", accuracy=100),
            Move("Cross Chop", "fighting", 100, "physical", accuracy=80),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
        ],
    },
    "magmar": {
        "types": ["fire"],
        "stats": {"hp": 65, "attack": 95, "defense": 57, "sp_atk": 100, "sp_def": 85, "speed": 93},
        "moves": [
            Move("Ember", "fire", 40, "special"),
            Move("Fire Punch", "fire", 75, "physical", accuracy=100),
            Move("Cross Chop", "fighting", 100, "physical", accuracy=80),
            Move("Flamethrower", "fire", 90, "special", accuracy=100),
        ],
    },
    "dratini": {
        "types": ["dragon"],
        "stats": {"hp": 41, "attack": 64, "defense": 45, "sp_atk": 50, "sp_def": 50, "speed": 50},
        "moves": [
            Move("Twister", "dragon", 40, "special"),
            Move("Aqua Tail", "water", 90, "physical", accuracy=90),
            Move("Iron Tail", "steel", 100, "physical", accuracy=75),
            Move("Dragon Rush", "dragon", 100, "physical", accuracy=75),
        ],
    },
    "dragonite": {
        "types": ["dragon", "flying"],
        "stats": {"hp": 91, "attack": 134, "defense": 95, "sp_atk": 100, "sp_def": 100, "speed": 80},
        "moves": [
            Move("Aqua Tail", "water", 90, "physical", accuracy=90),
            Move("Iron Tail", "steel", 100, "physical", accuracy=75),
            Move("Dragon Rush", "dragon", 100, "physical", accuracy=75),
            Move("Hurricane", "flying", 110, "special", accuracy=70),
        ],
    },
    "lapras": {
        "types": ["water", "ice"],
        "stats": {"hp": 130, "attack": 85, "defense": 80, "sp_atk": 85, "sp_def": 95, "speed": 60},
        "moves": [
            Move("Body Slam", "normal", 85, "physical", accuracy=100),
            Move("Surf", "water", 90, "special", accuracy=100),
            Move("Ice Beam", "ice", 90, "special", accuracy=100),
            Move("Hydro Pump", "water", 110, "special", accuracy=80),
        ],
    },
    "eevee": {
        "types": ["normal"],
        "stats": {"hp": 55, "attack": 55, "defense": 50, "sp_atk": 45, "sp_def": 65, "speed": 55},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Quick Attack", "normal", 40, "physical"),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Body Slam", "normal", 85, "physical", accuracy=100),
        ],
    },
    "vaporeon": {
        "types": ["water"],
        "stats": {"hp": 130, "attack": 65, "defense": 60, "sp_atk": 110, "sp_def": 95, "speed": 65},
        "moves": [
            Move("Water Gun", "water", 40, "special"),
            Move("Aqua Tail", "water", 90, "physical", accuracy=90),
            Move("Ice Beam", "ice", 90, "special", accuracy=100),
            Move("Hydro Pump", "water", 110, "special", accuracy=80),
        ],
    },
    "jolteon": {
        "types": ["electric"],
        "stats": {"hp": 65, "attack": 65, "defense": 60, "sp_atk": 110, "sp_def": 95, "speed": 130},
        "moves": [
            Move("Quick Attack", "normal", 40, "physical"),
            Move("Thunder Shock", "electric", 40, "special"),
            Move("Shadow Ball", "ghost", 80, "special", accuracy=100),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
        ],
    },
    "flareon": {
        "types": ["fire"],
        "stats": {"hp": 65, "attack": 130, "defense": 60, "sp_atk": 95, "sp_def": 110, "speed": 65},
        "moves": [
            Move("Ember", "fire", 40, "special"),
            Move("Fire Fang", "fire", 65, "physical", accuracy=95),
            Move("Bite", "dark", 60, "physical", accuracy=100),
            Move("Flamethrower", "fire", 90, "special", accuracy=100),
        ],
    },
    "snorlax": {
        "types": ["normal"],
        "stats": {"hp": 160, "attack": 110, "defense": 65, "sp_atk": 65, "sp_def": 110, "speed": 30},
        "moves": [
            Move("Tackle", "normal", 40, "physical"),
            Move("Body Slam", "normal", 85, "physical", accuracy=100),
            Move("Crunch", "dark", 80, "physical", accuracy=100),
            Move("Earthquake", "ground", 100, "physical", accuracy=100),
        ],
    },
    "articuno": {
        "types": ["ice", "flying"],
        "stats": {"hp": 90, "attack": 85, "defense": 100, "sp_atk": 95, "sp_def": 125, "speed": 85},
        "moves": [
            Move("Ancient Power", "rock", 60, "special"),
            Move("Aerial Ace", "flying", 60, "physical", accuracy=100),
            Move("Ice Beam", "ice", 90, "special", accuracy=100),
            Move("Hurricane", "flying", 110, "special", accuracy=70),
        ],
    },
    "zapdos": {
        "types": ["electric", "flying"],
        "stats": {"hp": 90, "attack": 90, "defense": 85, "sp_atk": 125, "sp_def": 90, "speed": 100},
        "moves": [
            Move("Ancient Power", "rock", 60, "special"),
            Move("Drill Peck", "flying", 80, "physical", accuracy=100),
            Move("Thunderbolt", "electric", 90, "special", accuracy=100),
            Move("Hurricane", "flying", 110, "special", accuracy=70),
        ],
    },
    "moltres": {
        "types": ["fire", "flying"],
        "stats": {"hp": 90, "attack": 100, "defense": 90, "sp_atk": 125, "sp_def": 85, "speed": 90},
        "moves": [
            Move("Ancient Power", "rock", 60, "special"),
            Move("Air Slash", "flying", 75, "special", accuracy=95),
            Move("Flamethrower", "fire", 90, "special", accuracy=100),
            Move("Fire Blast", "fire", 110, "special", accuracy=85),
        ],
    },
    "mewtwo": {
        "types": ["psychic"],
        "stats": {"hp": 106, "attack": 110, "defense": 90, "sp_atk": 154, "sp_def": 90, "speed": 130},
        "moves": [
            Move("Confusion", "psychic", 50, "special"),
            Move("Shadow Ball", "ghost", 80, "special", accuracy=100),
            Move("Psychic", "psychic", 90, "special", accuracy=100),
            Move("Focus Blast", "fighting", 120, "special", accuracy=70),
        ],
    },
}

# Nomes que "capitalize()" sozinho não acerta (por causa de apóstrofo,
# hífen etc.). Tudo que não está aqui usa capitalize() normal.
_DISPLAY_OVERRIDES = {
    "farfetchd": "Farfetch'd",
}


def list_species() -> list[str]:
    return list(_SPECIES.keys())


def display_name(species: str) -> str:
    """Nome de exibição de uma espécie (ex: 'farfetchd' -> "Farfetch'd")."""
    key = species.lower()
    return _DISPLAY_OVERRIDES.get(key, species.capitalize())


def list_species_starting_with(letter: str) -> list[str]:
    """Espécies (na ordem do roster) cujo nome começa com essa letra.

    Ignora maiúscula/minúscula. Uma letra vazia (ou só espaços) devolve o
    roster inteiro, pra dar pra usar a mesma função tanto pro caso "digitou
    uma letra" quanto pro caso "não digitou nada, quero ver tudo".
    """
    letter = letter.strip().lower()
    if not letter:
        return list_species()
    return [s for s in list_species() if s.lower().startswith(letter)]


def create_pokemon(species: str, level: int = LEVEL) -> Pokemon:
    key = species.lower()
    if key not in _SPECIES:
        raise ValueError(f"Pokémon desconhecido: {species}")
    data = _SPECIES[key]
    return Pokemon(display_name(key), data["types"], level, data["stats"], list(data["moves"]))
