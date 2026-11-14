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
    institution: bool = False
    requires: tuple[Technique, ...] = ()
    programme: bool = False


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
        B.CIVICS: Gate(),
    }
)

TECHNIQUES = MappingProxyType(
    {
        spec.technique: spec
        for spec in (
            TechniqueSpec(T.PHALANX_DRILL, B.WARFARE, 1, "Phalanx drill", "Pike lines and shield walls hold their ground."),
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
            TechniqueSpec(T.DRAINAGE, B.AGRICULTURE, 2, "Drainage", "Watered fields are drained so salt does not gather."),
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
            TechniqueSpec(T.CARTOGRAPHY, B.SEAFARING, 2, "Cartography", "Lands and coasts are drawn true on maps.", Gate(all_of=((B.WRITING, 1),))),
            TechniqueSpec(T.ORAL_LAW, B.CIVICS, 1, "Oral law", "Customs are recited and judged by elders."),
            TechniqueSpec(T.WRITTEN_LAW, B.CIVICS, 2, "Written law", "Laws are written down and read aloud.", Gate(all_of=((B.WRITING, 1),))),
            TechniqueSpec(T.CODIFIED_LAW, B.CIVICS, 3, "Codified law", "The laws are gathered into one code.", Gate(all_of=((B.WRITING, 2),))),
            TechniqueSpec(T.BUREAUCRACY, B.CIVICS, 3, "Bureaucracy", "Clerks and offices run the realm.", Gate(all_of=((B.WRITING, 2),)), institution=True),
            TechniqueSpec(T.CENSUS, B.CIVICS, 2, "Census", "Heads and hearths are counted."),
            TechniqueSpec(T.POSTAL_SERVICE, B.CIVICS, 3, "Postal service", "Riders carry letters along set roads."),
            TechniqueSpec(T.DIPLOMATIC_CORPS, B.CIVICS, 3, "Diplomatic corps", "Envoys are trained and kept abroad."),
            TechniqueSpec(T.STANDING_ARMY_ADMIN, B.CIVICS, 3, "Standing army administration", "Soldiers are paid and kept.", Gate(all_of=((B.WARFARE, 1),))),
            TechniqueSpec(T.DOUBLE_ENTRY, B.CIVICS, 3, "Double entry", "Every sum is booked twice and balanced.", Gate(all_of=((B.TRADE, 2),))),
            TechniqueSpec(T.JOINT_STOCK, B.CIVICS, 4, "Joint stock", "Many share the cost and gain of a venture.", Gate(all_of=((B.TRADE, 3),))),
            TechniqueSpec(T.INSURANCE, B.CIVICS, 4, "Insurance", "Losses at sea and on the road are shared.", Gate(all_of=((B.TRADE, 3),))),
            TechniqueSpec(T.GUILDS, B.CIVICS, 1, "Guilds", "Crafts bind themselves into sworn bodies."),
            TechniqueSpec(T.UNIVERSITIES, B.CIVICS, 3, "Universities", "Scholars gather to teach.", Gate(all_of=((B.WRITING, 2),)), institution=True),
            TechniqueSpec(
                T.EXAMINATIONS, B.CIVICS, 3, "Examinations", "Officials are chosen by tests of learning.", Gate(all_of=((B.WRITING, 2),)), institution=True
            ),
            TechniqueSpec(T.HOSPITALS, B.CIVICS, 3, "Hospitals", "The sick are tended in houses built for them.", Gate(all_of=((B.MEDICINE, 1),))),
            TechniqueSpec(T.PRINTING_PRESS, B.CIVICS, 4, "Printing houses", "Presses turn out books.", Gate(all_of=((B.WRITING, 4),)), institution=True),
            TechniqueSpec(T.ORGANISED_CLERGY, B.CIVICS, 1, "Organised clergy", "Priests are ranked and ordained."),
            TechniqueSpec(T.MONASTICISM, B.CIVICS, 2, "Monasticism", "Communities withdraw to pray, copy and work."),
            TechniqueSpec(T.THEOLOGY_SCHOOLS, B.CIVICS, 3, "Schools of theology", "Doctrine is taught and argued.", Gate(all_of=((B.WRITING, 1),))),
            TechniqueSpec(T.LOGIC, B.CIVICS, 1, "Logic", "Arguments are tested by rule."),
            TechniqueSpec(T.NATURAL_PHILOSOPHY, B.CIVICS, 2, "Natural philosophy", "The workings of the world are reasoned out."),
            TechniqueSpec(T.EMPIRICISM, B.CIVICS, 3, "Empiricism", "What is claimed is tried and observed.", Gate(all_of=((B.ASTRONOMY, 1),))),
            TechniqueSpec(T.HUMANIST_IDEALS, B.CIVICS, 4, "Humanist ideals", "The worth of each person is honoured.", Gate(all_of=((B.WRITING, 3),))),
            TechniqueSpec(T.GUNPOWDER, B.WARFARE, 5, "Gunpowder", "A burning powder throws shot and breaks rock.", Gate(all_of=((B.METALLURGY, 3),))),
            TechniqueSpec(
                T.FIREARMS, B.WARFARE, 6, "Firearms", "Soldiers carry guns that pierce armour.", Gate(all_of=((B.METALLURGY, 4),)), requires=(T.GUNPOWDER,)
            ),
            TechniqueSpec(T.CANNON, B.WARFARE, 6, "Cannon", "Great guns batter walls and ranks.", Gate(all_of=((B.METALLURGY, 5),)), requires=(T.GUNPOWDER,)),
            TechniqueSpec(
                T.STAR_FORTS, B.ARCHITECTURE, 6, "Star forts", "Low angled walls turn cannon shot.", Gate(all_of=((B.WARFARE, 5),)), requires=(T.CANNON,)
            ),
            TechniqueSpec(T.VOLLEY_DRILL, B.WARFARE, 7, "Volley drill", "Ranks load and fire by command.", Gate(), requires=(T.FIREARMS,)),
            TechniqueSpec(T.STEAM_POWER, B.METALLURGY, 6, "Steam power", "Boiling water drives engines.", Gate(all_of=((B.ARCHITECTURE, 4),))),
            TechniqueSpec(T.COKE_SMELTING, B.METALLURGY, 6, "Coke smelting", "Coal burned to coke smelts iron in great furnaces.", Gate()),
            TechniqueSpec(T.MACHINE_TOOLS, B.METALLURGY, 7, "Machine tools", "Machines cut parts to one measure.", Gate(), requires=(T.STEAM_POWER,)),
            TechniqueSpec(
                T.RAILWAYS, B.ARCHITECTURE, 7, "Railways", "Engines haul loads along iron rails.", Gate(all_of=((B.METALLURGY, 7),)), requires=(T.STEAM_POWER,)
            ),
            TechniqueSpec(
                T.STEAMSHIPS,
                B.SHIPBUILDING,
                6,
                "Steamships",
                "Ships sail against wind and current under steam.",
                Gate(all_of=((B.METALLURGY, 6),)),
                requires=(T.STEAM_POWER,),
            ),
            TechniqueSpec(
                T.FACTORY_PRODUCTION,
                B.TRADE,
                6,
                "Factory production",
                "Many hands and machines work under one roof.",
                Gate(all_of=((B.METALLURGY, 6),)),
                requires=(T.STEAM_POWER,),
            ),
            TechniqueSpec(
                T.INDUSTRIAL_CHEMISTRY,
                B.AGRICULTURE,
                6,
                "Industrial chemistry",
                "Acids, alkalis and fertilisers are made in bulk.",
                Gate(all_of=((B.METALLURGY, 6),)),
            ),
            TechniqueSpec(T.CANNED_FOOD, B.AGRICULTURE, 6, "Canned food", "Food sealed in tins keeps for years.", Gate(all_of=((B.METALLURGY, 5),))),
            TechniqueSpec(T.VACCINES, B.MEDICINE, 6, "Vaccines", "A mild exposure guards against a deadly sickness.", Gate(), requires=(T.INOCULATION,)),
            TechniqueSpec(
                T.ELECTRICITY,
                B.METALLURGY,
                8,
                "Electricity",
                "Current is made and carried along wires.",
                Gate(all_of=((B.ASTRONOMY, 5),)),
                requires=(T.STEAM_POWER,),
            ),
            TechniqueSpec(
                T.TELEGRAPH, B.WRITING, 7, "Telegraph", "Messages run along wires in an instant.", Gate(all_of=((B.METALLURGY, 8),)), requires=(T.ELECTRICITY,)
            ),
            TechniqueSpec(
                T.TELEPHONE, B.WRITING, 8, "Telephone", "Voices are carried along wires.", Gate(all_of=((B.METALLURGY, 8),)), requires=(T.TELEGRAPH,)
            ),
            TechniqueSpec(
                T.ELECTRIC_LIGHT,
                B.ARCHITECTURE,
                8,
                "Electric light",
                "Lamps burn without flame through the night.",
                Gate(all_of=((B.METALLURGY, 8),)),
                requires=(T.ELECTRICITY,),
            ),
            TechniqueSpec(
                T.REFRIGERATION, B.AGRICULTURE, 7, "Refrigeration", "Machines keep food cold.", Gate(all_of=((B.METALLURGY, 8),)), requires=(T.ELECTRICITY,)
            ),
            TechniqueSpec(
                T.COMBUSTION_ENGINE, B.METALLURGY, 8, "Combustion engine", "A burning fuel drives small engines.", Gate(), requires=(T.MACHINE_TOOLS,)
            ),
            TechniqueSpec(
                T.AVIATION, B.SKY_NAVIGATION, 5, "Aviation", "Winged machines fly.", Gate(all_of=((B.METALLURGY, 9),)), requires=(T.COMBUSTION_ENGINE,)
            ),
            TechniqueSpec(
                T.COMPUTATION,
                B.WRITING,
                9,
                "Computation",
                "Machines reckon faster than any clerk.",
                Gate(all_of=((B.ASTRONOMY, 7),)),
                requires=(T.ELECTRICITY,),
            ),
            TechniqueSpec(T.RADIO, B.WRITING, 8, "Radio", "Voices and signals cross the air.", Gate(all_of=((B.METALLURGY, 8),)), requires=(T.ELECTRICITY,)),
            TechniqueSpec(
                T.MASS_MEDIA, B.CIVICS, 8, "Mass media", "Papers and broadcasts reach every household.", Gate(all_of=((B.WRITING, 8),)), requires=(T.RADIO,)
            ),
            TechniqueSpec(T.ANTIBIOTICS, B.MEDICINE, 8, "Antibiotics", "Remedies kill the seeds of sickness.", Gate(), requires=(T.VACCINES,)),
            TechniqueSpec(
                T.GREEN_REVOLUTION,
                B.AGRICULTURE,
                9,
                "Bred and fed harvests",
                "New seed, fertiliser and water multiply harvests.",
                Gate(),
                requires=(T.INDUSTRIAL_CHEMISTRY,),
            ),
            TechniqueSpec(
                T.NUCLEAR_POWER,
                B.METALLURGY,
                10,
                "Nuclear power",
                "Split matter drives great engines.",
                Gate(all_of=((B.ASTRONOMY, 8),)),
                requires=(T.ELECTRICITY,),
                programme=True,
            ),
            TechniqueSpec(
                T.NUCLEAR_WEAPONS,
                B.WARFARE,
                10,
                "Nuclear weapons",
                "Weapons of split matter that can burn a land.",
                Gate(all_of=((B.METALLURGY, 10),)),
                requires=(T.NUCLEAR_POWER,),
                programme=True,
            ),
            TechniqueSpec(
                T.ROCKETRY,
                B.SKY_NAVIGATION,
                8,
                "Rocketry",
                "Rockets carry craft between worlds without magic.",
                Gate(all_of=((B.METALLURGY, 9),)),
                requires=(T.COMBUSTION_ENGINE,),
                programme=True,
            ),
            TechniqueSpec(
                T.GENETIC_ENGINEERING,
                B.MEDICINE,
                10,
                "Genetic engineering",
                "The inheritance of living things is rewritten.",
                Gate(all_of=((B.AGRICULTURE, 8),)),
                requires=(T.ANTIBIOTICS,),
                programme=True,
            ),
            TechniqueSpec(
                T.ARTIFICIAL_MINDS,
                B.WRITING,
                10,
                "Artificial minds",
                "Machines learn to think.",
                Gate(all_of=((B.ASTRONOMY, 8),)),
                requires=(T.COMPUTATION,),
                programme=True,
            ),
        )
    }
)
PROGRAMMES = frozenset(technique for technique, spec in TECHNIQUES.items() if spec.programme)
INSTITUTIONS = frozenset(technique for technique, spec in TECHNIQUES.items() if spec.institution) | {T.BANKING}

