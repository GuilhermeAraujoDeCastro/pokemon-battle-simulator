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
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox, simpledialog
from typing import Optional

from PIL import Image, ImageTk

from pokebattle import (
    abilities, achievements, ai, audio, avatar, gyms, held_items, items, locations,
    mega, nuzlocke, pokeapi, progression, quests, replay, roster, save, teamcodec,
    trade,
)
from pokebattle.battle import WEATHER_LABELS, Battle
from pokebattle.pokeapi import PokeApiError
from pokebattle.status import SHORT_LABEL
from pokebattle.tournament import Tournament, simulate_ai_battle

WEATHER_EMOJI = {"sun": "☀️", "rain": "🌧️", "sandstorm": "🏜️", "hail": "❄️"}
TOURNAMENT_PLAYER_NAME = "Você"

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


def _describe_action(action) -> str:
    """Descrição curta de uma ação de jogador, usada só no replay (ver
    pokebattle/replay.py)."""
    kind, payload = action
    if kind == "move":
        return f"usou {payload.name}"
    if kind == "switch":
        return "trocou de Pokémon"
    if kind == "item":
        return "usou um item"
    if kind == "flee":
        return "fugiu"
    return kind


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


def draw_avatar(canvas, trainer_name, color_id, size=48):
    """Avatar do treinador: um círculo colorido com a inicial do nome (ver
    pokebattle/avatar.py) — sem sprite de terceiro nenhum."""
    spec = avatar.avatar_spec(trainer_name, color_id)
    canvas.delete("all")
    canvas.create_oval(2, 2, size - 2, size - 2, fill=spec["color"], outline="#4b5670")
    canvas.create_text(
        size / 2, size / 2, text=spec["initial"], fill="#1f2733",
        font=("Segoe UI", int(size * 0.42), "bold"),
    )


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
        self._hp_ratio = 1.0  # ponto de partida do próximo tween da barra de HP
        # Widgets cuja cor de fundo pisca junto quando esse lado apanha.
        self._flashable = [
            self.frame, self.image_label, self.name_label,
            self.ability_label, self.status_label, self.popup_canvas,
        ]

    def update(self, pokemon, photo):
        self._photo = photo
        self.image_label.config(image=photo)
        shiny_mark = "✨ " if getattr(pokemon, "is_shiny", False) else ""
        mega_mark = "Mega " if getattr(pokemon, "is_mega", False) else ""
        name_color = ACCENT if getattr(pokemon, "is_shiny", False) else FG
        self.name_label.config(text=f"{shiny_mark}{mega_mark}{pokemon.name}  Lv.{pokemon.level}", fg=name_color)
        ability_text = abilities.display_name(getattr(pokemon, "ability", None))
        held_item_id = getattr(pokemon, "held_item", None)
        if held_item_id:
            ability_text += f"  •  {held_items.display_name(held_item_id)}"
        self.ability_label.config(text=ability_text)
        self.status_label.config(text=SHORT_LABEL.get(pokemon.status, ""))
        self._animate_hp_bar(pokemon.current_hp, pokemon.max_hp)
        self.hp_text.config(text=f"{pokemon.current_hp}/{pokemon.max_hp} HP")

    def _paint_bar(self, ratio, color):
        width = 180
        self.hp_canvas.delete("all")
        self.hp_canvas.create_rectangle(0, 0, width, 16, fill="#0d1117", outline="")
        self.hp_canvas.create_rectangle(0, 0, width * ratio, 16, fill=color, outline="")
        self.hp_canvas.create_rectangle(0, 0, width - 1, 15, outline="#4b5670")

    def _animate_hp_bar(self, current, max_hp, frames=10):
        """Anima a barra de HP do valor antigo pro novo em vez de saltar
        direto — mesmo padrão de after() que _rise_popup já usa."""
        target_ratio = 0 if max_hp <= 0 else max(0.0, current / max_hp)
        start_ratio = self._hp_ratio
        color = hp_color(current, max_hp)

        def step(i):
            if not self.hp_canvas.winfo_exists():
                return
            ratio = start_ratio + (target_ratio - start_ratio) * (i / frames)
            self._paint_bar(ratio, color)
            if i < frames:
                self.hp_canvas.after(20, lambda: step(i + 1))
            else:
                self._hp_ratio = target_ratio

        step(0)

    # ---------- animação de golpe ----------
    def play_hit(self, damage: int) -> None:
        """Painel pisca de vermelho e o número do dano sobe e some — chamado
        sempre que esse lado perde HP num turno."""
        audio.play("hit")
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
        self.tournament = None  # Tournament em andamento (pokebattle/tournament.py), ou None
        self.tournament_ai_teams = {}  # nome do participante IA -> time montado
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
        self.held_item_choices = {}  # índice em self.chosen -> id do item segurado equipado
        self.custom_builds = {}  # índice em self.chosen -> Pokemon já pronto (time importado/trocado)

        save_data = save.load()
        trainer_name = save_data.get("trainer_name")

        header = tk.Frame(self, bg=BG)
        header.pack(pady=(20, 4))
        self.avatar_canvas = tk.Canvas(header, width=48, height=48, bg=BG, highlightthickness=0)
        self.avatar_canvas.pack(side="left", padx=(0, 10))
        draw_avatar(self.avatar_canvas, trainer_name, save_data.get("avatar_color"))
        title = f"Monte seu time, {trainer_name}!" if trainer_name else "Monte seu time"
        tk.Label(header, text=title, font=FONT_TITLE, bg=BG, fg=ACCENT).pack(side="left")

        avatar_colors_frame = tk.Frame(self, bg=BG)
        avatar_colors_frame.pack(pady=(0, 4))
        tk.Label(avatar_colors_frame, text="Cor do avatar:", bg=BG, fg=FG, font=FONT_BODY).pack(side="left")
        for color_id in avatar.PALETTE:
            tk.Button(
                avatar_colors_frame, bg=avatar.PALETTE[color_id], width=2, relief="flat",
                command=lambda c=color_id: self._choose_avatar_color(c),
            ).pack(side="left", padx=2)

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

        self.nuzlocke_var = tk.BooleanVar(value=save_data.get("nuzlocke", False))
        tk.Checkbutton(
            difficulty_frame, text="Modo Nuzlocke", variable=self.nuzlocke_var,
            bg=BG, fg=FG, selectcolor=PANEL_BG, activebackground=BG, font=FONT_BODY,
            command=lambda: save.set_nuzlocke(self.nuzlocke_var.get()),
        ).pack(side="left", padx=(16, 0))

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
        tk.Button(
            team_frame, text="Equipar item segurado", command=self._equip_item_selected, font=FONT_BODY,
        ).pack(fill="x", pady=(4, 0))

        owned = save_data.get("owned_pokemon", [])
        if owned:
            tk.Label(team_frame, text="Comprados na loja", bg=BG, fg=MUTED_FG, font=FONT_BODY).pack(pady=(10, 0))
            self.owned_list = tk.Listbox(team_frame, height=min(4, len(owned)), font=FONT_BODY)
            self.owned_list.pack(pady=4, fill="x")
            for species in owned:
                self.owned_list.insert(tk.END, roster.display_name(species))
            tk.Button(
                team_frame, text="Adicionar comprado >>", command=self._add_owned_selected, font=FONT_BODY,
            ).pack(fill="x")
        else:
            self.owned_list = None

        buttons_row = tk.Frame(self, bg=BG)
        buttons_row.pack(pady=(16, 4))
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

        extra_row = tk.Frame(self, bg=BG)
        extra_row.pack(pady=(0, 16))
        tk.Button(
            extra_row, text="Conquistas", font=FONT_BODY,
            command=lambda: self.app.show_frame(AchievementsScreen),
        ).pack(side="left", padx=4)
        tk.Button(
            extra_row, text="Treino de EV", font=FONT_BODY,
            command=lambda: self.app.show_frame(TrainingScreen),
        ).pack(side="left", padx=4)
        tk.Button(
            extra_row, text="Torneio", font=FONT_BODY,
            command=lambda: self.app.show_frame(TournamentScreen),
        ).pack(side="left", padx=4)
        tk.Button(
            extra_row, text="PvP Local", font=FONT_BODY,
            command=lambda: self.app.show_frame(PvpTeamSelectScreen, player_index=0, chosen_species=[]),
        ).pack(side="left", padx=4)
        tk.Button(
            extra_row, text="Replays", font=FONT_BODY,
            command=lambda: self.app.show_frame(ReplayListScreen),
        ).pack(side="left", padx=4)
        tk.Button(extra_row, text="Exportar time", font=FONT_BODY, command=self._export_team).pack(side="left", padx=4)
        tk.Button(extra_row, text="Importar time", font=FONT_BODY, command=self._import_team).pack(side="left", padx=4)
        tk.Button(
            extra_row, text="Trocar Pokémon", font=FONT_BODY, command=self._trade_menu,
        ).pack(side="left", padx=4)

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

    def _add_species(self, species, prebuilt=None):
        if len(self.chosen) >= TEAM_SIZE or species in self.chosen:
            return
        index = len(self.chosen)
        self.chosen.append(species)
        if prebuilt is not None:
            self.custom_builds[index] = prebuilt
        self.team_list.insert(tk.END, roster.display_name(species))
        self.start_button.config(state="normal")

    def _add_owned_selected(self, *_args):
        if self.owned_list is None:
            return
        selection = self.owned_list.curselection()
        if not selection:
            return
        owned = save.load().get("owned_pokemon", [])
        index = selection[0]
        if index >= len(owned):
            return
        species = owned[index]
        before = len(self.chosen)
        self._add_species(species)
        if len(self.chosen) > before:  # só consome o comprado se realmente coube no time
            save.remove_owned_pokemon(species)
            self.owned_list.delete(index)

    def _choose_avatar_color(self, color_id):
        save.set_avatar_color(color_id)
        draw_avatar(self.avatar_canvas, save.load().get("trainer_name"), color_id)

    def _equip_item_selected(self):
        selection = self.team_list.curselection()
        if not selection:
            messagebox.showinfo("Nenhum selecionado", "Selecione um Pokémon do time primeiro.", parent=self)
            return
        index = selection[0]
        owned_items = save.load()["items"]
        available = [item for item in held_items.CATALOG if owned_items.get(item.id, 0) > 0]

        dialog = tk.Toplevel(self)
        dialog.title("Equipar item segurado")
        dialog.configure(bg=BG)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        tk.Label(dialog, text="Qual item equipar?", bg=BG, fg=FG, font=FONT_HEADING).pack(padx=16, pady=(16, 8))
        if not available:
            tk.Label(
                dialog, text="Você não tem nenhum item segurado. Compre na Loja.",
                bg=BG, fg=MUTED_FG, font=FONT_BODY,
            ).pack(padx=16, pady=4)
        for item in available:
            def pick(item_id=item.id):
                previous = self.held_item_choices.get(index)
                if previous:
                    save.add_item(previous)  # devolve o item anterior desse slot
                save.remove_item(item_id)
                self.held_item_choices[index] = item_id
                dialog.destroy()
            qty = owned_items.get(item.id, 0)
            tk.Button(dialog, text=f"{item.name} (tem {qty})", font=FONT_BODY, width=28, command=pick).pack(padx=16, pady=2)

        def unequip():
            previous = self.held_item_choices.pop(index, None)
            if previous:
                save.add_item(previous)
            dialog.destroy()
        tk.Button(dialog, text="Nenhum (remover item atual)", font=FONT_BODY, command=unequip).pack(padx=16, pady=(8, 2))
        tk.Button(dialog, text="Cancelar", font=FONT_BODY, command=dialog.destroy).pack(pady=(4, 16))

    def _export_team(self):
        if not self.chosen:
            messagebox.showinfo("Time vazio", "Monte um time primeiro.", parent=self)
            return
        self.status_label.config(text="Preparando o time pra exportar...")

        def build_for_export():
            team = self.app.player_team if self.app.player_team else None
            if team:
                return team
            return [roster.build_pokemon(species) for species in self.chosen]

        self.app.run_in_background(build_for_export, self._show_export_text, self._team_build_failed)

    def _show_export_text(self, team):
        self.status_label.config(text=f"{len(self.all_species or [])} Pokémon disponíveis. Digite pra filtrar.")
        text = teamcodec.team_to_text(team)

        dialog = tk.Toplevel(self)
        dialog.title("Exportar time")
        dialog.configure(bg=BG)
        dialog.transient(self.winfo_toplevel())

        tk.Label(
            dialog, text="Copie o texto abaixo pra compartilhar seu time:", bg=BG, fg=FG, font=FONT_BODY,
        ).pack(padx=12, pady=(12, 4))
        text_widget = tk.Text(dialog, width=48, height=16, font=FONT_MONO)
        text_widget.insert("1.0", text)
        text_widget.pack(padx=12, pady=4)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(text)

        tk.Button(dialog, text="Copiar", font=FONT_BODY, bg=ACCENT, command=copy).pack(pady=(4, 12))

    def _import_team(self):
        dialog = tk.Toplevel(self)
        dialog.title("Importar time")
        dialog.configure(bg=BG)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        tk.Label(
            dialog, text="Cole abaixo o texto de um time exportado:", bg=BG, fg=FG, font=FONT_BODY,
        ).pack(padx=12, pady=(12, 4))
        text_widget = tk.Text(dialog, width=48, height=16, font=FONT_MONO)
        text_widget.pack(padx=12, pady=4)

        def confirm():
            text = text_widget.get("1.0", tk.END).strip()
            dialog.destroy()
            if not text:
                return
            self.status_label.config(text="Montando o time importado...")
            self.app.run_in_background(
                lambda: teamcodec.build_team_from_text(text), self._team_imported, self._team_build_failed,
            )

        tk.Button(dialog, text="Importar", font=FONT_BODY, bg=ACCENT, command=confirm).pack(pady=(4, 12))

    def _team_imported(self, team):
        for pokemon in team:
            self._add_species(getattr(pokemon, "species", pokemon.name.lower()), prebuilt=pokemon)
        self.status_label.config(text=f"Time importado com {len(team)} Pokémon! Pode começar a batalha.")

    def _trade_menu(self):
        dialog = tk.Toplevel(self)
        dialog.title("Trocar Pokémon")
        dialog.configure(bg=BG)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        tk.Label(dialog, text="Troca de Pokémon entre saves", bg=BG, fg=FG, font=FONT_HEADING).pack(padx=16, pady=(16, 8))
        tk.Label(
            dialog, text="Exporte um Pokémon do seu time pra um arquivo e mande pro seu amigo,\n"
                         "ou importe um arquivo que ele te mandou.",
            bg=BG, fg=MUTED_FG, font=FONT_BODY, justify="left",
        ).pack(padx=16, pady=(0, 12))

        tk.Button(dialog, text="Exportar Pokémon do time...", font=FONT_BODY, command=lambda: self._trade_export(dialog)).pack(fill="x", padx=16, pady=2)
        tk.Button(dialog, text="Importar Pokémon de um arquivo...", font=FONT_BODY, command=lambda: self._trade_import(dialog)).pack(fill="x", padx=16, pady=2)
        tk.Button(dialog, text="Fechar", font=FONT_BODY, command=dialog.destroy).pack(pady=(8, 16))

    def _trade_export(self, parent_dialog):
        selection = self.team_list.curselection()
        if not selection:
            messagebox.showinfo("Nenhum selecionado", "Selecione um Pokémon do time primeiro.", parent=parent_dialog)
            return
        index = selection[0]
        path = filedialog.asksaveasfilename(
            title="Salvar Pokémon pra troca", defaultextension=".json",
            filetypes=[("Arquivo de troca", "*.json")], parent=parent_dialog,
        )
        if not path:
            return

        def build_and_export():
            existing = self.custom_builds.get(index)
            mon = existing if existing is not None else roster.build_pokemon(self.chosen[index])
            trade.export_pokemon_to_file(mon, path)
            return path

        self.app.run_in_background(
            build_and_export,
            lambda p: messagebox.showinfo("Exportado", f"Pokémon salvo em {p}.", parent=self),
            self._team_build_failed,
        )

    def _trade_import(self, parent_dialog):
        path = filedialog.askopenfilename(
            title="Importar Pokémon de troca", filetypes=[("Arquivo de troca", "*.json")], parent=parent_dialog,
        )
        if not path:
            return
        self.app.run_in_background(
            lambda: trade.import_pokemon_from_file(path), self._pokemon_traded_in, self._team_build_failed,
        )

    def _pokemon_traded_in(self, pokemon):
        self._add_species(getattr(pokemon, "species", pokemon.name.lower()), prebuilt=pokemon)
        self.status_label.config(text=f"{pokemon.name} entrou no time por troca!")

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
        custom_builds = dict(self.custom_builds)

        def build_teams():
            enemy_species = random.sample(species_pool, k=min(TEAM_SIZE, len(species_pool)))

            def safe_build(name, index=None):
                if index is not None and index in custom_builds:
                    return custom_builds[index]
                try:
                    return roster.build_pokemon(name)
                except (PokeApiError, KeyError, ValueError):
                    # forma rara com dados incompletos — troca por outra espécie
                    fallback = random.choice(species_pool)
                    return roster.build_pokemon(fallback)

            with ThreadPoolExecutor(max_workers=4) as pool:
                player_team = list(pool.map(lambda pair: safe_build(pair[1], pair[0]), enumerate(chosen)))
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
            held_item_id = self.held_item_choices.get(index)
            if held_item_id:
                mon.held_item = held_item_id
        self.app.player_team = player_team
        self.app.enemy_team = enemy_team
        self.app.battle = Battle(player_team, enemy_team, location=locations.random_location())
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
            location = locations.get_location(gym.location_id)
            location_text = f"  •  {location.name}" if location.id != "open_field" else ""
            text = f"{mark}  {gym.city} — Líder {gym.leader} ({gym.gym_type})  •  {gym.badge_name}{location_text}"
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
        self.app.battle = Battle(self.app.player_team, enemy_team, location=locations.get_location(gym.location_id))
        self.app.show_frame(BattleScreen, gym=gym)


