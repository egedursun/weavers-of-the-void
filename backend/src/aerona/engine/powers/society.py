from collections import defaultdict

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, PolityMemberRow
from aerona.db.tables.powers import GiftedAttitudeRow, PowerRegistryRow, PowerRestrictionRow, PowerRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import BloodlineRule, GiftedAttitude, GiftedStance, PowerDeviceEffect, PowerOrigin, PowerState, RestrictionKind
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.mind.book import values_for
from aerona.engine.notes import note
from aerona.engine.polity.laws import enact, law_param
from aerona.engine.polity.trials import report_crime
from aerona.engine.powers.devices import devices_of
from aerona.engine.powers.war import field_gifted
from aerona.engine.primitives.folk import present_among, towns_of_people
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record

GIFTED_LAWS = frozenset({"registered", "licensed", "conscripted"})
HUNTING_LAWS = frozenset({"hunted", "banned"})
STANCE_ATTITUDE = {
    GiftedStance.SACRED: GiftedAttitude.HONOURED,
    GiftedStance.FORBIDDEN: GiftedAttitude.PERSECUTED,
    GiftedStance.SUSPECT: GiftedAttitude.FEARED,
    GiftedStance.TOOL: GiftedAttitude.REGULATED,
}
LEAN = 25
BAND_POWER = 4


async def powered_in(ctx: TickContext, town_ids: list[int]) -> list[PowerRow]:
    if not town_ids:
        return []
    here = select(EntityRow.id).where(EntityRow.location_id.in_(town_ids), EntityRow.status == EntityStatus.CANON)
    return list(await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id.in_(here), PowerRow.state != PowerState.LOST).order_by(PowerRow.id)))


async def towns_of(ctx: TickContext, people_id: int) -> list[int]:
    return await towns_of_people(ctx.session, people_id)


async def harmed_by_gifted(ctx: TickContext, people_id: int, holders: set[int]) -> int:
    if not holders:
        return 0
    count = await ctx.session.scalar(
        select(func.count())
        .select_from(MemoryRow)
        .where(MemoryRow.holder_node_id == people_id, MemoryRow.subject_node_id.in_(holders), MemoryRow.magnitude < 0)
    )
    helped = await ctx.session.scalar(
        select(func.count())
        .select_from(MemoryRow)
        .where(MemoryRow.holder_node_id == people_id, MemoryRow.subject_node_id.in_(holders), MemoryRow.magnitude > 0)
    )
    return int(count or 0) - int(helped or 0)


async def attitude_for(ctx: TickContext, people: EntityRow, holders: set[int]) -> GiftedAttitude:
    doctrine = await doctrine_here(ctx.session, people)
    if doctrine is not None and doctrine.power_stance in STANCE_ATTITUDE:
        return STANCE_ATTITUDE[doctrine.power_stance]
    values = dict(await values_for(ctx.session, people.id))
    memory = await harmed_by_gifted(ctx, people.id, holders) * ctx.rules.powered_society.attitude_shift
    lean = values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.PURITY, 0) + memory
    if lean >= LEAN * 3:
        return GiftedAttitude.PERSECUTED
    if lean >= LEAN * 2:
        return GiftedAttitude.FEARED
    if values.get(ValueAxis.LAW, 0) >= LEAN:
        return GiftedAttitude.REGULATED
    if values.get(ValueAxis.KNOWLEDGE, 0) + values.get(ValueAxis.PIETY, 0) - memory >= LEAN * 2:
        return GiftedAttitude.HONOURED
    return GiftedAttitude.ORDINARY


