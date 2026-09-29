#!/usr/bin/env python3
"""Demo Flask local: roster fixo e Battle, sem PokéAPI ou persistência remota."""
import os
import random
import secrets
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from flask import Flask, redirect, render_template, request, session, url_for
from pokebattle.battle import Battle
from pokebattle.data import create_pokemon, display_name, list_species, list_species_starting_with

app = Flask(__name__)
app.secret_key = uuid.uuid4().hex
app.config.update(SESSION_COOKIE_NAME='pokemon_battle_demo', SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=16000)
_GAMES: dict[str, dict[str, Any]] = {}
_MAX_GAMES = 500
_MAX_TEAM = 6


def _session_id() -> str:
    if 'sid' not in session:
        session['sid'] = uuid.uuid4().hex
    return session['sid']


def _current_game() -> Optional[dict[str, Any]]:
    return _GAMES.get(_session_id())


def _csrf_token() -> str:
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


@app.context_processor
def template_context():
    return {'csrf_token': _csrf_token()}


@app.before_request
def protect_forms():
    if request.method == 'POST':
        submitted = request.form.get('csrf_token', '')
        expected = session.get('csrf_token', '')
        if not expected or not submitted.isascii() or not secrets.compare_digest(submitted, expected):
            return render_template('error.html', message='O formulário expirou. Abra a página novamente e tente outra vez.'), 403


@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
    if request.endpoint != 'static':
        response.headers['Cache-Control'] = 'no-store'
    return response


def _hp_view(pokemon) -> dict[str, Any]:
    ratio = 0 if pokemon.max_hp <= 0 else min(1, max(0, pokemon.current_hp / pokemon.max_hp))
    return {'percent': round(ratio * 100), 'state': 'healthy' if ratio > .5 else 'hurt' if ratio > .2 else 'critical'}


def _choose_response(error='', status=200):
    letter = request.args.get('letter', '').strip()[:1]
    species = list_species_starting_with(letter) if letter else list_species()
    return render_template('choose.html', species=species, all_species=list_species(), letter=letter,
                           display_name=display_name, error=error), status


def _new_game(player_species, enemy_species, demo=False):
    players = [create_pokemon(species) for species in player_species]
    enemies = [create_pokemon(species) for species in enemy_species]
    if demo:
        players[0].current_hp = 1
    battle = Battle(players, enemies, rng=random.Random(7) if demo else random.Random())
    if len(_GAMES) >= _MAX_GAMES:
        _GAMES.pop(next(iter(_GAMES)))
    game = {'battle': battle, 'player': battle.player, 'enemy': battle.enemy,
            'log': [f'Seu time tem {len(players)} Pokémon; o adversário tem {len(enemies)}.',
                    f'Você começou com {battle.player.name}. O oponente começou com {battle.enemy.name}.',
                    *battle.intro_log], 'revision': 0, 'lock': threading.RLock(), 'demo': demo}
    if demo:
        game['log'].append('Cenário fictício: seu ativo começa com 1 HP para demonstrar a troca obrigatória após desmaio.')
    _GAMES[_session_id()] = game
    return game


def _sync_active(game):
    battle = game['battle']
    game['player'], game['enemy'] = battle.player, battle.enemy
    # A reserva adversária entra após o turno, sem ataque extra de entrada.
    if battle.needs_switch('enemy'):
        index = next(i for i, pokemon in enumerate(battle.enemy_team) if not pokemon.is_fainted)
        game['log'].append('O adversário precisa substituir seu Pokémon desmaiado.')
        game['log'].extend(battle.switch('enemy', index))
        game['enemy'] = battle.enemy
    game['log'] = game['log'][-160:]


def _battle_response(game, error='', status=200):
    battle = game['battle']
    return render_template('battle.html', battle=battle, player=battle.player, enemy=battle.enemy,
                           log=game['log'], player_hp=_hp_view(battle.player), enemy_hp=_hp_view(battle.enemy),
                           revision=game['revision'], needs_switch=battle.needs_switch('player'),
                           demo=game['demo'], error=error), status


