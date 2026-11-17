import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.culture import LanguageIntelligibilityRow, LanguageRegisterRow, SpeakerCohortRow, TraditionEffectRow, TraditionParticipationRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import LanguageRegister, SpeakerKind, TraditionEffectKind, TraditionFunction
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.models.entity_stats import LanguageStats, SettlementStats
from aerona.services.player import canon, culture, lore
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def entity(session: AsyncSession, world: PlayerWorld, name: str, kind: EntityType) -> EntityRow:
    stats = SettlementStats(population=900, prosperity=40) if kind is EntityType.SETTLEMENT else LanguageStats(spread=20)
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=kind,
            description=f"The {kind.value} {name}.",
            stats=stats,
            power_level=2,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world.world.id,
            location_id=world.region.id if kind is EntityType.SETTLEMENT else None,
            split_title=False,
        )
    )


async def test_a_register_is_set_held_released_and_cleared(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await entity(session, world, "Ashford", EntityType.SETTLEMENT)
    tongue = await entity(session, world, "Ossic", EntityType.LANGUAGE)
    await culture.set_register(scope, culture.Register(holder_id=town.id, kind=LanguageRegister.COURT, language_id=tongue.id))
    row = await session.get(LanguageRegisterRow, (town.id, LanguageRegister.COURT))
    assert row is not None and row.locked == ["language_entity_id"]
    await culture.set_register(scope, culture.Register(holder_id=town.id, kind=LanguageRegister.COURT, language_id=tongue.id, hold=False))
    assert row.locked == []
    await culture.set_register(scope, culture.Register(holder_id=town.id, kind=LanguageRegister.COURT, language_id=None))
    assert await session.get(LanguageRegisterRow, (town.id, LanguageRegister.COURT)) is None


async def test_understanding_and_speakers_are_held_when_set_and_released_on_demand(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await entity(session, world, "Ashford", EntityType.SETTLEMENT)
    first, second = await entity(session, world, "Ossic", EntityType.LANGUAGE), await entity(session, world, "Varn", EntityType.LANGUAGE)
    await lore.set_intelligibility(scope, lore.Intelligibility(first_id=first.id, second_id=second.id, value=55))
    pair = await session.get(LanguageIntelligibilityRow, tuple(sorted((first.id, second.id))))
    assert pair is not None and pair.locked == ["value"]
    await culture.release_understanding(scope, culture.PairTarget(first_id=second.id, second_id=first.id))
    assert pair.locked == []
    await lore.set_speakers(scope, lore.Speakers(community_id=town.id, language_id=first.id, share=30))
    cohort = await session.get(SpeakerCohortRow, (town.id, first.id, SpeakerKind.SECOND))
    assert cohort is not None and cohort.locked == ["share"]
    await culture.release_speakers(scope, culture.SpeakerTarget(community_id=town.id, language_id=first.id))
    assert cohort.locked == []


async def test_tradition_effects_participation_and_reseeding_are_player_controls(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await entity(session, world, "Ashford", EntityType.SETTLEMENT)
    await lore.create_lore(
        scope, lore.CreateLore(entity_type=EntityType.TRADITION, name="Lamp Night", world_id=world.world.id, values={"kind": TraditionFunction.FESTIVAL.value})
    )
    tradition = await session.scalar(select(EntityRow).where(EntityRow.name == "Lamp Night"))
    assert tradition is not None
    await canon.add_bond(scope, canon.AddBond(source_id=town.id, target_id=tradition.id, kind=BondKind.CELEBRATES))
    await culture.set_tradition_effect(scope, culture.TraditionEffect(tradition_id=tradition.id, effect=TraditionEffectKind.VALUE, target="mercy", magnitude=4))
    rows = {
        (row.effect, row.target): row.magnitude
        for row in await session.scalars(select(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == tradition.id))
    }
    assert rows[(TraditionEffectKind.VALUE, "mercy")] == 4
    assert (TraditionEffectKind.COHESION, "") in rows
    with pytest.raises(ValidationFailedError):
        await culture.set_tradition_effect(
            scope, culture.TraditionEffect(tradition_id=tradition.id, effect=TraditionEffectKind.VALUE, target="nonsense", magnitude=4)
        )
    await culture.reseed_tradition(scope, culture.TraditionTarget(tradition_id=tradition.id))
    reseeded = {
        (row.effect, row.target) for row in await session.scalars(select(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == tradition.id))
    }
    assert (TraditionEffectKind.VALUE, "mercy") not in reseeded
    await lore.set_participation(scope, lore.Participation(tradition_id=tradition.id, community_id=town.id, participation=80))
    kept = await session.get(TraditionParticipationRow, (tradition.id, town.id))
    assert kept is not None and kept.locked == ["participation"]
    await culture.release_participation(scope, culture.KeeperTarget(tradition_id=tradition.id, community_id=town.id))
    assert kept.locked == []


async def test_derived_display_bonds_cannot_be_woven_by_hand(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await entity(session, world, "Ashford", EntityType.SETTLEMENT)
    tongue = await entity(session, world, "Ossic", EntityType.LANGUAGE)
    with pytest.raises(ValidationFailedError):
        await canon.add_bond(scope, canon.AddBond(source_id=town.id, target_id=tongue.id, kind=BondKind.TELLS))
