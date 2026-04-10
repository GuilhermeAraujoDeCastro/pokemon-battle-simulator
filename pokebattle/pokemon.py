"""Representa um Pokémon em batalha.

Os stats finais usam a fórmula completa dos jogos oficiais: nível, base
stat, IV (0-31, "talento" individual) e EV (pontos ganhos batalhando), mais
o multiplicador de 10% pra cima/pra baixo da natureza. Quem não passar
ivs/evs/nature na criação (o roster fixo do modo texto, os testes) ganha
IV 0, EV 0 e natureza neutra — exatamente os números "base" de antes, sem
mudar nenhum resultado já testado.
"""

from typing import Optional

from .natures import multiplier as nature_multiplier
from .status import BURN, PARALYSIS

_STAT_NAMES = ("hp", "attack", "defense", "sp_atk", "sp_def", "speed")
_STAGE_STAT_NAMES = ("attack", "defense", "sp_atk", "sp_def", "speed")
_NEUTRAL_NATURE = "Hardy"


def stage_multiplier(stage: int) -> float:
    """Fórmula oficial de estágio de stat (-6 a +6): Intimidate e afins
    mexem nisso, não no stat base."""
    stage = max(-6, min(6, stage))
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def calc_hp(base: int, level: int, iv: int = 0, ev: int = 0) -> int:
    return (2 * base + iv + ev // 4) * level // 100 + level + 10


def calc_stat(base: int, level: int, iv: int = 0, ev: int = 0,
              nature: Optional[str] = None, stat_name: Optional[str] = None) -> int:
    raw = (2 * base + iv + ev // 4) * level // 100 + 5
    if nature and stat_name:
        raw = int(raw * nature_multiplier(nature, stat_name))
    return raw


class Pokemon:
    def __init__(self, name, types, level, base_stats, moves, ivs=None, evs=None, nature=None):
        self.name = name
        self.types = [t.lower() for t in types]
        self.level = level
        self.base_stats = dict(base_stats)
        self.moves = list(moves)
        self.ivs = dict(ivs) if ivs else {stat: 0 for stat in _STAT_NAMES}
        self.evs = dict(evs) if evs else {stat: 0 for stat in _STAT_NAMES}
        self.nature = nature or _NEUTRAL_NATURE

        # Estado de batalha — todo Pokémon começa saudável.
        self.status = None  # None ou um de status.MAJOR_STATUSES
        self.sleep_turns = 0  # só usado enquanto status == SLEEP
        self.confusion_turns = 0  # confusão é à parte do status "maior"
        self.charging_move = None  # golpe de 2 turnos em andamento (None = nenhum)
        self.stat_stages = {stat: 0 for stat in _STAGE_STAT_NAMES}  # Intimidate etc.

        self.experience = 0  # XP acumulado — só o modo gráfico usa isso
        self.ability = None  # nome da habilidade (formato PokeAPI) — só o modo gráfico usa isso

        self.max_hp = None
        self.current_hp = None
        self._recalculate_stats(full_heal=True)

    def _recalculate_stats(self, full_heal: bool = False) -> None:
        """Recalcula os 6 stats a partir de nível/base/IV/EV/natureza.

        Chamado na criação e de novo a cada level up (pokebattle/progression.py).
        Fora da criação, o HP atual sobe pelo mesmo tanto que o máximo subiu,
        em vez de curar tudo — é assim que os jogos fazem.
        """
        old_max_hp = self.max_hp
        self.max_hp = calc_hp(self.base_stats["hp"], self.level, self.ivs["hp"], self.evs["hp"])
        self.attack = calc_stat(self.base_stats["attack"], self.level, self.ivs["attack"],
                                 self.evs["attack"], self.nature, "attack")
        self.defense = calc_stat(self.base_stats["defense"], self.level, self.ivs["defense"],
                                  self.evs["defense"], self.nature, "defense")
        self.sp_atk = calc_stat(self.base_stats["sp_atk"], self.level, self.ivs["sp_atk"],
                                 self.evs["sp_atk"], self.nature, "sp_atk")
        self.sp_def = calc_stat(self.base_stats["sp_def"], self.level, self.ivs["sp_def"],
                                 self.evs["sp_def"], self.nature, "sp_def")
        self.speed = calc_stat(self.base_stats["speed"], self.level, self.ivs["speed"],
                                self.evs["speed"], self.nature, "speed")

        if full_heal or old_max_hp is None:
            self.current_hp = self.max_hp
        else:
            self.current_hp = min(self.max_hp, self.current_hp + (self.max_hp - old_max_hp))

    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    @property
    def effective_attack(self) -> int:
        """Ataque físico efetivo: estágio (Intimidate etc.) primeiro, depois
        queimadura reduz à metade — exceto pra quem tem Guts, que ignora o
        corte da queimadura e ainda ganha +50% com qualquer status."""
        value = self.attack * stage_multiplier(self.stat_stages["attack"])
        if self.ability == "guts" and self.status:
            value *= 1.5
        elif self.status == BURN:
            value /= 2
        return max(1, int(value))

    @property
    def effective_defense(self) -> int:
        return max(1, int(self.defense * stage_multiplier(self.stat_stages["defense"])))

    @property
    def effective_sp_atk(self) -> int:
        return max(1, int(self.sp_atk * stage_multiplier(self.stat_stages["sp_atk"])))

    @property
    def effective_sp_def(self) -> int:
        return max(1, int(self.sp_def * stage_multiplier(self.stat_stages["sp_def"])))

    @property
    def effective_speed(self) -> int:
        """Velocidade efetiva: estágio primeiro, depois paralisia reduz à metade."""
        value = self.speed * stage_multiplier(self.stat_stages["speed"])
        if self.status == PARALYSIS:
            value /= 2
        return max(1, int(value))

    def modify_stage(self, stat: str, delta: int) -> int:
        """Muda um estágio de stat (-6 a +6, como Intimidate). Devolve quanto
        realmente mudou (0 se já estava no limite)."""
        old = self.stat_stages[stat]
        new = max(-6, min(6, old + delta))
        self.stat_stages[stat] = new
        return new - old

    def take_damage(self, amount: int) -> None:
        self.current_hp = max(0, self.current_hp - amount)

    def heal(self, amount: int) -> None:
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def cure_status(self) -> None:
        self.status = None
        self.sleep_turns = 0

    def gain_ev(self, stat: str, amount: int, stat_cap: int = 252, total_cap: int = 510) -> int:
        """Adiciona EV num stat respeitando os limites oficiais (252 por
        stat, 510 no total). Devolve quanto realmente foi ganho."""
        total = sum(self.evs.values())
        gain = max(0, min(amount, stat_cap - self.evs[stat], total_cap - total))
        self.evs[stat] += gain
        return gain

    def __repr__(self):
        return f"<Pokemon {self.name} Lv.{self.level} HP {self.current_hp}/{self.max_hp}>"
