"""Testes da versão web (Flask, item 15): usa app.test_client(), que nunca
abre socket de verdade — mesma filosofia dos outros testes do projeto (lógica
pura, sem I/O real). Reaproveita o roster fixo de pokebattle/data.py, então
não toca a PokeAPI nem precisa de internet."""

from web.app import _GAMES, app


def make_client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_choose_page_lists_the_fixed_roster():
    response = make_client().get("/")
    assert response.status_code == 200
    assert "Bulbasaur" in response.get_data(as_text=True)


def test_choose_page_filters_by_letter():
    text = make_client().get("/?letter=p").get_data(as_text=True)
    assert "Pikachu" in text
    assert "Bulbasaur" not in text


def test_starting_a_battle_redirects_to_the_battle_view():
    response = make_client().post("/choose", data={"species": "pikachu"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/battle")


def test_starting_a_battle_with_an_unknown_species_redirects_back_to_choose():
    response = make_client().post("/choose", data={"species": "nao-existe"})
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "http://localhost/")


def test_battle_view_without_a_game_redirects_to_choose():
    response = make_client().get("/battle")
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "http://localhost/")


def test_battle_view_shows_both_pokemon_and_move_buttons():
    client = make_client()
    client.post("/choose", data={"species": "charmander"})
    text = client.get("/battle").get_data(as_text=True)
    assert "Charmander" in text
    assert "Scratch" in text  # primeiro golpe do Charmander no roster fixo


def test_a_move_updates_the_battle_log():
    client = make_client()
    client.post("/choose", data={"species": "pikachu"})
    client.post("/battle/move", data={"move_index": 0})
    text = client.get("/battle").get_data(as_text=True)
    assert "usou" in text  # o log de battle.py sempre começa com "X usou Y!"


def test_full_battle_flow_ends_and_offers_play_again():
    client = make_client()
    client.post("/choose", data={"species": "mewtwo"})
    with client.session_transaction() as flask_session:
        sid = flask_session["sid"]
    _GAMES[sid]["enemy"].current_hp = 1  # garante o nocaute no próximo golpe, sem depender de sorte

    text = client.post("/battle/move", data={"move_index": 0}, follow_redirects=True).get_data(as_text=True)
    assert "Jogar de novo" in text


def test_reset_clears_the_session_game():
    client = make_client()
    client.post("/choose", data={"species": "pikachu"})
    client.post("/battle/reset")
    response = client.get("/battle")
    assert response.status_code == 302  # sem jogo: volta pra escolha


def test_move_index_out_of_range_is_ignored_not_crashed():
    client = make_client()
    client.post("/choose", data={"species": "pikachu"})
    response = client.post("/battle/move", data={"move_index": "99"})
    assert response.status_code == 302  # não quebra, só redireciona de volta
