import pokebattle.save as save_module


def test_load_returns_default_when_file_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    data = save_module.load()
    assert data == {
        "pokedex_seen": [], "badges": [], "money": 0, "items": {"potion": 3},
        "trainer_name": "", "starter": "", "difficulty": "normal",
        "trainers_defeated": 0, "quests_completed": [],
    }


def test_mark_seen_adds_species_without_duplicating(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.mark_seen("pikachu")
    save_module.mark_seen(["pikachu", "charmander"])

    data = save_module.load()
    assert data["pokedex_seen"] == ["charmander", "pikachu"]


def test_add_badge_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.add_badge("pedra")
    save_module.add_badge("pedra")
    save_module.add_badge("cascata")

    data = save_module.load()
    assert data["badges"] == ["pedra", "cascata"]
    assert save_module.has_badge("pedra") is True
    assert save_module.has_badge("trovao") is False


def test_load_recovers_from_a_corrupted_file(tmp_path, monkeypatch):
    save_path = tmp_path / "savegame.json"
    save_path.write_text("isso não é json{{{", encoding="utf-8")
    monkeypatch.setattr(save_module, "SAVE_PATH", save_path)

    assert save_module.load() == {
        "pokedex_seen": [], "badges": [], "money": 0, "items": {"potion": 3},
        "trainer_name": "", "starter": "", "difficulty": "normal",
        "trainers_defeated": 0, "quests_completed": [],
    }


def test_load_fills_in_missing_fields_from_an_older_save(tmp_path, monkeypatch):
    save_path = tmp_path / "savegame.json"
    save_path.write_text('{"pokedex_seen": ["mew"]}', encoding="utf-8")
    monkeypatch.setattr(save_module, "SAVE_PATH", save_path)

    data = save_module.load()
    assert data["pokedex_seen"] == ["mew"]
    assert data["badges"] == []
    assert data["money"] == 0


def test_add_money_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.add_money(1400)
    save_module.add_money(2100)

    assert save_module.load()["money"] == 3500


def test_spend_money_fails_without_enough_and_succeeds_with_enough(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.add_money(500)

    assert save_module.spend_money(1000) is False
    assert save_module.load()["money"] == 500  # não mudou nada na tentativa que falhou

    assert save_module.spend_money(300) is True
    assert save_module.load()["money"] == 200


def test_add_item_stacks_and_remove_item_fails_without_enough(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.add_item("super_potion", 2)
    save_module.add_item("super_potion", 1)

    assert save_module.load()["items"]["super_potion"] == 3

    assert save_module.remove_item("super_potion", 5) is False
    assert save_module.load()["items"]["super_potion"] == 3  # não mudou nada

    assert save_module.remove_item("super_potion", 2) is True
    assert save_module.load()["items"]["super_potion"] == 1


def test_set_trainer_name_and_set_starter_persist(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.set_trainer_name("Kirito")
    save_module.set_starter("charmander")

    data = save_module.load()
    assert data["trainer_name"] == "Kirito"
    assert data["starter"] == "charmander"


def test_set_difficulty_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    assert save_module.load()["difficulty"] == "normal"

    save_module.set_difficulty("hard")
    assert save_module.load()["difficulty"] == "hard"


def test_increment_trainers_defeated_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.increment_trainers_defeated()
    save_module.increment_trainers_defeated()

    assert save_module.load()["trainers_defeated"] == 2


def test_add_completed_quest_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(save_module, "SAVE_PATH", tmp_path / "savegame.json")
    save_module.add_completed_quest("first_wins")
    save_module.add_completed_quest("first_wins")
    save_module.add_completed_quest("rock_badge")

    assert save_module.load()["quests_completed"] == ["first_wins", "rock_badge"]
