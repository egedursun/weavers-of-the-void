from sqlalchemy import JSON, ForeignKey, Index, String, false
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.crafts import (
    AffinityMode,
    AssistiveAid,
    CatchGround,
    CatchRight,
    ChemicalProduct,
    ClockKind,
    Gear,
    InsuranceCover,
    LinkToken,
    Notation,
    RightAcquired,
    RightKind,
)
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.kind_crafts import GameCategory
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import Emotion, SkillKind

GROUND_FIELDS = ("ground", "gear", "right", "owner_node_id", "effort", "collapse_at", "collapsed", "last_catch", "first_stock")
WORKS_FIELDS = ("output", "hazard", "pollution", "accidents")
INSURER_FIELDS = ("pool", "risk_belief", "premium_pct", "ruined", "claims_seen")
POLICY_FIELDS = ("insurer_entity_id", "cover", "premium", "sum_insured", "active", "claims")
RIGHT_FIELDS = ("holder_node_id", "kind", "subject_node_id", "name", "acquired", "licensed_to_node_id")
AID_FIELDS = ("quality",)
CLOCK_FIELDS = ("kind", "precision", "built_epoch")
NUMBER_FIELDS = ("base", "notation", "zero", "numeracy")
AFFINITY_FIELDS = ("mode", "power")
LINK_FIELDS = ("token", "strength", "obtained_epoch")
SPIRIT_FIELDS = ("emotion", "strength", "lifetime", "bound_by_node_id")


