#!/usr/bin/env python3
"""Simulador de Batalha Pokémon — modo gráfico (Tkinter).

Usa a PokeAPI pra buscar qualquer Pokémon (stats, tipos e golpes reais,
incluindo golpes de status) e a ilustração oficial de cada um. É preciso ter
internet na primeira vez que um Pokémon ou golpe aparece — depois disso ele
fica salvo em cache local (pasta .pokecache/, criada do lado do projeto) e
funciona sem rede.

O modo texto original (main.py, roster fixo de 41 Pokémon, zero
dependência) continua funcionando do jeito que sempre funcionou. Esse aqui é
a evolução gráfica: troca "zero dependência" por Tkinter + requests + Pillow
em troca de sprites de verdade, do Pokédex inteiro e de efeitos de status.

Como jogar:
    python3 main_gui.py
"""

import random
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import messagebox, simpledialog
from typing import Optional

from PIL import Image, ImageTk

from pokebattle import abilities, ai, gyms, items, pokeapi, progression, quests, roster, save
from pokebattle.battle import WEATHER_LABELS, Battle
from pokebattle.pokeapi import PokeApiError
from pokebattle.status import SHORT_LABEL

WEATHER_EMOJI = {"sun": "☀️", "rain": "🌧️", "sandstorm": "🏜️", "hail": "❄️"}

# Os 3 iniciais clássicos — escolha única no começo do jogo, salva pro save.py.
STARTERS = [
    ("bulbasaur", "Planta/Veneno — equilibrado, fácil de cuidar."),
    ("charmander", "Fogo — ofensivo, evolui pra um dos favoritos dos fãs."),
    ("squirtle", "Água — defensivo, aguenta bem os primeiros combates."),
]

TEAM_SIZE = 6
SPRITE_SIZE = (200, 200)

BG = "#1f2733"
PANEL_BG = "#2b3648"
FG = "#f2f2f2"
MUTED_FG = "#9aa5b8"
ACCENT = "#ffcb05"  # amarelo Pikachu
HP_GREEN = "#59c135"
HP_YELLOW = "#f2c14e"
HP_RED = "#e34b4b"

FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_HEADING = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 11)


def hp_color(current: int, max_hp: int) -> str:
    ratio = 0 if max_hp <= 0 else current / max_hp
    if ratio > 0.5:
        return HP_GREEN
    if ratio > 0.2:
        return HP_YELLOW
    return HP_RED


def load_sprite(path):
    """Abre uma imagem de disco como PhotoImage do Tkinter, ou None se não
    tiver imagem (a PokeAPI não achou sprite, ou o download falhou)."""
    if not path:
        return None
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail(SPRITE_SIZE)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None


def run_in_background(app, work, on_done, on_error=None):
    """Roda `work()` numa thread separada pra não travar a janela esperando
    a PokeAPI, e chama `on_done(resultado)`/`on_error(exc)` de volta na
    thread principal quando terminar (widgets do Tkinter só podem ser
    tocados na thread principal)."""
    result_box = {}

    def target():
        try:
            result_box["value"] = work()
        except Exception as exc:  # noqa: BLE001 — qualquer erro vira mensagem pro jogador
            result_box["error"] = exc
        finally:
            result_box["done"] = True

    threading.Thread(target=target, daemon=True).start()

    def poll():
        if not app.winfo_exists():
            return  # a janela foi fechada enquanto isso rodava — não faz nada
        if not result_box.get("done"):
            app.after(80, poll)
            return
        if "error" in result_box:
            if on_error:
                on_error(result_box["error"])
        else:
            on_done(result_box["value"])

    poll()


FLASH_COLOR = "#ff4d4d"


