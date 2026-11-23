from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.communication import CUT_WHEN_TAKEN
from aerona.catalog.pacts import SIGNAL_STATES
from aerona.constants.units import PERCENT
from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.military import ArmyProfileRow, OccupationRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import SignalKind, SignalState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import bond_exists, living_entity
from aerona.engine.recording.record import record

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
    jammed: int = 0
    disused: int = 0
    restored: int = 0


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
        if await restore(ctx, owner, seat, tally):
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


async def jam(ctx: TickContext, link: SignalLinkRow, by_id: int) -> bool:
    if not SIGNAL_STATES[link.state].carries or STATE in (link.locked or []) or held(link.owner_node_id):
        return False
    link.state, link.jammed_epoch = SignalState.JAMMED, ctx.epoch
    await record(
        ctx,
        "signal.jammed",
        roles={IncidentRole.ACTOR: by_id, IncidentRole.OWNER: link.owner_node_id, IncidentRole.PLACE: link.to_region_id},
        facts={"station": link.kind},
        place=link.to_region_id,
    )
    return True


async def foes_near(ctx: TickContext, link: SignalLinkRow) -> int | None:
    armies = await ctx.session.execute(
        select(ArmyRow.owner_entity_id)
        .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == ArmyRow.entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), ArmyRow.war_id.is_not(None), ArmyProfileRow.region_entity_id.in_([link.from_region_id, link.to_region_id]))
        .order_by(ArmyRow.entity_id)
    )
    for (owner,) in armies:
        if owner != link.owner_node_id and await bond_exists(ctx.session, owner, link.owner_node_id, BondKind.ENEMY):
            return int(owner)
    return None


async def tend_stations(ctx: TickContext, tally: SignalTally) -> None:
    decay = ctx.rules.signals.disused_decay
    for link in list(await ctx.session.scalars(select(SignalLinkRow).order_by(SignalLinkRow.id))):
        if STATE in (link.locked or []) or held(link.owner_node_id):
            continue
        owner = await living_entity(ctx.session, link.owner_node_id)
        if link.state is SignalState.JAMMED and (link.jammed_epoch or 0) < ctx.epoch:
            link.state, link.jammed_epoch = SignalState.ACTIVE, None
        elif SIGNAL_STATES[link.state].carries and owner is None:
            link.state = SignalState.DISUSED
            tally.disused += 1
        elif link.state is SignalState.DISUSED:
            link.condition = max(0, link.condition - decay)
            if link.condition == 0:
                link.state = SignalState.BURNED
                tally.burned += 1
        elif SIGNAL_STATES[link.state].carries:
            foe = await foes_near(ctx, link)
            if foe is not None and await jam(ctx, link, foe):
                tally.jammed += 1


async def restore(ctx: TickContext, owner_id: int, seat: int, tally: SignalTally) -> bool:
    found = await ctx.session.scalar(
        select(SignalLinkRow).where(SignalLinkRow.from_region_id == seat, SignalLinkRow.state == SignalState.DISUSED).order_by(SignalLinkRow.id).limit(1)
    )
    if found is None or STATE in (found.locked or []):
        return False
    found.state, found.owner_node_id, found.condition = SignalState.ACTIVE, owner_id, PERCENT
    tally.restored += 1
    return True
