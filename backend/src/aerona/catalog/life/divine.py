from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.arcana import SpellTechnique
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.divine import CouncilMotion, DivineWoundKind, OuterHunger, PenanceDeed, SonPunishment, WoundCause
from aerona.domain.enums.mythic import MantlingState, ServitorOrigin
from aerona.rules.registry import Rules

HUNGER_LABELS = {
    OuterHunger.SOULS: "Souls",
    OuterHunger.KNOWLEDGE: "Knowledge",
    OuterHunger.LIGHT: "Light",
    OuterHunger.NAMES: "Names",
    OuterHunger.MEMORIES: "Memories",
}


HUNGER_TECHNIQUE: Mapping[OuterHunger, SpellTechnique] = total(
    OuterHunger,
    {
        OuterHunger.SOULS: SpellTechnique.CONTROL,
        OuterHunger.KNOWLEDGE: SpellTechnique.PERCEIVE,
        OuterHunger.LIGHT: SpellTechnique.DESTROY,
        OuterHunger.NAMES: SpellTechnique.BIND,
        OuterHunger.MEMORIES: SpellTechnique.TRANSFORM,
    },
)


MOTION_LABELS = {
    CouncilMotion.NONE: "No motion",
    CouncilMotion.AGAINST_DOOMSDAY: "Stand against the doom",
    CouncilMotion.JOINT_BLESSING: "Bless one another",
    CouncilMotion.CONDEMN_REBEL: "Condemn a rebel",
    CouncilMotion.CALL_FOR_PEACE: "Call for peace",
    CouncilMotion.WAR_ON_FOREIGN_GOD: "War on a foreign god",
    CouncilMotion.DIVIDE_WORLDS: "Divide the worlds",
    CouncilMotion.OUTLAW_RITE: "Outlaw a rite",
    CouncilMotion.PUNISH_SON: "Punish a son",
    CouncilMotion.BLESS_HERO: "Bless a hero",
    CouncilMotion.HOLY_WORLD: "Declare a holy world",
    CouncilMotion.COSMIC_TRUCE: "Set a cosmic truce",
    CouncilMotion.PETITION_CREATOR: "Petition the Creator",
    CouncilMotion.APPOINT_OFFICE: "Appoint a holder to a cosmic office",
    CouncilMotion.REASSIGN_WORLD: "Give a world to another son",
    CouncilMotion.OUTLAW_POWER: "Outlaw a god's powers",
    CouncilMotion.OUTLAW_SOURCE: "Close a source of power",
    CouncilMotion.ADMIT_MEMBER: "Admit a god to the council",
    CouncilMotion.EXPEL_MEMBER: "Put a god out of the council",
    CouncilMotion.RECOGNISE_GOD: "Recognise a new god",
    CouncilMotion.ESSENCE_TITHE: "Levy a tithe of essence for a common work",
    CouncilMotion.SET_COUNCIL_RULES: "Change how the council decides",
    CouncilMotion.REGULATE_MADE_MINDS: "Regulate made minds",
    CouncilMotion.REGULATE_POWERS: "Regulate powers",
    CouncilMotion.REGULATE_LIVING_CRAFT: "Regulate living craft",
}


WOUND_LABELS: Mapping[DivineWoundKind, str] = total(
    DivineWoundKind,
    {
        DivineWoundKind.SEVERED_DOMAIN: "Severed domain",
        DivineWoundKind.SHATTERED_MANIFESTATION: "Shattered manifestation",
        DivineWoundKind.STOLEN_NAME: "Stolen true name",
        DivineWoundKind.VOID_WOUND: "Wound of the void",
        DivineWoundKind.DRAINED_ESSENCE: "Drained essence",
        DivineWoundKind.LOST_WORSHIPPERS: "Lost worshippers",
        DivineWoundKind.BOUND: "Binding",
        DivineWoundKind.SPLIT_ASPECT: "Split aspect",
        DivineWoundKind.FORGOTTEN_NAME: "Forgotten name",
    },
)


STRUCK_KINDS = (
    DivineWoundKind.SEVERED_DOMAIN,
    DivineWoundKind.SHATTERED_MANIFESTATION,
    DivineWoundKind.STOLEN_NAME,
    DivineWoundKind.DRAINED_ESSENCE,
    DivineWoundKind.LOST_WORSHIPPERS,
    DivineWoundKind.BOUND,
    DivineWoundKind.SPLIT_ASPECT,
    DivineWoundKind.FORGOTTEN_NAME,
)

