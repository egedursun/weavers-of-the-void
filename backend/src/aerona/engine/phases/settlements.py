from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import aliased

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, canon, connect, has_flag, living_entity, remove_flag
from aerona.engine.primitives.records import append_sentence, sentence_case
from aerona.engine.primitives.stats import set_stats, stat

DEFAULT_RESETTLED_SUBTYPE = "village"


async def ruins_in(ctx: TickContext, region: EntityRow) -> list[EntityRow]:
    parent = aliased(EntityRow)
    ruin_ids = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.RUIN)
    void_ids = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.VOID)
    statement = (
        select(EntityRow)
        .outerjoin(parent, parent.id == EntityRow.location_id)
        .where(
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.DEAD,
            EntityRow.world_id == region.world_id,
            EntityRow.id.in_(ruin_ids),
            EntityRow.id.not_in(void_ids),
            (EntityRow.location_id == region.id) | (parent.location_id == region.id),
        )
        .order_by(EntityRow.end_epoch.desc(), EntityRow.id)
    )
    return list(await ctx.session.scalars(statement))


async def resettle_ruin(
    ctx: TickContext, region: EntityRow, source: EntityRow | None, population: float, reason: str, *, atlas: RegionAtlas | None = None
) -> EntityRow | None:
    ruins = await ruins_in(ctx, region)
    if not ruins:
        return None
    return await restore_ruin(ctx, ruins[0], source, population, reason, atlas=atlas)


async def restore_ruin(
    ctx: TickContext, ruin: EntityRow, source: EntityRow | None, population: float, reason: str, *, atlas: RegionAtlas | None = None
) -> EntityRow:
    life = ctx.rules.deep_life
    await EntityRepository(ctx.session).set_status(ruin, EntityStatus.CANON, ctx.epoch)
    ruin.end_epoch = None
    ruin.subtype = ruin.subtype or DEFAULT_RESETTLED_SUBTYPE
    defense = stat(ruin, "defense")
    set_stats(
        ruin,
        population=max(life.ruin_resettle_min_population, round_half_up(population)),
        prosperity=life.ruin_resettle_prosperity,
        defense=max(life.ruin_resettle_min_defense, round_half_up((defense if defense is not None else life.ruin_default_defense) / life.ruin_defense_divisor)),
    )
    ruin.fate_note = append_sentence(ruin.fate_note, f"Epoch {ctx.epoch}: {reason} rebuilt the ruin.")
    await remove_flag(ctx.session, ruin.id, EntityFlag.RUIN)
    await add_flag(ctx.session, ruin.id, EntityFlag.REBUILT, ctx.epoch)
    if source is not None:
        await connect(ctx.session, ruin.id, source.id, BondKind.DESCENDS_FROM, ctx.epoch, description="those who rebuilt the ruin")
    await bind_language_and_faith(ctx, ruin, atlas, source)
    ctx.count("ruins_resettled")
    return ruin


@reads("law.justice", "settlement.defense", "settlement.prosperity", "table.entities", "table.nodes")
@writes("settlement.defense", "table.entities")
async def settlement_laws(ctx: TickContext) -> None:
    effects = ctx.rules.world_effects
    justice: dict[int, list[int]] = defaultdict(list)
    for law in await canon(ctx.session, [EntityType.LAW]):
        if law.location_id is not None:
            value = stat(law, "justice")
            justice[law.location_id].append(value if value is not None else effects.unknown_justice)
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        values = justice.get(settlement.id)
        if not values:
            continue
        average = sum(values) / len(values)
        defense = stat(settlement, "defense")
        prosperity = stat(settlement, "prosperity")
        gain = effects.law_just_defense_gain if average >= effects.law_just_avg_threshold else 0
        loss = effects.law_unjust_prosperity_loss if average < effects.law_unjust_avg_threshold else 0
        set_stats(
            settlement,
            defense=clamp_int((defense if defense is not None else effects.unknown_stat) + gain, 0, PERCENT),
            prosperity=clamp_int((prosperity if prosperity is not None else effects.unknown_prosperity) - loss, 0, PERCENT) if loss else prosperity,
        )


@reads("settlement.defense", "table.bonds", "table.entities", "table.holder_levels", "table.nodes")
@writes("settlement.defense", "table.entities")
async def architecture(ctx: TickContext) -> None:
    effects = ctx.rules.world_effects
    knowledge = await KnowledgeMap.load(ctx.session)
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if knowledge.knows(settlement.id, KnowledgeBranch.ARCHITECTURE):
            defense = stat(settlement, "defense")
            set_stats(settlement, defense=clamp_int((defense if defense is not None else effects.unknown_stat) + effects.architecture_defense_gain, 0, PERCENT))


async def order_resettlement(ctx: TickContext, ruin_id: int, source_id: int | None, population: int) -> EntityRow:
    ruin = await ctx.session.get(EntityRow, ruin_id)
    if ruin is None or ruin.status is not EntityStatus.DEAD or not await has_flag(ctx.session, ruin_id, EntityFlag.RUIN):
        raise NotFoundError("No such ruin.")
    if population <= 0:
        raise ValidationFailedError("Settlers must number at least one.")
    source = await living_entity(ctx.session, source_id)
    reason = f"settlers from {source.name}" if source is not None else "settlers sent by the gods"
    await restore_ruin(ctx, ruin, source, population, reason)
    await note(ctx, f"{sentence_case(reason)} rebuilt the ruin of {ruin.name}.", key="settlements.resettled", ids=[ruin.id] + ([source.id] if source else []))
    return ruin


LAW_PHASES = (Phase("settlement_laws", settlement_laws),)
ARCHITECTURE_PHASES = (Phase("architecture", architecture),)
PHASES = LAW_PHASES + ARCHITECTURE_PHASES