UNIT_TECHNIQUES = MappingProxyType(
    {
        UnitKind.PIKE_INFANTRY: T.PHALANX_DRILL,
        UnitKind.MOUNTED_ARCHERS: T.HORSE_ARCHERY,
        UnitKind.SAPPERS: T.SIEGECRAFT,
        UnitKind.SIEGE_CREW: T.SIEGECRAFT,
        UnitKind.NAVAL_CREW: T.SAILING,
        UnitKind.MARINES: T.SAILING,
        UnitKind.SKY_CREW: T.SKY_SAILING,
        UnitKind.SUMMONERS: T.SUMMONING,
        UnitKind.ENGINEERS: T.FORTIFICATION,
        UnitKind.CONSTRUCTS: T.ALCHEMY,
        UnitKind.CROSSBOW_INFANTRY: T.IRON,
        UnitKind.HEAVY_CAVALRY: T.IRON,
        UnitKind.GUNNERS: T.FIREARMS,
        UnitKind.MOUNTED_GUNNERS: T.FIREARMS,
        UnitKind.GRENADIERS: T.GUNPOWDER,
        UnitKind.ARTILLERY_CREW: T.CANNON,
        UnitKind.MECHANISED_INFANTRY: T.COMBUSTION_ENGINE,
        UnitKind.PILOTS: T.AVIATION,
        UnitKind.DRONE_OPERATORS: T.COMPUTATION,
        UnitKind.SIGNALS_TROOPS: T.RADIO,
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
        KnowledgeBranch.CIVICS: (SkillKind.LAW, SkillKind.LORE),
        KnowledgeBranch.VOID_LIVING: (SkillKind.NAVIGATION, SkillKind.MEDICINE),
        KnowledgeBranch.IMMORTALITY: (SkillKind.MEDICINE, SkillKind.ALCHEMY),
        KnowledgeBranch.BIOMANCY: (SkillKind.MEDICINE, SkillKind.ALCHEMY),
        KnowledgeBranch.FORBIDDEN: (SkillKind.SPELLCRAFT, SkillKind.LORE),
    }
)
