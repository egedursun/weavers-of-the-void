from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from aerona.constants.schema import KEY_MAX_LENGTH, SINGLETON_ID, TITLE_MAX_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base, CreatedAtMixin, TimestampMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.node import NodeRow
from aerona.db.types import PydanticJSON, UtcDateTime
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.creator import CreatorMoodAxis, CreatorPassion
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.world import FateMode, ImageStyle, LoreLanguage, SonDistribution
from aerona.domain.models.genesis import GenesisSettings
from aerona.domain.models.profiles import Epic, GodDepth, TravelResource


class CosmosRow(TimestampMixin, Base):
    __tablename__ = "cosmos"
    __table_args__ = (
        CheckConstraint(f"id = {SINGLETON_ID}", name="singleton"),
        at_least("epoch", 1),
        at_least("epoch_start_year", 0),
        at_least("doom_clock", 0),
        at_least("map_version", 1),
        CheckConstraint("council_every_epochs IS NULL OR council_every_epochs >= 0", name="council_every_epochs_min"),
        CheckConstraint("mortal_agents_per_epoch IS NULL OR mortal_agents_per_epoch >= 0", name="mortal_agents_per_epoch_min"),
        CheckConstraint("mortal_agent_parallelism IS NULL OR mortal_agent_parallelism >= 1", name="mortal_agent_parallelism_min"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=SINGLETON_ID)
    name: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH))
    rng_seed: Mapped[int] = mapped_column(BigInteger)
    lore_language: Mapped[LoreLanguage] = mapped_column(enum_type(LoreLanguage, "lore_language"))
    seed_idea: Mapped[str] = mapped_column(Text)
    cosmology: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(Text)
    epoch: Mapped[int] = mapped_column(default=1)
    epoch_start_year: Mapped[int] = mapped_column(default=0)
    doom_clock: Mapped[int] = mapped_column(default=0)
    doom_fraction: Mapped[float] = mapped_column(Float, default=0.0)
    fate_mode: Mapped[FateMode] = mapped_column(enum_type(FateMode, "fate_mode"), default=FateMode.AUTO)
    son_distribution: Mapped[SonDistribution] = mapped_column(enum_type(SonDistribution, "son_distribution"), default=SonDistribution.AUTO)
    image_style: Mapped[ImageStyle] = mapped_column(
        enum_type(ImageStyle, "image_style"), default=ImageStyle.PHOTOREAL, server_default=ImageStyle.PHOTOREAL.value
    )
    image_style_custom: Mapped[str] = mapped_column(Text, default="", server_default="")
    council_every_epochs: Mapped[int | None]
    mortal_agents_per_epoch: Mapped[int | None]
    mortal_agent_parallelism: Mapped[int | None]
    fate_debt_epoch: Mapped[int | None]
    alignment_until_epoch: Mapped[int | None]
    map_version: Mapped[int] = mapped_column(default=1)
    primary_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL", use_alter=True))
    travel_resource: Mapped[TravelResource | None] = mapped_column(PydanticJSON(TravelResource))
    genesis_settings: Mapped[GenesisSettings | None] = mapped_column(PydanticJSON(GenesisSettings))
    notification_prefs: Mapped[dict[NotificationCategory, bool]] = mapped_column(PydanticJSON(dict[NotificationCategory, bool]), default=dict)
    rules_snapshot: Mapped[dict[str, dict[str, float]]] = mapped_column(JSON, default=dict)
    rules_snapshot_at: Mapped[datetime | None] = mapped_column(UtcDateTime())

    @validates("lore_language", "rng_seed")
    def _freeze_genesis_choices(self, key: str, value: Any) -> Any:
        current = self.__dict__.get(key)
        if current is not None and current != value:
            raise ValidationFailedError(f"The {key.replace('_', ' ')} is chosen at genesis and cannot change.")
        return value


class CreatorRow(NodeRow):
    __tablename__ = "creator"
    __table_args__ = (
        at_least("essence", 0),
        between("mood_contentment", PERCENT_MIN, PERCENT_MAX),
        between("mood_anger", PERCENT_MIN, PERCENT_MAX),
        between("mood_interest", PERCENT_MIN, PERCENT_MAX),
        between("mood_loneliness", PERCENT_MIN, PERCENT_MAX),
        between("mood_temperament", -PERCENT_MAX, PERCENT_MAX),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.CREATOR})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    appearance: Mapped[str | None] = mapped_column(Text)
    temperament: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    essence: Mapped[int]
    mood_contentment: Mapped[int]
    mood_anger: Mapped[int]
    mood_interest: Mapped[int]
    mood_loneliness: Mapped[int]
    mood_temperament: Mapped[int] = mapped_column(default=0)
    passions: Mapped[list[CreatorPassion]] = mapped_column(PydanticJSON(list[CreatorPassion]), default=list)
    passions_automatic: Mapped[bool] = mapped_column(default=True)
    depth: Mapped[GodDepth | None] = mapped_column(PydanticJSON(GodDepth))
    epic: Mapped[Epic | None] = mapped_column(PydanticJSON(Epic))


class CreatorMoodInputRow(Base):
    __tablename__ = "creator_mood_inputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int] = mapped_column(index=True)
    axis: Mapped[CreatorMoodAxis] = mapped_column(enum_type(CreatorMoodAxis, "axis"))
    item: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    delta: Mapped[float] = mapped_column(Float)


class AppliedFixupRow(CreatedAtMixin, Base):
    __tablename__ = "applied_fixups"

    key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
