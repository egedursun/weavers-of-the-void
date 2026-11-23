from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.arts import ArtMarketRole, CanonPath, ClubKind, FandomLine, ForgeryKind, ForgeryStatus
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

PRICE_FIELDS = ("price", "provenance", "interest", "acclaim", "last_buyer_node_id")
SALE_FIELDS = ("seller_node_id", "buyer_node_id", "price", "fair_place_entity_id")
COLLECTOR_FIELDS = ("role", "taste_form_entity_id", "connoisseurship")
FORGERY_FIELDS = ("kind", "forger_entity_id", "original_entity_id", "skill", "status", "exposed_by_entity_id")
CANON_FIELDS = ("path", "weight", "contested")
MOVEMENT_FIELDS = ("art_form_entity_id", "orthodoxy", "scandals", "patrons")
CLUB_FIELDS = (
    "kind",
    "league_entity_id",
    "arena_entity_id",
    "wins",
    "losses",
    "rating",
    "fandom",
    "line",
    "line_entity_id",
    "leverage",
    "bought_by_entity_id",
    "fixed_by_entity_id",
    "fixed_winner_entity_id",
)
LEAGUE_FIELDS = ("polity_entity_id", "champion_entity_id", "season_epoch")
MATCH_FIELDS = ("home_entity_id", "away_entity_id", "winner_entity_id", "stake", "riot", "fixed_by_entity_id", "fixing_exposed")
BET_FIELDS = ("club_entity_id", "stake", "won")


class ArtPriceRow(Base):
    __tablename__ = "art_prices"
    __table_args__ = (at_least("price", 0), at_least("provenance", 0), between("interest", PERCENT_MIN, PERCENT_MAX))

    artwork_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    price: Mapped[int] = mapped_column(default=0)
    provenance: Mapped[int] = mapped_column(default=0)
    interest: Mapped[int] = mapped_column(default=0)
    acclaim: Mapped[int] = mapped_column(default=0, server_default="0")
    last_buyer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    last_sale_epoch: Mapped[int | None]
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArtSaleRow(Base):
    __tablename__ = "art_sales"
    __table_args__ = (at_least("price", 0), at_least("epoch", 0), Index("ix_art_sales_artwork", "artwork_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    seller_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    buyer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    price: Mapped[int] = mapped_column(default=0)
    fair_place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CollectorRow(Base):
    __tablename__ = "collectors"
    __table_args__ = (between("connoisseurship", PERCENT_MIN, PERCENT_MAX),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[ArtMarketRole] = mapped_column(enum_type(ArtMarketRole, "role"), default=ArtMarketRole.COLLECTOR)
    taste_form_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    connoisseurship: Mapped[int] = mapped_column(default=30)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ForgeryRow(Base):
    __tablename__ = "forgeries"
    __table_args__ = (between("skill", PERCENT_MIN, PERCENT_MAX), at_least("made_epoch", 0), Index("ix_forgeries_item", "item_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[ForgeryKind] = mapped_column(enum_type(ForgeryKind, "kind"))
    forger_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    original_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id", ondelete="SET NULL"))
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"))
    skill: Mapped[int] = mapped_column(default=50)
    status: Mapped[ForgeryStatus] = mapped_column(enum_type(ForgeryStatus, "status"), default=ForgeryStatus.HIDDEN)
    exposed_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    exposed_epoch: Mapped[int | None]
    made_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CanonWorkRow(Base):
    __tablename__ = "canon_works"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX), Index("ix_canon_works_artwork", "artwork_entity_id"))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    artwork_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    path: Mapped[CanonPath] = mapped_column(enum_type(CanonPath, "path"))
    weight: Mapped[int] = mapped_column(default=50)
    contested: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArtMovementRow(Base):
    __tablename__ = "art_movements"
    __table_args__ = (at_least("scandals", 0), at_least("patrons", 0))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    manifesto: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    art_form_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    orthodoxy: Mapped[bool] = mapped_column(default=False)
    scandals: Mapped[int] = mapped_column(default=0)
    patrons: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ClubRow(Base):
    __tablename__ = "clubs"
    __table_args__ = (
        at_least("wins", 0),
        at_least("losses", 0),
        between("rating", PERCENT_MIN, PERCENT_MAX),
        between("fandom", PERCENT_MIN, PERCENT_MAX),
        between("leverage", PERCENT_MIN, PERCENT_MAX),
        Index("ix_clubs_league", "league_entity_id"),
    )

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[ClubKind] = mapped_column(enum_type(ClubKind, "kind"), default=ClubKind.TEAM_GAME)
    league_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    arena_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    wins: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)
    rating: Mapped[int] = mapped_column(default=50)
    fandom: Mapped[int] = mapped_column(default=10)
    line: Mapped[FandomLine] = mapped_column(enum_type(FandomLine, "line"), default=FandomLine.NONE)
    line_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    leverage: Mapped[int] = mapped_column(default=0)
    bought_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fixed_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fixed_winner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LeagueRow(Base):
    __tablename__ = "leagues"

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    champion_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    season_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MatchRow(Base):
    __tablename__ = "matches"
    __table_args__ = (at_least("stake", 0), at_least("epoch", 0), Index("ix_matches_league", "league_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    league_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    home_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    away_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    winner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    stake: Mapped[int] = mapped_column(default=0)
    riot: Mapped[bool] = mapped_column(default=False)
    fixed_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fixing_exposed: Mapped[bool] = mapped_column(default=False, server_default="0")
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BetRow(Base):
    __tablename__ = "bets"
    __table_args__ = (at_least("stake", 0), Index("ix_bets_match", "match_id"), Index("ix_bets_settlement", "settlement_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    club_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    stake: Mapped[int] = mapped_column(default=0)
    won: Mapped[bool | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
