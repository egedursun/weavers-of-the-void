from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.mythic import CosmicOffice, GeasLayer, GeasMode, MythicRealm, QuestTrial

C = CosmicOffice
F = SpellForm
D = Domain

OFFICE_FORMS = total(
    CosmicOffice,
    {
        C.DEAD: frozenset({F.DEATH, F.SPIRIT}),
        C.GATES: frozenset({F.AIR, F.VOID}),
        C.STARS: frozenset({F.LIGHT, F.TIME}),
        C.OATHS: frozenset({F.MIND}),
        C.HERALD: frozenset({F.IMAGE}),
        C.HUNT: frozenset({F.ANIMAL, F.PLANT}),
    },
)

OFFICE_DOMAINS = total(
    CosmicOffice,
    {
        C.DEAD: frozenset({D.DEATH, D.BONE, D.MEMORY, D.SLEEP}),
        C.GATES: frozenset({D.ROAD, D.BORDER, D.TRADE}),
        C.STARS: frozenset({D.STAR, D.MOON, D.SUN, D.SKY}),
        C.OATHS: frozenset({D.OATH, D.KNOWLEDGE}),
        C.HERALD: frozenset({D.SOUND, D.DREAM}),
        C.HUNT: frozenset({D.HUNT, D.PLANTS, D.HARVEST}),
    },
)

GEAS_ACTS = total(
    GeasMode,
    {
        GeasMode.TABOO: (
            ActKind.OATHBREAKING,
            ActKind.GUEST_KILLING,
            ActKind.COWARDICE,
            ActKind.THEFT,
            ActKind.KILLING_KIN,
            ActKind.DESECRATION,
            ActKind.BETRAYAL,
            ActKind.TORTURE,
            ActKind.MAGIC_USE,
            ActKind.HOARDING_IN_FAMINE,
        ),
        GeasMode.DUTY: (ActKind.HOSPITALITY, ActKind.MERCY_TO_ENEMY, ActKind.BUILDING_TEMPLES, ActKind.LEARNING),
    },
)

QUEST_PARTY_MAX = 12

A = LegendArchetype
Q = QuestTrial

ARCHETYPE_REALMS = total(
    LegendArchetype,
    {
        A.HERO_QUEST: MythicRealm.PALACE,
        A.MONSTER: MythicRealm.PALACE,
        A.TRICKSTER: MythicRealm.DREAM,
        A.CREATION: MythicRealm.PALACE,
        A.WORLD_DISASTER: MythicRealm.PALACE,
        A.BETRAYAL: MythicRealm.DREAM,
        A.LOST_GOLDEN_AGE: MythicRealm.DREAM,
        A.CHOSEN_ONE: MythicRealm.PALACE,
        A.CURSED_LINE: MythicRealm.DEAD,
        A.RETURN_OF_A_RULER: MythicRealm.DEAD,
        A.HAUNTED_PLACE: MythicRealm.DEAD,
        A.FOUNDING: MythicRealm.PALACE,
        A.EXILE: MythicRealm.DREAM,
        A.TRANSFORMATION: MythicRealm.DREAM,
        A.BARGAIN: MythicRealm.DEAD,
        A.SACRIFICE: MythicRealm.PALACE,
        A.RIVALRY: MythicRealm.PALACE,
        A.DISCOVERY: MythicRealm.DREAM,
        A.DECEPTION: MythicRealm.DREAM,
        A.UNION: MythicRealm.PALACE,
        A.ASCENT: MythicRealm.PALACE,
        A.FALL: MythicRealm.DEAD,
    },
)

