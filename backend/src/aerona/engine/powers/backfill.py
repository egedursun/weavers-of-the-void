from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.arcana import SCHOOL_GRAMMAR
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.concealment import HiddenTruthRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.powers import (
    MagicSystemRow,
    MagicSystemSourceRow,
    PowerRow,
    PowerSourceCostRow,
    PowerSourceHazardRow,
    PowerSourceResistanceRow,
    PowerSourceRow,
    SourceDensityRow,
)
from aerona.db.write_guard import held
from aerona.domain.enums.concealment import ConcealScope, HiddenTruthKind, KeeperRole, SeekerAim
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.powers import (
    PowerCost,
    PowerHazard,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerVisibility,
    ResistanceKind,
    SourceAccess,
    SourceLocus,
    SourceRenewal,
)
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import aptitudes
from aerona.engine.industry.energy import leys_by_region
from aerona.engine.primitives.numbers import clamp_percent

LEGACY_FIXUP = "powers.legacy_backfill"
LEY_STEP = 15
SEEKER_ROLES = frozenset({MortalRole.JOURNALIST, MortalRole.SAGE, MortalRole.SPY})


@dataclass(frozen=True)
class BuiltIn:
    name: str
    locus: SourceLocus
    renewal: SourceRenewal
    access: SourceAccess
    costs: tuple[PowerCost, ...]
    resisted_by: tuple[ResistanceKind, ...]
    hazards: tuple[PowerHazard, ...]
    visibility: PowerVisibility


BUILT_IN = total(
    MagicSource,
    {
        MagicSource.LEY: BuiltIn(
            "Ley",
            SourceLocus.PLACE,
            SourceRenewal.TIME,
            SourceAccess.TRAINED,
            (PowerCost.FATIGUE,),
            (ResistanceKind.WILL,),
            (PowerHazard.DEPLETION,),
            PowerVisibility.SUBTLE,
        ),
        MagicSource.DIVINE: BuiltIn(
            "Divine",
            SourceLocus.PATRON,
            SourceRenewal.WORSHIP,
            SourceAccess.GRANTED,
            (PowerCost.ESSENCE,),
            (ResistanceKind.FAITH,),
            (PowerHazard.ATTENTION,),
            PowerVisibility.OVERT,
        ),
        MagicSource.BLOOD: BuiltIn(
            "Blood",
            SourceLocus.SELF,
            SourceRenewal.REST,
            SourceAccess.ANYONE,
            (PowerCost.HP,),
            (ResistanceKind.SANCTITY,),
            (PowerHazard.INJURY,),
            PowerVisibility.OVERT,
        ),
        MagicSource.SOUL: BuiltIn(
            "Soul",
            SourceLocus.OTHERS,
            SourceRenewal.TAKING,
            SourceAccess.TRAINED,
            (PowerCost.SOUL,),
            (ResistanceKind.FAITH,),
            (PowerHazard.ESCAPE,),
            PowerVisibility.SUBTLE,
        ),
        MagicSource.REAGENT: BuiltIn(
            "Reagent",
            SourceLocus.SUBSTANCE,
            SourceRenewal.TIME,
            SourceAccess.TRAINED,
            (PowerCost.REAGENT,),
            (ResistanceKind.MATERIAL,),
            (PowerHazard.DEPENDENCY,),
            PowerVisibility.SUBTLE,
        ),
        MagicSource.VOID: BuiltIn(
            "Void",
            SourceLocus.VOID,
            SourceRenewal.NONE,
            SourceAccess.ANYONE,
            (PowerCost.SANITY,),
            (ResistanceKind.WILL,),
            (PowerHazard.LEAK,),
            PowerVisibility.HIDDEN,
        ),
    },
)


