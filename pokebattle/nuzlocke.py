"""Modo Nuzlocke (opcional, ligado na tela de time): um Pokémon que desmaia
numa batalha é removido permanentemente do time, e Revive deixa de funcionar
— sem mexer em nada da lógica de batalha em si (battle.py continua igual),
só nas regras de "o que acontece depois" que main_gui.py aplica.
"""


def surviving_team(team: list) -> list:
    """Quem sobrou vivo depois de uma batalha — usado pra saber quem fica no
    time quando o Nuzlocke está ligado."""
    return [pokemon for pokemon in team if not pokemon.is_fainted]


def released_members(team: list) -> list:
    """Quem desmaiou e vai ser liberado permanentemente."""
    return [pokemon for pokemon in team if pokemon.is_fainted]


def can_use_revive(nuzlocke_enabled: bool) -> bool:
    """Revive não existe no Nuzlocke: quem desmaia está fora de vez."""
    return not nuzlocke_enabled
