"""Testes de pokebattle/pokeapi.py que não tocam rede de verdade — só
substituem _get por uma versão falsa."""

from pokebattle import pokeapi

FAKE_LIST_RESPONSE = {
    "results": [
        {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon/1/"},
        {"name": "ivysaur", "url": "https://pokeapi.co/api/v2/pokemon/2/"},
        {"name": "venusaur", "url": "https://pokeapi.co/api/v2/pokemon/3/"},
    ]
}


def test_list_all_species_with_dex_numbers_parses_the_id_from_the_url(monkeypatch):
    monkeypatch.setattr(pokeapi, "_get", lambda url: FAKE_LIST_RESPONSE)

    result = pokeapi.list_all_species_with_dex_numbers()

    assert result == [(1, "bulbasaur"), (2, "ivysaur"), (3, "venusaur")]


def test_list_all_species_with_dex_numbers_falls_back_to_zero_on_a_bad_url(monkeypatch):
    monkeypatch.setattr(
        pokeapi, "_get",
        lambda url: {"results": [{"name": "weird-form", "url": "https://pokeapi.co/api/v2/pokemon/not-a-number/"}]},
    )

    result = pokeapi.list_all_species_with_dex_numbers()

    assert result == [(0, "weird-form")]
