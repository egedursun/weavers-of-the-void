from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.culture import Technique
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch

B = KnowledgeBranch
T = Technique
Need = tuple[KnowledgeBranch, int]


@dataclass(frozen=True)
class Gate:
    all_of: tuple[Need, ...] = ()
    any_of: tuple[Need, ...] = ()


@dataclass(frozen=True)
class TechniqueSpec:
    technique: Technique
    branch: KnowledgeBranch
    level: int
    label: str
    effect: str
    gate: Gate = Gate()


BRANCH_GRAPH = MappingProxyType(
    {
        B.AGRICULTURE: Gate(),
        B.METALLURGY: Gate(any_of=((B.AGRICULTURE, 1), (B.TRADE, 1))),
        B.SEAFARING: Gate(any_of=((B.TRADE, 1), (B.ASTRONOMY, 1))),
        B.WRITING: Gate(any_of=((B.TRADE, 1), (B.AGRICULTURE, 2))),
        B.ARCHITECTURE: Gate(all_of=((B.AGRICULTURE, 1),)),
        B.MEDICINE: Gate(any_of=((B.AGRICULTURE, 1), (B.MAGIC, 1))),
        B.MAGIC: Gate(),
        B.WARFARE: Gate(),
        B.ASTRONOMY: Gate(any_of=((B.WRITING, 1), (B.AGRICULTURE, 2))),
        B.TRADE: Gate(),
        B.SKY_NAVIGATION: Gate(all_of=((B.ASTRONOMY, 2),)),
        B.SHIPBUILDING: Gate(all_of=((B.SEAFARING, 2), (B.METALLURGY, 1))),
        B.GATE_LORE: Gate(all_of=((B.MAGIC, 2), (B.ASTRONOMY, 1))),
        B.PATHFINDING: Gate(all_of=((B.SKY_NAVIGATION, 2), (B.GATE_LORE, 1))),
        B.VOID_LIVING: Gate(all_of=((B.SKY_NAVIGATION, 1), (B.SHIPBUILDING, 1), (B.MEDICINE, 2))),
        B.IMMORTALITY: Gate(all_of=((B.MEDICINE, 3), (B.MAGIC, 2))),
        B.BIOMANCY: Gate(all_of=((B.MAGIC, 2), (B.MEDICINE, 2), (B.AGRICULTURE, 2))),
        B.FORBIDDEN: Gate(all_of=((B.MAGIC, 3),)),
    }
)

