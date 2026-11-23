from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import POWER_STATE_TRAITS, having
from aerona.catalog.seals import LINK_LABELS, SEALS
from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import DeepSealRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.powers import PowerRow
from aerona.db.write_guard import held
from aerona.domain.enums.couplings import SealKind, SealLink
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import PowerStateTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathStatus
from aerona.domain.enums.powers import PowerState
from aerona.engine.context import TickContext
from aerona.engine.couplings.rite_body import owned_rites
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record


async def active_seal(session: AsyncSession, place_id: int) -> DeepSealRow | None:
    return await session.scalar(
        select(DeepSealRow).where(DeepSealRow.place_entity_id == place_id, DeepSealRow.broken_epoch.is_(None), DeepSealRow.strength > 0).limit(1)
    )


USABLE_POWERS = having(POWER_STATE_TRAITS, PowerStateTrait.USABLE)


@dataclass(frozen=True)
class SealLinks:
    oath_id: int | None = None
    power_id: int | None = None
    line_id: int | None = None


def missing_link(kind: SealKind, links: SealLinks) -> str | None:
    link = SEALS[kind].link
    given = {SealLink.OATH: links.oath_id, SealLink.POWER: links.power_id, SealLink.LINE: links.line_id}
    return LINK_LABELS[link] if link is not None and given[link] is None else None


