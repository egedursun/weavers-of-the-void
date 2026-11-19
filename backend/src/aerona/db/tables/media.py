from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.media import MediaItemKind, OutletFunding, RecordForm
from aerona.domain.enums.mind import ValueAxis

LEAN_MIN = -100
LEAN_MAX = 100


class RecordMediumRow(Base):
    __tablename__ = "record_media"
    __table_args__ = (
        between("fidelity", PERCENT_MIN, PERCENT_MAX),
        between("durability", PERCENT_MIN, PERCENT_MAX),
        between("reach", PERCENT_MIN, PERCENT_MAX),
        at_least("copy_cost", 0),
        Index("ix_record_media_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    form: Mapped[RecordForm] = mapped_column(enum_type(RecordForm, "form"), default=RecordForm.WRITTEN)
    fidelity: Mapped[int] = mapped_column(default=50)
    durability: Mapped[int] = mapped_column(default=50)
    copy_cost: Mapped[int] = mapped_column(default=5)
    reach: Mapped[int] = mapped_column(default=20)
    technique_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MediaOutletRow(Base):
    __tablename__ = "media_outlets"
    __table_args__ = (
        between("reach", PERCENT_MIN, PERCENT_MAX),
        between("trust", PERCENT_MIN, PERCENT_MAX),
        between("lean", LEAN_MIN, LEAN_MAX),
        at_least("staff", 0),
        at_least("revenue", 0),
        at_least("founded_epoch", 0),
        Index("ix_media_outlets_owner", "owner_node_id"),
        Index("ix_media_outlets_seat", "seat_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    seat_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    medium_id: Mapped[int | None] = mapped_column(ForeignKey("record_media.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    reach: Mapped[int] = mapped_column(default=20)
    stance: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "stance"))
    lean: Mapped[int] = mapped_column(default=0)
    trust: Mapped[int] = mapped_column(default=50)
    censored: Mapped[bool] = mapped_column(default=False)
    funding: Mapped[OutletFunding] = mapped_column(enum_type(OutletFunding, "funding"), default=OutletFunding.SALES)
    revenue: Mapped[int] = mapped_column(default=0)
    staff: Mapped[int] = mapped_column(default=2)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MediaItemRow(Base):
    __tablename__ = "media_items"
    __table_args__ = (
        between("slant", LEAN_MIN, LEAN_MAX),
        between("accuracy", PERCENT_MIN, PERCENT_MAX),
        between("reach", PERCENT_MIN, PERCENT_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_media_items_outlet", "outlet_id"),
        Index("ix_media_items_owner", "owner_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    outlet_id: Mapped[int] = mapped_column(ForeignKey("media_outlets.id", ondelete="CASCADE"))
    owner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[MediaItemKind] = mapped_column(enum_type(MediaItemKind, "kind"), default=MediaItemKind.NEWS)
    subject_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    slant: Mapped[int] = mapped_column(default=0)
    accuracy: Mapped[int] = mapped_column(default=80)
    reach: Mapped[int] = mapped_column(default=20)
    condition: Mapped[int] = mapped_column(default=100)
    exposed: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
