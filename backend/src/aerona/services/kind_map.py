import math
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.domain.enums.economy import MoneyForm
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat

MAPPED_CONCEPTS = (KindConcept.CUISINE, KindConcept.GARMENT, KindConcept.ORGANISATION)
SHOWN_STANCES = frozenset({KindStance.MAKES, KindStance.USES, KindStance.FAVOURS})
POPULATED = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION)


@dataclass(frozen=True)
class KindShare:
    concept: KindConcept
    kind_id: int
    name: str
    share: int


async def communities(session: AsyncSession, world_id: int) -> list[EntityRow]:
    return list(
        await session.scalars(
            select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(POPULATED))
        )
    )


def weight_of(community: EntityRow) -> float:
    return math.log10((stat(community, "population") or 0) + 1) + 1


async def region_kinds(session: AsyncSession, world_id: int) -> dict[int, list[KindShare]]:
    atlas = await RegionAtlas.load(session)
    rows = await communities(session, world_id)
    regions = {row.id: atlas.top_region(row.id) for row in rows}
    weights = {row.id: weight_of(row) for row in rows}
    holdings = list(
        await session.scalars(
            select(KindHoldingRow).where(
                KindHoldingRow.holder_node_id.in_(list(regions)),
                KindHoldingRow.concept.in_([concept for concept in MAPPED_CONCEPTS if concept in CONCEPTS]),
                KindHoldingRow.stance.in_(list(SHOWN_STANCES)),
            )
        )
    )
    tally: dict[tuple[int, KindConcept], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for holding in holdings:
        region = regions.get(holding.holder_node_id)
        if region is not None:
            tally[region, holding.concept][holding.kind_id] += holding.strength * weights[holding.holder_node_id]
    names: dict[tuple[KindConcept, int], str] = {}
    for concept in {concept for _, concept in tally}:
        spec = CONCEPTS[concept]
        ids = sorted({kind_id for (_, held), weights_of in tally.items() if held is concept for kind_id in weights_of})
        names |= {(concept, row.id): row.name for row in await session.scalars(select(spec.table).where(spec.table.id.in_(ids)))}
    found: dict[int, list[KindShare]] = defaultdict(list)
    for (region, concept), weights_of in sorted(tally.items(), key=lambda item: (item[0][0], item[0][1].value)):
        total = sum(weights_of.values())
        kind_id, best = max(weights_of.items(), key=lambda item: (item[1], -item[0]))
        name = names.get((concept, kind_id))
        if name is not None and total > 0:
            found[region].append(KindShare(concept, kind_id, name, round(best * 100 / total)))
    return dict(found)


async def region_money(session: AsyncSession, world_id: int) -> dict[int, MoneyForm]:
    atlas = await RegionAtlas.load(session)
    rows = {row.id: row for row in await communities(session, world_id)}
    tally: dict[int, dict[MoneyForm, float]] = defaultdict(lambda: defaultdict(float))
    for currency in await session.scalars(select(CurrencyRow).where(CurrencyRow.issuer_entity_id.in_(list(rows)))):
        region = atlas.top_region(currency.issuer_entity_id)
        if region is not None:
            tally[region][currency.form] += weight_of(rows[currency.issuer_entity_id])
    return {region: max(forms.items(), key=lambda item: (item[1], item[0].value))[0] for region, forms in tally.items()}
