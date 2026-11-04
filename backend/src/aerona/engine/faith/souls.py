from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, PossessionRow, ReincarnationRow, SpiritProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.domain import DEATH_DOMAINS
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import AfterlifeState, JudgementDoctrine, ReincarnationGate, SpiritAlignment, StratumKind, TenetKind
from aerona.domain.enums.mind import TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.domain.enums.society import CreatureTrait, NaturalLaw
from aerona.engine.body.conditions import end_condition, gain_condition
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of as creature_traits
from aerona.engine.faith.book import Church, faith_tenets
from aerona.engine.faith.judgement import ledger_score
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.mind.book import add_trait, stored_values, values_for, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.phases.births import BirthPlan, born_mortal
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats, stat

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


async def tend(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> str:
    table = ctx.rules.spirits
    home = await home_of(ctx, profile)
    fed = home is not None and await venerates(ctx, home) and ctx.rng(f"offering.{spirit.id}.{ctx.epoch}").chance(table.offering_chance)
    if fed:
        profile.veneration = clamp_int(profile.veneration + table.remembrance, 0, PERCENT)
        profile.memory_strength = clamp_int(profile.memory_strength + table.remembrance, 0, PERCENT)
    else:
        profile.memory_strength = clamp_int(profile.memory_strength - table.memory_decay, 0, PERCENT)
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
    return None


async def rebirth(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow, home: EntityRow, gate: ReincarnationGate) -> EntityRow:
    table = ctx.rules.afterlife
    old = await ctx.session.get(EntityRow, profile.origin_mortal_id) if profile.origin_mortal_id is not None else None
    name = old.name if old is not None else spirit.name
    plan = BirthPlan(name=name, subtype="reborn", role=MortalRole.COMMONER, body=f"Born again with the soul of {name}.")
    child = await born_mortal(ctx, home, plan)
    set_stats(child, age=0)
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
            community_entity_id=home.id,
            gate=gate,
            memory_pct=table.reincarnation_memory_pct,
            epoch=ctx.epoch,
        )
    )
    profile.state = AfterlifeState.REBORN
    await retire_in(ctx, spirit, f"born again as {child.name}", close_bonds=False)
    return child


async def reincarnate(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> EntityRow | None:
    table = ctx.rules.afterlife
    home = await home_of(ctx, profile)
    gate = await gates(ctx, profile, home)
    if gate is None or home is None or ledger_score(profile.deeds) < table.reincarnation_min_score:
        return None
    if not ctx.rng(f"rebirth.{spirit.id}.{ctx.epoch}").chance(table.reincarnation_chance_pct):
        return None
    return await rebirth(ctx, profile, spirit, home, gate)


async def possess(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> EntityRow | None:
    if profile.alignment is not SpiritAlignment.VENGEFUL or spirit.location_id is None:
        return None
    if not ctx.rng(f"possess.{spirit.id}.{ctx.epoch}").chance(ctx.rules.necromancy.possession_chance):
        return None
    taken = select(PossessionRow.host_entity_id)
    host = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == spirit.location_id,
            EntityRow.id.not_in(taken),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if host is None:
        return None
    ctx.session.add(PossessionRow(host_entity_id=host.id, spirit_entity_id=spirit.id, since_epoch=ctx.epoch, stress=0))
    await gain_condition(ctx, host, ConditionKind.POSSESSION, HarmCause.CURSE, source_node_id=spirit.id)
    return host


async def possessions(ctx: TickContext) -> tuple[int, int]:
    table = ctx.rules.necromancy
    exorcised = held = 0
    for row in list(await ctx.session.scalars(select(PossessionRow).order_by(PossessionRow.host_entity_id))):
        host = await living_entity(ctx.session, row.host_entity_id)
        spirit = await living_entity(ctx.session, row.spirit_entity_id)
        if host is None or spirit is None:
            await ctx.session.delete(row)
            continue
        row.stress = clamp_int(row.stress + table.possession_stress, 0, PERCENT)
        priests = await ctx.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.location_id == host.location_id, EntityRow.mortal_role == MortalRole.PRIEST, EntityRow.status == EntityStatus.CANON)
            .limit(1)
        )
        if priests is not None and ctx.rng(f"exorcism.{host.id}.{ctx.epoch}").chance(table.exorcism_chance):
            await ctx.session.delete(row)
            await end_condition(ctx, host, ConditionKind.POSSESSION)
            exorcised += 1
            continue
        held += 1
    return held, exorcised


async def soul_eaters(ctx: TickContext, atlas: RegionAtlas) -> set[int]:
    eaters = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_([EntityType.SPECIES, EntityType.OUTER_BEING]), EntityRow.status == EntityStatus.CANON)
    )
    regions: set[int] = set()
    for eater in eaters:
        if eater.entity_type is EntityType.OUTER_BEING or CreatureTrait.SOUL_EATER in await creature_traits(ctx.session, eater.id):
            region = atlas.top_region(eater.id)
            if region is not None:
                regions.add(region)
    return regions


async def consume(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> None:
    profile.state = AfterlifeState.CONSUMED
    await retire_in(ctx, spirit, "devoured by a soul-eater", close_bonds=True)
    sons = await ctx.session.scalars(select(SonRow).where(SonRow.current_world_id == spirit.world_id).order_by(SonRow.id))
    for son in sons:
        if son.alive and {son.domain_primary, son.domain_secondary} & DEATH_DOMAINS:
            before = son.essence
            son.essence += ctx.rules.necromancy.consumption_essence
            cap_gained_essence(ctx.rules, son, before)


async def fear_of_torment(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None or doctrine.judgement is not JudgementDoctrine.DEEDS:
        return 0
    torment = await ctx.session.scalar(
        select(AfterlifeStratumRow.id).where(AfterlifeStratumRow.kind == StratumKind.TORMENT, AfterlifeStratumRow.population > 0).limit(1)
    )
    if torment is None:
        return 0
    step = ctx.rules.afterlife.torment_honour
    for member in church.members:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, member.id)
        if not values:
            continue
        for axis in (ValueAxis.HONOUR, ValueAxis.TRADITION):
            values[axis] = values.get(axis, 0) + step
        await write_values(ctx.session, ValueHolder.CULTURE, member.id, values)
    return len(church.members)


async def guardians_of(ctx: TickContext, community_id: int) -> int:
    mortals = select(EntityRow.id).where(EntityRow.location_id == community_id, EntityRow.entity_type == EntityType.MORTAL)
    rows = await ctx.session.scalars(
        select(SpiritProfileRow.spirit_entity_id).where(SpiritProfileRow.origin_mortal_id.in_(mortals), SpiritProfileRow.alignment == SpiritAlignment.GUARDIAN)
    )
    return len(list(rows))


async def doctrine_of(ctx: TickContext, cult_id: int) -> CultDoctrineRow | None:
    return await ctx.session.get(CultDoctrineRow, cult_id)
