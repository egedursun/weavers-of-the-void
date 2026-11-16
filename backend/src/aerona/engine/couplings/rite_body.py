from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.couplings import (
    BIOLOGY_COMPONENTS,
    BODILESS_VARIANTS,
    COLLECTIVE_COMPONENTS,
    COMPONENT_FUNCTIONS,
    ENSOULED_COMPONENTS,
    RESTRAINT_BLOCKS,
    SCHOOL_COMPONENTS,
    SLOW_VARIANTS,
    VOICE_REPLACED,
)
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.couplings import CaptiveRestraintRow, RiteComponentRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.couplings import RestraintKind, RiteComponent
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.book import function_unhindered
from aerona.engine.body.variants import folk_biology
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note


@dataclass(frozen=True)
class Bar:
    reason: str | None
    factor: float


async def components_of(ctx: TickContext, rite_id: int) -> set[RiteComponent]:
    rows = await ctx.session.scalars(select(RiteComponentRow.component).where(RiteComponentRow.rite_entity_id == rite_id))
    found = set(rows)
    if found:
        return found
    profile = await ctx.session.get(RiteProfileRow, rite_id)
    if profile is None:
        return set()
    for component in SCHOOL_COMPONENTS[profile.school]:
        ctx.session.add(RiteComponentRow(rite_entity_id=rite_id, component=component))
    await ctx.session.flush()
    return set(SCHOOL_COMPONENTS[profile.school])


async def held_captive(ctx: TickContext, entity_id: int) -> CaptiveRow | None:
    return await ctx.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == entity_id, CaptiveRow.status == CaptiveStatus.HELD).limit(1))


async def restraints_of(ctx: TickContext, entity_id: int) -> set[RestraintKind]:
    captive = await held_captive(ctx, entity_id)
    if captive is None:
        return set()
    return set(await ctx.session.scalars(select(CaptiveRestraintRow.restraint).where(CaptiveRestraintRow.captive_id == captive.id)))


async def component_bar(ctx: TickContext, caster: EntityRow, rite_id: int) -> Bar:
    needed = await components_of(ctx, rite_id)
    blocked = {component for restraint in await restraints_of(ctx, caster.id) for component in RESTRAINT_BLOCKS[restraint]}
    stopped = sorted(needed & blocked)
    if stopped:
        return Bar(f"the caster is held so that the rite cannot be {stopped[0].value}", 0.0)
    if caster.entity_type is not EntityType.MORTAL:
        return Bar(None, 1.0)
    nature = await folk_biology(ctx.session, caster)
    allowed = await allowed_components(ctx, caster, nature.variants)
    denied = sorted(needed - allowed)
    if denied:
        return Bar(f"a body of its nature cannot give the rite its {denied[0].value} part", 0.0)
    least = PERCENT
    replaced = {component for variant in nature.variants for component in VOICE_REPLACED.get(variant, frozenset())}
    bodiless = any(variant in BODILESS_VARIANTS for variant in nature.variants)
    for component in sorted(needed - replaced if not bodiless else set()):
        for function in COMPONENT_FUNCTIONS[component]:
            level = await function_unhindered(ctx.session, ctx.rules, caster.id, function)
            if level < ctx.rules.couplings.component_block_pct:
                return Bar(f"the caster's body cannot give the rite its {component.value} part", 0.0)
            least = min(least, level)
    return Bar(None, least / PERCENT * biology_factor(ctx, needed, nature.variants))


async def allowed_components(ctx: TickContext, caster: EntityRow, variants: tuple[BiologyVariant, ...]) -> set[RiteComponent]:
    allowed = set(RiteComponent)
    for variant in variants:
        if variant in BIOLOGY_COMPONENTS:
            allowed &= BIOLOGY_COMPONENTS[variant]
    if BiologyVariant.CONSTRUCT in variants and await ctx.session.scalar(select(ConstructRow.soul_entity_id).where(ConstructRow.entity_id == caster.id)):
        allowed |= ENSOULED_COMPONENTS
    return allowed


def biology_factor(ctx: TickContext, needed: set[RiteComponent], variants: tuple[BiologyVariant, ...]) -> float:
    table = ctx.rules.couplings
    factor = 1.0
    for variant in variants:
        if variant in SLOW_VARIANTS:
            factor *= table.slow_casting_pct / PERCENT
        if needed & COLLECTIVE_COMPONENTS.get(variant, frozenset()):
            factor *= table.hive_casting_pct / PERCENT
    return factor


async def casters_held(ctx: TickContext) -> list[tuple[CaptiveRow, EntityRow]]:
    rites = select(RiteProfileRow.rite_entity_id)
    owners = select(BondRow.source_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(rites))
    statement = (
        select(CaptiveRow, EntityRow)
        .join(EntityRow, EntityRow.id == CaptiveRow.captive_entity_id)
        .where(CaptiveRow.status == CaptiveStatus.HELD, EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(owners))
        .order_by(CaptiveRow.id)
    )
    return [(captive, entity) for captive, entity in await ctx.session.execute(statement)]


async def owned_rites(ctx: TickContext, entity_id: int) -> list[int]:
    rites = select(RiteProfileRow.rite_entity_id)
    statement = select(BondRow.target_node_id).where(
        BondRow.source_node_id == entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(rites)
    )
    return list(await ctx.session.scalars(statement))


@reads("table.bonds", "table.captive_restraints", "table.captives", "table.rite_components", "table.rite_profiles")
@writes("table.captive_restraints", "table.rite_components")
async def restrain_casters(ctx: TickContext) -> None:
    for captive, entity in await casters_held(ctx):
        if held(entity.id, captive.captor_entity_id):
            continue
        needed = set().union(*[await components_of(ctx, rite) for rite in await owned_rites(ctx, entity.id)])
        known = await restraints_of(ctx, entity.id)
        added: list[RestraintKind] = []
        for restraint, blocks in sorted(RESTRAINT_BLOCKS.items()):
            if restraint not in known and blocks & needed:
                ctx.session.add(CaptiveRestraintRow(captive_id=captive.id, restraint=restraint))
                added.append(restraint)
        if added:
            ctx.count("casters_restrained")
            captor = await ctx.session.get(EntityRow, captive.captor_entity_id)
            await note(
                ctx,
                f"{captor.name if captor else 'Its captors'} held {entity.name} so that no rite could be worked.",
                key="rite.restrained",
                ids=[entity.id, captive.captor_entity_id],
            )
    await ctx.session.flush()