class PokemonPanel:
    """Sprite + nome + nível + status + barra de HP de um dos lados da
    batalha, com a animação de golpe (painel pisca + número de dano sobe e
    some, num Canvas dedicado)."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=PANEL_BG, padx=18, pady=14)
        self.image_label = tk.Label(self.frame, bg=PANEL_BG)
        self.image_label.pack()
        self.name_label = tk.Label(self.frame, bg=PANEL_BG, fg=FG, font=FONT_HEADING)
        self.name_label.pack(pady=(6, 0))
        self.ability_label = tk.Label(self.frame, bg=PANEL_BG, fg=MUTED_FG, font=("Segoe UI", 9, "italic"))
        self.ability_label.pack()
        self.status_label = tk.Label(self.frame, bg=PANEL_BG, fg=ACCENT, font=("Segoe UI", 10, "bold"))
        self.status_label.pack()
        self.popup_canvas = tk.Canvas(self.frame, width=180, height=26, bg=PANEL_BG, highlightthickness=0)
        self.popup_canvas.pack()
        self.hp_canvas = tk.Canvas(self.frame, width=180, height=16, bg="#0d1117", highlightthickness=0)
        self.hp_canvas.pack(pady=4)
        self.hp_text = tk.Label(self.frame, bg=PANEL_BG, fg=MUTED_FG, font=FONT_MONO)
        self.hp_text.pack()
        self._photo = None  # segura a referência: sem isso o Tkinter descarta a imagem
        # Widgets cuja cor de fundo pisca junto quando esse lado apanha.
        self._flashable = [
            self.frame, self.image_label, self.name_label,
            self.ability_label, self.status_label, self.popup_canvas,
        ]

    def update(self, pokemon, photo):
        self._photo = photo
        self.image_label.config(image=photo)
        self.name_label.config(text=f"{pokemon.name}  Lv.{pokemon.level}")
        self.ability_label.config(text=abilities.display_name(getattr(pokemon, "ability", None)))
        self.status_label.config(text=SHORT_LABEL.get(pokemon.status, ""))
        self._draw_hp_bar(pokemon.current_hp, pokemon.max_hp)
        self.hp_text.config(text=f"{pokemon.current_hp}/{pokemon.max_hp} HP")

    def _draw_hp_bar(self, current, max_hp):
        width = 180
        ratio = 0 if max_hp <= 0 else max(0.0, current / max_hp)
        self.hp_canvas.delete("all")
        self.hp_canvas.create_rectangle(0, 0, width, 16, fill="#0d1117", outline="")
        self.hp_canvas.create_rectangle(0, 0, width * ratio, 16, fill=hp_color(current, max_hp), outline="")
        self.hp_canvas.create_rectangle(0, 0, width - 1, 15, outline="#4b5670")

    # ---------- animação de golpe ----------
    def play_hit(self, damage: int) -> None:
        """Painel pisca de vermelho e o número do dano sobe e some — chamado
        sempre que esse lado perde HP num turno."""
        self._flash(step=4)
        self._popup_damage(damage)

    def _flash(self, step: int) -> None:
        if not self.frame.winfo_exists():
            return
        color = FLASH_COLOR if step % 2 == 0 else PANEL_BG
        for widget in self._flashable:
            widget.config(bg=color)
        if step > 0:
            self.frame.after(70, lambda: self._flash(step - 1))

    def _popup_damage(self, damage: int) -> None:
        if not self.popup_canvas.winfo_exists():
            return
        self.popup_canvas.delete("all")
        text_id = self.popup_canvas.create_text(
            90, 20, text=f"-{damage}", fill=HP_RED, font=("Segoe UI", 13, "bold"),
        )
        self._rise_popup(text_id, frames_left=16)

    def _rise_popup(self, text_id: int, frames_left: int) -> None:
        if not self.popup_canvas.winfo_exists() or text_id not in self.popup_canvas.find_all():
            return  # o canvas sumiu (troca de tela) ou o texto já foi apagado
        if frames_left <= 0:
            self.popup_canvas.delete(text_id)
            return
        self.popup_canvas.move(text_id, 0, -1)
        if frames_left <= 5:  # nos últimos frames, "some" ficando cada vez mais claro
            fade = ["#e34b4b", "#c96b6b", "#a98080", "#8a8a8a", "#6b6b6b"][5 - frames_left]
            self.popup_canvas.itemconfig(text_id, fill=fade)
        self.popup_canvas.after(45, lambda: self._rise_popup(text_id, frames_left - 1))


class PokeBattleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Batalha Pokémon")
        self.geometry("980x720")
        self.minsize(860, 640)
        self.configure(bg=BG)

        self.player_team = []
        self.enemy_team = []
        self.battle = None
        self._photo_cache = {}

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self._show_initial_frame()

    def _show_initial_frame(self):
        """Primeira tela do app: nome do treinador e Pokémon inicial só são
        perguntados uma vez (ficam salvos no save.py); depois disso, vai
        direto pra seleção de time."""
        data = save.load()
        if not data.get("trainer_name"):
            self.show_frame(TrainerNameScreen)
        elif not data.get("starter"):
            self.show_frame(StarterScreen)
        else:
            self.show_frame(TeamSelectScreen)

    def go_to_next_onboarding_step(self):
        """Chamado pela TrainerNameScreen depois de salvar o nome: segue pro
        próximo passo que ainda falta (inicial ou, se já tiver, o time)."""
        if not save.load().get("starter"):
            self.show_frame(StarterScreen)
        else:
            self.show_frame(TeamSelectScreen)

    def show_frame(self, frame_cls, **kwargs):
        for child in self.container.winfo_children():
            child.destroy()
        frame = frame_cls(self.container, self, **kwargs)
        frame.pack(fill="both", expand=True)
        return frame

    def run_in_background(self, work, on_done, on_error=None):
        run_in_background(self, work, on_done, on_error)

    def photo_for(self, pokemon):
        key = getattr(pokemon, "pokedex_id", pokemon.name)
        if key not in self._photo_cache:
            self._photo_cache[key] = load_sprite(getattr(pokemon, "sprite_path", None))
        return self._photo_cache[key]


class TrainerNameScreen(tk.Frame):
    """Primeira tela do jogo: pede o nome do treinador, perguntado só uma
    vez e salvo no save.py."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Bem-vindo(a)!", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(60, 8))
        tk.Label(self, text="Como é o seu nome de treinador?", bg=BG, fg=FG, font=FONT_BODY).pack(pady=(0, 12))

        self.name_var = tk.StringVar()
        self.name_var.trace_add("write", self._on_change)
        entry = tk.Entry(self, textvariable=self.name_var, width=24, font=FONT_HEADING, justify="center")
        entry.pack()
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self._confirm())

        self.confirm_button = tk.Button(
            self, text="Confirmar", font=FONT_HEADING, bg=ACCENT, state="disabled", command=self._confirm,
        )
        self.confirm_button.pack(pady=20)

    def _on_change(self, *_args):
        self.confirm_button.config(state="normal" if self.name_var.get().strip() else "disabled")

    def _confirm(self):
        name = self.name_var.get().strip()
        if not name:
            return
        save.set_trainer_name(name)
        self.app.go_to_next_onboarding_step()


