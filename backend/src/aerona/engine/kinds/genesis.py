from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.kinds import KindHoldingRow, KindRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.engine.kinds.acts import category_named, filled
from aerona.rules.registry import Rules

KIND_MAKERS = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.POLITY, EntityType.FACTION, EntityType.CULT})


@dataclass(frozen=True)
class KindSeed:
    concept: KindConcept
    category: str
    name: str
    description: str


async def holding_of(session: AsyncSession, concept: KindConcept, kind_id: int, holder_id: int) -> KindHoldingRow | None:
    return await session.scalar(
        select(KindHoldingRow).where(KindHoldingRow.concept == concept, KindHoldingRow.kind_id == kind_id, KindHoldingRow.holder_node_id == holder_id)
    )


async def found_kind(
    session: AsyncSession, rules: Rules, seed: KindSeed, *, holder_id: int, world_id: int | None, epoch: int, spread: KindSpread
) -> KindRow | None:
    spec = CONCEPTS.get(seed.concept)
    name = seed.name.strip()
    if spec is None or not name:
        return None
    category = category_named(spec, seed.category)
    if category is None:
        return None
    row = spec.table(name=name, category=category, world_id=world_id, origin_node_id=holder_id)
    row.description = seed.description.strip() or None
    filled(spec, row)
    row.created_epoch = epoch
    row.locked = []
    session.add(row)
    await session.flush()
    if await holding_of(session, seed.concept, row.id, holder_id) is None:
        session.add(
            KindHoldingRow(
                concept=seed.concept,
                kind_id=row.id,
                holder_node_id=holder_id,
                stance=KindStance.MAKES,
                strength=rules.kinds.founding_strength,
                spread=spread,
                since_epoch=epoch,
                locked=[],
            )
        )
        await session.flush()
    return row


async def found_kinds(
    session: AsyncSession, rules: Rules, seeds: Sequence[KindSeed], *, holder_id: int, world_id: int | None, epoch: int, spread: KindSpread
) -> list[KindRow]:
    made: list[KindRow] = []
    for seed in seeds[: rules.kinds.founded_per_people]:
        row = await found_kind(session, rules, seed, holder_id=holder_id, world_id=world_id, epoch=epoch, spread=spread)
        if row is not None:
            made.append(row)
    return made
