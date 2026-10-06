import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pokebattle import campaign, save, teamcodec
from pokebattle.data import create_pokemon


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=patch.object(save,"SAVE_PATH",Path(self.tmp.name)/"save.json")
        self.path.start()
    def tearDown(self):
        self.path.stop(); self.tmp.cleanup()

    def test_equipment_survives_screen_reference_changes_and_cancel_is_idempotent(self):
        data=save.load(); data["items"]={"held_leftovers":1}; save.write(data)
        session=campaign.SelectionSession()
        session.chosen.append("pikachu")
        session.equip(0,"held_leftovers")
        screen_a=session.held_item_choices
        screen_b=session.held_item_choices
        self.assertIs(screen_a,screen_b)
        self.assertEqual(save.load()["items"]["held_leftovers"]+list(screen_b.values()).count("held_leftovers"),1)
        session.cancel(); session.cancel()
        self.assertEqual(save.load()["items"]["held_leftovers"],1)
        self.assertEqual(session.held_item_choices,{})

    def test_unavailable_equipment_changes_nothing(self):
        data=save.load(); save.write(data)
        session=campaign.SelectionSession()
        before=save.SAVE_PATH.read_bytes()
        with self.assertRaisesRegex(ValueError,"disponível"): session.equip(0,"held_leftovers")
        self.assertEqual(save.SAVE_PATH.read_bytes(),before)
        self.assertEqual(session.held_item_choices,{})

    def test_slots_restore_complete_team_offline_and_preserve_legacy(self):
        legacy={"money":321,"items":{"held_leftovers":0},"trainer_name":"Ficticio","starter":"pikachu"}
        save.SAVE_PATH.write_text(json.dumps(legacy),encoding="utf8")
        mon=create_pokemon("pikachu"); mon.species="pikachu"; mon.name="Faísca"; mon.experience=123; mon.held_item="held_leftovers"
        mon.current_hp=10
        campaign.save_slot("1",[mon])
        self.assertEqual(json.loads(save.SAVE_PATH.with_suffix(".json.legacy.bak").read_text("utf8")),legacy)
        other=create_pokemon("charmander"); other.species="charmander"
        data=save.load();data["money"]=999;save.write(data)
        campaign.save_slot("2",[other])
        with patch("pokebattle.roster.build_pokemon",side_effect=AssertionError("rede proibida")):
            team=campaign.load_slot("1")
        restored=team[0]
        self.assertEqual((restored.name,restored.experience,restored.held_item,restored.current_hp),("Faísca",123,"held_leftovers",10))
        self.assertEqual([m.name for m in restored.moves],[m.name for m in mon.moves])
        self.assertEqual(restored.ivs,mon.ivs);self.assertEqual(restored.evs,mon.evs)
        self.assertEqual(save.load()["money"],321)
        self.assertEqual(len(save.load()["slots"]),2)

    def test_bad_slot_does_not_replace_progress(self):
        data=save.load();save.write(data)
        before=save.SAVE_PATH.read_bytes()
        with self.assertRaises(ValueError):campaign.load_slot("3")
        self.assertEqual(save.SAVE_PATH.read_bytes(),before)

    def test_consumed_equipment_is_not_returned_on_unsaved_exit(self):
        data=save.load();data["items"]={"held_cheri_berry":1};save.write(data)
        session=campaign.SelectionSession();session.chosen.append("pikachu")
        session.equip(0,"held_cheri_berry")
        mon=create_pokemon("pikachu");mon.held_item=None
        session.custom_builds[0]=mon
        session.cancel()
        self.assertEqual(save.load()["items"]["held_cheri_berry"],0)
        self.assertEqual(session.borrowed,{})

    def test_discarding_saved_party_returns_committed_equipment_once(self):
        data=save.load();data["items"]={"held_leftovers":0};save.write(data)
        mon=create_pokemon("pikachu");mon.held_item="held_leftovers"
        session=campaign.SelectionSession();session.use_team([mon])
        session.discard();session.discard()
        self.assertEqual(save.load()["items"]["held_leftovers"],1)
        self.assertIsNone(mon.held_item)


class ImportValidationTests(unittest.TestCase):
    def test_all_invalid_fields_rejected_before_network(self):
        cases=[("Level: 0","level"),("Level: 999","level"),("IVs: -1 HP","ivs.hp"),("IVs: 32 Atk","ivs.attack"),
               ("EVs: 252 HP / 252 Atk / 252 Def","soma máxima"),("- a\n- b\n- c\n- d\n- e","moves")]
        for text,field in cases:
            with self.subTest(text=text),patch("pokebattle.roster.build_pokemon") as fetch:
                with self.assertRaisesRegex(ValueError,field):teamcodec.build_team_from_text("Pikachu\n"+text)
                fetch.assert_not_called()

    def test_valid_limits_and_later_invalid_member_prevent_partial_fetch(self):
        valid="Pikachu\nLevel: 100\nIVs: 31 HP\nEVs: 252 HP / 252 Atk / 6 Def\n- Tackle"
        self.assertEqual(teamcodec.text_to_specs(valid)[0]["evs"]["defense"],6)
        with patch("pokebattle.roster.build_pokemon") as fetch:
            with self.assertRaises(ValueError):teamcodec.build_team_from_text(valid+"\n\nCharmander\nLevel: 999")
            fetch.assert_not_called()

if __name__=="__main__":unittest.main()