TECHNIQUES = MappingProxyType(
    {
        spec.technique: spec
        for spec in (
            TechniqueSpec(T.PHALANX_DRILL, B.WARFARE, 1, "Phalanx drill", "Pikemen and shield walls hold their line."),
            TechniqueSpec(T.HORSE_ARCHERY, B.WARFARE, 2, "Horse archery", "Riders shoot from the saddle.", Gate(all_of=((B.AGRICULTURE, 1),))),
            TechniqueSpec(T.SIEGECRAFT, B.WARFARE, 2, "Siegecraft", "Sappers and engines take walls.", Gate(all_of=((B.ARCHITECTURE, 1),))),
            TechniqueSpec(T.FORTIFICATION, B.ARCHITECTURE, 2, "Fortification", "Walls rise higher and hold longer."),
            TechniqueSpec(T.LOGISTICS, B.WARFARE, 3, "Logistics", "Armies carry more and march farther.", Gate(all_of=((B.WRITING, 1),))),
            TechniqueSpec(T.HERBALISM, B.MEDICINE, 1, "Herbalism", "Herbs ease fevers and wounds."),
            TechniqueSpec(T.SURGERY, B.MEDICINE, 2, "Surgery", "Healers cut out what festers.", Gate(all_of=((B.METALLURGY, 1),))),
            TechniqueSpec(T.AMPUTATION, B.MEDICINE, 2, "Amputation", "A rotten limb is taken to save a life."),
            TechniqueSpec(T.PROSTHETICS, B.MEDICINE, 3, "Prosthetics", "The maimed walk and grip again.", Gate(any_of=((B.METALLURGY, 2), (B.MAGIC, 2)))),
            TechniqueSpec(T.QUARANTINE, B.MEDICINE, 2, "Quarantine", "The sick are shut away from the well."),
            TechniqueSpec(T.INOCULATION, B.MEDICINE, 4, "Inoculation", "A small sickness wards off the great one."),
            TechniqueSpec(T.IRRIGATION, B.AGRICULTURE, 1, "Irrigation", "Water is led to dry fields."),
            TechniqueSpec(T.CROP_ROTATION, B.AGRICULTURE, 2, "Crop rotation", "Fields rest and yield more."),
            TechniqueSpec(T.TERRACING, B.AGRICULTURE, 2, "Terracing", "Hills are cut into fields.", Gate(all_of=((B.ARCHITECTURE, 1),))),
            TechniqueSpec(T.PLOUGH, B.AGRICULTURE, 1, "The plough", "Beasts turn the soil.", Gate(any_of=((B.METALLURGY, 1),))),
            TechniqueSpec(T.SELECTIVE_BREEDING, B.AGRICULTURE, 3, "Selective breeding", "Herds and crops are bred for strength."),
            TechniqueSpec(T.BRONZE, B.METALLURGY, 1, "Bronze", "Copper and tin are cast into arms."),
            TechniqueSpec(T.IRON, B.METALLURGY, 2, "Iron", "Iron is smelted and forged."),
            TechniqueSpec(T.STEEL, B.METALLURGY, 3, "Steel", "Iron is hardened into steel."),
            TechniqueSpec(T.SKYSTEEL, B.METALLURGY, 5, "Skysteel", "Star-fallen metal is worked.", Gate(all_of=((B.MAGIC, 2),))),
            TechniqueSpec(T.ARCH, B.ARCHITECTURE, 1, "The arch", "Stone spans gaps."),
            TechniqueSpec(T.DOME, B.ARCHITECTURE, 3, "The dome", "Great halls are vaulted."),
            TechniqueSpec(T.AQUEDUCT, B.ARCHITECTURE, 3, "The aqueduct", "Water flows to cities from far hills."),
            TechniqueSpec(T.FORTRESS, B.ARCHITECTURE, 4, "The fortress", "Castles command the land.", Gate(all_of=((B.WARFARE, 2),))),
            TechniqueSpec(T.ALPHABET, B.WRITING, 1, "The alphabet", "A few letters write any word."),
            TechniqueSpec(T.PAPER, B.WRITING, 2, "Paper", "Writing is cheap and books multiply."),
            TechniqueSpec(T.PRINTING, B.WRITING, 4, "Printing", "Books are made by the hundred.", Gate(all_of=((B.METALLURGY, 2),))),
            TechniqueSpec(
                T.CRYPTOGRAPHY, B.WRITING, 3, "Cryptography", "Letters are written in ciphers only their readers can break.", Gate(all_of=((B.TRADE, 2),))
            ),
            TechniqueSpec(T.CALENDAR, B.ASTRONOMY, 1, "The calendar", "Seasons and holy days are counted."),
            TechniqueSpec(T.NAVIGATION_STARS, B.ASTRONOMY, 2, "Star navigation", "Ships steer by the stars.", Gate(all_of=((B.SEAFARING, 1),))),
            TechniqueSpec(T.ECLIPSE_PREDICTION, B.ASTRONOMY, 3, "Eclipse prediction", "Darkenings of the sun are foretold."),
            TechniqueSpec(T.SAILING, B.SEAFARING, 1, "Sailing", "Wind carries the ships."),
            TechniqueSpec(T.SHIPWRIGHTING, B.SHIPBUILDING, 1, "Shipwrighting", "Hulls for open seas and war."),
            TechniqueSpec(T.COINAGE, B.TRADE, 1, "Coinage", "Metal is struck into money.", Gate(all_of=((B.METALLURGY, 1),))),
            TechniqueSpec(T.BANKING, B.TRADE, 3, "Banking", "Credit and loans bind the markets.", Gate(all_of=((B.WRITING, 2),))),
            TechniqueSpec(T.WARDING, B.MAGIC, 2, "Warding", "Spells guard walls and homes."),
            TechniqueSpec(T.SUMMONING, B.MAGIC, 3, "Summoning", "Beings are called from elsewhere."),
            TechniqueSpec(T.SKY_SAILING, B.SKY_NAVIGATION, 1, "Sky sailing", "Ships sail the air between worlds."),
            TechniqueSpec(T.NECROMANCY, B.FORBIDDEN, 1, "Necromancy", "The dead are raised to serve."),
            TechniqueSpec(T.ALCHEMY, B.MAGIC, 2, "Alchemy", "Matter is changed by art.", Gate(all_of=((B.METALLURGY, 1),))),
            TechniqueSpec(
                T.ASTRONOMY_INSTRUMENTS,
                B.ASTRONOMY,
                2,
                "Instruments of the sky",
                "Astrolabes and sundials measure the heavens.",
                Gate(all_of=((B.METALLURGY, 1),)),
            ),
        )
    }
)

