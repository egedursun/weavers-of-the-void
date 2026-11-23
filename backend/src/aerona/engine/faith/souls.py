from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.faith import FEAR_OF_TORMENT_VALUE_AXISS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import CastingRow, RiteEffectRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, PossessionRow, ReincarnationRow, SpiritProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import free_rows
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import (
    AfterlifeState,
    BindingKind,
    JudgementDoctrine,
    RebirthPath,
    ReincarnationGate,
    SpiritAlignment,
    StratumValence,
    TenetKind,
)
from aerona.domain.enums.mind import MemoryKind, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import CreatureTrait, NaturalLaw
from aerona.domain.enums.transform import TransformKind
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.conditions import condition_of, end_condition
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of as creature_traits
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.faith.book import Church, faith_tenets
from aerona.engine.faith.judgement import leave_realm, ledger_score, reaches_living, seal, unseal
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.mind.book import add_trait, stored_values, values_for, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.phases.births import BirthPlan, born_mortal
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_of, present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record
from aerona.engine.sacred.guards import warded_hosts
from aerona.engine.sacred.places import enclosing
from aerona.engine.transform.record import blocked, record_transformation

LIVING_STATES = (AfterlifeState.WANDERING, AfterlifeState.JUDGED, AfterlifeState.IN_REALM)


async def profiles(ctx: TickContext) -> list[tuple[SpiritProfileRow, EntityRow]]:
    rows = await ctx.session.execute(
        select(SpiritProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == SpiritProfileRow.spirit_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, SpiritProfileRow.state.in_(list(LIVING_STATES)))
        .order_by(SpiritProfileRow.spirit_entity_id)
    )
    return [(profile, spirit) for profile, spirit in rows.all()]


async def home_of(ctx: TickContext, profile: SpiritProfileRow) -> EntityRow | None:
    mortal = await ctx.session.get(EntityRow, profile.origin_mortal_id) if profile.origin_mortal_id is not None else None
    return await living_entity(ctx.session, mortal.location_id) if mortal is not None and mortal.location_id is not None else None


async def venerates(ctx: TickContext, community: EntityRow) -> bool:
    if TenetKind.ANCESTOR_VENERATION in await faith_tenets(ctx.session, community.id):
        return True
    return (await values_for(ctx.session, community.id)).get(ValueAxis.DEATH, 0) >= ctx.rules.spirits.ancestor_death_value


async def house_luck(ctx: TickContext, profile: SpiritProfileRow) -> int:
    if profile.alignment is not SpiritAlignment.GUARDIAN or profile.origin_mortal_id is None or not await reaches_living(ctx.session, profile):
        return 0
    houses = await ctx.session.scalars(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == profile.origin_mortal_id))
    lucky = 0
    for house_id in houses:
        house = await ctx.session.get(HouseProfileRow, house_id)
        if house is None or house.extinct_epoch is not None or "wealth" in house.locked:
            continue
        house.wealth += round_half_up(ctx.rules.spirits.house_luck * max(profile.veneration, ctx.rules.spirits.guardian_veneration) / PERCENT)
        lucky += 1
    return lucky


