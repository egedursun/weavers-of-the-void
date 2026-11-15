from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.discovery import TheoryAdherentRow, TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.transform import TransformKind, TransformTrigger
from aerona.domain.models.entity_stats import KnowledgeStats, LegendStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.records import RecordSpec
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, end, make
from aerona.engine.transform.record import blocked, record_transformation

Push = tuple[int, TransformTrigger]
KNOWLEDGE_LEVEL = 1


async def orthodox_holders(ctx: TickContext, theory_id: int) -> list[int]:
    statement = select(TheoryAdherentRow.adherent_entity_id).where(TheoryAdherentRow.theory_entity_id == theory_id, TheoryAdherentRow.orthodox.is_(True))
    return list(await ctx.session.scalars(statement.order_by(TheoryAdherentRow.adherent_entity_id)))


async def theory_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    rows = await ctx.session.execute(
        select(TheoryAdherentRow.theory_entity_id, func.count()).where(TheoryAdherentRow.orthodox.is_(True)).group_by(TheoryAdherentRow.theory_entity_id)
    )
    counts = {theory_id: int(count) for theory_id, count in rows}
    found: dict[int, Push] = {}
    for profile in await ctx.session.scalars(select(TheoryProfileRow).where(TheoryProfileRow.correctness >= table.theory_correctness)):
        theory = await ctx.session.get(EntityRow, profile.theory_entity_id)
        if theory is not None and theory.status is EntityStatus.CANON and counts.get(profile.theory_entity_id, 0) >= table.theory_orthodox:
            found[theory.id] = (PERCENT, TransformTrigger.ENGINE)
    return found


async def theory_check(ctx: TickContext, theory_id: int) -> str | None:
    theory = await ctx.session.get(EntityRow, theory_id)
    if theory is None or theory.entity_type is not EntityType.THEORY or theory.status is not EntityStatus.CANON:
        return "Only a living account can settle into knowledge."
    return None


async def settle(ctx: TickContext, theory_id: int, ledger: Ledger) -> int:
    theory = await ctx.session.get_one(EntityRow, theory_id)
    profile = await ctx.session.get(TheoryProfileRow, theory.id)
    holders = await orthodox_holders(ctx, theory.id)
    knowledge = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.KNOWLEDGE,
            name=await NameRepository(ctx.session).unique_name(theory.name),
            body=profile.claim if profile is not None and profile.claim else f"What {theory.name} held, now known.",
            stats=KnowledgeStats(level=KNOWLEDGE_LEVEL, spread=clamp_percent(len(holders) * 10)),
            power=theory.power_level,
            world_id=theory.world_id,
            location_id=theory.location_id,
        ),
    )
    for holder in holders:
        await bind(ctx, ledger, (holder, knowledge.id, BondKind.KNOWS), f"settled out of {theory.name}")
    await bind(ctx, ledger, (knowledge.id, theory.id, BondKind.DESCENDS_FROM), f"settled out of the account {theory.name}")
    end(ctx, ledger, theory, EntityStatus.FULFILLED)
    return knowledge.id


async def remember_artwork(ctx: TickContext, artwork: EntityRow, profile: ArtworkProfileRow) -> EntityRow | None:
    if not (profile.canon or profile.quality >= ctx.rules.transform.remembered_quality) or await blocked(ctx, TransformKind.ARTWORK_REMEMBERED, artwork.id):
        return None
    ledger = Ledger()
    legend = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=await NameRepository(ctx.session).unique_name(f"The Lost {artwork.name}"),
            body=f"What is still told of the lost work {artwork.name}.",
            stats=LegendStats(),
            power=max(1, artwork.power_level // 2),
            world_id=artwork.world_id,
            location_id=artwork.location_id,
        ),
    )
    await bind(ctx, ledger, (legend.id, artwork.id, BondKind.TELLS_OF), f"tells of the lost work {artwork.name}")
    await record_transformation(ctx, TransformKind.ARTWORK_REMEMBERED, artwork.id, legend.id, ledger=ledger)
    return legend
