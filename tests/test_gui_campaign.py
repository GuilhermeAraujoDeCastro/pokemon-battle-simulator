"""Jornadas Tk reais, ativadas explicitamente com RUN_TK_TESTS=1."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import main_gui as gui
from pokebattle import save,roster,audio
from pokebattle.data import create_pokemon


@unittest.skipUnless(os.environ.get("RUN_TK_TESTS")=="1","Requer sessão gráfica e RUN_TK_TESTS=1")
class GuiCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.patches=[];self.apps=[]
        def build(species,*a,**kw):
            mon=create_pokemon(species);mon.species=species;mon.held_item=None;return mon
        changes=[patch.object(save,"SAVE_PATH",Path(self.tmp.name)/"save.json"),patch.object(roster,"build_pokemon",build),
                 patch.object(roster,"list_all_species",return_value=["pikachu"]),
                 patch.object(roster,"list_all_species_with_dex_numbers",return_value=[(25,"pikachu")]),
                 patch.object(audio,"stop_music"),patch.object(gui.PokeBattleApp,"run_in_background",lambda app,work,done,error=None: done(work()))]
        for change in changes:change.start();self.patches.append(change)
        data=save.load();data.update(trainer_name="Fictício",starter="pikachu",items={"held_leftovers":1});save.write(data)
    def tearDown(self):
        for app in self.apps:
            try:app.destroy()
            except gui.tk.TclError:pass
        for change in reversed(self.patches):change.stop()
        self.tmp.cleanup()
    def open(self):
        app=gui.PokeBattleApp();app.withdraw();app.update();self.apps.append(app);return app
    def equip(self,app):
        selection=app.container.winfo_children()[0];selection.team_list.selection_set(0)
        selection._equip_item_selected()
        dialog=next(child for child in selection.winfo_children() if isinstance(child,gui.tk.Toplevel))
        next(child for child in dialog.winfo_children() if isinstance(child,gui.tk.Button) and child.cget("text").startswith("Leftovers")).invoke()
        return selection

    def test_equipment_pokedex_return_exit_preserves_exactly_one_copy(self):
        app=self.open();self.equip(app)
        app.show_frame(gui.PokedexScreen);returned=app.show_frame(gui.TeamSelectScreen)
        self.assertEqual(returned.held_item_choices,{0:"held_leftovers"})
        self.assertEqual(save.load()["items"]["held_leftovers"],0)
        app._close_campaign()
        self.assertEqual(save.load()["items"]["held_leftovers"],1)

    def test_save_close_reopen_restores_team_xp_nickname_equipment(self):
        app=self.open();selection=self.equip(app);selection.nicknames[0]="Faísca"
        selection._save_slot()
        app.player_team[0].experience=123
        app._close_campaign()
        reopened=self.open();mon=reopened.player_team[0]
        self.assertEqual((mon.name,mon.experience,mon.held_item),("Faísca",123,"held_leftovers"))
        self.assertEqual(save.load()["items"]["held_leftovers"],0)

if __name__=="__main__":unittest.main()
