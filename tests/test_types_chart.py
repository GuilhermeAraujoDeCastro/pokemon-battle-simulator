from pokebattle.types_chart import effectiveness


def test_super_effective_single_type():
    assert effectiveness("water", ["fire"]) == 2.0
    assert effectiveness("fire", ["grass"]) == 2.0


def test_not_very_effective_single_type():
    assert effectiveness("fire", ["water"]) == 0.5
    assert effectiveness("water", ["grass"]) == 0.5


def test_no_effect():
    assert effectiveness("normal", ["ghost"]) == 0.0
    assert effectiveness("fighting", ["ghost"]) == 0.0
    assert effectiveness("electric", ["ground"]) == 0.0


def test_neutral_when_no_relation_listed():
    assert effectiveness("normal", ["fire"]) == 1.0


def test_dual_type_multiplies_both():
    # Gastly é Fantasma/Venenoso: Psíquico é 2x contra Fantasma e neutro contra Venenoso
    assert effectiveness("psychic", ["ghost", "poison"]) == 2.0
    # Bulbasaur é Grama/Venenoso: Gelo é 2x contra Grama e neutro contra Venenoso
    assert effectiveness("ice", ["grass", "poison"]) == 2.0
    # Um Pokémon hipotético Fogo/Venenoso levaria 4x de um golpe de Terra
    # (2x contra Fogo, 2x contra Venenoso)
    assert effectiveness("ground", ["fire", "poison"]) == 4.0
