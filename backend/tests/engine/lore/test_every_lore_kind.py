from typing import Any

import pytest

from aerona.domain.enums.culture import ArtMedium, IdeologyTenet, ItemClass, LegendArchetype, MagicSchool, ProphecyPredicate, TraditionKind
from aerona.domain.enums.discovery import ArtDiscipline, TheoryDomain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.lore.control import PROFILES, create_lore, edit_profile
from aerona.engine.lore.creation import CREATABLE, SEEDERS
from tests.engine.society.factories import Realm, context

FIRST_VALUES: dict[EntityType, dict[str, Any]] = {
    EntityType.LANGUAGE: {},
    EntityType.LEGEND: {"archetype": next(iter(LegendArchetype)).value},
    EntityType.TRADITION: {"kind": next(iter(TraditionKind)).value},
    EntityType.IDEOLOGY: {"tenets": [next(iter(IdeologyTenet)).value]},
    EntityType.RITE: {"school": next(iter(MagicSchool)).value},
    EntityType.PROPHECY: {"predicate": next(iter(ProphecyPredicate)).value},
    EntityType.ITEM: {"item_class": next(iter(ItemClass)).value},
    EntityType.ARTWORK: {"medium": next(iter(ArtMedium)).value},
    EntityType.KNOWLEDGE: {"branch": next(iter(KnowledgeBranch)).value},
    EntityType.THEORY: {"domain": next(iter(TheoryDomain)).value},
    EntityType.ART_FORM: {"discipline": next(iter(ArtDiscipline)).value},
}


def test_every_creatable_lore_kind_has_a_seeder_and_a_case() -> None:
    assert set(SEEDERS) == set(CREATABLE) == set(FIRST_VALUES)


@pytest.mark.parametrize("kind", sorted(FIRST_VALUES))
async def test_a_god_makes_every_kind_of_lore_and_opens_its_profile(realm: Realm, kind: EntityType) -> None:
    ctx = context(realm.session)
    made = await create_lore(
        ctx, kind, name=f"New {kind.value}", description="", world_id=realm.world.id, location_id=realm.region.id, power=3, values=dict(FIRST_VALUES[kind])
    )
    assert made.entity_type is kind and made.status is EntityStatus.CANON
    if kind in PROFILES:
        assert await edit_profile(ctx, made.id, {}, release=[]) is not None