class CatchGroundRow(Base):
    __tablename__ = "catch_grounds"
    __table_args__ = (
        between("effort", PERCENT_MIN, PERCENT_MAX),
        between("collapse_at", PERCENT_MIN, PERCENT_MAX),
        at_least("last_catch", 0),
        at_least("first_stock", 1),
    )

    source_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    ground: Mapped[CatchGround] = mapped_column(enum_type(CatchGround, "ground"))
    gear: Mapped[Gear] = mapped_column(enum_type(Gear, "gear"))
    right: Mapped[CatchRight] = mapped_column(enum_type(CatchRight, "right"), default=CatchRight.COMMONS)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    effort: Mapped[int] = mapped_column(default=50)
    collapse_at: Mapped[int] = mapped_column(default=20)
    collapsed: Mapped[bool] = mapped_column(default=False)
    last_catch: Mapped[int] = mapped_column(default=0)
    first_stock: Mapped[int] = mapped_column(default=100, server_default="100")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ChemicalWorksRow(Base):
    __tablename__ = "chemical_works"
    __table_args__ = (
        between("output", PERCENT_MIN, PERCENT_MAX),
        between("hazard", PERCENT_MIN, PERCENT_MAX),
        between("pollution", PERCENT_MIN, PERCENT_MAX),
        at_least("accidents", 0),
    )

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    product: Mapped[ChemicalProduct] = mapped_column(enum_type(ChemicalProduct, "product"), primary_key=True)
    output: Mapped[int] = mapped_column(default=20)
    hazard: Mapped[int] = mapped_column(default=10)
    pollution: Mapped[int] = mapped_column(default=10)
    accidents: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InsurerRow(Base):
    __tablename__ = "insurers"
    __table_args__ = (between("risk_belief", PERCENT_MIN, PERCENT_MAX), between("premium_pct", PERCENT_MIN, PERCENT_MAX), at_least("claims_seen", 0))

    insurer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    pool: Mapped[int] = mapped_column(default=0)
    risk_belief: Mapped[int] = mapped_column(default=20)
    premium_pct: Mapped[int] = mapped_column(default=5)
    ruined: Mapped[bool] = mapped_column(default=False)
    claims_seen: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InsurancePolicyRow(Base):
    __tablename__ = "insurance_policies"
    __table_args__ = (at_least("premium", 0), at_least("sum_insured", 0), at_least("claims", 0), Index("ix_insurance_policies_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    insurer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    cover: Mapped[InsuranceCover] = mapped_column(enum_type(InsuranceCover, "cover"))
    premium: Mapped[int] = mapped_column(default=1)
    sum_insured: Mapped[int] = mapped_column(default=20)
    active: Mapped[bool] = mapped_column(default=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    claims: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IncorporealRightRow(Base):
    __tablename__ = "incorporeal_rights"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_incorporeal_rights_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[RightKind] = mapped_column(enum_type(RightKind, "kind"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    acquired: Mapped[RightAcquired] = mapped_column(enum_type(RightAcquired, "acquired"), default=RightAcquired.CREATED)
    licensed_to_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AssistiveAidRow(Base):
    __tablename__ = "assistive_aids"
    __table_args__ = (between("quality", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[AssistiveAid] = mapped_column(enum_type(AssistiveAid, "kind"), primary_key=True)
    quality: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PublicClockRow(Base):
    __tablename__ = "public_clocks"
    __table_args__ = (between("precision", PERCENT_MIN, PERCENT_MAX), at_least("built_epoch", 0))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[ClockKind] = mapped_column(enum_type(ClockKind, "kind"))
    precision: Mapped[int] = mapped_column(default=30)
    built_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GameRow(KindRow):
    __tablename__ = "games"
    __table_args__ = (
        at_least("created_epoch", 0),
        between("chance_share", PERCENT_MIN, PERCENT_MAX),
        between("violence", PERCENT_MIN, PERCENT_MAX),
        between("team_size", 1, 500),
        between("betting", PERCENT_MIN, PERCENT_MAX),
        between("spectators", PERCENT_MIN, PERCENT_MAX),
        between("prestige", PERCENT_MIN, PERCENT_MAX),
    )

    origin_node_id: Mapped[int | None] = mapped_column("origin_entity_id", ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    built_in: Mapped[bool] = mapped_column(default=False, server_default=false())
    retired: Mapped[bool] = mapped_column(default=False, server_default=false())
    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="SET NULL"))
    category: Mapped[GameCategory] = mapped_column("kind", enum_type(GameCategory, "kind"))
    skill: Mapped[SkillKind | None] = mapped_column(enum_type(SkillKind, "skill"))
    chance_share: Mapped[int] = mapped_column(default=30, server_default="30")
    violence: Mapped[int] = mapped_column(default=0, server_default="0")
    team_size: Mapped[int] = mapped_column(default=1, server_default="1")
    betting: Mapped[int] = mapped_column(default=10, server_default="10")
    spectators: Mapped[int] = mapped_column(default=20, server_default="20")
    prestige: Mapped[int] = mapped_column(default=10, server_default="10")


class NumberSystemRow(Base):
    __tablename__ = "number_systems"
    __table_args__ = (between("base", 2, 60), between("numeracy", PERCENT_MIN, PERCENT_MAX))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    base: Mapped[int] = mapped_column(default=10)
    notation: Mapped[Notation] = mapped_column(enum_type(Notation, "notation"), default=Notation.ADDITIVE)
    zero: Mapped[bool] = mapped_column(default=False)
    numeracy: Mapped[int] = mapped_column(default=20)
    numerology: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, server_default="{}")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MaterialAffinityRow(Base):
    __tablename__ = "material_affinities"
    __table_args__ = (between("power", PERCENT_MIN, PERCENT_MAX),)

    material_id: Mapped[int] = mapped_column(ForeignKey("world_materials.id", ondelete="CASCADE"), primary_key=True)
    school: Mapped[MagicSchool] = mapped_column(enum_type(MagicSchool, "school"), primary_key=True)
    mode: Mapped[AffinityMode] = mapped_column(enum_type(AffinityMode, "mode"))
    power: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SympatheticLinkRow(Base):
    __tablename__ = "sympathetic_links"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("obtained_epoch", 0), Index("ix_sympathetic_links_target", "target_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    target_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    token: Mapped[LinkToken] = mapped_column(enum_type(LinkToken, "token"))
    strength: Mapped[int] = mapped_column(default=50)
    obtained_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EmotionSpiritRow(Base):
    __tablename__ = "emotion_spirits"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("lifetime", 0), at_least("born_epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    emotion: Mapped[Emotion] = mapped_column(enum_type(Emotion, "emotion"))
    strength: Mapped[int] = mapped_column(default=30)
    born_epoch: Mapped[int] = mapped_column(default=0)
    lifetime: Mapped[int] = mapped_column(default=3)
    bound_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
