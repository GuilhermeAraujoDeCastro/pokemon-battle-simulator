#!/usr/bin/env python3
"""Simulador de Batalha Pokémon — CLI.

Escolha seu Pokémon, o computador escolhe um aleatoriamente, e batalhem
usando a fórmula oficial de dano dos jogos (nível, ataque/defesa, poder do
golpe e efetividade de tipo).
"""

import random
import sys

from pokebattle.battle import Battle
from pokebattle.data import create_pokemon, display_name, list_species, list_species_starting_with
from pokebattle.ui import print_banner, render_hp_bar


def choose_player_pokemon():
    print_banner("Escolha seu Pokémon")
    total = len(list_species())
    print(f"({total} Pokémon disponíveis) Digite uma letra pra filtrar, ou só aperte Enter pra ver todos.")

    while True:
        letra = input("\nFiltrar por letra: ").strip()
        opcoes = list_species_starting_with(letra)

        if not opcoes:
            print(f'Nenhum Pokémon começa com "{letra}". Tenta outra letra.')
            continue

        for i, especie in enumerate(opcoes, start=1):
            print(f"  {i}. {display_name(especie)}")

        escolha = input("\nDigite o número do Pokémon (ou Enter pra filtrar de novo): ").strip()
        if not escolha:
            continue
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            return create_pokemon(opcoes[int(escolha) - 1])
        print("Opção inválida, tenta de novo.")


def choose_move(pokemon):
    print(f"\nMovimentos de {pokemon.name}:")
    for i, move in enumerate(pokemon.moves, start=1):
        print(f"  {i}. {move.name} ({move.type}, poder {move.power}, precisão {move.accuracy}%)")
    while True:
        choice = input("Escolha o movimento: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(pokemon.moves):
            return pokemon.moves[int(choice) - 1]
        print("Opção inválida, tenta de novo.")


def print_status(battle: Battle) -> None:
    print(f"\n{battle.player.name}: {render_hp_bar(battle.player.current_hp, battle.player.max_hp)}")
    print(f"{battle.enemy.name}: {render_hp_bar(battle.enemy.current_hp, battle.enemy.max_hp)}")


def play() -> None:
    print_banner("SIMULADOR DE BATALHA POKÉMON")

    player_pokemon = choose_player_pokemon()
    enemy_species = random.choice(list_species())
    enemy_pokemon = create_pokemon(enemy_species)

    print(f"\nVocê escolheu {player_pokemon.name}!")
    print(f"O oponente escolheu {enemy_pokemon.name}!")

    battle = Battle(player_pokemon, enemy_pokemon)

    while not battle.is_over:
        print_status(battle)
        player_move = choose_move(player_pokemon)
        enemy_move = random.choice(enemy_pokemon.moves)

        print()
        for line in battle.execute_turn(player_move, enemy_move):
            print(line)

    print()
    print_status(battle)
    if battle.winner == "player":
        print_banner(f"Você venceu com {player_pokemon.name}!")
    else:
        print_banner(f"Você perdeu... {enemy_pokemon.name} venceu.")

    again = input("\nJogar de novo? (s/n): ").strip().lower()
    if again == "s":
        print()
        play()
    else:
        print("Valeu por jogar!")


if __name__ == "__main__":
    try:
        play()
    except KeyboardInterrupt:
        print("\n\nBatalha interrompida. Até a próxima!")
        sys.exit(0)
