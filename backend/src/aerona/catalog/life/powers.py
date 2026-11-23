from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.powers import GiftedAttitude, GiftedStance, PowerOrigin, PowerState, RestrictionKind, SourceLawLevel, SourceLocus, SourceRenewal

HARM_TYPES = {
    SpellForm.FIRE: DamageType.FIRE,
    SpellForm.WATER: DamageType.COLD,
    SpellForm.AIR: DamageType.BLUNT,
    SpellForm.EARTH: DamageType.BLUNT,
    SpellForm.FORCE: DamageType.BLUNT,
    SpellForm.SOUND: DamageType.BLUNT,
    SpellForm.MIND: DamageType.PSYCHIC,
    SpellForm.EMOTION: DamageType.PSYCHIC,
    SpellForm.LIGHT: DamageType.FIRE,
}


FORM_WEATHER = {SpellForm.AIR: WeatherKind.STORM, SpellForm.WATER: WeatherKind.RAIN, SpellForm.FIRE: WeatherKind.HEAT_WAVE, SpellForm.IMAGE: WeatherKind.FOG}


STANCE_ATTITUDE: Mapping[GiftedStance, GiftedAttitude | None] = total(
    GiftedStance,
    {
        GiftedStance.SACRED: GiftedAttitude.HONOURED,
        GiftedStance.FORBIDDEN: GiftedAttitude.PERSECUTED,
        GiftedStance.SUSPECT: GiftedAttitude.FEARED,
        GiftedStance.TOOL: GiftedAttitude.REGULATED,
        GiftedStance.SILENT: None,
        GiftedStance.PITIED: None,
    },
)


CASTE_STANDING = {GiftedAttitude.HONOURED: 85, GiftedAttitude.PERSECUTED: 10}


RENEWAL_KINDS = {
    SourceRenewal.REST: "rest",
    SourceRenewal.TIME: "rest",
    SourceRenewal.SEASON: "season",
    SourceRenewal.SKY_CYCLE: "season",
    SourceRenewal.RETURN_TO_PLACE: "rest",
    SourceRenewal.VOWS_KEPT: "rest",
    SourceRenewal.FEEDING: "taking",
    SourceRenewal.TAKING: "taking",
    SourceRenewal.WORSHIP: "worship",
    SourceRenewal.OFFERING: "offering",
}

EFFECT_FOR_SPELL_TECHNIQUES = frozenset({SpellTechnique.CREATE, SpellTechnique.TRANSFORM})
EFFECT_FOR_SPELL_FORMS_2 = frozenset({SpellForm.BODY, SpellForm.PLANT})
EFFECT_FOR_SPELL_TECHNIQUES_3 = frozenset({SpellTechnique.DESTROY, SpellTechnique.CONTROL, SpellTechnique.TRANSFORM})
EFFECT_FOR_SPELL_FORMS_4 = frozenset({SpellForm.BODY, SpellForm.PLANT, SpellForm.ANIMAL})
EFFECT_FOR_SPELL_FORMS_5 = frozenset({SpellForm.SPIRIT, SpellForm.VOID})
BLOODLINE_POWER_ORIGINS = frozenset({PowerOrigin.BLOODLINE, PowerOrigin.BORN})
FADE_POWER_ORIGINS = frozenset({PowerOrigin.MADE, PowerOrigin.GROWN, PowerOrigin.HELD})
TRAIN_POWER_STATES = frozenset({PowerState.ACTIVE, PowerState.LATENT})
MOVE_LAWS_GIFTED_ATTITUDES = (GiftedAttitude.FEARED, GiftedAttitude.PERSECUTED)
HEIRS_POWER_ORIGINS = (PowerOrigin.BLOODLINE, PowerOrigin.EXPOSURE)
AT_DEATH_POWER_ORIGINS = frozenset({PowerOrigin.MADE, PowerOrigin.GROWN, PowerOrigin.HELD})
KEEP_APART_GIFTED_ATTITUDES = frozenset({GiftedAttitude.FEARED, GiftedAttitude.PERSECUTED, GiftedAttitude.EXPLOITED})
BROKEN_VOWS_RESTRICTION_KINDS = (RestrictionKind.SPOKEN_VOW, RestrictionKind.FORBIDDEN_ACT)
FELT_LOCI = frozenset({SourceLocus.EMOTION, SourceLocus.DREAM})
KEPT_LOCI = frozenset({SourceLocus.MEMORY, SourceLocus.NAME})
BINDABLE = frozenset({PowerState.ACTIVE, PowerState.EMERGING, PowerState.STRAINED})
REGISTERING_LEVELS = frozenset({SourceLawLevel.LICENSED, SourceLawLevel.CONSCRIPTED})
PACT_ORIGINS = frozenset({PowerOrigin.BONDED, PowerOrigin.BARGAIN})
