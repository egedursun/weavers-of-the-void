from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.speech import HumourForm, SpeechAim, SpeechVenue

EFFECT_SPAN = 100


class HumourStyleRow(Base):
    __tablename__ = "humour_styles"
    __table_args__ = (
        between("offence_threshold", PERCENT_MIN, PERCENT_MAX),
        between("directness", PERCENT_MIN, PERCENT_MAX),
        between("silence", PERCENT_MIN, PERCENT_MAX),
    )

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[HumourForm] = mapped_column(enum_type(HumourForm, "form"), default=HumourForm.WORDPLAY)
    mock_rulers: Mapped[bool] = mapped_column(default=False)
    mock_gods: Mapped[bool] = mapped_column(default=False)
    mock_kin: Mapped[bool] = mapped_column(default=True)
    mock_strangers: Mapped[bool] = mapped_column(default=True)
    offence_threshold: Mapped[int] = mapped_column(default=50)
    directness: Mapped[int] = mapped_column(default=50)
    silence: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeechRow(Base):
    __tablename__ = "speeches"
    __table_args__ = (
        between("skill", PERCENT_MIN, PERCENT_MAX),
        between("reach", PERCENT_MIN, PERCENT_MAX),
        between("effect", -EFFECT_SPAN, EFFECT_SPAN),
        at_least("epoch", 0),
        Index("ix_speeches_speaker", "speaker_node_id"),
        Index("ix_speeches_place", "place_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    speaker_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    venue: Mapped[SpeechVenue] = mapped_column(enum_type(SpeechVenue, "venue"), default=SpeechVenue.SQUARE)
    aim: Mapped[SpeechAim] = mapped_column(enum_type(SpeechAim, "aim"), default=SpeechAim.PERSUADE)
    audience_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    skill: Mapped[int] = mapped_column(default=50)
    reach: Mapped[int] = mapped_column(default=30)
    effect: Mapped[int] = mapped_column(default=0)
    heard: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
