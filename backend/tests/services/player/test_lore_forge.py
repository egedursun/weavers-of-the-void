import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.culture import (
    ArtworkProfileRow,
    CustomKindRow,
    IdeologyTenetRow,
    ItemProfileRow,
    LegendProfileRow,
    ProphecyConditionRow,
    RiteProfileRow,
    RumourRow,
    TraditionProfileRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import (
    ArtMedium,
    CustomCatalog,
    IdeologyTenet,
    ItemClass,
    LegendArchetype,
    MagicSchool,
    ProphecyPredicate,
    TraditionKind,
)
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.models.entity_stats import SettlementStats
from aerona.services.player import lore, rumours
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def town(session: AsyncSession, world: PlayerWorld, name: str) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=EntityType.SETTLEMENT,
            description="A town.",
            stats=SettlementStats(population=1000, prosperity=50, defense=40, piety=50),
            power_level=2,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world.world.id,
            location_id=world.region.id,
            split_title=False,
        )
    )


async def forge(scope: PlayerScope, world: PlayerWorld, entity_type: EntityType, **values: object) -> int:
    effect = await lore.create_lore(
        scope,
        lore.CreateLore(entity_type=entity_type, name=f"New {entity_type.value}", world_id=world.world.id, values=values),  # type: ignore[arg-type]
    )
    assert effect.created_ids
    return effect.created_ids[0]


async def test_every_lore_kind_can_be_forged_with_its_typed_profile(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    legend = await forge(scope, world, EntityType.LEGEND, archetype=LegendArchetype.FLOOD.value, credence=70)
    tradition = await forge(scope, world, EntityType.TRADITION, kind=TraditionKind.WAR_DANCE.value)
    creed = await forge(scope, world, EntityType.IDEOLOGY, tenets=[IdeologyTenet.EGALITARIANISM.value, IdeologyTenet.RATIONALISM.value])
    rite = await forge(scope, world, EntityType.RITE, school=MagicSchool.STORM.value, power=6)
    prophecy = await forge(scope, world, EntityType.PROPHECY, predicate=ProphecyPredicate.SKY_EVENT.value, args={"kind": "eclipse"})
    item = await forge(scope, world, EntityType.ITEM, item_class=ItemClass.CROWN.value, quality=90)
    artwork = await forge(scope, world, EntityType.ARTWORK, medium=ArtMedium.FRESCO.value)
    knowledge = await forge(scope, world, EntityType.KNOWLEDGE, branch="medicine", level=3)
    assert (await session.get(LegendProfileRow, legend)).credence == 70  # type: ignore[union-attr]
    assert (await session.get(TraditionProfileRow, tradition)).kind is TraditionKind.WAR_DANCE  # type: ignore[union-attr]
    tenets = set(await session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creed)))
    assert tenets == {IdeologyTenet.EGALITARIANISM, IdeologyTenet.RATIONALISM}
    assert (await session.get(RiteProfileRow, rite)).power == 6  # type: ignore[union-attr]
    assert (await session.get(ProphecyConditionRow, prophecy)).args == {"kind": "eclipse"}  # type: ignore[union-attr]
    assert (await session.get(ItemProfileRow, item)).quality == 90  # type: ignore[union-attr]
    assert (await session.get(ArtworkProfileRow, artwork)).medium is ArtMedium.FRESCO  # type: ignore[union-attr]
    made = await session.get(EntityRow, knowledge)
    assert made is not None and made.knowledge_branch is not None and made.knowledge_branch.value == "medicine"


async def test_a_lore_record_needs_its_kind_and_a_name(scope: PlayerScope, world: PlayerWorld) -> None:
    with pytest.raises(ValidationFailedError):
        await forge(scope, world, EntityType.ITEM)
    with pytest.raises(ValidationFailedError):
        await lore.create_lore(scope, lore.CreateLore(entity_type=EntityType.LEGEND, name=" ", world_id=world.world.id, values={"archetype": "flood"}))
    with pytest.raises(ValidationFailedError):
        await forge(scope, world, EntityType.MORTAL)


async def test_custom_kinds_are_named_reshaped_and_unmade(scope: PlayerScope, session: AsyncSession) -> None:
    await lore.create_kind(
        scope, lore.CreateKind(catalog=CustomCatalog.ITEM_CLASS, base="blade", name="Moon sickle", params={"reach": 3, "damage_type": "cold"})
    )
    row = await session.scalar(select(CustomKindRow))
    assert row is not None and row.params == {"reach": 3, "damage_type": "cold"}
    await lore.edit_kind(scope, lore.EditKind(kind_id=row.id, values={"params": {"reach": 4}}))
    assert row.params == {"reach": 4}
    with pytest.raises(ValidationFailedError):
        await lore.edit_kind(scope, lore.EditKind(kind_id=row.id, values={"params": {"reach": 500}}))
    with pytest.raises(ValidationFailedError):
        await lore.create_kind(scope, lore.CreateKind(catalog=CustomCatalog.TENET, base="no_such_tenet", name="X"))
    await lore.delete_kind(scope, lore.KindTarget(kind_id=row.id))
    assert await session.scalar(select(CustomKindRow)) is None


async def test_rumours_are_whispered_reshaped_and_silenced(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await town(session, world, "Ashford")
    second = await town(session, world, "Brindle")
    await rumours.plant_rumour(scope, rumours.PlantRumour(community_id=first.id, subject_id=second.id, text="They hoard grain", fidelity=60))
    row = await session.scalar(select(RumourRow))
    assert row is not None and row.fidelity == 60 and row.planted
    await rumours.edit_rumour(scope, rumours.EditRumour(rumour_id=row.id, fidelity=30))
    assert row.fidelity == 30 and "fidelity" in row.locked
    await rumours.edit_rumour(scope, rumours.EditRumour(rumour_id=row.id, release=True))
    assert "fidelity" not in row.locked
    await rumours.suppress_rumour(scope, rumours.SuppressRumour(rumour_id=row.id))
    assert await session.scalar(select(RumourRow)) is None
