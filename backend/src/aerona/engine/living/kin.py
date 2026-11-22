from collections.abc import Callable, Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, SymbiontRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.living import HostPlacement, HostRelation
from aerona.domain.enums.mind import MemoryKind, SkillSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.mind.book import set_skill
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import connect, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation
from aerona.rules.registry.living import SymbiontRules

CLONE_POWER = 1
HOST_HEALTH: Mapping[HostRelation, Callable[[SymbiontRules], int]] = total(
    HostRelation,
    {
        HostRelation.MUTUAL: lambda table: table.mutual_gain,
        HostRelation.COMMENSAL: lambda _table: 0,
        HostRelation.PARASITIC: lambda table: -table.parasite_harm,
        HostRelation.CONTROLLING: lambda table: -table.parasite_harm,
    },
)
DEPTH = total(HostPlacement, {HostPlacement.SKIN: 1, HostPlacement.BLOOD: 2, HostPlacement.ORGAN: 3, HostPlacement.NERVE: 4, HostPlacement.MIND: 5})


async def bank_the_wild(ctx: TickContext, bank: GeneBankRow, atlas: RegionAtlas) -> GeneBankSampleRow | None:
    region_id = atlas.top_region(bank.structure_entity_id)
    if region_id is None:
        return None
    banked = select(GeneBankSampleRow.organism_node_id).where(GeneBankSampleRow.bank_entity_id == bank.structure_entity_id)
    ranged = select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.species_entity_id.not_in(banked))
    candidates = sorted(set(await ctx.session.scalars(ranged.distinct())))
    living = [
        species for species in [await living_entity(ctx.session, species_id) for species_id in candidates] if species is not None and not held(species.id)
    ]
    endangered = [species for species in living if await has_flag(ctx.session, species.id, EntityFlag.ENDANGERED)]
    chosen = next(iter(endangered or living), None)
    if chosen is None:
        return None
    row = await sampled(ctx, bank.structure_entity_id, chosen.id, ctx.rules.genome_design.bank_sample_quality)
    await record(
        ctx, "living.sample_banked", roles={IncidentRole.SUBJECT: chosen.id, IncidentRole.DESTINATION: bank.structure_entity_id}, facts={"quality": row.quality}
    )
    return row


async def keep_banks(ctx: TickContext) -> int:
    table = ctx.rules.genome_design
    atlas = await RegionAtlas.load(ctx.session)
    lost = 0
    for bank in list(await ctx.session.scalars(select(GeneBankRow).order_by(GeneBankRow.structure_entity_id))):
        if held(bank.structure_entity_id):
            continue
        holder = await ctx.session.get(EntityRow, bank.holder_node_id) if bank.holder_node_id is not None else None
        paid = holder is not None and holder.status is EntityStatus.CANON and await points_of(ctx.session, holder) >= bank.upkeep
        if paid and holder is not None and not held(holder.id):
            await shift_points(ctx.session, holder, -bank.upkeep)
            await bank_the_wild(ctx, bank, atlas)
        if "unpaid_epochs" not in bank.locked:
            bank.unpaid_epochs = 0 if paid else bank.unpaid_epochs + 1
        if bank.unpaid_epochs < table.bank_unpaid_limit:
            continue
        oldest = await ctx.session.scalar(
            select(GeneBankSampleRow).where(GeneBankSampleRow.bank_entity_id == bank.structure_entity_id).order_by(GeneBankSampleRow.taken_epoch).limit(1)
        )
        if oldest is not None and not oldest.locked:
            await ctx.session.delete(oldest)
            lost += 1
            await record(ctx, "living.sample_lost", roles={IncidentRole.SUBJECT: bank.structure_entity_id}, facts={"lost": lost})
    return lost


async def host_effects(ctx: TickContext, row: SymbiontRow, host: EntityRow) -> None:
    table = ctx.rules.symbionts
    shift_stat(host, "hp", HOST_HEALTH[row.relation](table), 0)
    if row.relation is HostRelation.CONTROLLING and row.mind_node_id is not None:
        await change_relation(ctx, host.id, row.mind_node_id, table.control_pull, MemoryKind.GOODWILL, note="steered by what lives within")
    if row.mind_node_id is not None:
        profile = await ctx.session.get(MortalProfileRow, host.id)
        if profile is not None and "stress" not in (profile.locked or []) and row.relation is not HostRelation.MUTUAL:
            profile.stress = clamp_percent(profile.stress + table.co_mind_stress)


