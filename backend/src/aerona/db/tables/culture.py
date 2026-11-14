from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.arcana import RechargeRule
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.culture import (
    ArtMedium,
    BacklashKind,
    BoostTrigger,
    CalendarSlot,
    CurseKind,
    CustomCatalog,
    IdeologyTenet,
    ItemClass,
    ItemDeed,
    LanguageRegister,
    LegendArchetype,
    MagicSchool,
    MagicSource,
    ProphecyConsequence,
    ProphecyPredicate,
    ProphecyState,
    ResearchChooser,
    RiteEffectKind,
    RumourChannel,
    SpeakerKind,
    SummonForm,
    Technique,
    TraditionEffectKind,
    TraditionKind,
)
from aerona.domain.enums.faith import FuneralRite
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.society import KnowledgeBranch


class LanguageStandingRow(Base):
    __tablename__ = "language_standing"
    __table_args__ = (between("prestige", PERCENT_MIN, PERCENT_MAX), between("standardisation", PERCENT_MIN, PERCENT_MAX))

    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    prestige: Mapped[int] = mapped_column(default=30)
    standardisation: Mapped[int] = mapped_column(default=0)
    liturgical: Mapped[bool] = mapped_column(default=False)
    lingua_franca: Mapped[bool] = mapped_column(default=False)
    prestige_parts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LanguageIntelligibilityRow(Base):
    __tablename__ = "language_intelligibility"
    __table_args__ = (between("value", PERCENT_MIN, PERCENT_MAX), CheckConstraint("first_entity_id < second_entity_id", name="ordered_pair"))

    first_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    second_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeakerCohortRow(Base):
    __tablename__ = "speaker_cohorts"
    __table_args__ = (between("share", PERCENT_MIN, PERCENT_MAX), Index("ix_speaker_cohorts_language", "language_entity_id"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[SpeakerKind] = mapped_column(enum_type(SpeakerKind, "kind"), primary_key=True)
    share: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LanguageRegisterRow(Base):
    __tablename__ = "language_registers"
    __table_args__ = (Index("ix_language_registers_language", "language_entity_id"),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    register: Mapped[LanguageRegister] = mapped_column(enum_type(LanguageRegister, "register"), primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LegendProfileRow(Base):
    __tablename__ = "legend_profiles"
    __table_args__ = (between("credence", PERCENT_MIN, PERCENT_MAX), between("distortion", PERCENT_MIN, PERCENT_MAX))

    legend_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    archetype: Mapped[LegendArchetype] = mapped_column(enum_type(LegendArchetype, "archetype"))
    custom_archetype_id: Mapped[int | None] = mapped_column(ForeignKey("custom_kinds.id", ondelete="SET NULL"))
    credence: Mapped[int] = mapped_column(default=30)
    distortion: Mapped[int] = mapped_column(default=0)
    source_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    moral: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    tellers: Mapped[list[int]] = mapped_column(JSON, default=list)
    fixed_in_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TraditionProfileRow(Base):
    __tablename__ = "tradition_profiles"
    __table_args__ = (at_least("season_position", 0),)

    tradition_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[TraditionKind] = mapped_column(enum_type(TraditionKind, "kind"))
    custom_kind_id: Mapped[int | None] = mapped_column(ForeignKey("custom_kinds.id", ondelete="SET NULL"))
    calendar_slot: Mapped[CalendarSlot | None] = mapped_column(enum_type(CalendarSlot, "calendar_slot"))
    season_position: Mapped[int | None]
    calendar_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    notable_year_id: Mapped[int | None] = mapped_column(ForeignKey("notable_years.id", ondelete="SET NULL"))
    in_season: Mapped[bool | None]
    cost: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    effects: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    taboo_target: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    taboo_act: Mapped[ActKind | None] = mapped_column(enum_type(ActKind, "taboo_act"))
    funeral_rite: Mapped[FuneralRite | None] = mapped_column(enum_type(FuneralRite, "funeral_rite"))
    origin_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    origin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TraditionEffectRow(Base):
    __tablename__ = "tradition_effects"

    tradition_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    effect: Mapped[TraditionEffectKind] = mapped_column(enum_type(TraditionEffectKind, "effect"), primary_key=True)
    target: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True, default="")
    magnitude: Mapped[int] = mapped_column(default=0)


class TraditionParticipationRow(Base):
    __tablename__ = "tradition_participation"
    __table_args__ = (between("participation", PERCENT_MIN, PERCENT_MAX), Index("ix_tradition_participation_community", "community_entity_id"))

    tradition_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    participation: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    last_celebrated_epoch: Mapped[int | None]
    skipped: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HolderLevelRow(Base):
    __tablename__ = "holder_levels"
    __table_args__ = (at_least("level", 0), at_least("practitioners", 0), Index("ix_holder_levels_branch", "branch"))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    branch: Mapped[KnowledgeBranch] = mapped_column(enum_type(KnowledgeBranch, "branch"), primary_key=True)
    level: Mapped[int] = mapped_column(default=0)
    practitioners: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    secret: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HolderTechniqueRow(Base):
    __tablename__ = "holder_techniques"
    __table_args__ = (Index("ix_holder_techniques_technique", "technique"),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    secret: Mapped[bool] = mapped_column(default=False)


class ResearchProgressRow(Base):
    __tablename__ = "research_progress"
    __table_args__ = (between("progress", PERCENT_MIN, PERCENT_MAX),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"), primary_key=True)
    progress: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)


class CustomKindRow(Base):
    __tablename__ = "custom_kinds"
    __table_args__ = (Index("ix_custom_kinds_catalog", "catalog", "base"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    catalog: Mapped[CustomCatalog] = mapped_column(enum_type(CustomCatalog, "catalog"))
    base: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[dict[str, int | str | list[str] | dict[str, int]]] = mapped_column(JSON, default=dict)
    created_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HolderCustomTechniqueRow(Base):
    __tablename__ = "holder_custom_techniques"
    __table_args__ = (Index("ix_holder_custom_techniques_kind", "kind_id"),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind_id: Mapped[int] = mapped_column(ForeignKey("custom_kinds.id", ondelete="CASCADE"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    secret: Mapped[bool] = mapped_column(default=False)


class IdeologyProfileRow(Base):
    __tablename__ = "ideology_profiles"

    ideology_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    value_delta: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    tenets: Mapped[list[str]] = mapped_column(JSON, default=list)
    founder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    appeal: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    texts: Mapped[list[int]] = mapped_column(JSON, default=list)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IdeologyAdherentRow(Base):
    __tablename__ = "ideology_adherents"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), Index("ix_ideology_adherents_adherent", "adherent_entity_id"))

    ideology_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    adherent_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=30)
    state: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)


class IdeologyTenetRow(Base):
    __tablename__ = "ideology_tenets"

    ideology_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    tenet: Mapped[IdeologyTenet] = mapped_column(enum_type(IdeologyTenet, "tenet"), primary_key=True)


class IdeologyCustomTenetRow(Base):
    __tablename__ = "ideology_custom_tenets"

    ideology_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind_id: Mapped[int] = mapped_column(ForeignKey("custom_kinds.id", ondelete="CASCADE"), primary_key=True)


class RiteProfileRow(Base):
    __tablename__ = "rite_profiles"
    __table_args__ = (between("power", 1, 10), between("backlash_chance", PERCENT_MIN, PERCENT_MAX))

    rite_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    school: Mapped[MagicSchool] = mapped_column(enum_type(MagicSchool, "school"))
    source: Mapped[MagicSource] = mapped_column(enum_type(MagicSource, "source"))
    requirements: Mapped[dict[str, int | str]] = mapped_column(JSON, default=dict)
    cost: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    power: Mapped[int] = mapped_column(default=1)
    backlash_chance: Mapped[int] = mapped_column(default=10)
    backlash: Mapped[BacklashKind] = mapped_column(enum_type(BacklashKind, "backlash"), default=BacklashKind.INJURY)
    holy: Mapped[bool] = mapped_column(default=False)
    heretical: Mapped[bool] = mapped_column(default=False)
    inventor_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    forbidden_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RiteEffectRow(Base):
    __tablename__ = "rite_effects"

    rite_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    effect: Mapped[RiteEffectKind] = mapped_column(enum_type(RiteEffectKind, "effect"), primary_key=True)
    magnitude: Mapped[int] = mapped_column(default=10)
    detail: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    damage_type: Mapped[DamageType | None] = mapped_column(enum_type(DamageType, "damage_type"))
    summon_form: Mapped[SummonForm | None] = mapped_column(enum_type(SummonForm, "summon_form"))
    custom_kind_id: Mapped[int | None] = mapped_column(ForeignKey("custom_kinds.id", ondelete="SET NULL"))


class CastingRow(Base):
    __tablename__ = "castings"
    __table_args__ = (Index("ix_castings_epoch", "epoch"), Index("ix_castings_caster", "caster_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    rite_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    caster_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    succeeded: Mapped[bool] = mapped_column(default=True)
    backlash: Mapped[BacklashKind | None] = mapped_column(enum_type(BacklashKind, "backlash"))
    effect: Mapped[str] = mapped_column(Text, default="")


class ProphecyConditionRow(Base):
    __tablename__ = "prophecy_conditions"
    __table_args__ = (between("pressure", PERCENT_MIN, PERCENT_MAX),)

    prophecy_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    predicate: Mapped[ProphecyPredicate] = mapped_column(enum_type(ProphecyPredicate, "predicate"))
    args: Mapped[dict[str, int | str]] = mapped_column(JSON, default=dict)
    deadline_epoch: Mapped[int | None]
    consequence_kind: Mapped[ProphecyConsequence | None] = mapped_column(enum_type(ProphecyConsequence, "consequence_kind"))
    consequence_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    seer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    audience: Mapped[list[int]] = mapped_column(JSON, default=list)
    pressure: Mapped[int] = mapped_column(default=20)
    state: Mapped[ProphecyState] = mapped_column(enum_type(ProphecyState, "state"), default=ProphecyState.PENDING)
    resolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ItemProfileRow(Base):
    __tablename__ = "item_profiles"
    __table_args__ = (
        between("quality", PERCENT_MIN, PERCENT_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        between("renown", PERCENT_MIN, PERCENT_MAX),
        at_least("value", 0),
    )

    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    item_class: Mapped[ItemClass] = mapped_column(enum_type(ItemClass, "item_class"))
    custom_class_id: Mapped[int | None] = mapped_column(ForeignKey("custom_kinds.id", ondelete="SET NULL"))
    material: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    quality: Mapped[int] = mapped_column(default=50)
    condition: Mapped[int] = mapped_column(default=100)
    damage_type: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    reach: Mapped[int] = mapped_column(default=0)
    coverage: Mapped[int] = mapped_column(default=0)
    weight: Mapped[int] = mapped_column(default=0)
    curse: Mapped[CurseKind] = mapped_column(enum_type(CurseKind, "curse"), default=CurseKind.NONE)
    value: Mapped[int] = mapped_column(default=0)
    renown: Mapped[int] = mapped_column(default=0)
    maker_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    regalia_of_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    symbol: Mapped[bool] = mapped_column(default=False)
    prosthesis_for: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    secondary_materials: Mapped[list[str]] = mapped_column(JSON, default=list)
    bound_spirit_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ItemHistoryRow(Base):
    __tablename__ = "item_history"
    __table_args__ = (Index("ix_item_history_item", "item_entity_id", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    deed: Mapped[ItemDeed] = mapped_column(enum_type(ItemDeed, "deed"))
    actor_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    note: Mapped[str] = mapped_column(String(480), default="")


class ItemEnchantmentRow(Base):
    __tablename__ = "item_enchantments"

    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    effect: Mapped[RiteEffectKind] = mapped_column(enum_type(RiteEffectKind, "effect"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=10)
    rite_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    charges: Mapped[int] = mapped_column(default=3, server_default="3")
    capacity: Mapped[int] = mapped_column(default=3, server_default="3")
    recharge: Mapped[RechargeRule] = mapped_column(enum_type(RechargeRule, "recharge"), default=RechargeRule.VIS, server_default="vis")
    overuse: Mapped[int] = mapped_column(default=0, server_default="0")


class BookContentRow(Base):
    __tablename__ = "book_contents"
    __table_args__ = (between("fidelity", PERCENT_MIN, PERCENT_MAX),)

    book_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    knowledge_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    fidelity: Mapped[int] = mapped_column(default=80)


class ArtworkProfileRow(Base):
    __tablename__ = "artwork_profiles"
    __table_args__ = (between("quality", PERCENT_MIN, PERCENT_MAX), at_least("copies", 0))

    artwork_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    medium: Mapped[ArtMedium] = mapped_column(enum_type(ArtMedium, "medium"))
    performed: Mapped[bool] = mapped_column(default=False)
    author_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    patron_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    message: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    quality: Mapped[int] = mapped_column(default=50)
    copies: Mapped[int] = mapped_column(default=1)
    colour: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    shape: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    language_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    translations: Mapped[list[int]] = mapped_column(JSON, default=list)
    propaganda: Mapped[bool] = mapped_column(default=False)
    canon: Mapped[bool] = mapped_column(default=False)
    art_form_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RumourRow(Base):
    __tablename__ = "rumours"
    __table_args__ = (
        between("fidelity", PERCENT_MIN, PERCENT_MAX),
        at_least("hops", 0),
        at_least("lingered", 0),
        UniqueConstraint("incident_id", "carrier_entity_id", name="one_rumour_per_carrier"),
        Index("ix_rumours_carrier", "carrier_entity_id"),
        Index("ix_rumours_epoch", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    carrier_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    source_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    channel: Mapped[RumourChannel] = mapped_column(enum_type(RumourChannel, "channel"), default=RumourChannel.WITNESS)
    fidelity: Mapped[int] = mapped_column(default=100)
    hops: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int]
    lingered: Mapped[int] = mapped_column(default=0)
    acted: Mapped[bool] = mapped_column(default=False)
    legend_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    planted: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


register_profile_table(LanguageIntelligibilityRow.__tablename__, "first_entity_id")
register_profile_table(SpeakerCohortRow.__tablename__, "community_entity_id")
register_profile_table(LanguageRegisterRow.__tablename__, "holder_entity_id")
register_profile_table(TraditionParticipationRow.__tablename__, "community_entity_id")


class ResearchFocusRow(Base):
    __tablename__ = "research_focus"
    __table_args__ = (at_least("epoch", 0),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"))
    chooser: Mapped[ResearchChooser] = mapped_column(enum_type(ResearchChooser, "chooser"), default=ResearchChooser.SCHOLARS)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InstitutionRow(Base):
    __tablename__ = "institutions"
    __table_args__ = (at_least("since_epoch", 0), at_least("refused_epochs", 0), Index("ix_institutions_community", "community_entity_id"))

    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    origin: Mapped[bool] = mapped_column(default=False)
    embraced: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    refused_epochs: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ResearchBoostRow(Base):
    __tablename__ = "research_boosts"
    __table_args__ = (at_least("epoch", 0), Index("ix_research_boosts_holder", "holder_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"))
    trigger: Mapped[BoostTrigger] = mapped_column(enum_type(BoostTrigger, "trigger"))
    progress: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