async def tend(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> str:
    table = ctx.rules.spirits
    home = await home_of(ctx, profile)
    fed = home is not None and await venerates(ctx, home) and ctx.rng(f"offering.{spirit.id}.{ctx.epoch}").chance(table.offering_chance)
    if fed:
        if "veneration" not in profile.locked:
            profile.veneration = clamp_int(profile.veneration + table.remembrance, 0, PERCENT)
        if "memory_strength" not in profile.locked:
            profile.memory_strength = clamp_int(profile.memory_strength + table.remembrance, 0, PERCENT)
    else:
        if "memory_strength" not in profile.locked:
            profile.memory_strength = clamp_int(profile.memory_strength - table.memory_decay, 0, PERCENT)
        if "veneration" not in profile.locked:
            profile.veneration = clamp_int(profile.veneration - table.memory_decay, 0, PERCENT)
    unrest = stat(spirit, "unrest") or 0
    if profile.alignment is SpiritAlignment.GUARDIAN and not fed and profile.veneration < table.guardian_veneration:
        unrest = clamp_int(unrest + table.neglect_unrest, 0, PERCENT)
        set_stats(spirit, unrest=unrest)
    if "alignment" not in profile.locked:
        if unrest >= table.vengeful_unrest:
            profile.alignment = SpiritAlignment.VENGEFUL
        elif profile.veneration >= table.guardian_veneration:
            profile.alignment = SpiritAlignment.GUARDIAN
    ctx.count("houses_lucky", await house_luck(ctx, profile))
    profile.updated_epoch = ctx.epoch
    return "fed" if fed else "forgotten" if profile.memory_strength == 0 else "kept"


async def gates(ctx: TickContext, profile: SpiritProfileRow, home: EntityRow | None) -> ReincarnationGate | None:
    if profile.sealed:
        return None
    tenets = await faith_tenets(ctx.session, home.id) if home is not None else set()
    if TenetKind.SOULS_REST in tenets:
        return None
    if TenetKind.REINCARNATION in tenets:
        return ReincarnationGate.TENET
    laws = await ctx.laws()
    if home is not None and laws.has(NaturalLaw.SOULS_REINCARNATE, home.world_id):
        return ReincarnationGate.NATURAL_LAW
    if home is not None and await rebirth_rite(ctx, home.id, profile.spirit_entity_id):
        return ReincarnationGate.RITE
    return None


async def rebirth_rite(ctx: TickContext, home_id: int, spirit_id: int) -> bool:
    rites = select(RiteEffectRow.rite_entity_id).where(RiteEffectRow.effect.in_([RiteEffectKind.RAISE_DEAD, RiteEffectKind.UNSEAL_SOUL]))
    casters = select(EntityRow.id).where(EntityRow.location_id == home_id)
    statement = select(CastingRow.id).where(
        CastingRow.rite_entity_id.in_(rites),
        CastingRow.succeeded.is_(True),
        CastingRow.epoch >= ctx.epoch - 1,
        (CastingRow.target_entity_id == spirit_id) | CastingRow.caster_entity_id.in_(casters),
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def soul_doctrine(session: AsyncSession, profile: SpiritProfileRow) -> CultDoctrineRow | None:
    if profile.patron_son_id is None:
        return None
    cults = select(BondRow.source_node_id).where(BondRow.target_node_id == profile.patron_son_id, BondRow.kind == BondKind.WORSHIPS)
    return await session.scalar(select(CultDoctrineRow).where(CultDoctrineRow.cult_entity_id.in_(cults)).order_by(CultDoctrineRow.cult_entity_id).limit(1))


async def house_of(session: AsyncSession, mortal_id: int | None) -> HouseProfileRow | None:
    if mortal_id is None:
        return None
    house_id = await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).limit(1))
    house = await session.get(HouseProfileRow, house_id) if house_id is not None else None
    return house if house is not None and house.extinct_epoch is None else None


async def faithful_homes(session: AsyncSession, profile: SpiritProfileRow, world_id: int | None) -> list[EntityRow]:
    if profile.patron_son_id is None:
        return []
    worshippers = select(BondRow.source_node_id).where(
        BondRow.target_node_id == profile.patron_son_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
    )
    statement = select(EntityRow).where(EntityRow.id.in_(worshippers), EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON)
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


@dataclass(frozen=True)
class Cradle:
    community: EntityRow
    path: RebirthPath
    house: HouseProfileRow | None = field(default=None)


async def cradle(ctx: TickContext, profile: SpiritProfileRow, home: EntityRow) -> Cradle:
    doctrine = await soul_doctrine(ctx.session, profile)
    path = doctrine.rebirth_path if doctrine is not None else RebirthPath.PEOPLE
    if path is RebirthPath.HOUSE:
        house = await house_of(ctx.session, profile.origin_mortal_id)
        head = await living_entity(ctx.session, house.head_entity_id) if house is not None and house.head_entity_id is not None else None
        seat = await living_entity(ctx.session, head.location_id) if head is not None and head.location_id is not None else None
        if house is not None:
            return Cradle(seat if seat is not None and seat.entity_type in COMMUNITY_TYPES else home, path, house)
    if path is RebirthPath.MERIT:
        table = ctx.rules.afterlife
        score = ledger_score(profile.deeds)
        homes = await faithful_homes(ctx.session, profile, home.world_id) or [home]
        ranked = sorted(homes, key=lambda item: (stat(item, "prosperity") or 0, -item.id))
        if score >= table.paradise_score:
            return Cradle(ranked[-1], path)
        if score < table.torment_score:
            return Cradle(ranked[0], path)
    return Cradle(home, path)