async def keep_attitudes(ctx: TickContext) -> int:
    kept = 0
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        towns = await towns_of(ctx, people.id)
        powers = await powered_in(ctx, towns)
        row = await ctx.session.get(GiftedAttitudeRow, people.id)
        if row is None and not powers:
            continue
        if row is None:
            row = GiftedAttitudeRow(people_entity_id=people.id, locked=[])
            ctx.session.add(row)
        holders = {power.holder_node_id for power in powers}
        mortals = await ctx.session.scalar(
            select(func.count())
            .select_from(EntityRow)
            .where(await present_among(ctx.session, towns), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        )
        if "gifted_share" not in row.locked:
            row.gifted_share = min(PERCENT, len(holders) * PERCENT // max(1, int(mortals or 0), len(holders)))
        if "attitude" not in row.locked:
            row.attitude = await attitude_for(ctx, people, holders)
        registered = await ctx.session.scalar(select(func.count()).select_from(PowerRegistryRow).where(PowerRegistryRow.holder_node_id.in_(holders)))
        if "registered_share" not in row.locked:
            row.registered_share = min(PERCENT, int(registered or 0) * PERCENT // max(1, len(holders)))
        row.updated_epoch = ctx.epoch
        kept += 1
    return kept


async def realm_towns(ctx: TickContext, polity_id: int) -> list[int]:
    return list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))


async def register(ctx: TickContext, polity_id: int, holder_id: int, level: str) -> PowerRegistryRow:
    row = await ctx.session.scalar(select(PowerRegistryRow).where(PowerRegistryRow.polity_entity_id == polity_id, PowerRegistryRow.holder_node_id == holder_id))
    if row is None:
        row = PowerRegistryRow(polity_entity_id=polity_id, holder_node_id=holder_id, registered_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "licensed" not in row.locked:
        row.licensed = level in {"licensed", "conscripted"}
    if "conscripted" not in row.locked:
        row.conscripted = level == "conscripted" and ctx.rng(f"power.conscript.{polity_id}.{holder_id}").chance(ctx.rules.powered_society.conscription_share)
    return row


async def keep_registries(ctx: TickContext) -> int:
    table = ctx.rules.powered_society
    acted = 0
    polities = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for polity in list(polities):
        if held(polity.id):
            continue
        level = str(await law_param(ctx.session, polity.id, LawKind.POWER_LAW, "level") or "free")
        towns = await realm_towns(ctx, polity.id)
        drafted = hunted = 0
        detecting = PowerDeviceEffect.DETECT in await devices_of(ctx.session, [polity.id, *towns])
        for power in await powered_in(ctx, towns):
            holder = await ctx.session.get(EntityRow, power.holder_node_id)
            if holder is None or held(holder.id):
                continue
            seen = power.state is not PowerState.LATENT or detecting or ctx.rng(f"power.registry.{power.id}.{ctx.epoch}").chance(table.registry_detect)
            if level in GIFTED_LAWS and seen:
                entry = await register(ctx, polity.id, holder.id, level)
                drafted += int(entry.conscripted)
                acted += 1
            elif level in HUNTING_LAWS and power.state is PowerState.ACTIVE and holder.location_id is not None:
                await report_crime(ctx, holder.location_id, holder.id, CrimeKind.WITCHCRAFT)
                hunted += 1
                acted += 1
        await field_gifted(ctx, polity.id, UnitKind.GIFTED, drafted)
        await field_gifted(ctx, polity.id, UnitKind.DAMPENERS, hunted)
        await field_gifted(ctx, polity.id, UnitKind.DETECTORS, hunted // 2)
    return acted


async def form_bands(ctx: TickContext) -> int:
    table = ctx.rules.powered_society
    formed = 0
    by_realm: dict[int, set[int]] = defaultdict(set)
    rows = await ctx.session.execute(
        select(PolityMemberRow.polity_entity_id, PowerRow.holder_node_id)
        .join(EntityRow, EntityRow.id == PowerRow.holder_node_id)
        .join(PolityMemberRow, PolityMemberRow.member_entity_id == EntityRow.location_id)
        .where(PowerRow.state == PowerState.ACTIVE, EntityRow.status == EntityStatus.CANON)
    )
    for polity_id, holder_id in rows.all():
        by_realm[polity_id].add(holder_id)
    banded = set(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(
                BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.description == "one of the band"
            )
        )
    )
    for polity_id, holders in sorted(by_realm.items()):
        free = sorted(holders - banded)
        if len(free) < table.band_members or held(polity_id) or not ctx.rng(f"power.band.{polity_id}.{ctx.epoch}").chance(table.band_chance):
            continue
        founder = await ctx.session.get(EntityRow, free[0])
        if founder is None:
            continue
        band = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.FACTION,
                name=f"the band of {founder.name}",
                body=f"Those with powers who gathered around {founder.name}.",
                stats=FactionStats(),
                power=BAND_POWER,
                location_id=founder.location_id,
                world_id=founder.world_id,
            ),
        )
        for member in free:
            await connect(ctx.session, member, band.id, BondKind.MEMBER_OF, ctx.epoch, description="one of the band")
        await note(ctx, f"Those with powers gathered as {band.name}.", key="power.band", ids=[band.id, *free])
        formed += 1
    return formed


