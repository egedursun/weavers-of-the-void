from dataclasses import replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityOrigin, EntityType
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.entity_stats import (
    CultStats,
    EntityStats,
    FactionStats,
    KnowledgeStats,
    MortalStats,
    PeopleStats,
    RegionStats,
    SettlementStats,
    StructureStats,
)
from aerona.engine.context import TickContext, TickEnvironment
from aerona.engine.stats import TickStats
from aerona.rules.registry import Rules

STAT_MODELS: dict[EntityType, type[Any]] = {
    EntityType.PEOPLE: PeopleStats,
    EntityType.SETTLEMENT: SettlementStats,
    EntityType.FACTION: FactionStats,
    EntityType.CULT: CultStats,
    EntityType.MORTAL: MortalStats,
    EntityType.REGION: RegionStats,
    EntityType.KNOWLEDGE: KnowledgeStats,
    EntityType.STRUCTURE: StructureStats,
}


def tune(rules: Rules, **namespaces: dict[str, int]) -> Rules:
    for namespace, values in namespaces.items():
        rules = replace(rules, **{namespace: replace(getattr(rules, namespace), **values)})
    return rules


def make_ctx(session: AsyncSession, rules: Rules | None = None, epoch: int = 10, seed: int = 7, phase: str = "test") -> TickContext:
    environment = TickEnvironment(
        rules=rules or Rules(),
        epoch=epoch,
        world_seed=seed,
        lore_language=LoreLanguage.ENGLISH,
        publish=lambda kind, payload: None,
        stats=TickStats(),
    )
    return TickContext(environment=environment, session=session, phase=phase)


async def make(
    session: AsyncSession,
    name: str,
    entity_type: EntityType,
    world_id: int,
    *,
    location_id: int | None = None,
    engine_kind: EngineKind | None = None,
    social_class: SocialClass | None = None,
    birth_epoch: int = 1,
    power_level: int = 3,
    **stats: int,
) -> EntityRow:
    model: EntityStats = STAT_MODELS[entity_type](**stats)
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} {name}.",
            stats=model,
            power_level=power_level,
            origin=EntityOrigin.ENGINE,
            birth_epoch=birth_epoch,
            world_id=world_id,
            location_id=location_id,
            engine_kind=engine_kind,
            social_class=social_class,
            split_title=False,
        )
    )


async def bond(session: AsyncSession, source: int, target: int, kind: BondKind, *, epoch: int = 1, description: str | None = None) -> None:
    await BondRepository(session).connect(BondDraft(source, target, kind, epoch, description))


async def society(session: AsyncSession, entity_id: int, *, warrior: float = 10.0, merchant: float = 8.0, priest: float = 7.0, food: int = 60) -> None:
    farmer = 100.0 - warrior - merchant - priest - 10.0
    session.add(
        CommunitySocietyRow(
            entity_id=entity_id,
            share_farmer=farmer,
            share_artisan=5.0,
            share_merchant=merchant,
            share_priest=priest,
            share_warrior=warrior,
            share_scribe=5.0,
            satisfaction_farmer=50,
            satisfaction_artisan=50,
            satisfaction_merchant=50,
            satisfaction_priest=50,
            satisfaction_warrior=50,
            satisfaction_scribe=50,
            stock_food=food,
            stock_ore=10,
            stock_goods=40,
            price_food=100,
            price_ore=100,
            price_goods=100,
        )
    )
    await session.flush()
