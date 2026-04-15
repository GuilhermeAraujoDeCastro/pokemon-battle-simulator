"""Testes de pokebattle/quests.py — lógica pura sobre um dict de save.py,
sem tocar em disco nem em Tkinter."""

from pokebattle import gyms, quests


def base_save(**overrides):
    data = {
        "pokedex_seen": [], "badges": [], "money": 0, "items": {},
        "trainer_name": "", "starter": "", "difficulty": "normal",
        "trainers_defeated": 0, "quests_completed": [],
    }
    data.update(overrides)
    return data


def test_every_quest_has_a_unique_id():
    ids = [quest.id for quest in quests.QUESTS]
    assert len(ids) == len(set(ids))


def test_every_win_gym_quest_targets_a_real_gym():
    for quest in quests.QUESTS:
        if quest.goal_type == quests.GOAL_WIN_GYM:
            gyms.get_gym(quest.goal_target)  # levanta KeyError se o id não existir


def test_progress_for_defeat_trainers_reads_the_counter():
    quest = quests.get_quest("first_wins")
    assert quests.progress_for(quest, base_save(trainers_defeated=2)) == 2


def test_progress_for_see_pokemon_counts_the_pokedex_list():
    quest = quests.get_quest("young_researcher")
    save_data = base_save(pokedex_seen=["bulbasaur", "charmander", "squirtle"])
    assert quests.progress_for(quest, save_data) == 3


def test_progress_for_win_gym_is_1_only_with_the_badge():
    quest = quests.get_quest("rock_badge")
    assert quests.progress_for(quest, base_save(badges=[])) == 0
    assert quests.progress_for(quest, base_save(badges=["pewter"])) == 1


def test_target_for_win_gym_quest_is_always_one():
    quest = quests.get_quest("champion_challenge")
    assert quests.target_for(quest) == 1


def test_target_for_counting_quest_is_its_own_goal_number():
    quest = quests.get_quest("veteran_trainer")
    assert quests.target_for(quest) == 10


def test_is_complete_true_only_when_progress_meets_the_target():
    quest = quests.get_quest("first_wins")  # alvo: 3 vitórias
    assert quests.is_complete(quest, base_save(trainers_defeated=2)) is False
    assert quests.is_complete(quest, base_save(trainers_defeated=3)) is True
    assert quests.is_complete(quest, base_save(trainers_defeated=5)) is True


def test_is_claimed_reads_the_completed_quests_list():
    quest = quests.get_quest("first_wins")
    assert quests.is_claimed(quest, base_save(quests_completed=[])) is False
    assert quests.is_claimed(quest, base_save(quests_completed=["first_wins"])) is True


def test_is_claimable_requires_complete_and_not_yet_claimed():
    quest = quests.get_quest("first_wins")
    not_done_yet = base_save(trainers_defeated=0)
    done_but_claimed = base_save(trainers_defeated=3, quests_completed=["first_wins"])
    done_and_unclaimed = base_save(trainers_defeated=3)

    assert quests.is_claimable(quest, not_done_yet) is False
    assert quests.is_claimable(quest, done_but_claimed) is False
    assert quests.is_claimable(quest, done_and_unclaimed) is True
