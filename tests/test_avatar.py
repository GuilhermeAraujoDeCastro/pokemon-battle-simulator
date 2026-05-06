"""Testes de pokebattle/avatar.py — só a lógica pura (cor/letra); o desenho
no Canvas fica em main_gui.py."""

from pokebattle import avatar


def test_initial_for_uppercases_the_first_letter():
    assert avatar.initial_for("guilherme") == "G"
    assert avatar.initial_for("Ash") == "A"


def test_initial_for_empty_name_is_a_placeholder():
    assert avatar.initial_for("") == "?"
    assert avatar.initial_for("   ") == "?"


def test_color_hex_falls_back_to_the_default_for_an_unknown_id():
    assert avatar.color_hex("nao-existe") == avatar.PALETTE[avatar.DEFAULT_COLOR]
    assert avatar.color_hex(None) == avatar.PALETTE[avatar.DEFAULT_COLOR]


def test_color_hex_resolves_a_known_color():
    assert avatar.color_hex("blue") == avatar.PALETTE["blue"]


def test_avatar_spec_combines_initial_and_color():
    spec = avatar.avatar_spec("Kirito", "green")
    assert spec == {"initial": "K", "color": avatar.PALETTE["green"], "color_id": "green"}
