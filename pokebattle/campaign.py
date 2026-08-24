"""Slots offline de campanha e seleção compartilhada entre telas."""
import copy
from dataclasses import asdict
from datetime import datetime, timezone
from . import save
from .moves import Move
from .pokemon import Pokemon
from .team_validation import validate_team

_STATE_FIELDS = ("current_hp","status","sleep_turns","confusion_turns","stat_stages","experience",
                 "ability","held_item","species","pokedex_id","is_shiny","sprite_path")


def snapshot(team):
    from .teamcodec import pokemon_to_spec
    specs = [pokemon_to_spec(mon) for mon in team]
    validate_team(specs)
    return [{"spec": spec, "base_stats": dict(mon.base_stats), "types": list(mon.types),
             "moves": [asdict(move) for move in mon.moves],
             "state": {key: copy.deepcopy(getattr(mon,key)) for key in _STATE_FIELDS if hasattr(mon,key)}}
            for mon,spec in zip(team,specs)]


def restore(entries):
    if not isinstance(entries,list):
        raise ValueError("slot.team: esperado uma lista")
    validate_team([entry.get("spec") for entry in entries])
    team=[]
    for entry in entries:
        spec=entry["spec"]
        moves=[Move(**move) for move in entry["moves"]]
        if not 1 <= len(moves) <= 4:
            raise ValueError("slot.moves: informe de um a quatro golpes")
        mon=Pokemon(spec.get("nickname") or spec["species"],entry["types"],spec["level"],entry["base_stats"],moves,
                    ivs=spec["ivs"],evs=spec["evs"],nature=spec["nature"])
        for key,value in entry.get("state",{}).items():
            if key in _STATE_FIELDS:
                setattr(mon,key,value)
        team.append(mon)
    return team


def save_slot(slot,team):
    if slot not in ("1","2","3"):
        raise ValueError("Escolha um slot de 1 a 3.")
    entries=snapshot(team)  # valida antes de tocar o save
    data=save.load()
    slots=data.setdefault("slots",{})
    progress={key:copy.deepcopy(value) for key,value in data.items() if key not in ("slots","active_slot","schema_version")}
    slots[slot]={"schema_version":1,"saved_at":datetime.now(timezone.utc).isoformat(),"team":entries,"progress":progress}
    data.update(schema_version=2,active_slot=slot)
    save.write(data)


def load_slot(slot):
    data=save.load()
    record=data.get("slots",{}).get(slot)
    if not record or record.get("schema_version") != 1:
        raise ValueError("Slot vazio ou versão não suportada.")
    team=restore(record["team"])  # restaura tudo antes de alterar o progresso
    progress=copy.deepcopy(record["progress"])
    progress.update(schema_version=2,active_slot=slot,slots=data["slots"])
    save.write(progress)
    return team


class SelectionSession:
    def __init__(self):
        self.chosen=[]
        self.nicknames={}
        self.held_item_choices={}
        self.custom_builds={}
        self.borrowed={}

    def equip(self,index,item):
        previous=self.held_item_choices.get(index)
        save.transfer_equipment(previous,item)
        if item:
            self.held_item_choices[index]=item
            self.borrowed[index]=item
        else:
            self.held_item_choices.pop(index,None)
            self.borrowed.pop(index,None)
        if index in self.custom_builds:
            self.custom_builds[index].held_item=item

    def use_team(self,team):
        self.cancel()
        self.chosen[:]=[getattr(mon,"species",mon.name.lower()) for mon in team]
        self.nicknames.clear(); self.held_item_choices.clear(); self.custom_builds.clear()
        for index,mon in enumerate(team):
            self.nicknames[index]=mon.name
            self.custom_builds[index]=mon
            if getattr(mon,"held_item",None): self.held_item_choices[index]=mon.held_item

    def commit(self):
        self.borrowed.clear()

    def discard(self):
        """Desmontar a equipe devolve também equipamentos já salvos nela."""
        for index,item in list(self.held_item_choices.items()):
            if index in self.custom_builds and getattr(self.custom_builds[index],"held_item",None) != item:
                continue
            save.transfer_equipment(item,None)
            if index in self.custom_builds:self.custom_builds[index].held_item=None
        self.held_item_choices.clear()
        self.borrowed.clear()

    def cancel(self):
        # Só devolve equipamentos ainda não incorporados a uma campanha salva.
        for index,item in list(self.borrowed.items()):
            if index in self.custom_builds and getattr(self.custom_builds[index],"held_item",None) != item:
                continue  # consumido em batalha, não pode voltar ao inventário
            save.transfer_equipment(item,None)
            self.held_item_choices.pop(index,None)
            if index in self.custom_builds: self.custom_builds[index].held_item=None
        self.borrowed.clear()