POKEMON_SHOP_PRICE = 8000  # preço alto de propósito — é uma alternativa cara à busca de graça


class MartScreen(tk.Frame):
    """PokéMart: mostra o dinheiro atual e deixa comprar qualquer item do
    catálogo (cura, EV, itens segurados) um por vez, mais a loja de Pokémon
    de verdade (um Pokémon aleatório por um preço alto)."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self.item_rows = {}
        self.held_item_rows = {}
        self.all_species = None

        tk.Label(self, text="PokéMart", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        self.money_label = tk.Label(self, text="", bg=BG, fg=MUTED_FG, font=FONT_BODY)
        self.money_label.pack()

        list_container = tk.Frame(self, bg=BG)
        list_container.pack(fill="both", expand=True, padx=48, pady=16)
        canvas = tk.Canvas(list_container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        list_frame = tk.Frame(canvas, bg=BG)
        list_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(list_frame, text="Itens", bg=BG, fg=ACCENT, font=FONT_HEADING, anchor="w").pack(fill="x", pady=(0, 4))
        for item in items.CATALOG:
            self.item_rows[item.id] = self._build_row(
                list_frame, item.name, item.price, item.description, lambda item_id=item.id: self._buy(item_id),
            )

        tk.Label(
            list_frame, text="Itens Segurados", bg=BG, fg=ACCENT, font=FONT_HEADING, anchor="w",
        ).pack(fill="x", pady=(14, 4))
        for held_item in held_items.CATALOG:
            self.held_item_rows[held_item.id] = self._build_row(
                list_frame, held_item.name, held_item.price, held_item.description,
                lambda item_id=held_item.id: self._buy_held_item(item_id),
            )

        tk.Label(
            list_frame, text="Loja de Pokémon", bg=BG, fg=ACCENT, font=FONT_HEADING, anchor="w",
        ).pack(fill="x", pady=(14, 4))
        self.pokemon_row = self._build_row(
            list_frame, "Pokémon misterioso", POKEMON_SHOP_PRICE,
            "Um Pokémon aleatório de verdade entra pra sua coleção (aba \"Comprados\" na tela de time).",
            self._buy_random_pokemon,
        )
        self.pokemon_row[0].config(state="disabled")  # só libera depois de carregar a lista de espécies

        tk.Button(
            self, text="Voltar", font=FONT_HEADING,
            command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))

        self._refresh()
        self.app.run_in_background(roster.list_all_species, self._species_loaded, lambda _exc: None)

    def _build_row(self, parent, name, price, description, command):
        row = tk.Frame(parent, bg=PANEL_BG, padx=12, pady=8)
        row.pack(fill="x", pady=4)
        text = f"{name} — ${price}  •  {description}"
        tk.Label(row, text=text, bg=PANEL_BG, fg=FG, font=FONT_BODY, anchor="w", wraplength=520, justify="left").pack(
            side="left", fill="x", expand=True,
        )
        owned_label = tk.Label(row, text="", bg=PANEL_BG, fg=MUTED_FG, font=FONT_BODY)
        owned_label.pack(side="right", padx=(0, 12))
        buy_button = tk.Button(row, text="Comprar", font=FONT_BODY, bg=ACCENT, command=command)
        buy_button.pack(side="right")
        return buy_button, owned_label

    def _species_loaded(self, species):
        self.all_species = species
        self.pokemon_row[0].config(state="normal" if save.load()["money"] >= POKEMON_SHOP_PRICE else "disabled")

    def _refresh(self):
        data = save.load()
        money = data["money"]
        owned = data["items"]
        self.money_label.config(text=f"Dinheiro: ${money}")
        for item in items.CATALOG:
            buy_button, owned_label = self.item_rows[item.id]
            buy_button.config(state="normal" if money >= item.price else "disabled")
            owned_label.config(text=f"Você tem: {owned.get(item.id, 0)}")
        for held_item in held_items.CATALOG:
            buy_button, owned_label = self.held_item_rows[held_item.id]
            buy_button.config(state="normal" if money >= held_item.price else "disabled")
            owned_label.config(text=f"Você tem: {owned.get(held_item.id, 0)}")
        if self.all_species is not None:
            self.pokemon_row[0].config(state="normal" if money >= POKEMON_SHOP_PRICE else "disabled")

    def _buy(self, item_id: str):
        item = items.get_item(item_id)
        if not save.spend_money(item.price):
            return
        save.add_item(item_id)
        self._refresh()

    def _buy_held_item(self, item_id: str):
        item = held_items.get_item(item_id)
        if not save.spend_money(item.price):
            return
        save.add_item(item_id)
        self._refresh()

    def _buy_random_pokemon(self):
        if not self.all_species or not save.spend_money(POKEMON_SHOP_PRICE):
            return
        species = random.choice(self.all_species)
        save.add_owned_pokemon(species)
        self._refresh()
        messagebox.showinfo(
            "Pokémon misterioso!", f"Parabéns! Você comprou um {roster.display_name(species)}!", parent=self,
        )


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
    def __init__(self, parent, app: PokeBattleApp, gym: Optional[gyms.Gym] = None, pvp: bool = False,
                 player_names: Optional[tuple] = None, tournament_ctx: Optional[dict] = None):
        super().__init__(parent, bg=BG)
        self.app = app
        self.battle: Battle = app.battle
        self.gym = gym  # None numa batalha comum; o Gym sendo desafiado, se for uma
        self.pvp = pvp  # PvP local hot-seat: os dois lados escolhem golpe por humano
        self.player_names = player_names or ("Jogador 1", "Jogador 2")
        self.tournament_ctx = tournament_ctx  # {"round", "match", "opponent_name"} numa partida de torneio
        self._xp_awarded_for = set()  # ids dos inimigos já derrotados (evita XP em dobro)
        self._pvp_pending_move = None
        self._replay_turns = []  # log gravado turno a turno, ver pokebattle/replay.py
        self._turn_number = 0

        save_data = save.load()
        self.difficulty = save_data.get("difficulty", "normal")
        self._nuzlocke_enabled = bool(save_data.get("nuzlocke", False)) and not self.pvp
        # Ginásios têm personalidade curada (gyms.py); fora deles, a IA adaptativa pesa pela
        # taxa de vitória/derrota do jogador (ver pokebattle/ai.adaptive_personality).
        self.enemy_personality = gym.personality if gym else ai.adaptive_personality(save_data, rng=random)

        self._player_mega_evolved = False
        self._enemy_mega_evolved = False
        if not self.pvp:
            player_mega_msg = mega.try_mega_evolve(self.battle.player)
            enemy_mega_msg = mega.try_mega_evolve(self.battle.enemy)
            self._player_mega_evolved = player_mega_msg is not None
            self._enemy_mega_evolved = enemy_mega_msg is not None
        else:
            player_mega_msg = enemy_mega_msg = None

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
        self.avatar_canvas = tk.Canvas(middle, width=36, height=36, bg=BG, highlightthickness=0)
        if not self.pvp:
            self.avatar_canvas.pack(side="right", padx=(0, 8), pady=8)
            draw_avatar(self.avatar_canvas, save_data.get("trainer_name"), save_data.get("avatar_color"), size=36)

        self.log_text = tk.Text(
            self, height=8, bg="#10151d", fg=FG, wrap="word", state="disabled", font=FONT_MONO,
        )
        self.log_text.pack(fill="both", expand=True, padx=24, pady=12)

        self.menu_frame = tk.Frame(self, bg=BG)
        self.menu_frame.pack(fill="x", padx=24, pady=(0, 20))

        self._refresh_panels()
        if self.pvp:
            self._log(f"{self.player_names[0]} contra {self.player_names[1]}!")
        elif self.gym:
            self._log(f"Líder {self.gym.leader} te desafiou pela {self.gym.badge_name}!")
            audio.play_music("gym_theme")
        else:
            self._log(f"Um treinador adversário te desafiou com {self.battle.enemy.name}!")
        self._log(*self.battle.intro_log)
        if player_mega_msg:
            self._log(player_mega_msg)
        if enemy_mega_msg:
            self._log(enemy_mega_msg)
        if player_mega_msg or enemy_mega_msg:
            self._refresh_panels()
        if self.pvp:
            self._show_pvp_move_menu(0)
        else:
            self._show_action_menu()

    # ---------- desenho ----------
    def _refresh_panels(self):
        self.enemy_panel.update(self.battle.enemy, self.app.photo_for(self.battle.enemy))
        self.player_panel.update(self.battle.player, self.app.photo_for(self.battle.player))
        weather = self.battle.weather
        location = self.battle.location
        location_name = location.name if location and location.id != "open_field" else None
        if weather:
            emoji = WEATHER_EMOJI.get(weather, "")
            turns_text = str(self.battle.weather_turns) if self.battle.weather_turns is not None else "fixo"
            text = f"{emoji} Tempo {WEATHER_LABELS[weather]} ({turns_text})"
            if location_name:
                text += f"  •  {location_name}"
            self.weather_label.config(text=text)
        elif location_name:
            self.weather_label.config(text=location_name)
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
            if item.ev_stat:
                continue  # itens de treino de EV não entram na Mochila de batalha — ver TrainingScreen
            qty = inventory.get(item.id, 0)
            if qty <= 0:
                continue
            has_any_item = True
            if item.revive:
                usable = nuzlocke.can_use_revive(self._nuzlocke_enabled) and any(
                    mon.is_fainted for mon in self.app.player_team
                )
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

    def _record_replay_turn(self, description, log_lines):
        self._turn_number += 1
        self._replay_turns.append(replay.record_turn(
            self._turn_number, description, log_lines,
            replay.snapshot(self.battle.player), replay.snapshot(self.battle.enemy),
        ))

    def _run_turn(self, action):
        self._clear_menu()
        before = {
            "player": (self.battle.player, self.battle.player.current_hp),
            "enemy": (self.battle.enemy, self.battle.enemy.current_hp),
        }
        log = self.battle.take_turn(action, self._pick_enemy_move())
        self._log(*log)
        self._record_replay_turn(_describe_action(action), log)
        self._refresh_panels()
        self._play_hit_animations(before)
        self._handle_victory_progression()
        self._after_turn()

    # ---------- PvP local (hot-seat): golpe escolhido por humano dos dois lados ----------
    def _show_pvp_move_menu(self, player_index):
        self._clear_menu()
        active = self.battle.player if player_index == 0 else self.battle.enemy
        tk.Label(
            self.menu_frame, text=f"{self.player_names[player_index]}: escolha o golpe de {active.name}",
            bg=BG, fg=ACCENT, font=FONT_HEADING,
        ).pack(pady=(0, 6))
        for move in active.moves:
            power_text = "—" if move.power == 0 else str(move.power)
            text = f"{move.name}   ({move.type}, poder {power_text}, precisão {move.accuracy}%)"
            tk.Button(
                self.menu_frame, text=text, anchor="w", font=FONT_BODY,
                command=lambda m=move: self._pvp_move_chosen(player_index, m),
            ).pack(fill="x", pady=2)
        tk.Button(
            self.menu_frame, text="Fugir (encerra a partida)", font=FONT_BODY, command=self._pvp_flee,
        ).pack(pady=(8, 0))

    def _show_pass_device_screen(self, next_player_index):
        self._clear_menu()
        tk.Label(
            self.menu_frame, text=f"Passe o computador pro {self.player_names[next_player_index]}.",
            bg=BG, fg=FG, font=FONT_HEADING, wraplength=420, justify="center",
        ).pack(pady=(10, 10))
        tk.Button(
            self.menu_frame, text="Pronto, é a minha vez", font=FONT_HEADING, bg=ACCENT,
            command=lambda: self._show_pvp_move_menu(next_player_index),
        ).pack(pady=6)

    def _pvp_move_chosen(self, player_index, move):
        if player_index == 0:
            self._pvp_pending_move = move
            self._show_pass_device_screen(next_player_index=1)
            return
        p1_move = self._pvp_pending_move
        self._pvp_pending_move = None
        self._clear_menu()
        log = self.battle.take_turn(("move", p1_move), move)
        self._log(*log)
        description = f"{self.player_names[0]} usou {p1_move.name}; {self.player_names[1]} usou {move.name}"
        self._record_replay_turn(description, log)
        self._refresh_panels()
        self._after_turn()

    def _pvp_flee(self):
        self._clear_menu()
        self._log(self.battle.flee())
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

    def _check_achievements(self, victory: bool) -> None:
        if not victory:
            return
        context = {
            "no_faint_win": all(not mon.is_fainted for mon in self.app.player_team),
            "found_shiny": any(
                getattr(mon, "is_shiny", False) for mon in self.app.player_team + self.app.enemy_team
            ),
            "mega_evolved": self._player_mega_evolved,
            "nuzlocke_win": self._nuzlocke_enabled,
        }
        save_data = save.load()
        for achievement in achievements.newly_unlocked(save_data, context):
            save.add_achievement(achievement.id)
            messagebox.showinfo(
                "Conquista desbloqueada!", f"🏆 {achievement.name}\n{achievement.description}", parent=self,
            )

    def _save_replay(self, victory: bool) -> None:
        if not self._replay_turns:
            return
        metadata = {
            "result": "vitoria" if victory else "derrota",
            "pvp": self.pvp,
            "gym": self.gym.id if self.gym else None,
            "player": self.battle.player.name,
            "enemy": self.battle.enemy.name,
        }
        replay.save_replay(replay.REPLAY_DIR / f"batalha_{int(time.time())}.json", metadata, self._replay_turns)

    def _after_turn(self):
        if self.battle.is_over:
            victory = self.battle.winner == "player"
            if self.pvp:
                audio.play("victory" if victory else "faint")
                self._save_replay(victory)
                self.app.show_frame(EndScreen, victory=victory, pvp=True, player_names=self.player_names)
                return

            audio.play("victory" if victory else "faint")
            if victory:
                save.increment_trainers_defeated()
            else:
                save.increment_battles_lost()
            if victory and self.gym:
                save.add_badge(self.gym.id)
                save.add_money(self.gym.reward_money)

            self._check_achievements(victory)

            for mon in list(self.app.player_team) + list(self.app.enemy_team):
                mega.revert_mega_form(mon)

            if self._nuzlocke_enabled:
                released = nuzlocke.released_members(self.app.player_team)
                if released:
                    self.app.player_team = nuzlocke.surviving_team(self.app.player_team)
                    for mon in released:
                        self._log(f"{mon.name} foi liberado permanentemente (Nuzlocke).")

            if self.tournament_ctx and self.app.tournament:
                winner_name = TOURNAMENT_PLAYER_NAME if victory else self.tournament_ctx["opponent_name"]
                self.app.tournament.record_result(
                    self.tournament_ctx["round"], self.tournament_ctx["match"], winner_name,
                )

            self._save_replay(victory)
            self.app.show_frame(EndScreen, victory=victory, gym=self.gym, tournament_ctx=self.tournament_ctx)
            return

        if self.pvp:
            self._show_pvp_move_menu(0)
            return
        if self.battle.needs_switch("player"):
            self._log(f"{self.battle.player.name} não pode continuar lutando!")
            self._show_switch_menu(forced=True)
            return
        self._check_enemy_auto_switch()
        self._show_action_menu()


class EndScreen(tk.Frame):
    def __init__(self, parent, app: PokeBattleApp, victory: bool, gym: Optional[gyms.Gym] = None,
                 pvp: bool = False, player_names: Optional[tuple] = None, tournament_ctx: Optional[dict] = None):
        super().__init__(parent, bg=BG)
        self.app = app
        self.tournament_ctx = tournament_ctx

        if pvp:
            player_names = player_names or ("Jogador 1", "Jogador 2")
            text = f"{player_names[0] if victory else player_names[1]} venceu a partida!"
        elif victory and gym:
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
        if tournament_ctx:
            tk.Button(
                self, text="Voltar ao torneio", font=FONT_BODY,
                command=lambda: self.app.show_frame(TournamentScreen),
            ).pack()
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


class AchievementsScreen(tk.Frame):
    """Lista as conquistas (pokebattle/achievements.py), desbloqueadas
    sozinhas conforme o jogador atinge cada marco — sem botão de resgatar,
    diferente das missões (QuestScreen)."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        save_data = save.load()

        tk.Label(self, text="Conquistas", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        unlocked_count = sum(1 for a in achievements.ACHIEVEMENTS if achievements.is_unlocked(a, save_data))
        tk.Label(
            self, text=f"{unlocked_count}/{len(achievements.ACHIEVEMENTS)} desbloqueadas",
            bg=BG, fg=MUTED_FG, font=FONT_BODY,
        ).pack()

        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=48, pady=16)
        for achievement in achievements.ACHIEVEMENTS:
            unlocked = achievements.is_unlocked(achievement, save_data)
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=12, pady=8)
            row.pack(fill="x", pady=4)
            mark = "🏆" if unlocked else "🔒"
            fg = ACCENT if unlocked else MUTED_FG
            tk.Label(
                row, text=f"{mark}  {achievement.name}", bg=PANEL_BG, fg=fg, font=FONT_HEADING, anchor="w",
            ).pack(fill="x")
            tk.Label(
                row, text=achievement.description, bg=PANEL_BG, fg=MUTED_FG, font=FONT_BODY, anchor="w",
            ).pack(fill="x")

        tk.Button(
            self, text="Voltar", font=FONT_HEADING, command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))


