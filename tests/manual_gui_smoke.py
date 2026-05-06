"""Smoke test manual (não faz parte da suíte pytest): abre a janela do
main_gui.py com dados falsos (sem tocar na PokeAPI de verdade) e navega
pelas telas automaticamente, só pra pegar erro de layout/exceção antes de
entregar. Rodar com:

    xvfb-run -a python3.12 tests/manual_gui_smoke.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pokebattle.moves import Move
from pokebattle.pokemon import Pokemon

import main_gui


def fake_pokemon(name, types=None, hp=60, attack=60, speed=60, moves=None):
    stats = {"hp": hp, "attack": attack, "defense": 50, "sp_atk": 50, "sp_def": 50, "speed": speed}
    mon = Pokemon(name, types or ["normal"], 50, stats, moves or [Move("Tackle", "normal", 40, "physical")])
    mon.pokedex_id = name
    mon.sprite_path = None  # sem imagem de verdade nesse teste
    return mon


def main():
    app = main_gui.PokeBattleApp()

    player_team = [
        fake_pokemon("Testmander", moves=[
            Move("Ember", "fire", 40, "special"),
            Move("Scratch", "normal", 40, "physical"),
            Move("Thunder Wave", "electric", 0, "status", ailment="paralysis", ailment_chance=100),
            Move("Confuse Ray", "ghost", 0, "status", ailment="confusion", ailment_chance=100),
        ]),
        fake_pokemon("Banco1"),
    ]
    enemy_team = [fake_pokemon("Rival", attack=40)]

    app.player_team = player_team
    app.enemy_team = enemy_team
    app.potions = 3

    from pokebattle.battle import Battle
    app.battle = Battle(player_team, enemy_team)

    battle_screen = app.show_frame(main_gui.BattleScreen)
    app.update()

    # Navega pelos menus pra garantir que constroem sem quebrar.
    battle_screen._show_move_menu()
    app.update()
    battle_screen._show_action_menu()
    battle_screen._show_switch_menu(forced=False)
    app.update()
    battle_screen._show_action_menu()
    battle_screen._show_bag_menu()
    app.update()
    battle_screen._show_action_menu()
    app.update()

    # Executa um turno de verdade (golpe de status) e confere que a tela
    # de HP/log atualiza sem exceção.
    status_move = player_team[0].moves[2]
    battle_screen._player_move(status_move)
    app.update()

    # Golpe de dano de verdade: deixa a animação (pisca + número de dano
    # subindo no Canvas) rodar todos os frames sem travar nem quebrar.
    damaging_move = player_team[0].moves[0]
    battle_screen._player_move(damaging_move)
    for _ in range(20):
        app.update()
        time.sleep(0.05)

    # Troca de Pokémon de verdade (exercita Battle.switch, que agora devolve
    # uma lista de mensagens em vez de uma string só).
    battle_screen._player_switch(1, forced=False)
    app.update()

    print("OK: tela de batalha, menus, turno de status e troca.")
    app.destroy()


def test_team_select_and_end_screen():
    """Testa a tela de seleção de time e a tela final, com a PokeAPI trocada
    por funções falsas (sem rede)."""
    import pokebattle.roster as roster_module

    import pokebattle.save as save_module

    fake_species = ["bulbasaur", "charmander", "squirtle", "pikachu"]
    original_list = roster_module.list_all_species
    original_build = roster_module.build_pokemon
    original_load = save_module.load
    roster_module.list_all_species = lambda: fake_species
    roster_module.build_pokemon = lambda name, level=50: fake_pokemon(name.capitalize())
    # Onboarding (nome do treinador + inicial) já feito — vai direto pro time.
    save_module.load = lambda: {
        "pokedex_seen": [], "badges": [], "money": 0, "items": {"potion": 3},
        "trainer_name": "Ash", "starter": "bulbasaur",
    }

    try:
        app = main_gui.PokeBattleApp()  # onboarding já feito: abre a TeamSelectScreen
        app.update()
        app.after(200, app.update)
        app.update()

        screen = app.container.winfo_children()[0]
        # espera a lista carregar (roda numa thread; precisa de tempo real
        # passando pro app.after(...) da fila de polling disparar)
        for _ in range(40):
            app.update()
            time.sleep(0.05)
            if screen.all_species:
                break

        screen.chosen.append("pikachu")
        screen.team_list.insert("end", "Pikachu")
        screen.start_button.config(state="normal")
        screen._start_battle()

        for _ in range(40):
            app.update()
            time.sleep(0.05)
            if app.battle is not None:
                break

        assert app.battle is not None, "a batalha deveria ter começado"

        end_screen = app.show_frame(main_gui.EndScreen, victory=True)
        app.update()
        end_screen._play_again()
        app.update()

        print("OK: seleção de time e tela final.")
        app.destroy()
    finally:
        roster_module.list_all_species = original_list
        roster_module.build_pokemon = original_build
        save_module.load = original_load


def test_pokedex_screen():
    """Abre a tela de Pokédex com dados falsos (sem rede) e confere que a
    lista, a busca e a marcação de "visto" (via save.py) funcionam."""
    import pokebattle.roster as roster_module
    import pokebattle.save as save_module

    fake_entries = [(1, "bulbasaur"), (4, "charmander"), (7, "squirtle"), (25, "pikachu")]
    original_list = roster_module.list_all_species_with_dex_numbers
    original_load = save_module.load
    roster_module.list_all_species_with_dex_numbers = lambda: fake_entries
    save_module.load = lambda: {"pokedex_seen": ["charmander"], "badges": []}

    try:
        app = main_gui.PokeBattleApp()
        screen = app.show_frame(main_gui.PokedexScreen)
        app.update()

        for _ in range(40):
            app.update()
            time.sleep(0.05)
            if screen.all_entries:
                break
        assert screen.all_entries == fake_entries, "devia ter carregado os 4 falsos"

        # Charmander foi marcado como visto; os outros não.
        rows = screen.listbox.get(0, "end")
        assert any(row.startswith(screen.SEEN_MARK) and "Charmander" in row for row in rows)
        assert any(row.startswith(screen.UNSEEN_MARK) and "Pikachu" in row for row in rows)

        screen.search_var.set("char")
        app.update()
        assert screen.visible_entries == [(4, "charmander")]

        print("OK: tela de Pokédex, busca e marcação de visto.")
        app.destroy()
    finally:
        roster_module.list_all_species_with_dex_numbers = original_list
        save_module.load = original_load


def test_gym_screen_and_battle():
    """Abre a tela de Ginásios, desafia o primeiro (Brock) com dados falsos
    (sem rede) e confere que a batalha de ginásio abre e, ao vencer, dá a
    insígnia e o dinheiro (via save.py) sem travar nem quebrar."""
    import pokebattle.gyms as gyms_module
    import pokebattle.roster as roster_module
    import pokebattle.save as save_module

    saved = {
        "pokedex_seen": [], "badges": [], "money": 0, "items": {}, "trainers_defeated": 0,
        "quests_completed": [], "achievements_unlocked": [], "owned_pokemon": [],
        "battles_lost": 0, "avatar_color": "red", "nuzlocke": False,
    }

    def fake_load():
        return dict(saved)

    def fake_add_badge(gym_id):
        if gym_id not in saved["badges"]:
            saved["badges"].append(gym_id)
        return saved

    def fake_add_money(amount):
        saved["money"] += amount
        return saved

    def fake_increment_trainers_defeated(amount=1):
        saved["trainers_defeated"] += amount
        return saved

    def fake_add_achievement(achievement_id):
        if achievement_id not in saved["achievements_unlocked"]:
            saved["achievements_unlocked"].append(achievement_id)
        return saved

    original_load = save_module.load
    original_add_badge = save_module.add_badge
    original_add_money = save_module.add_money
    original_increment_trainers_defeated = save_module.increment_trainers_defeated
    original_add_achievement = save_module.add_achievement
    original_build_pokemon = roster_module.build_pokemon
    original_showinfo = main_gui.messagebox.showinfo
    save_module.load = fake_load
    save_module.add_badge = fake_add_badge
    save_module.add_money = fake_add_money
    save_module.increment_trainers_defeated = fake_increment_trainers_defeated
    save_module.add_achievement = fake_add_achievement
    roster_module.build_pokemon = lambda name, level=50, rng=None: fake_pokemon(
        name.capitalize(), hp=1, attack=10,
    )
    # Conquistas abrem um messagebox modal ao desbloquear — vira no-op aqui
    # (senão o script automatizado trava esperando um clique que nunca vem).
    main_gui.messagebox.showinfo = lambda *a, **k: None

    try:
        app = main_gui.PokeBattleApp()
        app.player_team = [fake_pokemon("Campeao", attack=200, moves=[Move("Golpe", "normal", 60, "physical")])]

        screen = app.show_frame(main_gui.GymScreen)
        app.update()
        assert screen.challenge_button["text"] == "Desafiar"

        screen._challenge()
        for _ in range(40):
            app.update()
            time.sleep(0.05)
            if app.battle is not None:
                break
        assert app.battle is not None, "a batalha de ginásio deveria ter começado"

        battle_screen = app.container.winfo_children()[0]
        assert isinstance(battle_screen, main_gui.BattleScreen)
        assert battle_screen.gym is gyms_module.get_gym("pewter")

        # Nocauteia o time inteiro do ginásio (2 Pokémon, 1 HP cada).
        battle_screen._player_move(app.player_team[0].moves[0])
        app.update()
        battle_screen._player_move(app.player_team[0].moves[0])
        app.update()

        assert "pewter" in saved["badges"], "devia ter ganhado a insígnia"
        assert saved["money"] == 1400, "devia ter ganhado a recompensa em dinheiro"
        assert saved["trainers_defeated"] == 1, "devia ter contado essa vitória pras missões"

        for _ in range(20):  # deixa a animação de dano terminar antes de fechar
            app.update()
            time.sleep(0.05)

        print("OK: tela de Ginásios, desafio e vitória (insígnia + dinheiro).")
        app.destroy()
    finally:
        save_module.load = original_load
        save_module.add_badge = original_add_badge
        save_module.add_money = original_add_money
        save_module.increment_trainers_defeated = original_increment_trainers_defeated
        save_module.add_achievement = original_add_achievement
        roster_module.build_pokemon = original_build_pokemon
        main_gui.messagebox.showinfo = original_showinfo


def test_victory_progression_flow():
    """Derrota um inimigo com dados falsos e confere que XP, level up,
    aprendizado de golpe (com diálogo) e evolução rodam sem travar nem
    quebrar — tudo isso pede uma janela de verdade, por isso é aqui e não
    no pytest."""
    import pokebattle.pokeapi as pokeapi_module

    fake_charmander = {
        "name": "charmander", "id": 4, "base_experience": 1,  # XP baixo: só 1 level up, não uma dezena
        "types": [{"slot": 1, "type": {"name": "fire"}}],
        "stats": [
            {"base_stat": 39, "stat": {"name": "hp"}},
            {"base_stat": 52, "stat": {"name": "attack"}},
            {"base_stat": 43, "stat": {"name": "defense"}},
            {"base_stat": 60, "stat": {"name": "special-attack"}},
            {"base_stat": 50, "stat": {"name": "special-defense"}},
            {"base_stat": 65, "stat": {"name": "speed"}},
        ],
        "moves": [{
            "move": {"name": "ember"},
            "version_group_details": [{"move_learn_method": {"name": "level-up"}, "level_learned_at": 51}],
        }],
        "sprites": {"front_default": None, "other": {"official-artwork": {"front_default": None}}},
    }
    fake_ember_move = {
        "name": "ember", "type": {"name": "fire"}, "power": 40, "accuracy": 100,
        "damage_class": {"name": "special"}, "meta": {"ailment": {"name": "none"}, "ailment_chance": 0},
    }
    fake_chain = {
        "chain": {
            "species": {"name": "charmander"},
            "evolves_to": [{
                "species": {"name": "charmeleon"},
                "evolution_details": [{"trigger": {"name": "level-up"}, "min_level": 51}],
                "evolves_to": [],
            }],
        }
    }
    fake_charmeleon = {**fake_charmander, "name": "charmeleon", "id": 5}

    original_get_pokemon = pokeapi_module.get_pokemon
    original_get_move = pokeapi_module.get_move
    original_get_species = pokeapi_module.get_species
    original_get_by_url = pokeapi_module.get_by_url
    original_askyesno = main_gui.messagebox.askyesno
    original_showinfo = main_gui.messagebox.showinfo
    original_ask_forget = main_gui.BattleScreen._ask_move_to_forget

    def fake_get_pokemon(name):
        return fake_charmeleon if name == "charmeleon" else fake_charmander

    pokeapi_module.get_pokemon = fake_get_pokemon
    pokeapi_module.get_move = lambda name: fake_ember_move
    pokeapi_module.get_species = lambda name: {"evolution_chain": {"url": "fake"}}
    pokeapi_module.get_by_url = lambda url: fake_chain
    main_gui.messagebox.askyesno = lambda *a, **k: True
    main_gui.messagebox.showinfo = lambda *a, **k: None
    main_gui.BattleScreen._ask_move_to_forget = lambda self, pokemon: 0

    try:
        app = main_gui.PokeBattleApp()

        player = fake_pokemon("Charmander", moves=[
            Move(f"Golpe{i}", "normal", 40, "physical") for i in range(4)
        ])
        player.species = "charmander"
        player.level = 50  # sobe pro 51: aprende Ember e evolui pra Charmeleon
        player.experience = 51 ** 3 - 1  # falta só 1 de XP pro próximo nível
        enemy = fake_pokemon("Rival")
        enemy.species = "charmander"
        enemy.current_hp = 1  # garante nocaute no primeiro golpe do jogador

        from pokebattle.battle import Battle
        app.player_team = [player]
        app.enemy_team = [enemy]
        app.battle = Battle(player, enemy)

        battle_screen = app.show_frame(main_gui.BattleScreen)
        app.update()

        battle_screen._player_move(player.moves[0])  # deve nocautear o inimigo de 1 HP
        app.update()

        assert player.experience > 0, "deveria ter ganhado XP"
        assert player.level == 51, "deveria ter subido de nível"
        assert player.species == "charmeleon", "deveria ter evoluído"

        # Deixa a animação de dano terminar antes de fechar a janela — senão
        # sobra um after() pendente que dispara depois do destroy() (erro
        # cosmético de teardown, mas sem isso o teste fica barulhento à toa).
        for _ in range(20):
            app.update()
            time.sleep(0.05)

        print("OK: XP, level up, aprender golpe e evolução.")
        app.destroy()
    finally:
        pokeapi_module.get_pokemon = original_get_pokemon
        pokeapi_module.get_move = original_get_move
        pokeapi_module.get_species = original_get_species
        pokeapi_module.get_by_url = original_get_by_url
        main_gui.messagebox.askyesno = original_askyesno
        main_gui.messagebox.showinfo = original_showinfo
        main_gui.BattleScreen._ask_move_to_forget = original_ask_forget


def test_mart_screen_and_bag_use():
    """Abre a Loja com dados falsos (sem rede), compra um item e confere que
    o saldo e o estoque atualizam; depois confere que a Mochila em batalha
    lista e usa esse item (cura) e reviver um companheiro desmaiado."""
    import pokebattle.save as save_module

    saved = {"pokedex_seen": [], "badges": [], "money": 1000, "items": {"potion": 1, "revive": 1}}

    def fake_load():
        return {**saved, "items": dict(saved["items"])}

    def fake_spend_money(amount):
        if saved["money"] < amount:
            return False
        saved["money"] -= amount
        return True

    def fake_add_item(item_id, qty=1):
        saved["items"][item_id] = saved["items"].get(item_id, 0) + qty
        return fake_load()

    def fake_remove_item(item_id, qty=1):
        have = saved["items"].get(item_id, 0)
        if have < qty:
            return False
        saved["items"][item_id] = have - qty
        return True

    original_load = save_module.load
    original_spend_money = save_module.spend_money
    original_add_item = save_module.add_item
    original_remove_item = save_module.remove_item
    save_module.load = fake_load
    save_module.spend_money = fake_spend_money
    save_module.add_item = fake_add_item
    save_module.remove_item = fake_remove_item

    try:
        app = main_gui.PokeBattleApp()

        mart = app.show_frame(main_gui.MartScreen)
        app.update()
        assert mart.money_label["text"] == "Dinheiro: $1000"

        mart._buy("super_potion")
        app.update()
        assert saved["money"] == 300, "devia ter descontado o preço da Super Poção"
        assert saved["items"]["super_potion"] == 1, "devia ter adicionado 1 Super Poção ao estoque"
        assert mart.money_label["text"] == "Dinheiro: $300"

        # Sem dinheiro pro Revive ($1500): o botão deve ficar desabilitado.
        revive_button, _ = mart.item_rows["revive"]
        assert str(revive_button["state"]) == "disabled"

        # Agora testa a Mochila em batalha usando os itens comprados.
        fainted = fake_pokemon("Banco1")
        fainted.current_hp = 0
        app.player_team = [fake_pokemon("Ativo"), fainted]
        app.enemy_team = [fake_pokemon("Rival")]

        from pokebattle.battle import Battle
        app.battle = Battle(app.player_team, app.enemy_team)

        battle_screen = app.show_frame(main_gui.BattleScreen)
        app.update()
        battle_screen._show_bag_menu()
        app.update()

        battle_screen._use_item("super_potion")
        app.update()
        assert saved["items"]["super_potion"] == 0, "devia ter consumido a Super Poção"

        battle_screen._show_bag_menu()
        app.update()
        battle_screen._show_revive_target_menu("revive")
        app.update()
        battle_screen._use_revive("revive", 1)  # índice 1 = "Banco1", o desmaiado
        app.update()
        assert saved["items"]["revive"] == 0, "devia ter consumido o Revive"
        assert not fainted.is_fainted, "devia ter revivido o Pokémon desmaiado"

        print("OK: Loja (compra/estoque/saldo) e uso de item/revive pela Mochila em batalha.")
        app.destroy()
    finally:
        save_module.load = original_load
        save_module.spend_money = original_spend_money
        save_module.add_item = original_add_item
        save_module.remove_item = original_remove_item


def test_onboarding_and_nickname_flow():
    """Confere o fluxo de primeira vez (nome do treinador -> inicial -> time,
    cada tela levando pra próxima e salvando no save.py) e o apelido de um
    Pokémon do time, que deve substituir o nome dele quando o time entra em
    batalha."""
    import pokebattle.save as save_module

    saved = {"pokedex_seen": [], "badges": [], "money": 0, "items": {"potion": 3},
              "trainer_name": "", "starter": ""}

    original_load = save_module.load
    original_set_trainer_name = save_module.set_trainer_name
    original_set_starter = save_module.set_starter
    original_askstring = main_gui.simpledialog.askstring
    save_module.load = lambda: dict(saved)
    save_module.set_trainer_name = lambda name: saved.__setitem__("trainer_name", name)
    save_module.set_starter = lambda species: saved.__setitem__("starter", species)

    try:
        app = main_gui.PokeBattleApp()
        app.update()
        screen = app.container.winfo_children()[0]
        assert isinstance(screen, main_gui.TrainerNameScreen), "sem nome salvo, devia abrir a tela de nome"

        screen.name_var.set("Kirito")
        app.update()
        assert str(screen.confirm_button["state"]) == "normal"
        screen._confirm()
        app.update()
        assert saved["trainer_name"] == "Kirito", "devia ter salvo o nome do treinador"

        screen = app.container.winfo_children()[0]
        assert isinstance(screen, main_gui.StarterScreen), "sem inicial salvo, devia abrir a tela de inicial"

        screen._choose("charmander")
        app.update()
        assert saved["starter"] == "charmander", "devia ter salvo o inicial escolhido"

        screen = app.container.winfo_children()[0]
        assert isinstance(screen, main_gui.TeamSelectScreen), "com onboarding feito, devia abrir a seleção de time"
        assert screen.chosen == ["charmander"], "o inicial devia entrar sozinho no time"

        # Apelida o inicial (índice 0) e confere que o texto do time_list muda.
        screen.team_list.selection_set(0)
        main_gui.simpledialog.askstring = lambda *a, **k: "Brasa"
        screen._rename_selected()
        app.update()
        assert screen.nicknames[0] == "Brasa"
        assert "Brasa" in screen.team_list.get(0)

        # O apelido precisa virar o nome de exibição quando o time é montado
        # de verdade (é isso que os painéis de batalha e os logs usam).
        fake_mon = fake_pokemon("Charmander")
        screen._teams_ready(([fake_mon], [fake_pokemon("Rival")]))
        app.update()
        assert fake_mon.name == "Brasa", "o apelido devia ter substituído o nome do Pokémon"
        assert isinstance(app.container.winfo_children()[0], main_gui.BattleScreen)

        print("OK: onboarding (nome + inicial) e apelido de Pokémon no time.")
        app.destroy()
    finally:
        save_module.load = original_load
        save_module.set_trainer_name = original_set_trainer_name
        save_module.set_starter = original_set_starter
        main_gui.simpledialog.askstring = original_askstring


def test_quest_screen():
    """Abre a tela de Missões com dados falsos (sem rede) e confere que uma
    missão de contagem mostra o progresso certo, fica reivindicável só
    depois de bater a meta, e o resgate soma o dinheiro e marca como
    cumprida sem travar nem quebrar."""
    import pokebattle.save as save_module

    saved = {"pokedex_seen": [], "badges": [], "money": 0, "items": {},
              "trainer_name": "Ash", "starter": "bulbasaur", "difficulty": "normal",
              "trainers_defeated": 0, "quests_completed": []}

    def fake_load():
        return dict(saved)

    def fake_add_money(amount):
        saved["money"] += amount
        return saved

    def fake_add_completed_quest(quest_id):
        if quest_id not in saved["quests_completed"]:
            saved["quests_completed"].append(quest_id)
        return saved

    original_load = save_module.load
    original_add_money = save_module.add_money
    original_add_completed_quest = save_module.add_completed_quest
    save_module.load = fake_load
    save_module.add_money = fake_add_money
    save_module.add_completed_quest = fake_add_completed_quest

    try:
        app = main_gui.PokeBattleApp()

        screen = app.show_frame(main_gui.QuestScreen)
        app.update()

        claim_button, progress_label = screen.quest_widgets["first_wins"]  # meta: 3 vitórias
        assert "0/3" in progress_label["text"]
        assert str(claim_button["state"]) == "disabled"

        saved["trainers_defeated"] = 3
        screen._refresh()
        app.update()
        assert str(claim_button["state"]) == "normal", "com a meta batida, devia poder reivindicar"

        import pokebattle.quests as quests_module
        screen._claim(quests_module.get_quest("first_wins"))
        app.update()

        assert saved["money"] == 500, "devia ter pago a recompensa da missão"
        assert "first_wins" in saved["quests_completed"], "devia ter marcado a missão como cumprida"
        assert str(claim_button["state"]) == "disabled", "depois de resgatada, não dá pra reivindicar de novo"

        print("OK: tela de Missões (progresso, reivindicação e recompensa).")
        app.destroy()
    finally:
        save_module.load = original_load
        save_module.add_money = original_add_money
        save_module.add_completed_quest = original_add_completed_quest


def test_new_feature_screens():
    """Abre as telas novas (Conquistas, Treino, Replays, Loja com itens
    segurados/Pokémon) e roda um turno de PvP e uma batalha com Nuzlocke e
    mega evolução — tudo com dados falsos, só pra pegar exceção de layout."""
    import pokebattle.pokeapi as pokeapi_module
    import pokebattle.roster as roster_module
    import pokebattle.save as save_module
    from pokebattle.battle import Battle

    base_save = {
        "pokedex_seen": [], "badges": [], "money": 5000, "items": {"held_leftovers": 1},
        "trainer_name": "Ash", "starter": "bulbasaur", "difficulty": "normal",
        "trainers_defeated": 0, "quests_completed": [], "achievements_unlocked": [],
        "owned_pokemon": [], "battles_lost": 0, "avatar_color": "blue", "nuzlocke": False,
    }
    original_load = save_module.load
    original_showinfo = main_gui.messagebox.showinfo
    save_module.load = lambda: dict(base_save)
    main_gui.messagebox.showinfo = lambda *a, **k: None

    try:
        app = main_gui.PokeBattleApp()

        app.show_frame(main_gui.AchievementsScreen)
        app.update()

        app.show_frame(main_gui.TrainingScreen)  # sem player_team: mostra a mensagem de "monte o time"
        app.update()
        app.player_team = [fake_pokemon("Treinado")]
        app.show_frame(main_gui.TrainingScreen)
        app.update()

        app.show_frame(main_gui.ReplayListScreen)  # sem replay nenhum salvo ainda
        app.update()

        app.show_frame(main_gui.MartScreen)  # itens segurados + loja de Pokémon
        app.update()

        print("OK: Conquistas, Treino, Replays e Loja (itens segurados + Pokémon).")

        # ---------- PvP local: um turno completo dos dois lados ----------
        p1 = fake_pokemon("Jogador1Mon", moves=[Move("Tackle", "normal", 40, "physical")])
        p2 = fake_pokemon("Jogador2Mon", moves=[Move("Tackle", "normal", 40, "physical")])
        app.battle = Battle(p1, p2)
        pvp_screen = app.show_frame(main_gui.BattleScreen, pvp=True, player_names=("Jogador 1", "Jogador 2"))
        app.update()
        pvp_screen._pvp_move_chosen(0, p1.moves[0])
        app.update()
        pvp_screen._pvp_move_chosen(1, p2.moves[0])
        for _ in range(10):
            app.update()
            time.sleep(0.02)
        print("OK: turno de PvP local (hot-seat) dos dois lados.")

        # ---------- Nuzlocke: quem desmaia é removido do time pra sempre ----------
        nuzlocke_save = dict(base_save, nuzlocke=True)
        save_module.load = lambda: dict(nuzlocke_save)
        survivor = fake_pokemon("Sobrevivente", hp=200, moves=[Move("Tackle", "normal", 100, "physical")])
        doomed = fake_pokemon("Condenado", hp=1)
        doomed.current_hp = 0
        strong_enemy = fake_pokemon("Forte", attack=999, hp=999)
        app.player_team = [survivor, doomed]
        app.enemy_team = [strong_enemy]
        app.battle = Battle([survivor, doomed], [strong_enemy])
        nuzlocke_screen = app.show_frame(main_gui.BattleScreen)
        app.update()
        assert nuzlocke_screen._nuzlocke_enabled is True
        nuzlocke_screen._player_move(survivor.moves[0])
        for _ in range(20):
            app.update()
            time.sleep(0.02)
        assert doomed not in app.player_team, "quem desmaiou devia ter sido liberado pra sempre no Nuzlocke"
        print("OK: modo Nuzlocke libera quem desmaiou.")
        save_module.load = lambda: dict(base_save)

        # ---------- mega evolução: ativa no início e reverte no fim da batalha ----------
        fake_charizard_data = {
            "name": "charizard-mega-x", "id": 10034,
            "types": [{"slot": 1, "type": {"name": "fire"}}, {"slot": 2, "type": {"name": "dragon"}}],
            "stats": [
                {"base_stat": 78, "stat": {"name": "hp"}}, {"base_stat": 130, "stat": {"name": "attack"}},
                {"base_stat": 111, "stat": {"name": "defense"}}, {"base_stat": 130, "stat": {"name": "special-attack"}},
                {"base_stat": 85, "stat": {"name": "special-defense"}}, {"base_stat": 100, "stat": {"name": "speed"}},
            ],
        }
        original_get_pokemon = pokeapi_module.get_pokemon
        pokeapi_module.get_pokemon = lambda name: fake_charizard_data
        mega_mon = fake_pokemon("Charizard", hp=200)
        mega_mon.species = "charizard"
        mega_mon.held_item = "held_mega_stone_charizardite_x"
        weak_enemy = fake_pokemon("Fraquinho", hp=1, attack=1)
        weak_enemy.current_hp = 1  # garante nocaute no primeiro golpe (hp acima é stat base, não o HP final)
        app.player_team = [mega_mon]
        app.enemy_team = [weak_enemy]
        app.battle = Battle(mega_mon, weak_enemy)
        mega_screen = app.show_frame(main_gui.BattleScreen)
        app.update()
        assert getattr(mega_mon, "is_mega", False) is True, "devia ter mega evoluído no início da batalha"
        mega_screen._player_move(mega_mon.moves[0])
        for _ in range(20):
            app.update()
            time.sleep(0.02)
        assert getattr(mega_mon, "is_mega", False) is False, "devia ter revertido a mega evolução no fim da batalha"
        pokeapi_module.get_pokemon = original_get_pokemon
        print("OK: mega evolução ativa no início e reverte no fim da batalha.")

        # ---------- torneio: bracket de 4, partidas só-IA simulam sozinhas ----------
        original_build_pokemon = roster_module.build_pokemon
        original_list_species = roster_module.list_all_species
        roster_module.build_pokemon = lambda species, level=50, rng=None: fake_pokemon(species.capitalize())
        roster_module.list_all_species = lambda: ["rattata", "pidgey", "weedle", "caterpie"]
        app.player_team = [fake_pokemon("Campeao", attack=200, hp=200)]
        app.tournament = None
        app.tournament_ai_teams = {}
        tournament_screen = app.show_frame(main_gui.TournamentScreen)
        for _ in range(20):
            app.update()
            time.sleep(0.02)
            if app.tournament_ai_teams:
                break
        app.show_frame(main_gui.TournamentScreen)  # re-renderiza já com os times prontos
        app.update()
        roster_module.build_pokemon = original_build_pokemon
        roster_module.list_all_species = original_list_species
        print("OK: tela de Torneio monta o bracket e simula as partidas só de IA.")

        app.destroy()
    finally:
        save_module.load = original_load
        main_gui.messagebox.showinfo = original_showinfo


def test_team_select_extras():
    """Avatar, equipar item segurado, Pokémon comprado, exportar/importar
    time e troca — tudo na TeamSelectScreen, com dados falsos (sem rede)."""
    import pokebattle.roster as roster_module
    import pokebattle.save as save_module

    saved = {
        "pokedex_seen": [], "badges": [], "money": 0, "items": {"held_leftovers": 2},
        "trainer_name": "Ash", "starter": "", "difficulty": "normal",
        "trainers_defeated": 0, "quests_completed": [], "achievements_unlocked": [],
        "owned_pokemon": ["mewtwo"], "battles_lost": 0, "avatar_color": "red", "nuzlocke": False,
    }

    def fake_load():
        return {**saved, "items": dict(saved["items"]), "owned_pokemon": list(saved["owned_pokemon"])}

    def fake_set_avatar_color(color_id):
        saved["avatar_color"] = color_id
        return fake_load()

    def fake_add_item(item_id, qty=1):
        saved["items"][item_id] = saved["items"].get(item_id, 0) + qty
        return fake_load()

    def fake_remove_item(item_id, qty=1):
        have = saved["items"].get(item_id, 0)
        if have < qty:
            return False
        saved["items"][item_id] = have - qty
        return True

    def fake_remove_owned_pokemon(species):
        if species not in saved["owned_pokemon"]:
            return False
        saved["owned_pokemon"].remove(species)
        return True

    original_load = save_module.load
    original_set_avatar_color = save_module.set_avatar_color
    original_add_item = save_module.add_item
    original_remove_item = save_module.remove_item
    original_remove_owned = save_module.remove_owned_pokemon
    original_build_pokemon = roster_module.build_pokemon
    original_build_move = roster_module._build_move
    save_module.load = fake_load
    save_module.set_avatar_color = fake_set_avatar_color
    save_module.add_item = fake_add_item
    save_module.remove_item = fake_remove_item
    save_module.remove_owned_pokemon = fake_remove_owned_pokemon
    def fake_build_pokemon(species, level=50, rng=None, ivs=None, nature=None):
        mon = fake_pokemon(species.capitalize())
        mon.species = species
        return mon

    roster_module.build_pokemon = fake_build_pokemon
    roster_module._build_move = lambda name: Move("Golpe", "normal", 40, "physical")

    try:
        app = main_gui.PokeBattleApp()
        screen = app.show_frame(main_gui.TeamSelectScreen)
        app.update()

        # ---------- avatar ----------
        screen._choose_avatar_color("blue")
        app.update()
        assert saved["avatar_color"] == "blue"

        # ---------- Pokémon comprado ----------
        assert screen.owned_list is not None
        screen.owned_list.selection_set(0)
        screen._add_owned_selected()
        app.update()
        assert screen.chosen == ["mewtwo"]
        assert "mewtwo" not in saved["owned_pokemon"], "devia ter saído da lista de comprados"

        # ---------- equipar item segurado ----------
        screen.team_list.selection_set(0)
        screen._equip_item_selected()
        app.update()
        dialog = self_toplevel(screen)
        # clica no primeiro botão de item disponível (Leftovers)
        _click_first_matching_button(dialog, "Leftovers")
        app.update()
        assert screen.held_item_choices.get(0) == "held_leftovers"
        assert saved["items"]["held_leftovers"] == 1, "devia ter consumido 1 Leftovers ao equipar"

        # ---------- exportar/importar time (round trip em texto) ----------
        text = main_gui.teamcodec.team_to_text([roster_module.build_pokemon("mewtwo")])
        specs = main_gui.teamcodec.text_to_specs(text)
        assert specs[0]["species"] == "mewtwo"

        # ---------- troca: exporta e reimporta um Pokémon num arquivo ----------
        import tempfile
        from pathlib import Path
        mon = roster_module.build_pokemon("mewtwo")
        mon.held_item = "held_leftovers"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "troca.json"
            main_gui.trade.export_pokemon_to_file(mon, path)
            rebuilt = main_gui.trade.import_pokemon_from_file(path)
            assert rebuilt.species == "mewtwo"
            assert rebuilt.held_item == "held_leftovers"

        print("OK: avatar, comprados, equipar item, exportar/importar time e troca.")
        app.destroy()
    finally:
        save_module.load = original_load
        save_module.set_avatar_color = original_set_avatar_color
        save_module.add_item = original_add_item
        save_module.remove_item = original_remove_item
        save_module.remove_owned_pokemon = original_remove_owned
        roster_module.build_pokemon = original_build_pokemon
        roster_module._build_move = original_build_move


def self_toplevel(widget):
    """Acha o Toplevel mais recente aberto a partir desse widget (um
    tk.Toplevel(self) vira filho de `self` na árvore de widgets do Tk,
    mesmo sendo uma janela própria)."""
    toplevels = [w for w in widget.winfo_children() if isinstance(w, main_gui.tk.Toplevel)]
    return toplevels[-1]


def _click_first_matching_button(widget, text_fragment):
    for child in widget.winfo_children():
        if isinstance(child, main_gui.tk.Button) and text_fragment in child["text"]:
            child.invoke()
            return True
        if _click_first_matching_button(child, text_fragment):
            return True
    return False


if __name__ == "__main__":
    main()
    test_team_select_and_end_screen()
    test_pokedex_screen()
    test_gym_screen_and_battle()
    test_victory_progression_flow()
    test_mart_screen_and_bag_use()
    test_onboarding_and_nickname_flow()
    test_quest_screen()
    test_new_feature_screens()
    test_team_select_extras()
