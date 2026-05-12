#!/usr/bin/env python3
"""Simulador de Batalha Pokémon — versão web (Flask).

Reaproveita exatamente a mesma lógica pura do modo texto: o roster fixo de
41 Pokémon (pokebattle/data.py, zero dependência de rede) e a classe Battle
(pokebattle/battle.py) — a mesma que main.py e main_gui.py já usam. Só a
interface é nova: em vez de print()/input() ou uma janela Tkinter, é HTTP
com Flask. É a mesma separação lógica/interface que o projeto já leva a
sério, aplicada numa terceira interface.

Como jogar:
    pip install -r requirements.txt   # já inclui o Flask
    python3 web/app.py
    # abre http://127.0.0.1:5000 no navegador

O estado de cada partida fica em memória de processo, por sessão (cookie) —
não em banco nem em disco. Reiniciar o servidor zera as partidas em
andamento. É um app de demonstração local, não pensado pra escala nem pra
múltiplos processos.
"""

import os
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, redirect, render_template, request, session, url_for  # noqa: E402

from pokebattle.battle import Battle  # noqa: E402
from pokebattle.data import create_pokemon, display_name, list_species, list_species_starting_with  # noqa: E402

app = Flask(__name__)
# Só assina o cookie de sessão (guarda um id de partida, nada sensível) —
# gerado uma vez por processo, então reiniciar o servidor também desloga
# sessões antigas. Não é uma chave de autenticação de verdade.
app.secret_key = uuid.uuid4().hex

# Partidas em andamento, por id de sessão — um dict em memória é suficiente
# pra um app de demonstração local (ver docstring do módulo).
_GAMES: dict[str, dict[str, Any]] = {}
# Teto de partidas guardadas: sem isso o dict so cresce enquanto o servidor estiver no ar.
_MAX_GAMES = 500


def _session_id() -> str:
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


def _current_game() -> Optional[dict[str, Any]]:
    return _GAMES.get(_session_id())


def _hp_view(pokemon) -> dict[str, Any]:
    ratio = 0.0 if pokemon.max_hp <= 0 else max(0.0, pokemon.current_hp / pokemon.max_hp)
    state = "healthy" if ratio > 0.5 else "hurt" if ratio > 0.2 else "critical"
    return {"percent": round(ratio * 100), "state": state}


@app.route("/")
def choose():
    letter = request.args.get("letter", "").strip()
    species = list_species_starting_with(letter) if letter else list_species()
    return render_template("choose.html", species=species, letter=letter, display_name=display_name)


@app.route("/choose", methods=["POST"])
def start_battle():
    species = request.form.get("species", "")
    if species.lower() not in {s.lower() for s in list_species()}:
        return redirect(url_for("choose"))

    player = create_pokemon(species)
    enemy = create_pokemon(random.choice(list_species()))
    battle = Battle(player, enemy)

    if len(_GAMES) >= _MAX_GAMES:
        _GAMES.pop(next(iter(_GAMES)))  # descarta a partida mais antiga
    _GAMES[_session_id()] = {
        "battle": battle,
        "player": player,
        "enemy": enemy,
        "log": [f"Você escolheu {player.name}!", f"O oponente escolheu {enemy.name}!"],
    }
    return redirect(url_for("battle_view"))


@app.route("/battle")
def battle_view():
    game = _current_game()
    if game is None:
        return redirect(url_for("choose"))
    battle: Battle = game["battle"]
    return render_template(
        "battle.html", battle=battle, player=game["player"], enemy=game["enemy"], log=game["log"],
        player_hp=_hp_view(game["player"]), enemy_hp=_hp_view(game["enemy"]),
    )


@app.route("/battle/move", methods=["POST"])
def battle_move():
    game = _current_game()
    if game is None:
        return redirect(url_for("choose"))
    battle: Battle = game["battle"]
    if not battle.is_over:
        try:
            move_index = int(request.form.get("move_index", -1))
        except ValueError:
            return redirect(url_for("battle_view"))
        # Indice negativo tambem e valido em lista Python (-1 = ultimo golpe), entao barra na mao.
        if not 0 <= move_index < len(game["player"].moves):
            return redirect(url_for("battle_view"))
        player_move = game["player"].moves[move_index]

        enemy_move = random.choice(game["enemy"].moves)
        game["log"].extend(battle.execute_turn(player_move, enemy_move))
    return redirect(url_for("battle_view"))


@app.route("/battle/reset", methods=["POST"])
def battle_reset():
    _GAMES.pop(_session_id(), None)
    return redirect(url_for("choose"))


if __name__ == "__main__":
    # Debug do Flask so com FLASK_DEBUG=1: o console dele executa codigo e nao pode ficar ligado por padrao.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
