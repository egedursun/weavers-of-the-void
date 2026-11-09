from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmography import PhenomenonFootprintRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.cosmos.kinds import PHENOMENON_MECHANICS
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.queries import canon

PREFIX = "cosmic."
MAGIC_KEY = "magic"
FERTILITY_KEY = "fertility"


@dataclass(frozen=True)
class Want:
    target: int
    key: str
    op: ModifierOp
    source: ModifierSource
    source_node: int | None
    reason: str


async def wanted(ctx: TickContext, cosmography: Cosmography) -> dict[Want, float]:
    rules = ctx.rules
    found: dict[Want, float] = {}
    regions = {region.id: region for region in await canon(ctx.session, [EntityType.REGION]) if not held(region.id)}
    for region in regions.values():
        placement = cosmography.place_world_id(region.world_id)
        pull = cosmography.pull(rules, placement)
        if pull.magic:
            found[Want(region.id, MAGIC_KEY, ModifierOp.ADD, ModifierSource.COSMOS, placement.dimension_id, f"{PREFIX}heavens")] = float(pull.magic)
        world = cosmography.worlds.get(region.world_id)
        if world is not None and world.biosphere_health < rules.world_life.biosphere_collapse:
            share = (PERCENT - rules.world_life.collapse_harvest_pct) / PERCENT
            found[Want(region.id, FERTILITY_KEY, ModifierOp.MULTIPLY, ModifierSource.COSMOS, world.id, f"{PREFIX}collapse")] = share
    statement = (
        select(PhenomenonFootprintRow, PhenomenonProfileRow)
        .join(PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id)
        .join(EntityRow, EntityRow.id == PhenomenonProfileRow.entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
    )
    for footprint, profile in await ctx.session.execute(statement):
        if footprint.region_entity_id not in regions:
            continue
        mechanics = PHENOMENON_MECHANICS[profile.kind]
        share = footprint.intensity / PERCENT
        magic, fertility = round(mechanics.magic(rules) * share), round(mechanics.fertility(rules) * share)
        source = profile.entity_id
        if magic:
            found[Want(footprint.region_entity_id, MAGIC_KEY, ModifierOp.ADD, ModifierSource.PHENOMENON, source, f"{PREFIX}phenomenon")] = float(magic)
        if fertility:
            found[Want(footprint.region_entity_id, FERTILITY_KEY, ModifierOp.ADD, ModifierSource.PHENOMENON, source, f"{PREFIX}phenomenon")] = float(fertility)
    for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES)))):
        if rift.region_entity_id in regions:
            magic = rift.size * rules.rifts.magic_pct // PERCENT
            if magic:
                found[Want(rift.region_entity_id, MAGIC_KEY, ModifierOp.ADD, ModifierSource.RIFT, rift.dimension_id, f"{PREFIX}rift.{rift.id}")] = float(magic)
    return found


async def cosmic_influence(ctx: TickContext) -> int:
    cosmography = await Cosmography.load(ctx.session)
    desired = await wanted(ctx, cosmography)
    existing = list(await ctx.session.scalars(select(ModifierRow).where(ModifierRow.reason_key.like(f"{PREFIX}%")).order_by(ModifierRow.id)))
    stale: list[int] = []
    kept: set[Want] = set()
    for row in existing:
        key = Want(row.target_node_id, row.target_key, row.op, row.source_kind, row.source_node_id, row.reason_key)
        if held(row.target_node_id) or row.held:
            kept.add(key)
            continue
        if key in desired and key not in kept:
            row.magnitude = desired[key]
            row.end_epoch = None
            kept.add(key)
        else:
            stale.append(row.id)
    if stale:
        await ctx.session.execute(delete(ModifierRow).where(ModifierRow.id.in_(stale)))
    made = 0
    for want, magnitude in desired.items():
        if want in kept:
            continue
        await add_modifier(
            ctx.session,
            ModifierDraft(
                target_node_id=want.target,
                target_key=want.key,
                op=want.op,
                magnitude=magnitude,
                source_kind=want.source,
                source_node_id=want.source_node,
                reason_key=want.reason,
                start_epoch=ctx.epoch,
                stacking_group=f"{want.reason}.{want.source_node}",
            ),
        )
        made += 1
    await ctx.session.flush()
    return made