class TrainingScreen(tk.Frame):
    """Treino de EV fora de batalha (item 12): aplica Proteína e companhia
    num Pokémon do time atual. Só funciona depois que o time já foi
    montado numa batalha nessa sessão — é onde o Pokémon de verdade (com
    IV/EV/natureza) existe; a tela de montar time só guarda espécie."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Treino de EV", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))

        if not self.app.player_team:
            tk.Label(
                self, text="Monte seu time e comece uma batalha primeiro — o treino usa\n"
                           "os Pokémon já montados, com IV/EV/natureza de verdade.",
                bg=BG, fg=MUTED_FG, font=FONT_BODY, justify="center",
            ).pack(pady=40)
            tk.Button(
                self, text="Voltar", font=FONT_HEADING, command=lambda: self.app.show_frame(TeamSelectScreen),
            ).pack()
            return

        self.mon_var = tk.StringVar(value=self.app.player_team[0].name)
        self.mon_var.trace_add("write", lambda *_a: self._refresh())
        mon_frame = tk.Frame(self, bg=BG)
        mon_frame.pack(pady=8)
        tk.Label(mon_frame, text="Pokémon:", bg=BG, fg=FG, font=FONT_BODY).pack(side="left")
        tk.OptionMenu(mon_frame, self.mon_var, *[mon.name for mon in self.app.player_team]).pack(side="left", padx=8)

        self.ev_label = tk.Label(self, text="", bg=BG, fg=MUTED_FG, font=FONT_BODY)
        self.ev_label.pack(pady=4)

        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=48, pady=16)
        for item in items.CATALOG:
            if not item.ev_stat:
                continue
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=12, pady=8)
            row.pack(fill="x", pady=4)
            tk.Label(
                row, text=f"{item.name} — {item.description}", bg=PANEL_BG, fg=FG, font=FONT_BODY, anchor="w",
            ).pack(side="left", fill="x", expand=True)
            tk.Button(
                row, text="Usar", font=FONT_BODY, bg=ACCENT, command=lambda item_id=item.id: self._use(item_id),
            ).pack(side="right")

        tk.Button(
            self, text="Voltar", font=FONT_HEADING, command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))

        self._refresh()

    def _current_mon(self):
        name = self.mon_var.get()
        return next((mon for mon in self.app.player_team if mon.name == name), self.app.player_team[0])

    def _refresh(self):
        mon = self._current_mon()
        evs = ", ".join(f"{stat.replace('_', ' ').title()}: {value}" for stat, value in mon.evs.items())
        self.ev_label.config(text=f"EVs de {mon.name} — {evs}")

    def _use(self, item_id):
        data = save.load()
        if data["items"].get(item_id, 0) <= 0:
            messagebox.showinfo("Sem estoque", "Você não tem esse item. Compre na Loja.", parent=self)
            return
        mon = self._current_mon()
        gained = items.apply_ev_item(item_id, mon)
        if gained <= 0:
            messagebox.showinfo("Limite atingido", f"{mon.name} já está no teto de EV pra esse stat.", parent=self)
            return
        save.remove_item(item_id)
        self._refresh()


class TournamentScreen(tk.Frame):
    """Modo torneio (item 1): bracket de eliminação simples reaproveitando
    Battle e ai.py (pokebattle/tournament.py). As partidas do jogador
    acontecem na BattleScreen de sempre; as outras são simuladas na hora."""

    ENTRANT_COUNT = 4

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Torneio", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, padx=48, pady=16)

        if self.app.tournament is None:
            if not self.app.player_team:
                messagebox.showinfo(
                    "Sem time", "Monte seu time e comece uma batalha antes de entrar num torneio.", parent=self,
                )
                self.app.show_frame(TeamSelectScreen)
                return
            tk.Label(self.body, text="Montando os rivais do torneio...", bg=BG, fg=MUTED_FG, font=FONT_BODY).pack(pady=20)
            entrants = [TOURNAMENT_PLAYER_NAME] + [f"Rival {i}" for i in range(1, self.ENTRANT_COUNT)]
            self.app.tournament = Tournament(entrants)
            self.app.run_in_background(self._build_ai_teams, self._ai_teams_ready, self._build_failed)
        else:
            self._render()

    def _build_ai_teams(self):
        species_pool = roster.list_all_species()
        teams = {}
        for name in self.app.tournament.entrants:
            if name == TOURNAMENT_PLAYER_NAME:
                continue
            picks = random.sample(species_pool, k=min(3, len(species_pool)))
            teams[name] = [roster.build_pokemon(species) for species in picks]
        return teams

    def _ai_teams_ready(self, teams):
        self.app.tournament_ai_teams = teams
        self._render()

    def _build_failed(self, exc):
        self.app.tournament = None
        messagebox.showinfo("Erro", f"Não consegui montar o torneio: {exc}", parent=self)
        self.app.show_frame(TeamSelectScreen)

    def _team_for(self, name):
        if name == TOURNAMENT_PLAYER_NAME:
            return self.app.player_team
        return self.app.tournament_ai_teams[name]

    def _auto_resolve_ai_only_matches(self):
        tournament = self.app.tournament
        round_index = tournament.current_round()
        for match_index, (a, b) in enumerate(tournament.pairings(round_index)):
            if match_index in tournament.results.get(round_index, {}):
                continue
            if TOURNAMENT_PLAYER_NAME in (a, b):
                continue
            winner_index = simulate_ai_battle(self._team_for(a), self._team_for(b), rng=random)
            tournament.record_result(round_index, match_index, a if winner_index == 0 else b)

    def _render(self):
        for child in self.body.winfo_children():
            child.destroy()
        tournament = self.app.tournament
        self._auto_resolve_ai_only_matches()

        if tournament.is_complete:
            champion = tournament.champion
            if champion == TOURNAMENT_PLAYER_NAME:
                text = "Você é o campeão do torneio!"
                save_data = save.load()
                for achievement in achievements.newly_unlocked(save_data, {"tournament_champion": True}):
                    save.add_achievement(achievement.id)
                    messagebox.showinfo(
                        "Conquista desbloqueada!", f"🏆 {achievement.name}\n{achievement.description}", parent=self,
                    )
            else:
                text = f"{champion} venceu o torneio."
            tk.Label(self.body, text=text, font=FONT_HEADING, bg=BG, fg=ACCENT).pack(pady=30)
            tk.Button(self.body, text="Novo torneio", font=FONT_HEADING, bg=ACCENT, command=self._restart).pack(pady=6)
            tk.Button(self.body, text="Voltar", font=FONT_BODY, command=self._back).pack()
            return

        round_index = tournament.current_round()
        tk.Label(
            self.body, text=f"Rodada {round_index + 1} de {tournament.total_rounds}", bg=BG, fg=FG, font=FONT_HEADING,
        ).pack(pady=(0, 8))

        for match_index, (a, b) in enumerate(tournament.pairings(round_index)):
            row = tk.Frame(self.body, bg=PANEL_BG, padx=12, pady=8)
            row.pack(fill="x", pady=4)
            done = match_index in tournament.results.get(round_index, {})
            if done:
                winner = tournament.results[round_index][match_index]
                tk.Label(row, text=f"{a}  vs  {b}   →   {winner} venceu", bg=PANEL_BG, fg=FG, font=FONT_BODY).pack(side="left")
            elif TOURNAMENT_PLAYER_NAME in (a, b):
                tk.Label(row, text=f"{a}  vs  {b}", bg=PANEL_BG, fg=FG, font=FONT_BODY).pack(side="left")
                tk.Button(
                    row, text="Lutar", font=FONT_BODY, bg=ACCENT,
                    command=lambda ri=round_index, mi=match_index, aa=a, bb=b: self._play_match(ri, mi, aa, bb),
                ).pack(side="right")
            else:
                tk.Label(row, text=f"{a}  vs  {b}", bg=PANEL_BG, fg=MUTED_FG, font=FONT_BODY).pack(side="left")

        tk.Button(self.body, text="Abandonar torneio", font=FONT_BODY, command=self._back).pack(pady=(10, 0))

    def _play_match(self, round_index, match_index, a, b):
        opponent_name = b if a == TOURNAMENT_PLAYER_NAME else a
        opponent_team = self._team_for(opponent_name)
        for mon in self.app.player_team:
            mon.cure_status()
            mon.current_hp = mon.max_hp
        self.app.enemy_team = opponent_team
        self.app.battle = Battle(self.app.player_team, opponent_team)
        self.app.show_frame(
            BattleScreen, tournament_ctx={"round": round_index, "match": match_index, "opponent_name": opponent_name},
        )

    def _restart(self):
        self.app.tournament = None
        self.app.tournament_ai_teams = {}
        self.app.show_frame(TournamentScreen)

    def _back(self):
        self.app.tournament = None
        self.app.tournament_ai_teams = {}
        self.app.show_frame(TeamSelectScreen)


class PvpTeamSelectScreen(tk.Frame):
    """Escolha de 1 Pokémon por jogador pro PvP local (item 5): hot-seat, os
    dois no mesmo computador, sem rede nenhuma entre eles. Fica em 1x1 de
    propósito — times de 6 exigiriam troca no meio da partida, e a Battle
    hoje só aceita golpe pro lado "enemy" (ver take_turn em battle.py)."""

    VISIBLE_LIMIT = 200

    def __init__(self, parent, app: PokeBattleApp, player_index=0, chosen_species=None):
        super().__init__(parent, bg=BG)
        self.app = app
        self.player_index = player_index
        self.chosen_species = list(chosen_species or [])
        self.all_species = None
        self.visible_species = []

        title = f"PvP Local — Jogador {player_index + 1}: escolha seu Pokémon"
        tk.Label(self, text=title, font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
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
        list_frame.pack(fill="both", expand=True, padx=48, pady=12)
        self.listbox = tk.Listbox(list_frame, activestyle="none", font=FONT_BODY)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Double-Button-1>", self._choose_selected)

        tk.Button(self, text="Escolher", font=FONT_HEADING, bg=ACCENT, command=self._choose_selected).pack(pady=8)
        tk.Button(
            self, text="Cancelar", font=FONT_BODY, command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack()

        self.app.run_in_background(roster.list_all_species, self._species_loaded, self._species_load_failed)

    def _species_loaded(self, species):
        self.all_species = species
        self.status_label.config(text=f"{len(species)} Pokémon disponíveis. Digite pra filtrar.")
        self._refresh_listbox(species[: self.VISIBLE_LIMIT])

    def _species_load_failed(self, exc):
        self.status_label.config(text="Não consegui carregar a lista de Pokémon. Verifique sua internet.")

    def _refresh_listbox(self, names):
        self.visible_species = names
        self.listbox.delete(0, tk.END)
        for name in names:
            self.listbox.insert(tk.END, roster.display_name(name))

    def _on_search_changed(self, *_args):
        if not self.all_species:
            return
        query = self.search_var.get().strip().lower()
        matches = [s for s in self.all_species if query in s.lower()] if query else self.all_species[: self.VISIBLE_LIMIT]
        self._refresh_listbox(matches[: self.VISIBLE_LIMIT])

    def _choose_selected(self, *_args):
        selection = self.listbox.curselection()
        if not selection:
            return
        species = self.visible_species[selection[0]]
        chosen = self.chosen_species + [species]
        if self.player_index == 0:
            self.app.show_frame(PvpPassDeviceScreen, next_species=chosen, next_player_index=1)
        else:
            self.status_label.config(text="Montando os dois Pokémon...")
            self.app.run_in_background(
                lambda: [roster.build_pokemon(chosen[0]), roster.build_pokemon(chosen[1])],
                self._pvp_teams_ready, self._species_load_failed,
            )

    def _pvp_teams_ready(self, mons):
        p1_mon, p2_mon = mons
        self.app.battle = Battle(p1_mon, p2_mon)
        self.app.show_frame(BattleScreen, pvp=True, player_names=("Jogador 1", "Jogador 2"))


class PvpPassDeviceScreen(tk.Frame):
    """Interstício "passe o computador" entre os dois jogadores do PvP
    local — evita que o Jogador 2 veja a escolha do Jogador 1 sem querer."""

    def __init__(self, parent, app: PokeBattleApp, next_species, next_player_index):
        super().__init__(parent, bg=BG)
        self.app = app
        tk.Label(self, text="Passe o computador", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(100, 12))
        tk.Label(
            self, text=f"Agora é a vez do Jogador {next_player_index + 1} escolher seu Pokémon.",
            bg=BG, fg=FG, font=FONT_BODY,
        ).pack(pady=(0, 24))
        tk.Button(
            self, text="Pronto", font=FONT_HEADING, bg=ACCENT,
            command=lambda: self.app.show_frame(
                PvpTeamSelectScreen, player_index=next_player_index, chosen_species=next_species,
            ),
        ).pack()


class ReplayListScreen(tk.Frame):
    """Lista os replays salvos (pokebattle/replay.py), do mais recente pro
    mais antigo."""

    def __init__(self, parent, app: PokeBattleApp):
        super().__init__(parent, bg=BG)
        self.app = app
        tk.Label(self, text="Replays", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))

        files = replay.list_replays()
        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=48, pady=16)
        if not files:
            tk.Label(
                list_frame, text="Nenhum replay salvo ainda. Jogue uma batalha até o fim!",
                bg=BG, fg=MUTED_FG, font=FONT_BODY,
            ).pack(pady=20)
        for path in files:
            try:
                data = replay.load_replay(path)
            except (OSError, ValueError):
                continue
            meta = data.get("metadata", {})
            label = f"{path.stem}  —  {meta.get('player', '?')} x {meta.get('enemy', '?')}  ({meta.get('result', '?')})"
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=12, pady=8)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, bg=PANEL_BG, fg=FG, font=FONT_BODY, anchor="w").pack(
                side="left", fill="x", expand=True,
            )
            tk.Button(
                row, text="Assistir", font=FONT_BODY, bg=ACCENT,
                command=lambda p=path: self.app.show_frame(ReplayPlayerScreen, path=p),
            ).pack(side="right")

        tk.Button(
            self, text="Voltar", font=FONT_HEADING, command=lambda: self.app.show_frame(TeamSelectScreen),
        ).pack(pady=(0, 20))


class ReplayPlayerScreen(tk.Frame):
    """Reproduz um replay salvo turno a turno — só os retratos gravados
    (ver pokebattle/replay.py), sem nenhuma Battle de verdade rodando."""

    def __init__(self, parent, app: PokeBattleApp, path):
        super().__init__(parent, bg=BG)
        self.app = app
        data = replay.load_replay(path)
        self.turns = data.get("turns", [])
        self.index = 0

        tk.Label(self, text="Replay", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24, 4))
        self.progress_label = tk.Label(self, text="", bg=BG, fg=MUTED_FG, font=FONT_BODY)
        self.progress_label.pack()
        self.state_label = tk.Label(self, text="", bg=BG, fg=FG, font=FONT_HEADING, justify="left")
        self.state_label.pack(pady=8)

        self.log_text = tk.Text(
            self, height=10, bg="#10151d", fg=FG, wrap="word", state="disabled", font=FONT_MONO,
        )
        self.log_text.pack(fill="both", expand=True, padx=24, pady=12)

        controls = tk.Frame(self, bg=BG)
        controls.pack(pady=(0, 16))
        tk.Button(controls, text="◀ Anterior", font=FONT_BODY, command=self._prev).pack(side="left", padx=4)
        tk.Button(controls, text="Próximo ▶", font=FONT_BODY, command=self._next).pack(side="left", padx=4)
        tk.Button(
            controls, text="Voltar", font=FONT_HEADING, command=lambda: self.app.show_frame(ReplayListScreen),
        ).pack(side="left", padx=12)

        self._render()

    def _render(self):
        if not self.turns:
            self.progress_label.config(text="Esse replay não tem turnos gravados.")
            return
        turn = self.turns[self.index]
        self.progress_label.config(text=f"Turno {self.index + 1} de {len(self.turns)}")
        player, enemy = turn["player"], turn["enemy"]
        self.state_label.config(
            text=f"{player['name']} Lv.{player['level']}  {player['current_hp']}/{player['max_hp']} HP"
                 f"     x     {enemy['name']} Lv.{enemy['level']}  {enemy['current_hp']}/{enemy['max_hp']} HP",
        )
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, f"{turn['description']}\n\n")
        for line in turn["log"]:
            self.log_text.insert(tk.END, line + "\n")
        self.log_text.config(state="disabled")

    def _prev(self):
        if self.index > 0:
            self.index -= 1
            self._render()

    def _next(self):
        if self.index < len(self.turns) - 1:
            self.index += 1
            self._render()


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
