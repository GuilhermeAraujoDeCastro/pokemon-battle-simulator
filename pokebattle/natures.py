"""As 25 naturezas oficiais dos jogos. Cada uma sobe um stat em 10% e desce
outro em 10%; 5 delas ("neutras") não mudam nada. HP nunca é afetado por
natureza, nos jogos nem aqui.
"""

import random

# nome: (stat que sobe, stat que desce). None, None = natureza neutra.
NATURES = {
    "Hardy": (None, None),
    "Lonely": ("attack", "defense"),
    "Brave": ("attack", "speed"),
    "Adamant": ("attack", "sp_atk"),
    "Naughty": ("attack", "sp_def"),
    "Bold": ("defense", "attack"),
    "Docile": (None, None),
    "Relaxed": ("defense", "speed"),
    "Impish": ("defense", "sp_atk"),
    "Lax": ("defense", "sp_def"),
    "Timid": ("speed", "attack"),
    "Hasty": ("speed", "defense"),
    "Serious": (None, None),
    "Jolly": ("speed", "sp_atk"),
    "Naive": ("speed", "sp_def"),
    "Modest": ("sp_atk", "attack"),
    "Mild": ("sp_atk", "defense"),
    "Quiet": ("sp_atk", "speed"),
    "Bashful": (None, None),
    "Rash": ("sp_atk", "sp_def"),
    "Calm": ("sp_def", "attack"),
    "Gentle": ("sp_def", "defense"),
    "Sassy": ("sp_def", "speed"),
    "Careful": ("sp_def", "sp_atk"),
    "Quirky": (None, None),
}


def random_nature(rng=random) -> str:
    return rng.choice(list(NATURES.keys()))


def multiplier(nature: str, stat: str) -> float:
    """1.1 se a natureza sobe esse stat, 0.9 se desce, 1.0 nos outros casos."""
    boosted, lowered = NATURES[nature]
    if stat == boosted:
        return 1.1
    if stat == lowered:
        return 0.9
    return 1.0