class StarterScreen(tk.Frame):
    """Escolha do Pokémon inicial: só acontece uma vez, e a partir daí ele
    entra sozinho no time toda vez que a tela de seleção abre."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Escolha seu Pokémon inicial", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(48, 20))

        row = tk.Frame(self, bg=BG)
        row.pack()
        for species, description in STARTERS:
            card = tk.Frame(row, bg=PANEL_BG, padx=16, pady=16)
            card.pack(side="left", padx=12)
            tk.Label(card, text=roster.display_name(species), bg=PANEL_BG, fg=FG, font=FONT_HEADING).pack()
            tk.Label(
                card, text=description, bg=PANEL_BG, fg=MUTED_FG, font=FONT_BODY, wraplength=160, justify="left",
            ).pack(pady=6)
            tk.Button(
                card, text="Escolher", font=FONT_BODY, bg=ACCENT,
                command=lambda s=species: self._choose(s),
            ).pack()

    def _choose(self, species):
        save.set_starter(species)
        self.app.show_frame(TeamSelectScreen)


class TeamSelectScreen(tk.Frame):
    VISIBLE_LIMIT = 200

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self.all_species = None
        self.visible_species = []
        self.chosen = []
        self.nicknames = {}  # índice em self.chosen -> apelido escolhido pelo jogador

        save_data = save.load()
        trainer_name = save_data.get("trainer_name")
        title = f"Monte seu time, {trainer_name}!" if trainer_name else "Monte seu time"
        tk.Label(self, text=title, font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        self.status_label = tk.Label(self, text="Carregando lista de Pokémon...", bg=BG, fg=MUTED_FG)
        self.status_label.pack()

        difficulty_frame = tk.Frame(self, bg=BG)
        difficulty_frame.pack(pady=(4, 0))
        tk.Label(difficulty_frame, text="Dificuldade da IA:", bg=BG, fg=FG, font=FONT_BODY).pack(side="left")
        self.difficulty_var = tk.StringVar(value=save_data.get("difficulty", "normal"))
        for level in ai.DIFFICULTIES:
            tk.Radiobutton(
                difficulty_frame, text=ai.DIFFICULTY_LABELS[level], variable=self.difficulty_var, value=level,
                bg=BG, fg=FG, selectcolor=PANEL_BG, activebackground=BG, font=FONT_BODY,
                command=lambda lvl=level: save.set_difficulty(lvl),
            ).pack(side="left", padx=4)

        search_frame = tk.Frame(self, bg=BG)
        search_frame.pack(pady=12)
        tk.Label(search_frame, text="Buscar:", bg=BG, fg=FG, font=FONT_BODY).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        entry = tk.Entry(search_frame, textvariable=self.search_var, width=32, font=FONT_BODY)
        entry.pack(side="left", padx=8)
        entry.focus_set()

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=12)

        list_frame = tk.Frame(body, bg=BG)
        list_frame.pack(side="left", fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, activestyle="none", font=FONT_BODY)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Double-Button-1>", self._add_selected)

        team_frame = tk.Frame(body, bg=BG, width=240)
        team_frame.pack(side="left", fill="y", padx=(24, 0))
        team_frame.pack_propagate(False)
        tk.Label(team_frame, text=f"Seu time (até {TEAM_SIZE})", bg=BG, fg=FG, font=FONT_HEADING).pack()
        self.team_list = tk.Listbox(team_frame, height=TEAM_SIZE, font=FONT_BODY)
        self.team_list.pack(pady=8, fill="x")
        tk.Button(team_frame, text="Adicionar >>", command=self._add_selected, font=FONT_BODY).pack(fill="x")
        tk.Button(
            team_frame, text="Apelidar selecionado", command=self._rename_selected, font=FONT_BODY,
        ).pack(fill="x", pady=(4, 0))

        buttons_row = tk.Frame(self, bg=BG)
        buttons_row.pack(pady=16)
        self.start_button = tk.Button(
            buttons_row, text="Começar batalha!", state="disabled", font=FONT_HEADING,
            bg=ACCENT, command=self._start_battle,
        )
        self.start_button.pack(side="left", padx=6)
        tk.Button(
            buttons_row, text="Pokédex", font=FONT_HEADING,
            command=lambda: self.app.show_frame(PokedexScreen),
        ).pack(side="left", padx=6)
        tk.Button(
            buttons_row, text="Ginásios", font=FONT_HEADING,
            command=lambda: self.app.show_frame(GymScreen),
        ).pack(side="left", padx=6)
        tk.Button(
            buttons_row, text="Loja", font=FONT_HEADING,
            command=lambda: self.app.show_frame(MartScreen),
        ).pack(side="left", padx=6)
        tk.Button(
            buttons_row, text="Missões", font=FONT_HEADING,
            command=lambda: self.app.show_frame(QuestScreen),
        ).pack(side="left", padx=6)

        starter = save_data.get("starter")
        if starter:
            self._add_species(starter)

        self.app.run_in_background(roster.list_all_species, self._species_loaded, self._species_load_failed)

    def _species_loaded(self, species):
        self.all_species = species
        self.status_label.config(text=f"{len(species)} Pokémon disponíveis. Digite pra filtrar.")
        self._refresh_listbox(species[: self.VISIBLE_LIMIT])

    def _species_load_failed(self, exc):
        self.status_label.config(
            text="Não consegui carregar a lista de Pokémon. Verifique sua internet e tente de novo."
        )

    def _refresh_listbox(self, names):
        self.visible_species = names
        self.listbox.delete(0, tk.END)
        for name in names:
            self.listbox.insert(tk.END, roster.display_name(name))

    def _on_search_changed(self, *_args):
        if not self.all_species:
            return
        query = self.search_var.get().strip().lower()
        if query:
            matches = [s for s in self.all_species if query in s.lower()]
        else:
            matches = self.all_species[: self.VISIBLE_LIMIT]
        self._refresh_listbox(matches[: self.VISIBLE_LIMIT])

    def _add_selected(self, *_args):
        selection = self.listbox.curselection()
        if not selection:
            return
        self._add_species(self.visible_species[selection[0]])

    def _add_species(self, species):
        if len(self.chosen) >= TEAM_SIZE or species in self.chosen:
            return
        self.chosen.append(species)
        self.team_list.insert(tk.END, roster.display_name(species))
        self.start_button.config(state="normal")

    def _rename_selected(self):
        """Apelida o Pokémon selecionado no time — o apelido substitui o
        nome de exibição a partir do momento em que o time entra em
        batalha (Pokemon.name é o que os logs e painéis mostram)."""
        selection = self.team_list.curselection()
        if not selection:
            return
        index = selection[0]
        species = self.chosen[index]
        default_name = roster.display_name(species)
        current = self.nicknames.get(index, default_name)
        nickname = simpledialog.askstring(
            "Apelido", f"Apelido para {default_name}:", initialvalue=current, parent=self,
        )
        if nickname is None:
            return
        nickname = nickname.strip()
        self.team_list.delete(index)
        if nickname and nickname != default_name:
            self.nicknames[index] = nickname
            self.team_list.insert(index, f"{nickname} ({default_name})")
        else:
            self.nicknames.pop(index, None)
            self.team_list.insert(index, default_name)

    def _start_battle(self):
        if not self.chosen or not self.all_species:
            return
        self.start_button.config(state="disabled", text="Carregando time...")
        self.status_label.config(text="Buscando dados na PokeAPI (só demora na primeira vez de cada um)...")
        chosen = list(self.chosen)
        species_pool = list(self.all_species)

        def build_teams():
            enemy_species = random.sample(species_pool, k=min(TEAM_SIZE, len(species_pool)))

            def safe_build(name):
                try:
                    return roster.build_pokemon(name)
                except (PokeApiError, KeyError, ValueError):
                    # forma rara com dados incompletos — troca por outra espécie
                    fallback = random.choice(species_pool)
                    return roster.build_pokemon(fallback)

            with ThreadPoolExecutor(max_workers=4) as pool:
                player_team = list(pool.map(safe_build, chosen))
                enemy_team = list(pool.map(safe_build, enemy_species))
            return player_team, enemy_team

        self.app.run_in_background(build_teams, self._teams_ready, self._team_build_failed)

    def _team_build_failed(self, exc):
        self.status_label.config(text=f"Não consegui montar o time: {exc}")
        self.start_button.config(state="normal", text="Começar batalha!")

    def _teams_ready(self, teams):
        player_team, enemy_team = teams
        for index, mon in enumerate(player_team):
            nickname = self.nicknames.get(index)
            if nickname:
                mon.name = nickname
        self.app.player_team = player_team
        self.app.enemy_team = enemy_team
        self.app.battle = Battle(player_team, enemy_team)
        save.mark_seen([mon.species for mon in player_team + enemy_team if hasattr(mon, "species")])
        self.app.show_frame(BattleScreen)


class PokedexScreen(tk.Frame):
    """Lista todos os Pokémon da PokeAPI, marcando quais já apareceram numa
    batalha (visto), com a mesma busca da tela de time."""

    VISIBLE_LIMIT = 200
    SEEN_MARK = "✓"
    UNSEEN_MARK = "—"

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self.all_entries = None  # lista de (dex_id, species) depois de carregar
        self.visible_entries = []
        self.seen = set(save.load()["pokedex_seen"])

        tk.Label(self, text="Pokédex", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        self.status_label = tk.Label(self, text="Carregando lista de Pokémon...", bg=BG, fg=MUTED_FG)
        self.status_label.pack()

        search_frame = tk.Frame(self, bg=BG)
        search_frame.pack(pady=12)
        tk.Label(search_frame, text="Buscar:", bg=BG, fg=FG, font=FONT_BODY).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        entry = tk.Entry(search_frame, textvariable=self.search_var, width=32, font=FONT_BODY)
        entry.pack(side="left", padx=8)
        entry.focus_set()

        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=24, pady=12)
        self.listbox = tk.Listbox(list_frame, activestyle="none", font=FONT_MONO)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        tk.Button(
            self, text="Voltar", font=FONT_HEADING,
            command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))

        self.app.run_in_background(
            roster.list_all_species_with_dex_numbers, self._species_loaded, self._species_load_failed,
        )

    def _species_loaded(self, entries):
        self.all_entries = entries
        self._update_status()
        self._refresh_listbox(entries[: self.VISIBLE_LIMIT])

    def _species_load_failed(self, exc):
        self.status_label.config(
            text="Não consegui carregar a Pokédex. Verifique sua internet e tente de novo."
        )

    def _update_status(self):
        total = len(self.all_entries)
        seen_count = sum(1 for _, species in self.all_entries if species in self.seen)
        self.status_label.config(text=f"{seen_count}/{total} vistos. Digite pra filtrar.")

    def _refresh_listbox(self, entries):
        self.visible_entries = entries
        self.listbox.delete(0, tk.END)
        for dex_id, species in entries:
            mark = self.SEEN_MARK if species in self.seen else self.UNSEEN_MARK
            self.listbox.insert(tk.END, f"{mark}  #{dex_id:04d}  {roster.display_name(species)}")

    def _on_search_changed(self, *_args):
        if not self.all_entries:
            return
        query = self.search_var.get().strip().lower()
        if query:
            matches = [e for e in self.all_entries if query in e[1].lower()]
        else:
            matches = self.all_entries[: self.VISIBLE_LIMIT]
        self._refresh_listbox(matches[: self.VISIBLE_LIMIT])


class GymScreen(tk.Frame):
    """Lista os 8 ginásios em ordem fixa, marcando quais já caíram, e deixa
    desafiar só o próximo ainda não vencido (igual aos jogos)."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        save_data = save.load()
        self.badges = save_data["badges"]
        self.money = save_data["money"]

        tk.Label(self, text="Ginásios", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        tk.Label(self, text=f"Dinheiro: ${self.money}", bg=BG, fg=MUTED_FG, font=FONT_BODY).pack()

        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=48, pady=16)

        next_gym = gyms.next_gym(self.badges)
        for gym in gyms.GYMS:
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=12, pady=8)
            row.pack(fill="x", pady=4)
            won = gym.id in self.badges
            mark = "✓" if won else ("▶" if gym is next_gym else "🔒")
            text = f"{mark}  {gym.city} — Líder {gym.leader} ({gym.gym_type})  •  {gym.badge_name}"
            tk.Label(row, text=text, bg=PANEL_BG, fg=FG if (won or gym is next_gym) else MUTED_FG,
                     font=FONT_BODY, anchor="w").pack(side="left", fill="x", expand=True)
            if gym is next_gym:
                self.challenge_button = tk.Button(
                    row, text="Desafiar", font=FONT_BODY, bg=ACCENT, command=self._challenge,
                )
                self.challenge_button.pack(side="right")

        self.status_label = tk.Label(self, text="", bg=BG, fg=MUTED_FG, font=FONT_BODY)
        self.status_label.pack()

        tk.Button(
            self, text="Voltar", font=FONT_HEADING,
            command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))

    def _challenge(self):
        if not self.app.player_team:
            messagebox.showinfo(
                "Sem time", "Monte seu time na tela principal antes de desafiar um ginásio.", parent=self,
            )
            return
        gym = gyms.next_gym(self.badges)
        if gym is None:
            return

        # Cura o time de graça antes do ginásio, como um Centro Pokémon.
        for mon in self.app.player_team:
            mon.cure_status()
            mon.current_hp = mon.max_hp

        self.challenge_button.config(state="disabled", text="Carregando time do ginásio...")
        self.status_label.config(text="Buscando o time do ginásio na PokeAPI...")
        self.app.run_in_background(
            lambda: gyms.build_gym_team(gym), lambda team: self._start_gym_battle(gym, team), self._build_failed,
        )

    def _build_failed(self, exc):
        self.status_label.config(text=f"Não consegui montar o time do ginásio: {exc}")
        self.challenge_button.config(state="normal", text="Desafiar")

    def _start_gym_battle(self, gym, enemy_team):
        self.app.enemy_team = enemy_team
        self.app.battle = Battle(self.app.player_team, enemy_team)
        self.app.show_frame(BattleScreen, gym=gym)


