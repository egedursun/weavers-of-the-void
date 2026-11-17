from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domains import match_domain
from aerona.core.random import SeededRandom
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus

MIN_DOMAIN_WORD = 3


def named_domains(*texts: str | None) -> list[Domain]:
    found: list[Domain] = []
    for text in texts:
        for word in (text or "").split():
            domain = match_domain(word) if len(word) >= MIN_DOMAIN_WORD else None
            if domain is not None:
                found.append(domain)
    return found


async def canon_counts(session: AsyncSession, world: WorldRow, among: EntityRow | None = None) -> Counter[Domain]:
    counts: Counter[Domain] = Counter(named_domains(world.name))
    entities = list(await session.scalars(select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.status == EntityStatus.CANON)))
    for entity in entities:
        counts.update(named_domains(entity.subtype, entity.name))
    if among is not None:
        counts.update(named_domains(among.subtype, among.name, among.title) * 2)
    for god in await session.scalars(select(ForeignGodRow).where(ForeignGodRow.world_id == world.id)):
        counts.update(domain for domain in (god.domain_primary, god.domain_secondary) if domain is not None)
    worshipped = select(BondRow.target_node_id).where(
        BondRow.source_node_id.in_([entity.id for entity in entities]), BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
    )
    for son in await session.scalars(select(SonRow).where(SonRow.id.in_(worshipped))):
        counts.update(son.domains)
    return counts


async def canon_domains(session: AsyncSession, world: WorldRow, rng: SeededRandom, among: EntityRow | None = None) -> tuple[Domain, Domain]:
    counts = await canon_counts(session, world, among)
    order = rng.shuffled(list(Domain))
    ranked = sorted(order, key=lambda domain: -counts[domain])
    return ranked[0], ranked[1]
