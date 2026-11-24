from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.mind import MELEE_SKILLS, MISSILE_SKILLS
from aerona.core.total import total
from aerona.domain.enums.military import CommandArea, CommanderTrait, UnitFamily
from aerona.domain.enums.mind import SkillKind

A = CommandArea
S = SkillKind


@dataclass(frozen=True)
class AreaSpec:
    label: str
    lead: SkillKind
    support: tuple[SkillKind, ...]
    effect: str


AREAS: MappingProxyType[CommandArea, AreaSpec] = total(
    CommandArea,
    {
        A.FIRE: AreaSpec("Fire", S.TACTICS, MISSILE_SKILLS, "missile stacks strike harder"),
        A.SHOCK: AreaSpec("Shock", S.TACTICS, MELEE_SKILLS, "melee stacks and charges strike harder"),
        A.MANOEUVRE: AreaSpec("Manoeuvre", S.STRATEGY, (S.TACTICS,), "fewer are cut down in a rout and ships and fliers strike harder"),
        A.SIEGE: AreaSpec("Siege", S.SIEGECRAFT, (S.ENGINEERING,), "engineers strike harder and walls fall sooner"),
        A.LOGISTICS: AreaSpec("Logistics", S.LOGISTICS, (S.STRATEGY,), "the army eats less of its stores"),
        A.INTELLIGENCE: AreaSpec("Intelligence", S.INTRIGUE, (S.LANGUAGES,), "scouts and spies read the field before battle"),
    },
)

TRAIT_AREAS: MappingProxyType[CommanderTrait, dict[CommandArea, int]] = total(
    CommanderTrait,
    {
        CommanderTrait.AGGRESSIVE_ASSAULTER: {A.SHOCK: 20},
        CommanderTrait.DEFENSIVE_GENIUS: {A.FIRE: 10, A.MANOEUVRE: 10},
        CommanderTrait.CAVALRY_MASTER: {A.SHOCK: 10, A.MANOEUVRE: 15},
        CommanderTrait.WINTER_CAMPAIGNER: {A.LOGISTICS: 15},
        CommanderTrait.HILL_FIGHTER: {A.MANOEUVRE: 10},
        CommanderTrait.SIEGE_EXPERT: {A.SIEGE: 25},
        CommanderTrait.RECKLESS: {A.SHOCK: 10, A.LOGISTICS: -10},
        CommanderTrait.CAUTIOUS: {A.MANOEUVRE: 10, A.SHOCK: -5},
        CommanderTrait.INSPIRING: {A.SHOCK: 5, A.FIRE: 5},
        CommanderTrait.BRUTAL: {A.SHOCK: 10},
        CommanderTrait.FOREST_FIGHTER: {A.MANOEUVRE: 10, A.SHOCK: 5},
        CommanderTrait.DESERT_FIGHTER: {A.LOGISTICS: 10, A.MANOEUVRE: 5},
        CommanderTrait.MARSH_FIGHTER: {A.MANOEUVRE: 10, A.LOGISTICS: 5},
        CommanderTrait.SKY_COMMANDER: {A.MANOEUVRE: 15, A.FIRE: 5},
        CommanderTrait.SPACE_COMMANDER: {A.MANOEUVRE: 15, A.FIRE: 5},
        CommanderTrait.ARTILLERIST: {A.FIRE: 20, A.SIEGE: 5},
        CommanderTrait.AMBUSHER: {A.MANOEUVRE: 10, A.SHOCK: 10},
        CommanderTrait.LOGISTICIAN: {A.LOGISTICS: 25},
        CommanderTrait.UNDERGROUND_FIGHTER: {A.SHOCK: 10, A.SIEGE: 10},
        CommanderTrait.AMPHIBIOUS_COMMANDER: {A.MANOEUVRE: 15, A.LOGISTICS: 5},
        CommanderTrait.SIEGE_DEFENDER: {A.FIRE: 10, A.SIEGE: 15},
        CommanderTrait.SKIRMISHER: {A.FIRE: 10, A.MANOEUVRE: 10},
        CommanderTrait.ARMOURED_COMMANDER: {A.SHOCK: 15, A.MANOEUVRE: 5},
        CommanderTrait.DISCIPLINARIAN: {A.FIRE: 5, A.SHOCK: 5, A.LOGISTICS: 5},
        CommanderTrait.SIGNALS_COMMANDER: {A.MANOEUVRE: 10, A.FIRE: 10},
        CommanderTrait.NIGHT_FIGHTER: {A.SHOCK: 10, A.MANOEUVRE: 10},
        CommanderTrait.JUNGLE_FIGHTER: {A.MANOEUVRE: 10, A.SHOCK: 5},
        CommanderTrait.COLD_FIGHTER: {A.LOGISTICS: 10, A.SHOCK: 5},
        CommanderTrait.RIVER_CROSSER: {A.MANOEUVRE: 15},
    },
)

FAMILY_AREA: MappingProxyType[UnitFamily, CommandArea | None] = total(
    UnitFamily,
    {
        UnitFamily.INFANTRY: A.SHOCK,
        UnitFamily.MISSILE: A.FIRE,
        UnitFamily.MOUNTED: A.SHOCK,
        UnitFamily.BEAST: A.SHOCK,
        UnitFamily.ENGINEER: A.SIEGE,
        UnitFamily.MAGIC: None,
        UnitFamily.VEHICLE: A.MANOEUVRE,
        UnitFamily.EXOTIC: A.SHOCK,
        UnitFamily.AIR: A.FIRE,
        UnitFamily.SPACE: A.MANOEUVRE,
        UnitFamily.ELECTRONIC: A.FIRE,
        UnitFamily.SPECIAL: A.MANOEUVRE,
    },
)