async def kind_to_bear(ctx: TickContext, spirit: EntityRow, home: EntityRow) -> EntityRow | None:
    region = await enclosing(ctx.session, home, EntityType.REGION)
    if region is None or not ctx.rng(f"rebirth.kind.{spirit.id}.{ctx.epoch}").chance(ctx.rules.rebirth.kind_path_pct):
        return None
    ranges = await ctx.session.scalars(
        select(SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id == region.id, SpeciesRangeRow.abundance > 0)
        .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.species_entity_id)
    )
    living = [species for species_id in ranges if (species := await living_entity(ctx.session, species_id)) is not None]
    return living[0] if living else None


async def reborn_as_kind(
    ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow, home: EntityRow, *, gate: ReincarnationGate, species: EntityRow
) -> EntityRow:
    old = await ctx.session.get(EntityRow, profile.origin_mortal_id) if profile.origin_mortal_id is not None else None
    folk = await people_of(ctx.session, home)
    if folk is not None and not frozen(folk.id):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=folk.id,
            subject_id=species.id,
            kind=MemoryKind.GOODWILL,
            magnitude=ctx.rules.rebirth.kind_reverence,
            epoch=ctx.epoch,
            note="one of their dead was born again as one of its kind",
        )
    ctx.session.add(
        ReincarnationRow(
            spirit_entity_id=spirit.id,
            past_mortal_id=old.id if old is not None else None,
            newborn_entity_id=None,
            community_entity_id=home.id,
            gate=gate,
            path=RebirthPath.KIND,
            species_entity_id=species.id,
            memory_pct=ctx.rules.afterlife.reincarnation_memory_pct,
            epoch=ctx.epoch,
        )
    )
    await record(
        ctx,
        "soul.reborn",
        roles={IncidentRole.PREDECESSOR: old.id if old is not None else spirit.id, IncidentRole.PRODUCT: species.id, IncidentRole.PLACE: home.id},
        facts={"path": RebirthPath.KIND},
    )
    await leave_realm(ctx, profile, AfterlifeState.REBORN)
    await retire_in(ctx, spirit, f"born again as one of the {species.name}", close_bonds=False)
    return species


async def rebirth(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow, home: EntityRow, gate: ReincarnationGate) -> EntityRow:
    table = ctx.rules.afterlife
    old = await ctx.session.get(EntityRow, profile.origin_mortal_id) if profile.origin_mortal_id is not None else None
    name = old.name if old is not None else spirit.name
    place = await cradle(ctx, profile, home)
    species = await kind_to_bear(ctx, spirit, home) if place.path is RebirthPath.KIND else None
    if species is not None:
        return await reborn_as_kind(ctx, profile, spirit, home, gate=gate, species=species)
    plan = BirthPlan(name=name, subtype="reborn", role=MortalRole.COMMONER, body=f"Born again with the soul of {name}.")
    child = await born_mortal(ctx, place.community, plan)
    set_stats(child, age=0)
    if place.house is not None:
        ctx.session.add(HouseMemberRow(house_entity_id=place.house.house_entity_id, mortal_entity_id=child.id, joined_epoch=ctx.epoch, by_marriage=False))
    carried = round_half_up(len(profile.traits) * table.reincarnation_traits_pct / PERCENT)
    for trait in profile.traits[:carried]:
        await add_trait(ctx.session, child.id, TraitKind(trait), TraitSource.INHERITED, ctx.epoch, source_node_id=spirit.id)
    if old is not None:
        memories = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == old.id).order_by(MemoryRow.id))
        for memory in memories:
            faint = round_half_up(memory.magnitude * table.reincarnation_memory_pct / PERCENT)
            if faint and memory.subject_node_id != child.id:
                await remember(
                    ctx.session,
                    ctx.rules,
                    holder_id=child.id,
                    subject_id=memory.subject_node_id,
                    kind=memory.kind,
                    magnitude=faint,
                    epoch=ctx.epoch,
                    note="from a past life",
                    inherited_from=old.id,
                )
    ctx.session.add(
        ReincarnationRow(
            spirit_entity_id=spirit.id,
            past_mortal_id=old.id if old is not None else None,
            newborn_entity_id=child.id,
            community_entity_id=place.community.id,
            gate=gate,
            path=place.path,
            memory_pct=table.reincarnation_memory_pct,
            epoch=ctx.epoch,
        )
    )
    await record(
        ctx,
        "soul.reborn",
        roles={IncidentRole.PREDECESSOR: old.id if old is not None else spirit.id, IncidentRole.PRODUCT: child.id, IncidentRole.PLACE: place.community.id},
        facts={"path": place.path},
    )
    await leave_realm(ctx, profile, AfterlifeState.REBORN)
    await retire_in(ctx, spirit, f"born again as {child.name}", close_bonds=False)
    return child


