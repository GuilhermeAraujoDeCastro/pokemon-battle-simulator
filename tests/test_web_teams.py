"""Jornadas Flask reais com Battle e catálogo local; nenhuma chamada à rede."""
import random
import socket
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from werkzeug.datastructures import MultiDict
from web.app import app, _GAMES
from pokebattle.battle import Battle


class Forms(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.forms = []
        self.current = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.current = {'attrs': attrs, 'inputs': []}
            self.forms.append(self.current)
        elif tag in ('input', 'select', 'button') and self.current is not None:
            self.current['inputs'].append(attrs)

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None


class WebTeamsTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        _GAMES.clear()
        self.client = app.test_client()
        self.client.get('/')

    def game(self, client=None):
        client = client or self.client
        with client.session_transaction() as session:
            return _GAMES[session['sid']]

    def post(self, path, data=None, client=None, revision=None, follow_redirects=False):
        client = client or self.client
        with client.session_transaction() as session:
            token = session['csrf_token']
            sid = session.get('sid')
        payload = MultiDict(data or {})
        payload.add('csrf_token', token)
        if path in ('/battle/move', '/battle/switch'):
            payload.add('revision', str(_GAMES[sid]['revision'] if revision is None else revision))
        return client.post(path, data=payload, follow_redirects=follow_redirects)

    def demo(self):
        self.assertEqual(self.post('/demo').status_code, 302)
        return self.game()

    def test_selecao_mostra_seis_slots_e_preserva_batalha_rapida(self):
        response = self.client.get('/')
        html = response.get_data(as_text=True)
        self.assertEqual(html.count('name="team"'), 6)
        self.assertIn('Batalha rápida de um contra um', html)
        response = self.post('/choose', {'species': 'Pikachu'})
        self.assertEqual(response.status_code, 302)
        battle = self.game()['battle']
        self.assertIsInstance(battle, Battle)
        self.assertEqual(len(battle.player_team), 1)
        self.assertEqual(len(battle.enemy_team), 1)

    def test_equipes_de_seis_usam_dominio_e_preservam_ordem(self):
        names = ['pikachu', 'bulbasaur', 'squirtle', 'charmander', 'eevee', 'mewtwo']
        response = self.post('/choose', MultiDict([('team', name) for name in names]))
        self.assertEqual(response.status_code, 302)
        battle = self.game()['battle']
        self.assertEqual([pokemon.name.lower() for pokemon in battle.player_team], names)
        self.assertEqual(len(battle.enemy_team), 6)
        self.assertEqual(battle.player_active, 0)
        html = self.client.get('/battle').get_data(as_text=True)
        self.assertIn('Seu time e reservas', html)
        self.assertIn('Trocar para Squirtle', html)

    def test_validacao_recusa_time_vazio_excedente_e_especie_desconhecida(self):
        for data in ({}, MultiDict([('team', 'pikachu')] * 7), {'team': '<script>alert(1)</script>'}):
            response = self.post('/choose', data)
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('<script>', response.get_data(as_text=True))
        self.assertFalse(_GAMES)

    def test_troca_voluntaria_consume_turno_com_ataque_real(self):
        game = self.demo()
        battle = game['battle']
        reserve = battle.player_team[1]
        response = self.post('/battle/switch', {'team_index': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(battle.player_active, 1)
        self.assertLess(reserve.current_hp, reserve.max_hp)
        self.assertTrue(any('Scratch' in line for line in game['log']))

    def test_desmaio_exige_reserva_e_troca_forcada_nao_da_ataque_extra(self):
        game = self.demo()
        battle = game['battle']
        self.assertEqual(self.post('/battle/move', {'move_index': '0'}).status_code, 302)
        self.assertTrue(battle.player.is_fainted)
        self.assertTrue(battle.needs_switch('player'))
        html = self.client.get('/battle').get_data(as_text=True)
        self.assertIn('Escolha uma reserva', html)
        self.assertNotIn('action="/battle/move"', html)
        log = list(game['log'])
        self.assertEqual(self.post('/battle/move', {'move_index': '0'}).status_code, 409)
        self.assertEqual(game['log'], log)
        reserve_hp = battle.player_team[1].current_hp
        enemy_hp = battle.enemy.current_hp
        self.assertEqual(self.post('/battle/switch', {'team_index': '1'}).status_code, 302)
        self.assertEqual(battle.player_active, 1)
        self.assertEqual(battle.player.current_hp, reserve_hp)
        self.assertEqual(battle.enemy.current_hp, enemy_hp)
        self.assertIn('action="/battle/move"', self.client.get('/battle').get_data(as_text=True))

    def test_reserva_desmaiada_indice_negativo_atual_ou_invalido_nao_alteram_estado(self):
        game = self.demo()
        battle = game['battle']
        battle.player_team[2].current_hp = 0
        before = [pokemon.current_hp for pokemon in battle.player_team]
        for index in ('-1', '99', 'abc', '0', '2'):
            self.assertEqual(self.post('/battle/switch', {'team_index': index}).status_code, 400)
        for index in ('-1', '99', 'abc'):
            self.assertEqual(self.post('/battle/move', {'move_index': index}).status_code, 400)
        self.assertEqual(before, [pokemon.current_hp for pokemon in battle.player_team])
        self.assertEqual(game['revision'], 0)

    def test_adversario_envia_reserva_e_vitoria_exige_time_inteiro(self):
        with patch('web.app.random.sample', return_value=['charmander', 'machop']):
            self.post('/choose', MultiDict([('team', 'mewtwo'), ('team', 'snorlax')]))
        game = self.game()
        battle = game['battle']
        battle.rng = random.Random(0)
        battle.enemy.current_hp = 1
        self.post('/battle/move', {'move_index': '0'})
        self.assertTrue(battle.enemy_team[0].is_fainted)
        self.assertEqual(battle.enemy_active, 1)
        self.assertFalse(battle.is_over)
        self.assertEqual(battle.enemy.current_hp, battle.enemy.max_hp)
        battle.enemy.current_hp = 1
        response = self.post('/battle/move', {'move_index': '0'}, follow_redirects=True)
        self.assertTrue(battle.is_over)
        self.assertEqual(battle.winner, 'player')
        self.assertIn('Você venceu a equipe adversária', response.get_data(as_text=True))

    def test_csrf_e_revisao_bloqueiam_formulario_invalido_e_reenvio(self):
        self.assertEqual(self.client.post('/choose', data={'species': 'pikachu'}).status_code, 403)
        self.assertEqual(self.client.post('/choose', data={'species': 'pikachu', 'csrf_token': 'errado'}).status_code, 403)
        self.assertEqual(self.client.post('/choose', data={'species': 'pikachu', 'csrf_token': 'inválido'}).status_code, 403)
        game = self.demo()
        self.post('/battle/switch', {'team_index': '1'}, revision=0)
        after = [pokemon.current_hp for pokemon in game['battle'].player_team]
        response = self.post('/battle/switch', {'team_index': '2'}, revision=0)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(after, [pokemon.current_hp for pokemon in game['battle'].player_team])
        self.assertEqual(game['battle'].player_active, 1)

    def test_sessoes_nao_compartilham_partida(self):
        self.post('/choose', {'species': 'pikachu'})
        first = self.game()
        other = app.test_client()
        other.get('/')
        self.post('/choose', {'species': 'squirtle'}, client=other)
        second = self.game(other)
        self.assertIsNot(first, second)
        hp = first['battle'].player.current_hp
        self.post('/battle/move', {'move_index': '0'}, client=other)
        self.assertEqual(first['battle'].player.current_hp, hp)

    def test_nomes_e_log_sao_escapados_e_cabecalhos_restringem_scripts(self):
        game = self.demo()
        game['log'].append('<script>alert(1)</script>')
        game['battle'].player.name = '<img src=x onerror=alert(1)>'
        response = self.client.get('/battle')
        html = response.get_data(as_text=True)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn("script-src 'none'", response.headers['Content-Security-Policy'])
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_formularios_renderizados_contem_token_e_revisao(self):
        self.demo()
        html = self.client.get('/battle').get_data(as_text=True)
        posts = [form for form in Forms(html).forms if form['attrs'].get('method') == 'post']
        self.assertTrue(posts)
        for form in posts:
            names = {field.get('name') for field in form['inputs']}
            self.assertIn('csrf_token', names)
            if form['attrs']['action'] in ('/battle/move', '/battle/switch'):
                self.assertIn('revision', names)

    def test_cenario_completo_usa_somente_dados_locais(self):
        with patch.object(socket, 'create_connection', side_effect=AssertionError('Rede proibida')):
            game = self.demo()
            self.post('/battle/move', {'move_index': '0'})
            self.post('/battle/switch', {'team_index': '1'})
            self.post('/battle/move', {'move_index': '0'})
            self.assertGreater(game['revision'], 0)
            self.assertEqual(self.client.get('/battle').status_code, 200)


if __name__ == '__main__':
    unittest.main()