TARGET_FOR_CREATOR_PASSIONS = frozenset({CreatorPassion.WAR, CreatorPassion.CHAOS})
TARGET_FOR_CREATOR_PASSIONS_2 = frozenset({CreatorPassion.CREATION, CreatorPassion.ORDER})
PREVENT_MANTLING_STATES = frozenset({MantlingState.ASCENDED, MantlingState.REPLACED})
PREVENT_MANTLING_STATES_2 = frozenset({MantlingState.BLOCKED, MantlingState.FAILED})
SPONSOR_MANTLING_STATES = frozenset({MantlingState.ASCENDED, MantlingState.REPLACED})
SPONSOR_MANTLING_STATES_2 = frozenset({MantlingState.BLOCKED, MantlingState.FAILED})
LEANING_COUNCIL_MOTIONS = frozenset({CouncilMotion.COSMIC_TRUCE, CouncilMotion.CALL_FOR_PEACE})

RULING_LASTING = frozenset(
    {CouncilMotion.COSMIC_TRUCE, CouncilMotion.OUTLAW_RITE, CouncilMotion.PUNISH_SON, CouncilMotion.DIVIDE_WORLDS, CouncilMotion.HOLY_WORLD}
)


@dataclass(frozen=True)
class CauseSpec:
    label: str
    severity: Callable[[Rules], int] | None = None
    by_mortal: bool = False


WOUND_CAUSES: Mapping[WoundCause, CauseSpec] = total(
    WoundCause,
    {
        WoundCause.DUEL: CauseSpec("a duel of the gods"),
        WoundCause.GOD_WAR: CauseSpec("a war of gods"),
        WoundCause.CREATOR: CauseSpec("the Creator"),
        WoundCause.AVATAR_SLAIN: CauseSpec("the death of its mortal form", lambda rules: rules.divine_wounds.avatar_severity),
        WoundCause.OUTER_BARGAIN: CauseSpec("a bargain with an outer being"),
        WoundCause.NEGLECT: CauseSpec("neglect", lambda rules: rules.divine_wounds.neglect_severity),
        WoundCause.BETRAYAL: CauseSpec("betrayal by one in its service", lambda rules: rules.divine_wounds.betrayal_severity),
        WoundCause.MORTAL_SLAYER: CauseSpec("a mortal's deed", lambda rules: rules.divine_wounds.mortal_slayer_severity, by_mortal=True),
    },
)
NEGLECT_KINDS = frozenset({DivineWoundKind.LOST_WORSHIPPERS, DivineWoundKind.FORGOTTEN_NAME})


@dataclass(frozen=True)
class PunishmentSpec:
    label: str
    lasting: bool = False
    renown: Callable[[Rules], int] | None = None


PUNISHMENTS: Mapping[SonPunishment, PunishmentSpec] = total(
    SonPunishment,
    {
        SonPunishment.CHAIN: PunishmentSpec("chains", lasting=True),
        SonPunishment.EXILE: PunishmentSpec("exile", lasting=True),
        SonPunishment.STRIP_POWER: PunishmentSpec("the loss of a power"),
        SonPunishment.STRIP_DIVINITY: PunishmentSpec("the loss of its divinity"),
        SonPunishment.PENANCE: PunishmentSpec("a penance", lasting=True),
        SonPunishment.ESSENCE_FINE: PunishmentSpec("a fine of essence", renown=lambda rules: rules.council.essence_fine_renown),
    },
)


@dataclass(frozen=True)
class PenanceSpec:
    label: str
    deeds: frozenset[str]


PENANCE_DEEDS: Mapping[PenanceDeed, PenanceSpec] = total(
    PenanceDeed,
    {
        PenanceDeed.RESTORE_WORLD: PenanceSpec("restore a wounded land", frozenset({"scar.healed", "scar.cleansed"})),
        PenanceDeed.RAISE_HERO: PenanceSpec("raise a hero", frozenset({"tools.son.call_heroquest", "heroism.victory"})),
        PenanceDeed.UNDO_CURSE: PenanceSpec("undo a curse", frozenset({"curses.lifted", "transform.curse_lifted", "gods.power.bloodline_lift"})),
    },
)


@dataclass(frozen=True)
class OriginSpec:
    label: str
    names_former_god: bool = False
    loyalty: Callable[[Rules], int] | None = None


SERVITOR_ORIGINS: Mapping[ServitorOrigin, OriginSpec] = total(
    ServitorOrigin,
    {
        ServitorOrigin.MADE: OriginSpec("made by its god"),
        ServitorOrigin.RAISED: OriginSpec("raised from a saint's soul"),
        ServitorOrigin.SUMMONED: OriginSpec("summoned by a rite"),
        ServitorOrigin.DEFECTED: OriginSpec("come over from another god", names_former_god=True, loyalty=lambda rules: rules.servitors.defected_loyalty),
        ServitorOrigin.BORN: OriginSpec("born to its god"),
    },
)