async def seal_deep(
    ctx: TickContext, place_id: int, kind: SealKind, sealer_id: int | None, *, strength: int | None = None, links: SealLinks | None = None
) -> DeepSealRow:
    linked = links or SealLinks()
    row = DeepSealRow(
        place_entity_id=place_id,
        kind=kind,
        strength=clamp_percent(strength if strength is not None else SEALS[kind].strength(ctx.rules)),
        decay=SEALS[kind].decay(ctx.rules),
        sealer_node_id=sealer_id,
        pact_oath_id=linked.oath_id,
        power_id=linked.power_id,
        living_line_id=linked.line_id,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def knows_school(ctx: TickContext, holder_id: int, school: MagicSchool) -> bool:
    rites = await owned_rites(ctx, holder_id)
    if not rites:
        return False
    found = await ctx.session.scalar(
        select(RiteProfileRow.rite_entity_id).where(RiteProfileRow.rite_entity_id.in_(rites), RiteProfileRow.school == school).limit(1)
    )
    return found is not None


async def sealing_means(ctx: TickContext, community: EntityRow) -> tuple[SealKind, SealLinks] | None:
    member = select(EntityRow.id).where(EntityRow.location_id == community.id, EntityRow.status == EntityStatus.CANON)
    power = await ctx.session.scalar(
        select(PowerRow.id)
        .where(PowerRow.holder_node_id.in_(member), PowerRow.state == PowerState.ACTIVE)
        .order_by(PowerRow.strength.desc(), PowerRow.id)
        .limit(1)
    )
    if power is not None:
        return SealKind.POWER, SealLinks(power_id=power)
    line = await ctx.session.scalar(
        select(LivingLineRow.id).where(LivingLineRow.owner_node_id == community.id, LivingLineRow.escaped.is_(False)).order_by(LivingLineRow.id).limit(1)
    )
    if line is not None:
        return SealKind.LIVING, SealLinks(line_id=line)
    if await knows_school(ctx, community.id, MagicSchool.WARDING):
        return SealKind.RITE, SealLinks()
    if stat_or(community, "prosperity", 0) >= ctx.rules.deep_seals.structure_prosperity:
        return SealKind.STRUCTURE, SealLinks()
    return None


async def seal_after_breach(ctx: TickContext, resource: EntityRow, community: EntityRow) -> DeepSealRow | None:
    if held(resource.id, community.id) or await active_seal(ctx.session, resource.id) is not None:
        return None
    means = await sealing_means(ctx, community)
    if means is None:
        return None
    kind, links = means
    row = await seal_deep(ctx, resource.id, kind, community.id, links=links)
    await record(ctx, "seal.made", roles={IncidentRole.SUBJECT: [community.id, resource.id]})
    return row


async def danger_below(ctx: TickContext, region_id: int | None) -> int:
    if region_id is None:
        return 0
    statement = (
        select(EntityRow)
        .join(SpeciesRangeRow, SpeciesRangeRow.species_entity_id == EntityRow.id)
        .where(SpeciesRangeRow.region_entity_id == region_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.SPECIES)
    )
    return max((stat_or(species, "danger", 0) for species in await ctx.session.scalars(statement)), default=0)


async def test_seal(ctx: TickContext, row: DeepSealRow) -> None:
    table = ctx.rules.deep_seals
    place = await ctx.session.get(EntityRow, row.place_entity_id)
    if place is None or held(place.id) or "strength" in row.locked:
        return
    loss = row.decay
    if row.kind is SealKind.RITE and row.sealer_node_id is not None and not await knows_school(ctx, row.sealer_node_id, MagicSchool.WARDING):
        loss += table.lapsed_rite
    if row.kind is SealKind.PACT and await pact_broken(ctx, row):
        await break_pact(ctx, row, place)
        return
    if row.kind is SealKind.POWER and not await power_holds(ctx, row):
        loss = row.strength
    if row.kind is SealKind.LIVING:
        loss = await living_change(ctx, row)
    if await danger_below(ctx, place.location_id) >= table.beast_danger:
        loss += table.beast_test
    profile = await ctx.session.get(ResourceProfileRow, place.id)
    if profile is not None and profile.reserve * PERCENT < profile.initial_reserve * table.unseal_reserve_pct:
        row.strength = 0
        row.broken_epoch = ctx.epoch
        await record(ctx, "seal.unsealed", roles={IncidentRole.SUBJECT: place.id})
        return
    before = row.strength
    row.strength = clamp_percent(row.strength - loss)
    if before > PERCENT // 2 >= row.strength > 0:
        await record(ctx, "seal.weakened", roles={IncidentRole.SUBJECT: place.id}, facts={"strength": row.strength}, place=place.id)
    if row.strength == 0:
        row.broken_epoch = ctx.epoch
        await record(ctx, "seal.broken", roles={IncidentRole.SUBJECT: place.id})


async def pact_broken(ctx: TickContext, row: DeepSealRow) -> bool:
    oath = await ctx.session.get(OathRow, row.pact_oath_id) if row.pact_oath_id is not None else None
    return oath is None or oath.status is not OathStatus.SWORN


async def break_pact(ctx: TickContext, row: DeepSealRow, place: EntityRow) -> None:
    row.strength = 0
    row.broken_epoch = ctx.epoch
    oath = await ctx.session.get(OathRow, row.pact_oath_id) if row.pact_oath_id is not None else None
    breaker = oath.swearer_entity_id if oath is not None else row.sealer_node_id
    below = oath.recipient_node_id if oath is not None else None
    if breaker is not None and below is not None and not held(below):
        grievance = ctx.rules.deep_seals.pact_grievance
        await remember(ctx.session, ctx.rules, holder_id=below, subject_id=breaker, kind=MemoryKind.BROKE_OATH, magnitude=-grievance, epoch=ctx.epoch)
    await record(ctx, "seal.pact_broken", roles={IncidentRole.SUBJECT: place.id, IncidentRole.ACTOR: breaker}, place=place.id)


async def power_holds(ctx: TickContext, row: DeepSealRow) -> bool:
    power = await ctx.session.get(PowerRow, row.power_id) if row.power_id is not None else None
    if power is None or power.state not in USABLE_POWERS:
        return False
    holder = await ctx.session.get(EntityRow, power.holder_node_id)
    return holder is None or holder.status is not EntityStatus.DEAD


async def living_change(ctx: TickContext, row: DeepSealRow) -> int:
    line = await ctx.session.get(LivingLineRow, row.living_line_id) if row.living_line_id is not None else None
    fed = line is not None and not line.escaped and line.stability > 0
    return row.decay - ctx.rules.deep_seals.living_feed if fed else row.strength


@reads("table.bonds", "table.deep_seals", "table.resource_profiles", "table.rite_profiles", "table.species_ranges")
@writes("table.deep_seals")
async def deep_seals(ctx: TickContext) -> None:
    for row in list(await ctx.session.scalars(select(DeepSealRow).where(DeepSealRow.broken_epoch.is_(None)).order_by(DeepSealRow.id))):
        await test_seal(ctx, row)
    await ctx.session.flush()
