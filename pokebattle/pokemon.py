"""Representa um Pokémon em batalha.

Os stats finais são calculados a partir do nível e dos base stats usando a
mesma fórmula dos jogos oficiais, assumindo IVs e EVs neutros (0) e sem
natureza — o que a comunidade costuma chamar de stats "base" de um Pokémon
naquele nível. Não é preciso reproduzir IV/EV/natureza pra esse projeto:
o que importa aqui é a lógica de nível x poder x tipo, não a otimização
competitiva de stats.
"""


def calc_hp(base: int, level: int) -> int:
    return (2 * base * level) // 100 + level + 10


def calc_stat(base: int, level: int) -> int:
    return (2 * base * level) // 100 + 5


class Pokemon:
    def __init__(self, name, types, level, base_stats, moves):
        self.name = name
        self.types = [t.lower() for t in types]
        self.level = level
        self.base_stats = dict(base_stats)
        self.moves = list(moves)

        self.max_hp = calc_hp(self.base_stats["hp"], level)
        self.current_hp = self.max_hp
        self.attack = calc_stat(self.base_stats["attack"], level)
        self.defense = calc_stat(self.base_stats["defense"], level)
        self.sp_atk = calc_stat(self.base_stats["sp_atk"], level)
        self.sp_def = calc_stat(self.base_stats["sp_def"], level)
        self.speed = calc_stat(self.base_stats["speed"], level)

    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    def take_damage(self, amount: int) -> None:
        self.current_hp = max(0, self.current_hp - amount)

    def __repr__(self):
        return f"<Pokemon {self.name} Lv.{self.level} HP {self.current_hp}/{self.max_hp}>"