async def built_in_source(session: AsyncSession, source: MagicSource) -> PowerSourceRow:
    found = await session.scalar(select(PowerSourceRow).where(PowerSourceRow.built_in == source).limit(1))
    if found is not None:
        return found
    spec = BUILT_IN[source]
    row = PowerSourceRow(
        name=spec.name,
        description="",
        scope_node_id=None,
        drawn_from=spec.locus,
        renewal=spec.renewal,
        access=spec.access,
        visibility=spec.visibility,
        stability=60,
        built_in=source,
        founded_epoch=0,
        locked=[],
    )
    session.add(row)
    await session.flush()
    for cost in spec.costs:
        session.add(PowerSourceCostRow(source_id=row.id, cost=cost, weight=PERCENT // 2, locked=[]))
    for resistance in spec.resisted_by:
        session.add(PowerSourceResistanceRow(source_id=row.id, resistance=resistance, material=None, locked=[]))
    for hazard in spec.hazards:
        session.add(PowerSourceHazardRow(source_id=row.id, hazard=hazard, weight=10, locked=[]))
    await session.flush()
    return row


async def sources(ctx: TickContext) -> int:
    made = 0
    for source in MagicSource:
        await built_in_source(ctx.session, source)
        made += 1
    return made


async def ley_density(ctx: TickContext) -> int:
    ley = await built_in_source(ctx.session, MagicSource.LEY)
    made = 0
    for region, lines in sorted((await leys_by_region(ctx)).items()):
        if held(region):
            continue
        base = clamp_percent(ctx.rules.power_sources.start_density // 2 + lines * LEY_STEP)
        ctx.session.add(SourceDensityRow(region_entity_id=region, source_id=ley.id, density=base, base_density=base, renewal_pct=10, depleted=False, locked=[]))
        made += 1
    return made


async def world_magic(ctx: TickContext, world_id: int) -> int:
    mean = await ctx.session.scalar(
        select(func.avg(func.json_extract(EntityRow.stats, "$.magic"))).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION)
    )
    return clamp_percent(round(mean)) if mean is not None else PERCENT // 2


async def systems(ctx: TickContext) -> int:
    made = 0
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if held(world.id) or await ctx.session.scalar(select(MagicSystemRow.id).where(MagicSystemRow.scope_node_id == world.id)) is not None:
            continue
        rites = await ctx.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.RITE, EntityRow.status == EntityStatus.CANON)
            .limit(1)
        )
        system = MagicSystemRow(
            name=f"the ways of power of {world.name}",
            description="",
            scope_node_id=world.id,
            structure=PowerStructure.RITE if rites is not None else PowerStructure.MIXED,
            predictability=PERCENT // 2,
            prevalence=await world_magic(ctx, world.id),
            cost_severity=PERCENT // 2,
            visibility=PowerVisibility.SUBTLE,
            founded_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(system)
        await ctx.session.flush()
        for source in MagicSource:
            row = await built_in_source(ctx.session, source)
            ctx.session.add(MagicSystemSourceRow(system_id=system.id, source_id=row.id, locked=[]))
        made += 1
    return made


async def gifted(ctx: TickContext) -> int:
    made = 0
    at = ctx.rules.powers.gifted_latent_at
    genomes = await ctx.session.execute(
        select(GenomeRow, EntityRow)
        .join(EntityRow, EntityRow.id == GenomeRow.holder_node_id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    powered = set(await ctx.session.scalars(select(PowerRow.holder_node_id)))
    for genome, mortal in genomes.all():
        if mortal.id in powered or held(mortal.id):
            continue
        found = aptitudes(ctx.rules, genome.genes)
        best = max(found.items(), key=lambda item: (item[1], item[0].value), default=None)
        if best is None or best[1] < at:
            continue
        technique, form = SCHOOL_GRAMMAR[best[0]]
        ctx.session.add(
            PowerRow(
                holder_node_id=mortal.id,
                technique=technique,
                form=form,
                strength=max(1, best[1] // 20),
                control=0,
                origin=PowerOrigin.BORN,
                state=PowerState.LATENT,
                visibility=PowerVisibility.SUBTLE,
                strain=0,
                strain_cap=30,
                uses=0,
                gained_epoch=ctx.epoch,
                locked=[],
            )
        )
        made += 1
    return made


async def buried_histories(ctx: TickContext) -> int:
    made = 0
    for secret in list(await ctx.session.scalars(select(SecretRow).where(SecretRow.kind == IntrigueSecret.TRUE_HISTORY).order_by(SecretRow.id))):
        subject = secret.about_node_id or secret.holder_node_id
        if held(subject):
            continue
        truth = HiddenTruthRow(
            title="what truly happened",
            description="",
            subject_node_id=subject,
            kind=HiddenTruthKind.EVENT,
            hidden_from=ConcealScope.EVERYONE,
            strength=secret.severity,
            by_neglect=True,
            founded_epoch=ctx.epoch,
            tended_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(truth)
        await ctx.session.flush()
        ctx.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=secret.holder_node_id, role=KeeperRole.MEMBER, locked=[]))
        for knower in sorted(set(secret.known_by) - {secret.holder_node_id}):
            found = await ctx.session.get(EntityRow, knower)
            if found is not None and found.mortal_role in SEEKER_ROLES:
                ctx.session.add(TruthSeekerRow(truth_id=truth.id, seeker_node_id=knower, aim=SeekerAim.EXPOSE, progress=0, began_epoch=ctx.epoch, locked=[]))
        made += 1
    return made


async def legacy_backfill(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return 0
    result = {
        "sources": await sources(ctx),
        "ley_density": await ley_density(ctx),
        "systems": await systems(ctx),
        "gifted": await gifted(ctx),
        "buried_histories": await buried_histories(ctx),
    }
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