def _check_revision(game):
    if request.form.get('revision') != str(game['revision']):
        return _battle_response(game, 'A partida mudou. Confira o estado atual antes de agir novamente.', 409)
    return None


def _enemy_move(game):
    battle = game['battle']
    return battle.enemy.moves[0] if game['demo'] else battle.rng.choice(battle.enemy.moves)


@app.route('/')
def choose():
    return _choose_response()


@app.route('/choose', methods=['POST'])
def start_battle():
    selected = request.form.getlist('team') if 'team' in request.form else request.form.getlist('species')
    selected = [species.strip().lower() for species in selected if species.strip()]
    if not 1 <= len(selected) <= _MAX_TEAM:
        return _choose_response('Escolha de 1 a 6 Pokémon.', 400)
    available = set(list_species())
    if any(species not in available for species in selected):
        return _choose_response('Escolha somente espécies do catálogo local.', 400)
    enemies = random.sample(list_species(), len(selected))
    _new_game(selected, enemies)
    return redirect(url_for('battle_view'))


@app.route('/demo', methods=['GET', 'POST'])
def demo_battle():
    if request.method == 'GET':
        return render_template('demo.html')
    _new_game(['bulbasaur', 'squirtle', 'pikachu'], ['charmander', 'machop', 'eevee'], demo=True)
    return redirect(url_for('battle_view'))


@app.route('/battle')
def battle_view():
    game = _current_game()
    if game is None:
        return redirect(url_for('choose'))
    with game['lock']:
        _sync_active(game)
        return _battle_response(game)


@app.route('/battle/move', methods=['POST'])
def battle_move():
    game = _current_game()
    if game is None:
        return redirect(url_for('choose'))
    with game['lock']:
        stale = _check_revision(game)
        if stale is not None:
            return stale
        battle = game['battle']
        if battle.is_over:
            return _battle_response(game, 'Esta partida terminou. Comece outra para jogar.', 409)
        if battle.needs_switch('player'):
            return _battle_response(game, 'Seu Pokémon desmaiou. Escolha uma reserva antes de atacar.', 409)
        try:
            move_index = int(request.form.get('move_index', ''))
        except ValueError:
            return _battle_response(game, 'Escolha um golpe válido.', 400)
        if not 0 <= move_index < len(battle.player.moves):
            return _battle_response(game, 'Escolha um golpe válido.', 400)
        game['log'].extend(battle.take_turn(('move', battle.player.moves[move_index]), _enemy_move(game)))
        _sync_active(game)
        game['revision'] += 1
    return redirect(url_for('battle_view'))


@app.route('/battle/switch', methods=['POST'])
def battle_switch():
    game = _current_game()
    if game is None:
        return redirect(url_for('choose'))
    with game['lock']:
        stale = _check_revision(game)
        if stale is not None:
            return stale
        battle = game['battle']
        if battle.is_over:
            return _battle_response(game, 'Esta partida terminou.', 409)
        try:
            index = int(request.form.get('team_index', ''))
        except ValueError:
            return _battle_response(game, 'Escolha uma reserva válida.', 400)
        if not 0 <= index < len(battle.player_team) or index == battle.player_active or battle.player_team[index].is_fainted:
            return _battle_response(game, 'A reserva deve estar viva e ser diferente do Pokémon ativo.', 400)
        if battle.needs_switch('player'):
            game['log'].extend(battle.switch('player', index))
        else:
            game['log'].extend(battle.take_turn(('switch', index), _enemy_move(game)))
        _sync_active(game)
        game['revision'] += 1
    return redirect(url_for('battle_view'))


@app.route('/battle/reset', methods=['POST'])
def battle_reset():
    game = _current_game()
    if game:
        with game['lock']:
            _GAMES.pop(_session_id(), None)
    return redirect(url_for('choose'))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=os.environ.get('FLASK_DEBUG') == '1')