async def reincarnate(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> EntityRow | None:
    table = ctx.rules.afterlife
    home = await home_of(ctx, profile)
    gate = await gates(ctx, profile, home) if "state" not in profile.locked else None
    if gate is None or home is None or ledger_score(profile.deeds) < table.reincarnation_min_score:
        return None
    if not ctx.rng(f"rebirth.{spirit.id}.{ctx.epoch}").chance(table.reincarnation_chance_pct) or await blocked(ctx, TransformKind.REINCARNATION, spirit.id):
        return None
    child = await rebirth(ctx, profile, spirit, home, gate)
    await record_transformation(ctx, TransformKind.REINCARNATION, spirit.id, child.id)
    return child


def restless(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> bool:
    return profile.alignment is SpiritAlignment.VENGEFUL or (stat(spirit, "unrest") or 0) >= ctx.rules.apocalypse.restless_threshold


async def take_host(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow, host: EntityRow) -> PossessionRow:
    original = await stored_values(ctx.session, ValueHolder.PERSONAL, host.id)
    row = PossessionRow(
        host_entity_id=host.id,
        spirit_entity_id=spirit.id,
        since_epoch=ctx.epoch,
        stress=0,
        host_values={axis.value: value for axis, value in original.items()},
        locked=[],
    )
    ctx.session.add(row)
    if profile.imprint:
        await write_values(ctx.session, ValueHolder.PERSONAL, host.id, {ValueAxis(axis): value for axis, value in profile.imprint.items()})
    if "binding" not in profile.locked:
        profile.binding, profile.bound_entity_id = BindingKind.PERSON, host.id
    if await condition_of(ctx, host.id, ConditionKind.POSSESSION) is None:
        await afflict(ctx, host, PackageKind.POSSESSION, Transmission.CURSE, source_node_id=spirit.id)
    await ctx.session.flush()
    return row


async def release_host(ctx: TickContext, row: PossessionRow, *, end: bool = True) -> None:
    host = await ctx.session.get(EntityRow, row.host_entity_id)
    profile = await ctx.session.get(SpiritProfileRow, row.spirit_entity_id)
    if host is not None and row.host_values:
        await write_values(ctx.session, ValueHolder.PERSONAL, host.id, {ValueAxis(axis): value for axis, value in row.host_values.items()})
    if profile is not None and profile.bound_entity_id == row.host_entity_id and "binding" not in profile.locked:
        profile.binding, profile.bound_entity_id = BindingKind.NONE, None
    if end and host is not None:
        await end_condition(ctx, host, ConditionKind.POSSESSION)
    await ctx.session.delete(row)
    await ctx.session.flush()


async def possess(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> EntityRow | None:
    if not restless(ctx, profile, spirit) or spirit.location_id is None or profile.binding is BindingKind.PERSON or "state" in profile.locked:
        return None
    if not ctx.rng(f"possess.{spirit.id}.{ctx.epoch}").chance(ctx.rules.necromancy.possession_chance):
        return None
    taken = select(PossessionRow.host_entity_id)
    host = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, [spirit.location_id]),
            EntityRow.id.not_in(taken),
            EntityRow.id.not_in(warded_hosts()),
            free_rows(EntityRow.id),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if host is None or await blocked(ctx, TransformKind.POSSESSION, spirit.id):
        return None
    await take_host(ctx, profile, spirit, host)
    await record_transformation(ctx, TransformKind.POSSESSION, spirit.id, host.id)
    return host


async def burden(ctx: TickContext) -> list[tuple[PossessionRow, EntityRow, EntityRow]]:
    table = ctx.rules.necromancy
    held: list[tuple[PossessionRow, EntityRow, EntityRow]] = []
    for row in list(await ctx.session.scalars(select(PossessionRow).order_by(PossessionRow.host_entity_id))):
        host = await living_entity(ctx.session, row.host_entity_id)
        spirit = await living_entity(ctx.session, row.spirit_entity_id)
        if host is None or spirit is None:
            await release_host(ctx, row, end=host is not None)
            continue
        if await condition_of(ctx, host.id, ConditionKind.POSSESSION) is None:
            await release_host(ctx, row, end=False)
            continue
        if "stress" not in row.locked:
            row.stress = clamp_int(row.stress + table.possession_stress, 0, PERCENT)
        shift_sanity(ctx.rules, host, -row.stress * table.possession_sanity_pct / PERCENT)
        held.append((row, host, spirit))
    return held


async def exorcise(ctx: TickContext, host: EntityRow, power: int) -> bool:
    table = ctx.rules.necromancy
    row = await ctx.session.get(PossessionRow, host.id)
    if row is None:
        return False
    community = await living_entity(ctx.session, host.location_id) if host.location_id is not None else None
    piety = (stat(community, "piety") or 0) if community is not None else 0
    chance = power * table.exorcism_per_power * (1 + piety * table.exorcism_piety_pct / PERCENT / PERCENT)
    if not ctx.rng(f"exorcise.{host.id}.{ctx.epoch}").chance(clamp_int(chance, 0, PERCENT)):
        return False
    await release_host(ctx, row)
    return True


async def seal_with(ctx: TickContext, spirit_id: int, power: int) -> bool:
    profile = await ctx.session.get(SpiritProfileRow, spirit_id)
    if profile is None:
        return False
    seal(profile, power * ctx.rules.necromancy.seal_per_power)
    return profile.sealed


async def unseal_with(ctx: TickContext, spirit_id: int, power: int) -> bool:
    profile = await ctx.session.get(SpiritProfileRow, spirit_id)
    if profile is None or not profile.sealed:
        return False
    if power * ctx.rules.necromancy.seal_per_power <= profile.seal_strength:
        return False
    unseal(profile)
    return not profile.sealed


async def soul_near(ctx: TickContext, place_id: int | None, *, sealed: bool) -> SpiritProfileRow | None:
    if place_id is None:
        return None
    here = select(EntityRow.id).where(EntityRow.location_id == place_id, EntityRow.status == EntityStatus.CANON)
    mortals = select(EntityRow.id).where(await present_among(ctx.session, [place_id]), EntityRow.entity_type == EntityType.MORTAL)
    statement = select(SpiritProfileRow).where(
        SpiritProfileRow.state.in_(list(LIVING_STATES)),
        SpiritProfileRow.sealed.is_(sealed),
        SpiritProfileRow.spirit_entity_id.in_(here) | SpiritProfileRow.origin_mortal_id.in_(mortals),
    )
    return await ctx.session.scalar(statement.order_by(SpiritProfileRow.spirit_entity_id).limit(1))


@dataclass(frozen=True)
class Eater:
    entity: EntityRow
    outer: bool


async def soul_eaters(ctx: TickContext, atlas: RegionAtlas) -> dict[int, list[Eater]]:
    eaters = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_([EntityType.SPECIES, EntityType.OUTER_BEING]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    regions: dict[int, list[Eater]] = {}
    for eater in eaters:
        outer = eater.entity_type is EntityType.OUTER_BEING
        if outer or CreatureTrait.SOUL_EATER in await creature_traits(ctx.session, eater.id):
            region = atlas.top_region(eater.id)
            if region is not None:
                regions.setdefault(region, []).append(Eater(eater, outer))
    return regions


async def feed_eater(ctx: TickContext, eater: EntityRow) -> SonRow | None:
    creator = await ctx.session.get(SonRow, eater.creator_son_id) if eater.creator_son_id is not None else None
    if creator is None or not creator.alive or await ctx.god_share(creator.id, DomainHook.SOUL_HOLD) <= 0:
        return None
    before = creator.essence
    creator.essence += ctx.rules.necromancy.consumption_essence
    cap_gained_essence(ctx.rules, creator, before)
    return creator


async def consume(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow, eater: EntityRow | None = None) -> SonRow | None:
    await leave_realm(ctx, profile, AfterlifeState.CONSUMED)
    await retire_in(ctx, spirit, "devoured by a soul-eater", close_bonds=True)
    owner = await ctx.session.get(SonRow, profile.patron_son_id) if profile.patron_son_id is not None else None
    if owner is not None and owner.alive:
        owner.essence = max(0, owner.essence - ctx.rules.necromancy.consumption_loss)
    return await feed_eater(ctx, eater) if eater is not None else None


async def gnaw(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow, eaters: list[Eater]) -> str | None:
    table = ctx.rules.necromancy
    if "state" in profile.locked:
        return None
    for eater in eaters:
        if ctx.rng(f"eaten.{spirit.id}.{eater.entity.id}.{ctx.epoch}").chance(table.soul_eater_chance):
            await consume(ctx, profile, spirit, eater.entity)
            return "eaten"
        if eater.outer and not profile.sealed and ctx.rng(f"gnawed.{spirit.id}.{eater.entity.id}.{ctx.epoch}").chance(table.outer_seal_chance):
            seal(profile, table.outer_seal)
            return "gnawed"
    return None


async def realm_population(session: AsyncSession, son_id: int) -> int:
    found = await session.scalar(
        select(func.count(SpiritProfileRow.spirit_entity_id))
        .join(EntityRow, EntityRow.id == SpiritProfileRow.spirit_entity_id)
        .where(SpiritProfileRow.patron_son_id == son_id, SpiritProfileRow.state == AfterlifeState.IN_REALM, EntityRow.status == EntityStatus.CANON)
    )
    return int(found or 0)


async def realm_essence(ctx: TickContext) -> int:
    drawn = 0
    for son in list(await ctx.session.scalars(select(SonRow).order_by(SonRow.id))):
        hold = await ctx.god_share(son.id, DomainHook.SOUL_HOLD)
        if not son.alive or hold <= 0:
            continue
        gain = round(await realm_population(ctx.session, son.id) * ctx.rules.afterlife.realm_essence_per_100 * hold / PERCENT)
        if gain > 0:
            before = son.essence
            son.essence += gain
            cap_gained_essence(ctx.rules, son, before)
            drawn += gain
    return drawn


async def tormented(ctx: TickContext, church: Church) -> int:
    if church.god is None:
        return 0
    origins = select(EntityRow.id).where(EntityRow.world_id == church.cult.world_id)
    found = await ctx.session.scalar(
        select(func.count(SpiritProfileRow.spirit_entity_id))
        .join(AfterlifeStratumRow, AfterlifeStratumRow.id == SpiritProfileRow.stratum_id)
        .where(
            SpiritProfileRow.patron_son_id == church.god.id,
            SpiritProfileRow.state == AfterlifeState.IN_REALM,
            SpiritProfileRow.origin_mortal_id.in_(origins),
            AfterlifeStratumRow.valence == StratumValence.PUNISHMENT,
        )
    )
    return int(found or 0)


async def fear_of_torment(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None or doctrine.judgement is not JudgementDoctrine.DEEDS or not await tormented(ctx, church):
        return 0
    table = ctx.rules.afterlife
    moved = 0
    for member in church.members:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, member.id)
        if not values:
            continue
        changed = False
        for axis in FEAR_OF_TORMENT_VALUE_AXISS:
            current = values.get(axis, 0)
            if current < table.torment_value_target:
                values[axis] = min(table.torment_value_target, current + table.torment_honour)
                changed = True
        if changed:
            await write_values(ctx.session, ValueHolder.CULTURE, member.id, values)
            moved += 1
    return moved


async def guardians_of(ctx: TickContext, community_id: int) -> int:
    mortals = select(EntityRow.id).where(await present_among(ctx.session, [community_id]), EntityRow.entity_type == EntityType.MORTAL)
    rows = await ctx.session.scalars(
        select(SpiritProfileRow.spirit_entity_id).where(SpiritProfileRow.origin_mortal_id.in_(mortals), SpiritProfileRow.alignment == SpiritAlignment.GUARDIAN)
    )
    return len(list(rows))


async def ancestral_site(ctx: TickContext, community: EntityRow, place_id: int | None) -> bool:
    if place_id is None:
        return False
    if place_id in {community.id, community.location_id}:
        return True
    atlas = await RegionAtlas.load(ctx.session)
    if atlas.top_region(community.id) is not None and atlas.top_region(community.id) == atlas.top_region(place_id):
        return True
    mortals = select(EntityRow.id).where(await folk_of(ctx.session, community), EntityRow.entity_type == EntityType.MORTAL)
    bound = await ctx.session.scalar(
        select(SpiritProfileRow.spirit_entity_id)
        .where(
            SpiritProfileRow.origin_mortal_id.in_(mortals),
            SpiritProfileRow.alignment == SpiritAlignment.GUARDIAN,
            SpiritProfileRow.binding == BindingKind.PLACE,
            SpiritProfileRow.bound_entity_id == place_id,
        )
        .limit(1)
    )
    return bound is not None
