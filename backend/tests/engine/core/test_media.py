from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.economy import MarketPriceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow, RecordMediumRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.urban import MarketPlayRow
from aerona.domain.enums.communication import OpinionSubject
from aerona.domain.enums.customs import EvidenceKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.media import MediaItemKind, RecordForm
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.urban import MarketPlay
from aerona.engine.context import TickContext
from aerona.engine.media.press import keep_media, recorded_evidence
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules


async def outlet_in(session: AsyncSession, world: CoreWorld, **values: object) -> tuple[EntityRow, EntityRow, MediaOutletRow]:
    town = await settlement(session, "Ardun", world, world.regions[0])
    owner = await mortal(session, "Crier", world, town.id)
    session.add(MortalProfileRow(entity_id=owner.id, wealth=10, locked=[]))
    outlet = MediaOutletRow(owner_node_id=owner.id, seat_entity_id=town.id, name="The Ford Crier", locked=[], **values)
    session.add(outlet)
    await session.flush()
    return town, owner, outlet


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(media=values)))


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("media.")).order_by(IncidentRow.id)))


async def test_an_outlet_reaches_by_its_staff_earns_and_reports_what_happens_in_its_town(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, owner, outlet = await outlet_in(session, world, staff=10, trust=80)
    session.add(IncidentRow(kind="works.begun", epoch=ctx.epoch, place_entity_id=town.id))
    await session.flush()
    tally = await keep_media(tuned(ctx, reach_per_staff=5, revenue_per_reach=2))
    profile = await session.get(MortalProfileRow, owner.id)
    assert outlet.reach == 50 and profile is not None and profile.wealth > 10
    assert tally.published == 1 and "media.item_published" in await kinds_of(session)


async def test_a_slanted_item_moves_opinion_and_a_false_one_costs_trust(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, owner, outlet = await outlet_in(session, world, reach=100, trust=100, staff=50)
    subject = await mortal(session, "Ruler", world, town.id)
    session.add(PublicOpinionRow(community_node_id=town.id, subject_node_id=subject.id, subject=OpinionSubject.RULER, approval=0, locked=[]))
    session.add(
        MediaItemRow(outlet_id=outlet.id, owner_node_id=owner.id, subject_node_id=subject.id, slant=100, accuracy=0, reach=100, epoch=ctx.epoch, locked=[])
    )
    await session.flush()
    tally = await keep_media(tuned(ctx, opinion_shift_pct=20))
    opinion = await session.get(PublicOpinionRow, (town.id, subject.id))
    assert opinion is not None and opinion.approval == 20 and tally.swayed == 1
    assert tally.exposed == 1 and outlet.trust < 100
    assert "media.item_exposed" in await kinds_of(session)


async def test_records_wear_by_the_durability_of_their_medium(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    _town, owner, outlet = await outlet_in(session, world)
    medium = RecordMediumRow(holder_node_id=owner.id, name="loose leaves", form=RecordForm.WRITTEN, durability=0, locked=[])
    session.add(medium)
    await session.flush()
    outlet.medium_id = medium.id
    item = MediaItemRow(
        outlet_id=outlet.id, owner_node_id=owner.id, kind=MediaItemKind.RECORD_OF_EVENT, accuracy=90, condition=5, epoch=ctx.epoch - 1, locked=[]
    )
    session.add(item)
    await session.flush()
    tally = await keep_media(tuned(ctx, record_decay_per_epoch=10))
    assert tally.decayed == 1 and await session.get(MediaItemRow, item.id) is None


async def test_entertainment_raises_a_star_and_a_faithful_record_becomes_evidence(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, owner, outlet = await outlet_in(session, world, reach=90, staff=50)
    star = await mortal(session, "Lark", world, town.id)
    session.add(MortalProfileRow(entity_id=star.id, renown=10, locked=[]))
    session.add(
        MediaItemRow(
            outlet_id=outlet.id, owner_node_id=owner.id, kind=MediaItemKind.ENTERTAINMENT, subject_node_id=star.id, reach=90, epoch=ctx.epoch, locked=[]
        )
    )
    culprit = await mortal(session, "Thief", world, town.id)
    session.add(MediaItemRow(outlet_id=outlet.id, owner_node_id=owner.id, kind=MediaItemKind.RECORD_OF_EVENT, accuracy=100, epoch=ctx.epoch, locked=[]))
    case = CrimeCaseRow(settlement_entity_id=town.id, crime=CrimeKind.THEFT, culprit_entity_id=culprit.id, opened_epoch=ctx.epoch)
    session.add(case)
    await session.flush()
    tally = await keep_media(tuned(ctx, star_reach=60, star_renown=15, reach_per_staff=2))
    profile = await session.get(MortalProfileRow, star.id)
    assert tally.stars == 1 and profile is not None and profile.renown == 25
    evidence = await recorded_evidence(tuned(ctx, evidence_weight_pct=40), case)
    assert len(evidence) == 1 and evidence[0].kind is EvidenceKind.DOCUMENT and evidence[0].reliability == 40


async def test_alarming_news_of_a_town_sends_its_folk_to_hoard_what_it_is_shortest_of(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, owner, outlet = await outlet_in(session, world, reach=100, trust=100)
    session.add_all(
        [
            MarketPriceRow(market_entity_id=town.id, commodity=CommodityKind.GRAIN, epoch=ctx.epoch, price=10, supply=50, demand=40),
            MarketPriceRow(market_entity_id=town.id, commodity=CommodityKind.FISH, epoch=ctx.epoch, price=10, supply=10, demand=60),
            MediaItemRow(outlet_id=outlet.id, owner_node_id=owner.id, subject_node_id=town.id, slant=-100, accuracy=100, reach=100, epoch=ctx.epoch, locked=[]),
        ]
    )
    await session.flush()
    tally = await keep_media(tuned(ctx, alarm_slant=50, alarm_strength_pct=60))
    play = await session.get(MarketPlayRow, (town.id, town.id, CommodityKind.FISH, MarketPlay.CORNER))
    assert play is not None and play.strength == 60 and tally.alarmed == 1
    assert "media.market_alarmed" in await kinds_of(session)
