"""Testes de pokebattle/achievements.py — mesmo molde de test_quests.py."""

from pokebattle import achievements


def base_save(**overrides):
    data = {
        "pokedex_seen": [], "badges": [], "trainers_defeated": 0,
        "achievements_unlocked": [],
    }
    data.update(overrides)
    return data


def test_every_achievement_has_a_unique_id():
    ids = [a.id for a in achievements.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


def test_is_satisfied_pokedex_goal_reads_the_seen_list():
    achievement = achievements.get_achievement("young_researcher")
    assert achievements.is_satisfied(achievement, base_save(pokedex_seen=["mew"] * 9)) is False
    assert achievements.is_satisfied(achievement, base_save(pokedex_seen=["mew"] * 10)) is True


def test_is_satisfied_badges_goal_needs_all_eight():
    achievement = achievements.get_achievement("champion")
    assert achievements.is_satisfied(achievement, base_save(badges=["a"] * 7)) is False
    assert achievements.is_satisfied(achievement, base_save(badges=["a"] * 8)) is True


def test_is_satisfied_wins_goal_reads_trainers_defeated():
    achievement = achievements.get_achievement("first_win")
    assert achievements.is_satisfied(achievement, base_save(trainers_defeated=0)) is False
    assert achievements.is_satisfied(achievement, base_save(trainers_defeated=1)) is True


def test_is_satisfied_flag_goal_reads_the_context():
    achievement = achievements.get_achievement("flawless_victory")
    assert achievements.is_satisfied(achievement, base_save(), context={"no_faint_win": False}) is False
    assert achievements.is_satisfied(achievement, base_save(), context={"no_faint_win": True}) is True
    assert achievements.is_satisfied(achievement, base_save()) is False  # sem contexto nenhum


def test_is_unlocked_reads_the_save():
    achievement = achievements.get_achievement("first_win")
    assert achievements.is_unlocked(achievement, base_save()) is False
    assert achievements.is_unlocked(achievement, base_save(achievements_unlocked=["first_win"])) is True


def test_newly_unlocked_skips_achievements_already_saved():
    save_data = base_save(trainers_defeated=1, achievements_unlocked=["first_win"])
    unlocked = achievements.newly_unlocked(save_data)
    assert "first_win" not in [a.id for a in unlocked]


def test_newly_unlocked_returns_satisfied_but_unsaved_achievements():
    save_data = base_save(trainers_defeated=1)
    unlocked = achievements.newly_unlocked(save_data)
    assert "first_win" in [a.id for a in unlocked]