class MartScreen(tk.Frame):
    """PokéMart: mostra o dinheiro atual e deixa comprar qualquer item do
    catálogo, um por vez, atualizando o saldo na hora."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self.item_rows = {}

        tk.Label(self, text="PokéMart", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        self.money_label = tk.Label(self, text="", bg=BG, fg=MUTED_FG, font=FONT_BODY)
        self.money_label.pack()

        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=48, pady=16)

        for item in items.CATALOG:
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=12, pady=8)
            row.pack(fill="x", pady=4)
            text = f"{item.name} — ${item.price}  •  {item.description}"
            tk.Label(row, text=text, bg=PANEL_BG, fg=FG, font=FONT_BODY, anchor="w").pack(
                side="left", fill="x", expand=True,
            )
            owned_label = tk.Label(row, text="", bg=PANEL_BG, fg=MUTED_FG, font=FONT_BODY)
            owned_label.pack(side="right", padx=(0, 12))
            buy_button = tk.Button(
                row, text="Comprar", font=FONT_BODY, bg=ACCENT,
                command=lambda item_id=item.id: self._buy(item_id),
            )
            buy_button.pack(side="right")
            self.item_rows[item.id] = (buy_button, owned_label)

        tk.Button(
            self, text="Voltar", font=FONT_HEADING,
            command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))

        self._refresh()

    def _refresh(self):
        data = save.load()
        money = data["money"]
        owned = data["items"]
        self.money_label.config(text=f"Dinheiro: ${money}")
        for item in items.CATALOG:
            buy_button, owned_label = self.item_rows[item.id]
            buy_button.config(state="normal" if money >= item.price else "disabled")
            owned_label.config(text=f"Você tem: {owned.get(item.id, 0)}")

    def _buy(self, item_id: str):
        item = items.get_item(item_id)
        if not save.spend_money(item.price):
            return
        save.add_item(item_id)
        self._refresh()


class QuestScreen(tk.Frame):
    """Lista os NPCs com missão (curados em quests.py): fala do NPC,
    progresso atual e um botão pra resgatar a recompensa quando cumprida."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self.quest_widgets = {}  # quest.id -> (botão, label de progresso)

        tk.Label(self, text="Missões", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))

        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=48, pady=16)

        for quest in quests.QUESTS:
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=12, pady=10)
            row.pack(fill="x", pady=4)

            info = tk.Frame(row, bg=PANEL_BG)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=quest.npc_name, bg=PANEL_BG, fg=FG, font=FONT_HEADING, anchor="w").pack(fill="x")
            tk.Label(
                info, text=f"“{quest.dialogue}”", bg=PANEL_BG, fg=MUTED_FG,
                font=("Segoe UI", 10, "italic"), anchor="w", justify="left", wraplength=480,
            ).pack(fill="x")
            progress_label = tk.Label(info, bg=PANEL_BG, fg=FG, font=FONT_BODY, anchor="w")
            progress_label.pack(fill="x", pady=(4, 0))

            claim_button = tk.Button(
                row, text="Reivindicar", font=FONT_BODY, bg=ACCENT,
                command=lambda q=quest: self._claim(q),
            )
            claim_button.pack(side="right")
            self.quest_widgets[quest.id] = (claim_button, progress_label)

        tk.Button(
            self, text="Voltar", font=FONT_HEADING,
            command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))

        self._refresh()

    def _refresh(self):
        data = save.load()
        for quest in quests.QUESTS:
            claim_button, progress_label = self.quest_widgets[quest.id]
            reward_text = f"Recompensa: ${quest.reward_money}"
            if quests.is_claimed(quest, data):
                progress_label.config(text=f"✓ Cumprida! {reward_text}")
                claim_button.config(text="Recebida", state="disabled")
            elif quests.is_complete(quest, data):
                progress_label.config(text=f"Concluída! {reward_text}")
                claim_button.config(text="Reivindicar", state="normal")
            else:
                if quest.goal_type == quests.GOAL_WIN_GYM:
                    gym = gyms.get_gym(quest.goal_target)
                    objective = f"Vença o ginásio de {gym.city}"
                else:
                    objective = f"Progresso: {quests.progress_for(quest, data)}/{quests.target_for(quest)}"
                progress_label.config(text=f"{objective}  •  {reward_text}")
                claim_button.config(text="Reivindicar", state="disabled")

    def _claim(self, quest):
        data = save.load()
        if not quests.is_claimable(quest, data):
            return
        save.add_money(quest.reward_money)
        save.add_completed_quest(quest.id)
        self._refresh()