async def spread(ctx: TickContext, row: SymbiontRow, host: EntityRow) -> int:
    if row.relation not in {HostRelation.PARASITIC, HostRelation.CONTROLLING} or host.location_id is None:
        return 0
    if not ctx.rng(f"symbiont.spread.{row.id}.{ctx.epoch}").chance(ctx.rules.symbionts.spread_chance):
        return 0
    hosted = select(SymbiontRow.host_node_id).where(SymbiontRow.line_id == row.line_id)
    other = await ctx.session.scalar(
        select(EntityRow)
        .where(await present_among(ctx.session, [host.location_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.id.not_in(hosted))
        .order_by(EntityRow.id)
        .limit(1)
    )
    if other is None or held(other.id):
        return 0
    ctx.session.add(
        SymbiontRow(
            host_node_id=other.id,
            line_id=row.line_id,
            placement=row.placement,
            relation=row.relation,
            strength=row.strength // 2,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    await record(
        ctx,
        "living.spread",
        roles={IncidentRole.ORIGIN: host.id, IncidentRole.DESTINATION: other.id},
        facts={"strength": row.strength // 2, "relation": row.relation},
    )
    return 1


async def keep_symbionts(ctx: TickContext) -> int:
    spread_to = 0
    for row in list(await ctx.session.scalars(select(SymbiontRow).order_by(SymbiontRow.id))):
        host = await ctx.session.get(EntityRow, row.host_node_id)
        if host is None or host.status is not EntityStatus.CANON or held(host.id) or row.locked:
            continue
        await host_effects(ctx, row, host)
        spread_to += await spread(ctx, row, host)
    return spread_to


async def remove_symbiont(ctx: TickContext, row: SymbiontRow) -> None:
    host = await ctx.session.get(EntityRow, row.host_node_id)
    if host is not None and not held(host.id):
        shift_stat(host, "hp", -ctx.rules.symbionts.removal_harm * DEPTH[row.placement], 0)
        await lose_partner(ctx, host)
    await ctx.session.delete(row)


async def lose_partner(ctx: TickContext, host: EntityRow) -> None:
    if host.entity_type is not EntityType.PEOPLE or held(host.id):
        return
    loss = ctx.rules.symbionts.partner_loss
    shift_stat(host, "prosperity", -loss, 0)
    shift_stat(host, "craft", -loss, 0)
    await record(ctx, "living.partner_lost", roles={IncidentRole.SUBJECT: host.id}, facts={"loss": loss})


async def generation_of(ctx: TickContext, source_id: int) -> int:
    depth = 0
    current = source_id
    while depth < PERCENT:
        parent = await ctx.session.scalar(
            select(BondRow.target_node_id)
            .where(BondRow.source_node_id == current, BondRow.kind == BondKind.CLONE_OF, BondRow.state == BondState.ACTIVE)
            .limit(1)
        )
        if parent is None:
            return depth
        depth += 1
        current = parent
    return depth


async def clone(ctx: TickContext, source_id: int, maker_id: int | None, *, forced: bool = False) -> EntityRow:
    source = await ctx.session.get(EntityRow, source_id)
    if source is None or source.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a living being with a body can be cloned.")
    if not forced and source.location_id is not None and str(await law_param(ctx.session, source.location_id, LawKind.CLONE_LAW, "level")) == "banned":
        raise ValidationFailedError("Cloning is banned here.")
    table = ctx.rules.clones
    generation = await generation_of(ctx, source.id) + 1
    span = stat_or(source, "lifespan", 70) * clamp_int(table.health_pct - table.generation_loss * (generation - 1), 1, PERCENT) // PERCENT
    copy = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.MORTAL,
            name=f"{source.name}, born again of the same body",
            body=f"A clone of {source.name}, grown in epoch {ctx.epoch}.",
            stats=MortalStats(hp=stat_or(source, "hp", 40), age=0, lifespan=max(1, span)),
            power=CLONE_POWER,
            world_id=source.world_id,
            location_id=source.location_id,
        ),
    )
    genome = await ctx.session.get(GenomeRow, source.id)
    if genome is not None:
        ctx.session.add(GenomeRow(holder_node_id=copy.id, genes=dict(genome.genes), potential=dict(genome.potential), beauty=genome.beauty, epoch=ctx.epoch))
    for skill in list(await ctx.session.scalars(select(SkillRow).where(SkillRow.holder_node_id == source.id, SkillRow.subject_node_id.is_(None)))):
        born = skill.level * table.born_skill_pct // PERCENT
        if born > 0:
            await set_skill(ctx.session, copy.id, skill.skill, born, epoch=ctx.epoch, source=SkillSource.BIRTH)
    await connect(ctx.session, copy.id, source.id, BondKind.CLONE_OF, ctx.epoch, description="grown from this body")
    if maker_id is not None:
        await connect(ctx.session, maker_id, copy.id, BondKind.PRODUCED, ctx.epoch, description="grew this clone")
    await record(
        ctx,
        "living.cloned",
        roles={IncidentRole.ORIGIN: source.id, IncidentRole.PRODUCT: copy.id, IncidentRole.MAKER: maker_id},
        facts={"generation": await generation_of(ctx, source.id)},
    )
    return copy


async def sampled(ctx: TickContext, bank_id: int, organism_id: int, quality: int) -> GeneBankSampleRow:
    if await ctx.session.get(GeneBankRow, bank_id) is None:
        raise ValidationFailedError("No such bank of life.")
    found = await ctx.session.scalar(
        select(GeneBankSampleRow).where(GeneBankSampleRow.bank_entity_id == bank_id, GeneBankSampleRow.organism_node_id == organism_id)
    )
    if found is not None:
        if "quality" not in found.locked and quality > found.quality:
            found.quality, found.taken_epoch = clamp_percent(quality), ctx.epoch
        return found
    row = GeneBankSampleRow(bank_entity_id=bank_id, organism_node_id=organism_id, quality=clamp_percent(quality), taken_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def line_of(ctx: TickContext, line_id: int) -> LivingLineRow:
    row = await ctx.session.get(LivingLineRow, line_id)
    if row is None:
        raise ValidationFailedError("No such living line.")
    return row