async def move_laws(ctx: TickContext) -> int:
    table = ctx.rules.powered_society
    moved = 0
    for row in list(
        await ctx.session.scalars(select(GiftedAttitudeRow).where(GiftedAttitudeRow.attitude.in_([GiftedAttitude.FEARED, GiftedAttitude.PERSECUTED])))
    ):
        homes = await towns_of_people(ctx.session, row.people_entity_id)
        polity_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(homes)).limit(1))
        polity = await ctx.session.get(EntityRow, polity_id) if polity_id is not None else None
        if polity is None or held(polity.id) or not ctx.rng(f"power.law.{polity.id}.{ctx.epoch}").chance(table.law_adopt_chance):
            continue
        current = str(await law_param(ctx.session, polity.id, LawKind.POWER_LAW, "level") or "free")
        wanted = "hunted" if row.attitude is GiftedAttitude.PERSECUTED else "registered"
        if current == wanted:
            continue
        await enact(ctx, polity, LawKind.POWER_LAW, {"level": wanted, "mind_powers": "licensed"})
        moved += 1
    return moved


async def test_people(ctx: TickContext, town_id: int) -> int:
    found = 0
    for power in await powered_in(ctx, [town_id]):
        if power.state is not PowerState.LATENT or "state" in power.locked:
            continue
        if ctx.rng(f"power.test.{power.id}.{ctx.epoch}").chance(ctx.rules.powered_society.testing_finds):
            power.state = PowerState.EMERGING
            found += 1
    return found


