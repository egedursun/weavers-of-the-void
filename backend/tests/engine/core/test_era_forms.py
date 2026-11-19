from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import TIER_LABELS
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.polity import GovernmentKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.phases.society_economy import default_society, normalized_shares, save_society
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import found_polity, government_for
from tests.engine.core.factories import CoreWorld, settlement

ARCHAIC = frozenset({"tribe", "city-state", "kingdom", "world empire"})


async def test_a_town_that_knows_written_law_is_no_longer_ruled_as_a_chiefdom(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    town.civ_tier = 0
    await session.flush()
    assert await government_for(ctx, town, [town], None) is GovernmentKind.CHIEFDOM
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.WRITTEN_LAW, since_epoch=1, secret=False))
    await session.flush()
    assert await government_for(ctx, town, [town], None) is not GovernmentKind.CHIEFDOM
    realm = await found_polity(ctx, await RealmBook.load(session), town, told=False)
    assert realm.profile.government is not GovernmentKind.CHIEFDOM


def test_scale_tiers_name_a_scale_and_no_age() -> None:
    assert not {label.lower() for label in TIER_LABELS.values()} & ARCHAIC


async def test_a_realm_of_voting_citizens_elects_its_government_and_learning_alone_does_not_hand_it_to_experts(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    town.civ_tier = 3
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.WRITTEN_LAW, since_epoch=1, secret=False))
    society = default_society(ctx.rules)
    society.shares = normalized_shares({**society.shares, SocialClass.PROFESSIONAL: 15.0, SocialClass.CITIZEN: 0.0})
    await save_society(session, town.id, society)
    await session.flush()
    assert await government_for(ctx, town, [town], None) is not GovernmentKind.TECHNOCRACY
    society.shares = normalized_shares({**society.shares, SocialClass.CITIZEN: 15.0})
    await save_society(session, town.id, society)
    await session.flush()
    assert await government_for(ctx, town, [town], None) is GovernmentKind.REPUBLIC