ARCHETYPE_TRIALS = total(
    LegendArchetype,
    {
        A.HERO_QUEST: (Q.SKILL, Q.PASSION, Q.FAITH),
        A.MONSTER: (Q.SKILL, Q.CONVICTION, Q.ENDURANCE),
        A.TRICKSTER: (Q.CUNNING, Q.SKILL, Q.CUNNING),
        A.CREATION: (Q.FAITH, Q.SKILL, Q.FAITH),
        A.WORLD_DISASTER: (Q.ENDURANCE, Q.SKILL, Q.FAITH),
        A.BETRAYAL: (Q.PASSION, Q.CONVICTION, Q.SKILL),
        A.LOST_GOLDEN_AGE: (Q.FAITH, Q.PASSION, Q.SKILL),
        A.CHOSEN_ONE: (Q.FAITH, Q.CONVICTION, Q.SKILL),
        A.CURSED_LINE: (Q.PASSION, Q.FAITH, Q.SKILL),
        A.RETURN_OF_A_RULER: (Q.CONVICTION, Q.SKILL, Q.PASSION),
        A.HAUNTED_PLACE: (Q.CONVICTION, Q.SKILL, Q.FAITH),
        A.FOUNDING: (Q.SKILL, Q.CONVICTION, Q.FAITH),
        A.EXILE: (Q.ENDURANCE, Q.PASSION, Q.SKILL),
        A.TRANSFORMATION: (Q.FAITH, Q.SKILL, Q.PASSION),
        A.BARGAIN: (Q.CONVICTION, Q.CUNNING, Q.FAITH),
        A.SACRIFICE: (Q.FAITH, Q.ENDURANCE, Q.CONVICTION),
        A.RIVALRY: (Q.SKILL, Q.PASSION, Q.SKILL),
        A.DISCOVERY: (Q.SKILL, Q.CUNNING, Q.CONVICTION),
        A.DECEPTION: (Q.CUNNING, Q.CONVICTION, Q.SKILL),
        A.UNION: (Q.PASSION, Q.FAITH, Q.SKILL),
        A.ASCENT: (Q.ENDURANCE, Q.FAITH, Q.SKILL),
        A.FALL: (Q.PASSION, Q.CONVICTION, Q.FAITH),
    },
)


CUNNING_SKILLS = frozenset({SkillKind.DECEPTION, SkillKind.INTRIGUE})


def trial_at(archetype: LegendArchetype | None, step: int) -> QuestTrial:
    trials = ARCHETYPE_TRIALS[archetype] if archetype is not None else (QuestTrial.SKILL,)
    return trials[step % len(trials)]


ARCHETYPE_SKILLS = total(
    LegendArchetype,
    {
        A.HERO_QUEST: frozenset({SkillKind.BLADE, SkillKind.SPEAR, SkillKind.LEADERSHIP, SkillKind.TACTICS}),
        A.MONSTER: frozenset({SkillKind.BLADE, SkillKind.SPEAR, SkillKind.AXE, SkillKind.BOW, SkillKind.HUNTING}),
        A.TRICKSTER: frozenset({SkillKind.DECEPTION, SkillKind.INTRIGUE, SkillKind.ORATORY}),
        A.CREATION: frozenset({SkillKind.RITUAL, SkillKind.LORE, SkillKind.THEOLOGY}),
        A.WORLD_DISASTER: frozenset({SkillKind.SAILING, SkillKind.SWIMMING, SkillKind.ENGINEERING}),
        A.BETRAYAL: frozenset({SkillKind.NEGOTIATION, SkillKind.INTRIGUE, SkillKind.LAW}),
        A.LOST_GOLDEN_AGE: frozenset({SkillKind.FORAGING, SkillKind.LORE, SkillKind.PROPHECY}),
        A.CHOSEN_ONE: frozenset({SkillKind.PROPHECY, SkillKind.LEADERSHIP, SkillKind.RITUAL}),
        A.CURSED_LINE: frozenset({SkillKind.RITUAL, SkillKind.SPIRIT_SPEAKING, SkillKind.MEDICINE}),
        A.RETURN_OF_A_RULER: frozenset({SkillKind.LEADERSHIP, SkillKind.STRATEGY, SkillKind.ORATORY}),
        A.HAUNTED_PLACE: frozenset({SkillKind.SPIRIT_SPEAKING, SkillKind.RITUAL, SkillKind.TRACKING}),
        A.FOUNDING: frozenset({SkillKind.LEADERSHIP, SkillKind.ENGINEERING, SkillKind.LAW}),
        A.EXILE: frozenset({SkillKind.FORAGING, SkillKind.TRACKING, SkillKind.LANGUAGES}),
        A.TRANSFORMATION: frozenset({SkillKind.RITUAL, SkillKind.MEDICINE, SkillKind.LORE}),
        A.BARGAIN: frozenset({SkillKind.NEGOTIATION, SkillKind.LAW, SkillKind.RITUAL}),
        A.SACRIFICE: frozenset({SkillKind.RITUAL, SkillKind.THEOLOGY, SkillKind.LEADERSHIP}),
        A.RIVALRY: frozenset({SkillKind.TACTICS, SkillKind.ORATORY, SkillKind.INTRIGUE}),
        A.DISCOVERY: frozenset({SkillKind.LORE, SkillKind.NAVIGATION, SkillKind.ENGINEERING}),
        A.DECEPTION: frozenset({SkillKind.DECEPTION, SkillKind.INTRIGUE, SkillKind.NEGOTIATION}),
        A.UNION: frozenset({SkillKind.NEGOTIATION, SkillKind.ORATORY, SkillKind.LAW}),
        A.ASCENT: frozenset({SkillKind.LEADERSHIP, SkillKind.STRATEGY, SkillKind.THEOLOGY}),
        A.FALL: frozenset({SkillKind.STRATEGY, SkillKind.LAW, SkillKind.ORATORY}),
    },
)

