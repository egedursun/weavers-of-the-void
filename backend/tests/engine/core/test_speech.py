from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.speech import HumourStyleRow, SpeechRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.speech import HumourForm, SpeechAim, SpeechVenue
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.speech.oratory import keep_speech
from aerona.engine.speech.seed import seed_humour
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def realm_town(session: AsyncSession, world: CoreWorld, unrest: int = 10) -> tuple[EntityRow, EntityRow, EntityRow]:
    town = await settlement(session, "Ardun", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=unrest, locked=[], foreigners={}))
    realm = await entity(session, "Crown of Ardun", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, legitimacy=50, locked=[], emblem={}
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    ruler = await mortal(session, "Queen", world, town.id, charisma=80)
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id))
    await session.flush()
    return town, realm, ruler


async def speaker(session: AsyncSession, world: CoreWorld, town: EntityRow, name: str) -> EntityRow:
    being = await mortal(session, name, world, town.id, charisma=100)
    session.add(MortalProfileRow(entity_id=being.id, honour=50, locked=[]))
    await session.flush()
    return being


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(speech=values)))


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("speech.")).order_by(IncidentRow.id)))


async def test_a_speech_to_the_assembly_moves_the_realm_and_one_in_the_square_stirs_the_crowd(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    town, realm, _ruler = await realm_town(session, world)
    orator = await speaker(session, world, town, "Orator")
    session.add(SpeechRow(speaker_node_id=orator.id, place_entity_id=town.id, venue=SpeechVenue.ASSEMBLY, aim=SpeechAim.RALLY, skill=100, reach=100, locked=[]))
    session.add(SpeechRow(speaker_node_id=orator.id, place_entity_id=town.id, venue=SpeechVenue.SQUARE, aim=SpeechAim.ACCUSE, skill=100, reach=100, locked=[]))
    await session.flush()
    tally = await keep_speech(tuned(ctx, persuasion_pct=20, ruler_speech_pct=0))
    profile = await session.get(PolityProfileRow, realm.id)
    town_profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.legitimacy == 70 and tally.votes == 1
    assert town_profile is not None and town_profile.unrest == 30 and tally.crowds == 1


async def test_mocking_the_ruler_offends_where_forbidden_and_wears_them_where_allowed(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, realm, ruler = await realm_town(session, world)
    session.add(HumourStyleRow(people_entity_id=world.people.id, form=HumourForm.SATIRE, mock_rulers=False, offence_threshold=10, locked=[]))
    jester = await speaker(session, world, town, "Jester")
    session.add(SpeechRow(speaker_node_id=jester.id, place_entity_id=town.id, aim=SpeechAim.MOCK, audience_node_id=ruler.id, skill=100, reach=100, locked=[]))
    await session.flush()
    tally = await keep_speech(tuned(ctx, persuasion_pct=50, ruler_speech_pct=0))
    shamed = await session.get(MortalProfileRow, jester.id)
    assert tally.offended == 1 and shamed is not None and shamed.honour < 50
    style = await session.get(HumourStyleRow, world.people.id)
    assert style is not None
    style.mock_rulers = True
    session.add(SpeechRow(speaker_node_id=jester.id, place_entity_id=town.id, aim=SpeechAim.MOCK, audience_node_id=ruler.id, skill=100, reach=100, locked=[]))
    await session.flush()
    await keep_speech(tuned(ctx, persuasion_pct=50, ruler_speech_pct=0))
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None and profile.legitimacy < 50
    assert "speech.offence_taken" in await kinds_of(session)


async def test_a_ruler_of_a_restless_town_rallies_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, _realm, ruler = await realm_town(session, world, unrest=80)
    tally = await keep_speech(tuned(ctx, ruler_speech_pct=100, restless_at=50))
    spoken = await session.scalar(select(SpeechRow).where(SpeechRow.speaker_node_id == ruler.id))
    assert tally.rallied == 1 and spoken is not None and spoken.heard
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.unrest < 80
    assert "speech.given" in await kinds_of(session)


async def test_humour_follows_the_values_of_a_people(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add_all(
        [
            CultureValueRow(entity_id=world.people.id, axis=ValueAxis.TRUTH, value=90),
            CultureValueRow(entity_id=world.people.id, axis=ValueAxis.HIERARCHY, value=90),
        ]
    )
    await session.flush()
    assert await seed_humour(ctx) >= 1
    style = await session.get(HumourStyleRow, world.people.id)
    assert style is not None and style.form is HumourForm.IRONY and not style.mock_rulers
