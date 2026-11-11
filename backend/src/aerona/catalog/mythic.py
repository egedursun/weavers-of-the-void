from aerona.core.total import total
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.mythic import CosmicOffice, GeasMode, MythicRealm, QuestTrial

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
        A.FLOOD: MythicRealm.PALACE,
        A.BETRAYAL: MythicRealm.DREAM,
        A.LOST_PARADISE: MythicRealm.DREAM,
        A.CHOSEN_ONE: MythicRealm.PALACE,
        A.CURSED_LINE: MythicRealm.DEAD,
        A.RETURN_OF_THE_KING: MythicRealm.DEAD,
        A.HAUNTED_PLACE: MythicRealm.DEAD,
    },
)

ARCHETYPE_TRIALS = total(
    LegendArchetype,
    {
        A.HERO_QUEST: (Q.SKILL, Q.PASSION, Q.FAITH),
        A.MONSTER: (Q.SKILL, Q.CONVICTION, Q.SKILL),
        A.TRICKSTER: (Q.SKILL, Q.SKILL, Q.CONVICTION),
        A.CREATION: (Q.FAITH, Q.SKILL, Q.FAITH),
        A.FLOOD: (Q.CONVICTION, Q.SKILL, Q.FAITH),
        A.BETRAYAL: (Q.PASSION, Q.CONVICTION, Q.SKILL),
        A.LOST_PARADISE: (Q.FAITH, Q.PASSION, Q.SKILL),
        A.CHOSEN_ONE: (Q.FAITH, Q.CONVICTION, Q.SKILL),
        A.CURSED_LINE: (Q.PASSION, Q.FAITH, Q.SKILL),
        A.RETURN_OF_THE_KING: (Q.CONVICTION, Q.SKILL, Q.PASSION),
        A.HAUNTED_PLACE: (Q.CONVICTION, Q.SKILL, Q.FAITH),
    },
)


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
        A.FLOOD: frozenset({SkillKind.SAILING, SkillKind.SWIMMING, SkillKind.ENGINEERING}),
        A.BETRAYAL: frozenset({SkillKind.NEGOTIATION, SkillKind.INTRIGUE, SkillKind.LAW}),
        A.LOST_PARADISE: frozenset({SkillKind.FORAGING, SkillKind.LORE, SkillKind.PROPHECY}),
        A.CHOSEN_ONE: frozenset({SkillKind.PROPHECY, SkillKind.LEADERSHIP, SkillKind.RITUAL}),
        A.CURSED_LINE: frozenset({SkillKind.RITUAL, SkillKind.SPIRIT_SPEAKING, SkillKind.MEDICINE}),
        A.RETURN_OF_THE_KING: frozenset({SkillKind.LEADERSHIP, SkillKind.STRATEGY, SkillKind.ORATORY}),
        A.HAUNTED_PLACE: frozenset({SkillKind.SPIRIT_SPEAKING, SkillKind.RITUAL, SkillKind.TRACKING}),
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

REALM_STEPS = total(MythicRealm, {MythicRealm.PALACE: 1, MythicRealm.DEAD: 2, MythicRealm.DREAM: 0, MythicRealm.SACRED_SITE: 0})

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
    },
)