class BattleScreen(tk.Frame):
    def __init__(self, parent, app: PokeBattleApp, gym: Optional[gyms.Gym] = None):
        super().__init__(parent, bg=BG)
        self.app = app
        self.battle: Battle = app.battle
        self.gym = gym  # None numa batalha comum; o Gym sendo desafiado, se for uma
        self._xp_awarded_for = set()  # ids dos inimigos já derrotados (evita XP em dobro)

        self.difficulty = save.load().get("difficulty", "normal")
        # Ginásios têm personalidade curada (gyms.py); fora deles, sorteia uma por batalha.
        self.enemy_personality = gym.personality if gym else random.choice(ai.PERSONALITIES)

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", pady=(16, 0))
        self.enemy_panel = PokemonPanel(top)
        self.enemy_panel.frame.pack(side="left", padx=32)

        self.weather_label = tk.Label(self, text="", bg=BG, fg=ACCENT, font=FONT_HEADING)
        self.weather_label.pack()

        middle = tk.Frame(self, bg=BG)
        middle.pack(fill="x")
        self.player_panel = PokemonPanel(middle)
        self.player_panel.frame.pack(side="right", padx=32)

        self.log_text = tk.Text(
            self, height=8, bg="#10151d", fg=FG, wrap="word", state="disabled", font=FONT_MONO,
        )
        self.log_text.pack(fill="both", expand=True, padx=24, pady=12)

        self.menu_frame = tk.Frame(self, bg=BG)
        self.menu_frame.pack(fill="x", padx=24, pady=(0, 20))

        self._refresh_panels()
        if self.gym:
            self._log(f"Líder {self.gym.leader} te desafiou pela {self.gym.badge_name}!")
        else:
            self._log(f"Um treinador adversário te desafiou com {self.battle.enemy.name}!")
        self._log(*self.battle.intro_log)
        self._show_action_menu()

    # ---------- desenho ----------
    def _refresh_panels(self):
        self.enemy_panel.update(self.battle.enemy, self.app.photo_for(self.battle.enemy))
        self.player_panel.update(self.battle.player, self.app.photo_for(self.battle.player))
        weather = self.battle.weather
        if weather:
            emoji = WEATHER_EMOJI.get(weather, "")
            self.weather_label.config(text=f"{emoji} Tempo {WEATHER_LABELS[weather]} ({self.battle.weather_turns})")
        else:
            self.weather_label.config(text="")

    def _log(self, *lines):
        self.log_text.config(state="normal")
        for line in lines:
            self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _clear_menu(self):
        for child in self.menu_frame.winfo_children():
            child.destroy()

    # ---------- menus ----------
    def _show_action_menu(self):
        self._clear_menu()
        actions = [
            ("Lutar", self._show_move_menu),
            ("Pokémon", lambda: self._show_switch_menu(forced=False)),
            ("Mochila", self._show_bag_menu),
            ("Fugir", self._flee),
        ]
        for i, (label, command) in enumerate(actions):
            tk.Button(
                self.menu_frame, text=label, width=16, font=FONT_HEADING, bg=ACCENT, command=command,
            ).grid(row=i // 2, column=i % 2, padx=6, pady=6, sticky="ew")
        self.menu_frame.grid_columnconfigure(0, weight=1)
        self.menu_frame.grid_columnconfigure(1, weight=1)

    def _show_move_menu(self):
        self._clear_menu()
        for move in self.battle.player.moves:
            power_text = "—" if move.power == 0 else str(move.power)
            text = f"{move.name}   ({move.type}, poder {power_text}, precisão {move.accuracy}%)"
            tk.Button(
                self.menu_frame, text=text, anchor="w", font=FONT_BODY,
                command=lambda m=move: self._player_move(m),
            ).pack(fill="x", pady=2)
        tk.Button(self.menu_frame, text="Voltar", font=FONT_BODY, command=self._show_action_menu).pack(pady=(8, 0))

    def _show_switch_menu(self, forced):
        self._clear_menu()
        if forced:
            tk.Label(
                self.menu_frame, text="Escolha o próximo Pokémon:", bg=BG, fg=FG, font=FONT_HEADING,
            ).pack(pady=(0, 6))
        for i, mon in enumerate(self.app.player_team):
            is_active = mon is self.battle.player
            disabled = mon.is_fainted or is_active
            label = f"{mon.name}   {mon.current_hp}/{mon.max_hp} HP"
            if mon.is_fainted:
                label += "  (desmaiou)"
            elif is_active:
                label += "  (em campo)"
            tk.Button(
                self.menu_frame, text=label, anchor="w", font=FONT_BODY,
                state="disabled" if disabled else "normal",
                command=lambda idx=i: self._player_switch(idx, forced),
            ).pack(fill="x", pady=2)
        if not forced:
            tk.Button(self.menu_frame, text="Voltar", font=FONT_BODY, command=self._show_action_menu).pack(pady=(8, 0))

    def _show_bag_menu(self):
        self._clear_menu()
        inventory = save.load()["items"]
        active = self.battle.player
        has_any_item = False
        for item in items.CATALOG:
            qty = inventory.get(item.id, 0)
            if qty <= 0:
                continue
            has_any_item = True
            if item.revive:
                usable = any(mon.is_fainted for mon in self.app.player_team)
            else:
                usable = not active.is_fainted
            text = f"{item.name} ({item.description}) — restam {qty}"
            tk.Button(
                self.menu_frame, text=text, anchor="w", font=FONT_BODY,
                state="normal" if usable else "disabled",
                command=lambda item_id=item.id: self._use_item(item_id),
            ).pack(fill="x", pady=2)
        if not has_any_item:
            tk.Label(
                self.menu_frame, text="Mochila vazia. Visite a loja antes da próxima batalha!",
                bg=BG, fg=MUTED_FG, font=FONT_BODY,
            ).pack(pady=4)
        tk.Button(self.menu_frame, text="Voltar", font=FONT_BODY, command=self._show_action_menu).pack(pady=(8, 0))

    def _show_revive_target_menu(self, item_id):
        self._clear_menu()
        tk.Label(
            self.menu_frame, text="Reviver qual Pokémon?", bg=BG, fg=FG, font=FONT_HEADING,
        ).pack(pady=(0, 6))
        for i, mon in enumerate(self.app.player_team):
            if not mon.is_fainted:
                continue
            tk.Button(
                self.menu_frame, text=mon.name, anchor="w", font=FONT_BODY,
                command=lambda idx=i: self._use_revive(item_id, idx),
            ).pack(fill="x", pady=2)
        tk.Button(self.menu_frame, text="Voltar", font=FONT_BODY, command=self._show_bag_menu).pack(pady=(8, 0))

    # ---------- ações do jogador ----------
    def _player_move(self, move):
        self._run_turn(("move", move))

    def _player_switch(self, index, forced):
        if forced:
            messages = self.battle.switch("player", index)
            self._log(*messages)
            self._refresh_panels()
            self._check_enemy_auto_switch()
            self._show_action_menu()
        else:
            self._run_turn(("switch", index))

    def _use_item(self, item_id):
        item = items.get_item(item_id)
        if item.revive:
            self._show_revive_target_menu(item_id)
            return
        active = self.battle.player
        if not items.can_use_on(item_id, active):
            return
        save.remove_item(item_id)
        self._run_turn(("item", items.heal_amount_for(item_id, active)))

    def _use_revive(self, item_id, index):
        target = self.app.player_team[index]
        save.remove_item(item_id)
        self._run_turn(("item", (items.heal_amount_for(item_id, target), index)))

    def _flee(self):
        self._run_turn(("flee", None))

    def _pick_enemy_move(self):
        return ai.choose_move(
            self.battle.enemy, self.battle.player, self.difficulty, self.enemy_personality,
        )

    def _run_turn(self, action):
        self._clear_menu()
        before = {
            "player": (self.battle.player, self.battle.player.current_hp),
            "enemy": (self.battle.enemy, self.battle.enemy.current_hp),
        }
        log = self.battle.take_turn(action, self._pick_enemy_move())
        self._log(*log)
        self._refresh_panels()
        self._play_hit_animations(before)
        self._handle_victory_progression()
        self._after_turn()

    def _play_hit_animations(self, before):
        """Pisca o painel e mostra o número de dano de quem perdeu HP nesse
        turno (ataque do adversário e/ou dano residual de status)."""
        mon, hp_before = before["player"]
        if mon is self.battle.player and mon.current_hp < hp_before:
            self.player_panel.play_hit(hp_before - mon.current_hp)
        mon, hp_before = before["enemy"]
        if mon is self.battle.enemy and mon.current_hp < hp_before:
            self.enemy_panel.play_hit(hp_before - mon.current_hp)

    # ---------- XP, level up, golpe novo e evolução ----------
    def _handle_victory_progression(self):
        enemy = self.battle.enemy
        winner = self.battle.player
        if not enemy.is_fainted or winner.is_fainted or id(enemy) in self._xp_awarded_for:
            return
        self._xp_awarded_for.add(id(enemy))

        try:
            defeated_data = pokeapi.get_pokemon(enemy.species)
        except (PokeApiError, AttributeError):
            return  # sem espécie/rede: só pula a progressão, a batalha continua normal

        xp_gained = progression.experience_for_win(defeated_data, enemy.level)
        winner.experience += xp_gained
        self._log(f"{winner.name} ganhou {xp_gained} pontos de experiência!")

        ev_message = progression.gain_ev_from_victory(winner, defeated_data)
        if ev_message:
            self._log(ev_message)

        result = progression.apply_level_up(winner)
        if result["levels_gained"]:
            plural = "s" if result["levels_gained"] > 1 else ""
            self._log(f"{winner.name} subiu {result['levels_gained']} nível{plural}! Agora é nível {winner.level}.")
            self._refresh_panels()

        for move in result["new_moves"]:
            self._offer_new_move(winner, move)

        if result["evolved_into"]:
            self._handle_evolution(winner, result["evolved_into"])

    def _offer_new_move(self, pokemon, move):
        if len(pokemon.moves) < 4:
            progression.learn_move(pokemon, move)
            self._log(f"{pokemon.name} aprendeu {move.name}!")
            return

        wants_it = messagebox.askyesno(
            "Novo golpe",
            f"{pokemon.name} quer aprender {move.name}, mas já sabe 4 golpes.\n"
            "Esquecer um golpe pra aprender esse?",
            parent=self,
        )
        if not wants_it:
            self._log(f"{pokemon.name} não aprendeu {move.name}.")
            return

        slot = self._ask_move_to_forget(pokemon)
        if slot is None:
            self._log(f"{pokemon.name} não aprendeu {move.name}.")
            return
        forgotten = pokemon.moves[slot].name
        progression.learn_move(pokemon, move, forget_index=slot)
        self._log(f"{pokemon.name} esqueceu {forgotten} e aprendeu {move.name}!")

    def _ask_move_to_forget(self, pokemon):
        dialog = tk.Toplevel(self)
        dialog.title("Esquecer qual golpe?")
        dialog.configure(bg=BG)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        choice = {"index": None}

        tk.Label(
            dialog, text=f"Qual golpe {pokemon.name} esquece?", bg=BG, fg=FG, font=FONT_BODY,
        ).pack(padx=16, pady=(16, 8))
        for i, existing_move in enumerate(pokemon.moves):
            def pick(index=i):
                choice["index"] = index
                dialog.destroy()
            tk.Button(dialog, text=existing_move.name, font=FONT_BODY, width=24, command=pick).pack(padx=16, pady=2)
        tk.Button(dialog, text="Cancelar", font=FONT_BODY, command=dialog.destroy).pack(pady=(8, 16))

        dialog.wait_window()
        return choice["index"]

    def _handle_evolution(self, pokemon, new_species):
        old_name = pokemon.name
        try:
            progression.evolve_pokemon(pokemon, new_species)
        except (PokeApiError, KeyError):
            return
        self._log(f"{old_name} evoluiu para {pokemon.name}!")
        messagebox.showinfo("Evolução!", f"Parabéns! {old_name} evoluiu para {pokemon.name}!", parent=self)
        self._refresh_panels()

    def _check_enemy_auto_switch(self):
        if self.battle.needs_switch("enemy"):
            reserves = [i for i, mon in enumerate(self.app.enemy_team) if not mon.is_fainted]
            _vai_message, *extra_messages = self.battle.switch("enemy", reserves[0])
            self._log(f"O oponente enviou {self.battle.enemy.name}!", *extra_messages)
            self._refresh_panels()

    def _after_turn(self):
        if self.battle.is_over:
            victory = self.battle.winner == "player"
            if victory:
                save.increment_trainers_defeated()
            if victory and self.gym:
                save.add_badge(self.gym.id)
                save.add_money(self.gym.reward_money)
            self.app.show_frame(EndScreen, victory=victory, gym=self.gym)
            return
        if self.battle.needs_switch("player"):
            self._log(f"{self.battle.player.name} não pode continuar lutando!")
            self._show_switch_menu(forced=True)
            return
        self._check_enemy_auto_switch()
        self._show_action_menu()


class EndScreen(tk.Frame):
    def __init__(self, parent, app: PokeBattleApp, victory: bool, gym: Optional[gyms.Gym] = None):
        super().__init__(parent, bg=BG)
        self.app = app
        if victory and gym:
            text = f"Você venceu {gym.leader}!"
        elif gym:
            text = f"Você perdeu para {gym.leader}..."
        else:
            text = "Você venceu a batalha!" if victory else "Você perdeu essa batalha..."
        color = HP_GREEN if victory else HP_RED
        tk.Label(self, text=text, font=("Segoe UI", 26, "bold"), bg=BG, fg=color).pack(expand=True, pady=(0, 4))

        if victory and gym:
            tk.Label(
                self, text=f"Você ganhou a {gym.badge_name} e ${gym.reward_money}!",
                font=FONT_HEADING, bg=BG, fg=ACCENT,
            ).pack(pady=(0, 16))

        tk.Button(
            self, text="Jogar de novo", font=FONT_HEADING, bg=ACCENT, command=self._play_again,
        ).pack(pady=8)
        if gym:
            tk.Button(
                self, text="Ver ginásios", font=FONT_BODY,
                command=lambda: self.app.show_frame(GymScreen),
            ).pack()
        tk.Button(self, text="Sair", font=FONT_BODY, command=app.destroy).pack()

    def _play_again(self):
        self.app.player_team = []
        self.app.enemy_team = []
        self.app.battle = None
        self.app.show_frame(TeamSelectScreen)


def main():
    try:
        app = PokeBattleApp()
    except tk.TclError as exc:
        print("Não consegui abrir a janela gráfica. Esse modo precisa de um ambiente com tela.")
        print(f"Detalhe: {exc}")
        return
    app.mainloop()


if __name__ == "__main__":
    main()
