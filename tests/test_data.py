import pytest

from pokebattle.data import (
    create_pokemon,
    display_name,
    list_species,
    list_species_starting_with,
)


def test_roster_has_at_least_thirty_species():
    species = list_species()
    assert len(species) >= 30
    assert "pikachu" in species
    assert len(species) == len(set(species))  # sem espécie duplicada


def test_filter_by_letter_is_case_insensitive():
    matches = list_species_starting_with("P")
    assert "pikachu" in matches
    assert all(name.lower().startswith("p") for name in matches)
    assert matches == list_species_starting_with("p")


def test_filter_with_empty_letter_returns_everything():
    assert list_species_starting_with("") == list_species()
    assert list_species_starting_with("   ") == list_species()


def test_filter_with_no_match_returns_empty_list():
    assert list_species_starting_with("zzz-inexistente") == []


def test_display_name_handles_the_apostrophe_exception():
    assert display_name("farfetchd") == "Farfetch'd"
    assert display_name("pikachu") == "Pikachu"


def test_create_pokemon_uses_the_display_name():
    mon = create_pokemon("farfetchd")
    assert mon.name == "Farfetch'd"


def test_every_species_has_a_complete_moveset_with_valid_moves():
    for species in list_species():
        mon = create_pokemon(species)
        assert 1 <= len(mon.moves) <= 4
        for move in mon.moves:
            assert move.power > 0
            assert move.type
            assert move.category in ("physical", "special")


def test_create_pokemon_rejects_unknown_species():
    with pytest.raises(ValueError):
        create_pokemon("pokemon-que-nao-existe")