UNIT_TECHNIQUES = MappingProxyType(
    {
        UnitKind.PIKEMEN: T.PHALANX_DRILL,
        UnitKind.HORSE_ARCHERS: T.HORSE_ARCHERY,
        UnitKind.SAPPERS: T.SIEGECRAFT,
        UnitKind.SIEGE_ENGINES: T.SIEGECRAFT,
        UnitKind.LONGSHIPS: T.SAILING,
        UnitKind.GALLEYS: T.SAILING,
        UnitKind.WARSHIPS: T.SHIPWRIGHTING,
        UnitKind.FIRE_SHIPS: T.SHIPWRIGHTING,
        UnitKind.SKYSHIPS: T.SKY_SAILING,
        UnitKind.NECROMANCERS: T.NECROMANCY,
        UnitKind.GHOST_HOST: T.NECROMANCY,
        UnitKind.GOLEMS: T.ALCHEMY,
        UnitKind.CROSSBOWMEN: T.IRON,
        UnitKind.HEAVY_CAVALRY: T.IRON,
    }
)


BRANCH_SKILLS: MappingProxyType[KnowledgeBranch, tuple[SkillKind, ...]] = MappingProxyType(
    {
        KnowledgeBranch.AGRICULTURE: (SkillKind.FORAGING, SkillKind.BEAST_HANDLING),
        KnowledgeBranch.METALLURGY: (SkillKind.SMITHING, SkillKind.JEWELLING),
        KnowledgeBranch.SEAFARING: (SkillKind.SAILING, SkillKind.NAVIGATION),
        KnowledgeBranch.WRITING: (SkillKind.WRITING, SkillKind.LANGUAGES),
        KnowledgeBranch.ARCHITECTURE: (SkillKind.MASONRY, SkillKind.ENGINEERING),
        KnowledgeBranch.MEDICINE: (SkillKind.MEDICINE, SkillKind.SURGERY),
        KnowledgeBranch.MAGIC: (SkillKind.SPELLCRAFT, SkillKind.RITUAL),
        KnowledgeBranch.WARFARE: (SkillKind.TACTICS, SkillKind.STRATEGY),
        KnowledgeBranch.ASTRONOMY: (SkillKind.ASTRONOMY,),
        KnowledgeBranch.TRADE: (SkillKind.NEGOTIATION, SkillKind.ACCOUNTING),
        KnowledgeBranch.SKY_NAVIGATION: (SkillKind.NAVIGATION, SkillKind.ASTRONOMY),
        KnowledgeBranch.SHIPBUILDING: (SkillKind.SHIPWRIGHT, SkillKind.CARPENTRY),
        KnowledgeBranch.GATE_LORE: (SkillKind.LORE, SkillKind.SPELLCRAFT),
        KnowledgeBranch.PATHFINDING: (SkillKind.TRACKING, SkillKind.NAVIGATION),
    }
)
