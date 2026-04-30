"""Testes de pokebattle/locations.py — catálogo de arenas e o "clima fixo"
que cada uma aplica."""

import random

from pokebattle import locations


def test_open_field_has_no_weather():
    assert locations.get_location("open_field").weather is None


def test_volcano_favors_fire_with_sun():
    assert locations.get_location("volcano").weather == "sun"


def test_lake_favors_water_with_rain():
    assert locations.get_location("lake").weather == "rain"


def test_location_for_type_matches_the_obvious_pairing():
    assert locations.location_for_type("fire").id == "volcano"
    assert locations.location_for_type("water").id == "lake"
    assert locations.location_for_type("ice").id == "glacier"


def test_location_for_type_returns_none_without_an_obvious_pairing():
    assert locations.location_for_type("psychic") is None


def test_random_location_always_returns_a_known_location():
    rng = random.Random(1)
    for _ in range(20):
        location = locations.random_location(rng)
        assert location.id in {loc.id for loc in locations.CATALOG}


def test_random_location_favors_open_field_most_of_the_time():
    rng = random.Random(42)
    picks = [locations.random_location(rng).id for _ in range(500)]
    assert picks.count("open_field") > len(picks) / 3