REALM_PHRASES = total(
    MythicRealm,
    {
        MythicRealm.PALACE: "the palace of its god",
        MythicRealm.DEAD: "the realm of the dead",
        MythicRealm.DREAM: "a dream world",
        MythicRealm.SACRED_SITE: "the place where its myth happened",
    },
)


S = SkillKind

SKILL_DOMAINS = total(
    SkillKind,
    {
        S.BLADE: frozenset({D.WAR, D.BLOOD}),
        S.SPEAR: frozenset({D.WAR, D.HUNT}),
        S.AXE: frozenset({D.WAR, D.PLANTS}),
        S.BLUNT: frozenset({D.WAR, D.BONE}),
        S.UNARMED: frozenset({D.WAR, D.BLOOD}),
        S.SHIELD: frozenset({D.WAR, D.BORDER}),
        S.BOW: frozenset({D.HUNT}),
        S.SLING: frozenset({D.HUNT, D.STONE}),
        S.THROWING: frozenset({D.HUNT}),
        S.MOUNTED_COMBAT: frozenset({D.WAR, D.ROAD}),
        S.NAVAL_COMBAT: frozenset({D.WAR, D.SEA, D.STORM}),
        S.SIEGECRAFT: frozenset({D.WAR, D.BORDER, D.STONE}),
        S.TACTICS: frozenset({D.WAR}),
        S.STRATEGY: frozenset({D.WAR, D.TIME}),
        S.LEADERSHIP: frozenset({D.WAR, D.OATH}),
        S.INTIMIDATION: frozenset({D.SHADOW, D.MADNESS}),
        S.ORATORY: frozenset({D.SOUND}),
        S.NEGOTIATION: frozenset({D.TRADE, D.OATH}),
        S.ETIQUETTE: frozenset({D.LOVE, D.OATH}),
        S.DECEPTION: frozenset({D.TRICKERY, D.SHADOW}),
        S.INTRIGUE: frozenset({D.LIES, D.SHADOW}),
        S.CRYPTOGRAPHY: frozenset({D.LIES, D.KNOWLEDGE}),
        S.ACCOUNTING: frozenset({D.TRADE, D.MEMORY}),
        S.LOGISTICS: frozenset({D.TRADE, D.ROAD, D.HUNGER}),
        S.SMITHING: frozenset({D.CRAFT, D.FIRE, D.ASH}),
        S.JEWELLING: frozenset({D.CRAFT, D.GLASS}),
        S.POTTERY: frozenset({D.CRAFT, D.EARTH, D.FIRE}),
        S.WEAVING: frozenset({D.CRAFT}),
        S.CARPENTRY: frozenset({D.CRAFT, D.PLANTS}),
        S.MASONRY: frozenset({D.STONE, D.EARTH}),
        S.ENGINEERING: frozenset({D.CRAFT}),
        S.SHIPWRIGHT: frozenset({D.CRAFT, D.SEA}),
        S.ALCHEMY: frozenset({D.KNOWLEDGE, D.GLASS, D.SALT}),
        S.LORE: frozenset({D.KNOWLEDGE, D.MEMORY}),
        S.LANGUAGES: frozenset({D.SOUND, D.KNOWLEDGE}),
        S.TEACHING: frozenset({D.KNOWLEDGE, D.LOVE}),
        S.WRITING: frozenset({D.MEMORY, D.TIME}),
        S.MEDICINE: frozenset({D.LIFE, D.PLAGUE}),
        S.SURGERY: frozenset({D.LIFE, D.BLOOD, D.BONE}),
        S.ASTRONOMY: frozenset({D.STAR, D.MOON, D.SUN, D.SKY, D.TIME}),
        S.LAW: frozenset({D.OATH}),
        S.THEOLOGY: frozenset({D.KNOWLEDGE, D.LIGHT, D.SUN}),
        S.HUNTING: frozenset({D.HUNT, D.BLOOD}),
        S.TRACKING: frozenset({D.HUNT, D.EARTH}),
        S.FORAGING: frozenset({D.PLANTS, D.HARVEST, D.HUNGER}),
        S.BEAST_HANDLING: frozenset({D.HUNT, D.LIFE}),
        S.RIDING: frozenset({D.ROAD}),
        S.MOUNTAINEERING: frozenset({D.EARTH, D.ICE, D.SKY}),
        S.SWIMMING: frozenset({D.SEA}),
        S.SAILING: frozenset({D.SEA, D.STORM, D.SALT}),
        S.NAVIGATION: frozenset({D.ROAD, D.STAR}),
        S.RITUAL: frozenset({D.DEATH, D.BONE, D.LIGHT}),
        S.PROPHECY: frozenset({D.DREAM, D.SLEEP, D.MADNESS, D.TIME}),
        S.SPELLCRAFT: frozenset({D.KNOWLEDGE}),
        S.SPIRIT_SPEAKING: frozenset({D.DEATH, D.SHADOW, D.SLEEP}),
        S.FIREARMS: frozenset({D.WAR, D.FIRE}),
        S.PILOTING: frozenset({D.SKY, D.SPACE}),
        S.DRIVING: frozenset({D.ROAD, D.MACHINES}),
        S.MECHANICS: frozenset({D.MACHINES, D.CRAFT, D.INDUSTRY}),
        S.ELECTRONICS: frozenset({D.MACHINES, D.TECHNOLOGY}),
        S.COMPUTING: frozenset({D.INFORMATION, D.TECHNOLOGY}),
        S.SCIENCE: frozenset({D.SCIENCE, D.KNOWLEDGE}),
        S.ADMINISTRATION: frozenset({D.CITIES, D.KNOWLEDGE}),
    },
)


@dataclass(frozen=True)
class GeasLayerSpec:
    label: str
    passes_to_line: bool = False
    sworn: bool = False
    dooms: bool = True


GEAS_LAYERS = total(
    GeasLayer,
    {
        GeasLayer.SEER: GeasLayerSpec("Laid by a seer"),
        GeasLayer.GOD: GeasLayerSpec("Laid by a god"),
        GeasLayer.RITE: GeasLayerSpec("Laid by a rite"),
        GeasLayer.KIN: GeasLayerSpec("Laid by kin", passes_to_line=True),
        GeasLayer.SELF: GeasLayerSpec("Sworn by its bearer", sworn=True, dooms=False),
    },
)
LINE_LAYERS = frozenset(layer for layer, spec in GEAS_LAYERS.items() if spec.passes_to_line)