async def heirs(ctx: TickContext) -> int:
    inherited = 0
    born = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.birth_epoch == ctx.epoch, EntityRow.status == EntityStatus.CANON)
    )
    for child in list(born):
        if held(child.id):
            continue
        parents = select(BondRow.source_node_id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.target_node_id == child.id)
        rule = await ctx.session.scalar(
            select(HouseProfileRow.bloodline_rule)
            .join(HouseMemberRow, HouseMemberRow.house_entity_id == HouseProfileRow.house_entity_id)
            .where(HouseMemberRow.mortal_entity_id.in_(parents), HouseProfileRow.bloodline_rule != BloodlineRule.NONE)
            .limit(1)
        )
        housed = rule is not None
        rule = rule or BloodlineRule.ALL_CHILDREN
        siblings = await ctx.session.scalar(
            select(func.count())
            .select_from(BondRow)
            .where(BondRow.kind == BondKind.PARENT_OF, BondRow.source_node_id.in_(parents), BondRow.target_node_id != child.id)
        )
        if rule is BloodlineRule.ELDEST and int(siblings or 0) > 0:
            continue
        for power in list(
            await ctx.session.scalars(
                select(PowerRow).where(PowerRow.holder_node_id.in_(parents), PowerRow.origin.in_([PowerOrigin.BLOODLINE, PowerOrigin.EXPOSURE]))
            )
        ):
            if power.origin is PowerOrigin.BLOODLINE and not housed:
                continue
            if rule is BloodlineRule.SKIPPED and ctx.rng(f"power.skip.{child.id}.{power.id}").chance(PERCENT // 2):
                continue
            if not ctx.rng(f"power.blood.{child.id}.{power.id}").chance(ctx.rules.powers.bloodline_chance):
                continue
            ctx.session.add(
                PowerRow(
                    holder_node_id=child.id,
                    system_id=power.system_id,
                    source_id=power.source_id,
                    technique=power.technique,
                    form=power.form,
                    strength=power.strength,
                    control=0,
                    origin=power.origin,
                    state=PowerState.LATENT,
                    visibility=power.visibility,
                    strain=0,
                    strain_cap=power.strain_cap,
                    uses=0,
                    gained_epoch=ctx.epoch,
                    locked=[],
                )
            )
            inherited += 1
    return inherited


async def at_death(ctx: TickContext) -> int:
    ended = 0
    gone = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON, EntityRow.end_epoch == ctx.epoch)
    for power in list(await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id.in_(gone), PowerRow.state != PowerState.LOST))):
        if held(power.holder_node_id) or "state" in power.locked:
            continue
        if power.origin in {PowerOrigin.MADE, PowerOrigin.GROWN, PowerOrigin.HELD} and power.item_node_id is not None:
            power.holder_node_id = power.item_node_id
            power.state = PowerState.LATENT
        else:
            power.state = PowerState.LOST
        ended += 1
    return ended


async def broken_vows(ctx: TickContext) -> int:
    broken = 0
    vows = await ctx.session.execute(
        select(PowerRestrictionRow, PowerRow)
        .join(PowerRow, PowerRow.id == PowerRestrictionRow.power_id)
        .where(PowerRestrictionRow.kind.in_([RestrictionKind.SPOKEN_VOW, RestrictionKind.FORBIDDEN_ACT]), PowerRestrictionRow.broken.is_(False))
    )
    for restriction, power in vows.all():
        if held(power.holder_node_id) or "broken" in restriction.locked:
            continue
        oath = await ctx.session.scalar(
            select(SecretRow.id).where(SecretRow.holder_node_id == power.holder_node_id, SecretRow.kind == IntrigueSecret.BROKEN_OATH).limit(1)
        )
        if oath is None:
            continue
        restriction.broken = True
        if "state" not in power.locked:
            power.state = PowerState.LOST
        await note(ctx, "A vow was broken, and the power bound to it was lost.", key="power.vow_broken", ids=[power.holder_node_id])
        broken += 1
    return broken


@reads(
    "cult.zeal",
    "table.armies",
    "table.bonds",
    "table.cult_doctrines",
    "table.entities",
    "table.gifted_attitudes",
    "table.house_members",
    "table.house_profiles",
    "table.law_profiles",
    "table.memories",
    "table.personality_values",
    "table.polity_members",
    "table.power_registry",
    "table.power_restrictions",
    "table.powers",
    "table.secrets",
)
@writes(
    "table.bonds",
    "table.crime_cases",
    "table.entities",
    "table.gifted_attitudes",
    "table.law_profiles",
    "table.power_registry",
    "table.power_restrictions",
    "table.powers",
)
async def keep_powered_society(ctx: TickContext) -> None:
    ctx.count("gifted_attitudes_kept", await keep_attitudes(ctx))
    ctx.count("registry_acts", await keep_registries(ctx))
    ctx.count("power_bands_formed", await form_bands(ctx))
    ctx.count("power_laws_moved", await move_laws(ctx))
    ctx.count("bloodline_powers", await heirs(ctx))
    ctx.count("powers_ended_at_death", await at_death(ctx))
    ctx.count("vows_broken", await broken_vows(ctx))
    await ctx.session.flush()
