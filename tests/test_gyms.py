"""Testes de pokebattle/gyms.py — sem tocar rede de verdade."""

from pokebattle import gyms


def test_next_gym_is_the_first_one_without_a_badge():
    assert gyms.next_gym([]).id == "pewter"
    assert gyms.next_gym(["pewter"]).id == "cerulean"


def test_next_gym_returns_none_when_every_badge_is_won():
    all_ids = [gym.id for gym in gyms.GYMS]
    assert gyms.next_gym(all_ids) is None


def test_gyms_are_all_unique_and_in_a_fixed_order():
    ids = [gym.id for gym in gyms.GYMS]
    assert len(ids) == len(set(ids))
    assert ids[0] == "pewter"
    assert ids[-1] == "viridian"


def test_get_gym_looks_up_by_id():
    gym = gyms.get_gym("pewter")
    assert gym.leader == "Brock"
    assert gym.badge_name == "Insígnia Rocha"
    assert gym.reward_money == 1400
    assert [t.species for t in gym.team] == ["geodude", "onix"]


def test_every_gym_has_a_valid_ai_personality():
    from pokebattle import ai

    for gym in gyms.GYMS:
        assert gym.personality in ai.PERSONALITIES, f"{gym.id} tem personalidade inválida: {gym.personality}"


def test_build_gym_team_uses_each_trainers_own_level(monkeypatch):
    from pokebattle import roster

    built = []

    def fake_build_pokemon(species, level, rng=None):
        built.append((species, level))
        return object()

    monkeypatch.setattr(roster, "build_pokemon", fake_build_pokemon)

    gym = gyms.get_gym("pewter")
    team = gyms.build_gym_team(gym)

    assert len(team) == 2
    assert built == [("geodude", 12), ("onix", 14)]
