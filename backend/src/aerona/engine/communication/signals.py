from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.communication import CUT_WHEN_TAKEN
from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.communication import SignalKind, SignalState
from aerona.domain.enums.culture import Technique
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of

STATE = "state"
CAPTURE_PCT = 50
KIND_TECHNIQUES: tuple[tuple[SignalKind, Technique], ...] = (
    (SignalKind.MIND_LINK_STATION, Technique.ARTIFICIAL_MINDS),
    (SignalKind.GROWN_NODE, Technique.GENETIC_ENGINEERING),
    (SignalKind.RADIO_STATION, Technique.RADIO),
    (SignalKind.WIRE_STATION, Technique.TELEGRAPH),
    (SignalKind.BOUND_PAIR, Technique.ALCHEMY),
    (SignalKind.OPTICAL_RELAY, Technique.CRYPTOGRAPHY),
    (SignalKind.COURIER_POST, Technique.PAPER),
    (SignalKind.BEACON_CHAIN, Technique.ALPHABET),
)


@dataclass
class SignalTally:
    built: int = 0
    captured: int = 0
    burned: int = 0


async def known_kind(ctx: TickContext, owner_id: int) -> SignalKind | None:
    for kind, technique in KIND_TECHNIQUES:
        if await has_technique(ctx.session, owner_id, technique):
            return kind
    return None


async def build_links(ctx: TickContext, atlas: RegionAtlas, tally: SignalTally) -> None:
    table = ctx.rules.communication
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        owner = realm.polity_entity_id
        seat = atlas.top_region(realm.capital_entity_id) if realm.capital_entity_id is not None else None
        if seat is None or held(owner) or not ctx.rng(seed_of("signal.build", owner, ctx.epoch)).chance(table.signal_build_pct):
            continue
        kind = await known_kind(ctx, owner)
        if kind is None:
            continue
        linked = set(await ctx.session.scalars(select(SignalLinkRow.to_region_id).where(SignalLinkRow.owner_node_id == owner)))
        far = next((region for region in atlas.neighbour_regions(seat) if region not in linked), None)
        if far is None:
            continue
        ctx.session.add(
            SignalLinkRow(owner_node_id=owner, kind=kind, from_region_id=seat, to_region_id=far, state=SignalState.ACTIVE, since_epoch=ctx.epoch, locked=[])
        )
        tally.built += 1


async def fall_links(ctx: TickContext, tally: SignalTally) -> None:
    occupied = {row.region_entity_id: row.occupier_entity_id for row in await ctx.session.scalars(select(OccupationRow))}
    for link in list(await ctx.session.scalars(select(SignalLinkRow).where(SignalLinkRow.state == SignalState.ACTIVE).order_by(SignalLinkRow.id))):
        if STATE in (link.locked or []) or held(link.owner_node_id):
            continue
        taker = occupied.get(link.to_region_id) or occupied.get(link.from_region_id)
        if taker is None or taker == link.owner_node_id:
            continue
        if link.kind is SignalKind.MIND_LINK_STATION:
            continue
        taken = link.kind is SignalKind.BOUND_PAIR or ctx.rng(seed_of("signal.fall", link.id, ctx.epoch)).chance(CAPTURE_PCT)
        if taken and not CUT_WHEN_TAKEN[link.kind]:
            link.state, link.owner_node_id = SignalState.CAPTURED, taker
            tally.captured += 1
        else:
            link.state = SignalState.BURNED
            tally.burned += 1
