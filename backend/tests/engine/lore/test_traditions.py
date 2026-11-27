from types import SimpleNamespace
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import InjuryRow
from aerona.db.tables.culture import TraditionEffectRow, TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, WorldSeasonRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.body import HarmCause, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CalendarSlot, TraditionEffectKind, TraditionFunction
from aerona.domain.enums.demography import InheritanceCustom, MartialStyle
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.models.entity_stats import CultStats, TraditionStats
from aerona.engine.body.customs import presence_pct
from aerona.engine.lore import taboos, traditions
from aerona.engine.lore.culture_control import set_tradition_effect
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, link, make, mortal, people, settlement


async def custom(realm: Realm, name: str, kind: TraditionFunction, rigidity: int = 50, **values: object) -> EntityRow:
    entity = await make(realm.session, name, EntityType.TRADITION, TraditionStats(spread=20, rigidity=rigidity), world_id=realm.world.id)
    row = await traditions.profile_of(context(realm.session), entity, kind)
    for key, value in values.items():
        setattr(row, key, value)
    await realm.session.flush()
    return entity


async def culture(session: AsyncSession, people_id: int, cohesion: int = 50) -> PeopleCultureRow:
    row = PeopleCultureRow(
        people_entity_id=people_id,
        cohesion=cohesion,
        literacy=0,
        urbanisation=0,
        martial_style=next(iter(MartialStyle)),
        inheritance=next(iter(InheritanceCustom)),
    )
    session.add(row)
    await session.flush()
    return row


async def test_the_effects_table_drives_what_a_feast_brings(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Ossians")
    kept = await culture(session, folk.id)
    feast = await custom(realm, "The Lamp Night", TraditionFunction.MOURNING)
    await link(session, folk.id, feast.id, BondKind.CELEBRATES)
    effects = {row.effect for row in await session.scalars(select(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == feast.id))}
    assert TraditionEffectKind.COHESION in effects
    ctx = context(session, epoch=4)
    await set_tradition_effect(ctx, feast.id, TraditionEffectKind.COHESION, "", 20)
    participation = await traditions.participate(ctx, feast, folk)
    participation.participation, participation.locked = 100, ["participation"]
    before = kept.cohesion
    await traditions.celebrate(ctx, feast, folk, await RegionAtlas.load(session))
    profile = await session.get(TraditionProfileRow, feast.id)
    assert profile is not None
    assert kept.cohesion == before + round(20 * await traditions.slot_weight(ctx, profile, folk, TraditionEffectKind.COHESION))


async def test_a_feast_out_of_its_season_is_weaker_and_in_its_season_stronger(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Ossians")
    feast = await custom(realm, "Midwinter Fires", TraditionFunction.FESTIVAL, calendar_slot=CalendarSlot.MIDWINTER)
    ctx = context(session, epoch=4)
    row = await session.get(TraditionProfileRow, feast.id)
    assert row is not None
    rules = Rules().traditions
    assert await traditions.slot_weight(ctx, row, folk, TraditionEffectKind.COHESION) == rules.calendar_misfit_pct / 100
    session.add(WorldSeasonRow(world_id=realm.world.id, position=0, name="Deep Winter", temperature_shift=-20, rain_shift=0, growth=5, travel=20, campaign=10))
    session.add(WorldSeasonRow(world_id=realm.world.id, position=1, name="High Sun", temperature_shift=20, rain_shift=0, growth=80, travel=80, campaign=80))
    await session.flush()
    assert await traditions.slot_weight(ctx, row, folk, TraditionEffectKind.COHESION) == 1 + rules.calendar_slot_pct / 100


async def test_a_taboo_holds_its_keepers_back_and_shames_the_one_who_breaks_it(realm: Realm) -> None:
    session = realm.session
    home = await settlement(realm, "Ashford")
    duellist = await mortal(realm, "Brann", location_id=home.id)
    taboo = await custom(realm, "No Blood Between Kin", TraditionFunction.TABOO, taboo_act=ActKind.DUELLING)
    await link(session, home.id, taboo.id, BondKind.CELEBRATES)
    session.add(TraditionParticipationRow(tradition_entity_id=taboo.id, community_entity_id=home.id, participation=100, locked=[]))
    await session.flush()
    ctx = context(session, epoch=4)
    assert await taboos.forbidden(ctx, duellist.id, ActKind.DUELLING)
    assert not await taboos.forbidden(ctx, duellist.id, ActKind.RAIDING)
    assert await taboos.violated(ctx, duellist.id, ActKind.DUELLING) == 1
    shame = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == home.id, MemoryRow.subject_node_id == duellist.id))
    assert shame is not None and shame.magnitude < 0
    assert "lore.taboo_broken" in await chronicle_keys(session)


async def test_killing_a_guest_under_the_law_of_hospitality_is_grave_infamy(realm: Realm) -> None:
    session = realm.session
    host, home = await settlement(realm, "Ashford"), await settlement(realm, "Brindle")
    guest = await mortal(realm, "Wanderer", location_id=host.id)
    killer = await mortal(realm, "Host", location_id=host.id)
    await link(session, guest.id, home.id, BondKind.LIVES_IN)
    law = await custom(realm, "Bread and Salt", TraditionFunction.HOSPITALITY)
    await link(session, host.id, law.id, BondKind.CELEBRATES)
    ctx = context(session, epoch=4)
    assert await taboos.guest_killed(ctx, killer.id, guest) >= 1
    assert "lore.guest_killing" in await chronicle_keys(session)
    assert await taboos.guest_killed(ctx, killer.id, killer) == 0


async def test_a_people_takes_the_custom_that_fits_its_values(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Ossians")
    war, feast = await custom(realm, "War Drums", TraditionFunction.MARTIAL_DISPLAY), await custom(realm, "Hearth Feast", TraditionFunction.FESTIVAL)
    ctx = context(session, epoch=4)
    chosen = await traditions.best_fit(ctx, [war, feast], folk.id)
    assert chosen is not None
    assert chosen[1] == min(await traditions.fit_of(ctx, war.id, folk.id), await traditions.fit_of(ctx, feast.id, folk.id))


async def test_notable_years_found_remembrances_tied_to_their_incident(realm: Realm) -> None:
    session = realm.session
    await settlement(realm, "Ashford")
    year = NotableYearRow(
        world_id=realm.world.id, region_entity_id=realm.region.id, epoch=4, year=40, kind=NotableYearKind.HUNGER, name="the Hungry Year", magnitude=90
    )
    session.add(year)
    await session.flush()
    ctx = context(session, Rules(), epoch=4)
    founded = await traditions.remember_years(ctx, await RegionAtlas.load(session))
    if founded:
        row = await session.get(TraditionProfileRow, founded[0].id)
        assert row is not None and row.kind is TraditionFunction.MOURNING
        assert row.origin_incident_id == year.incident_id


async def test_a_new_faith_absorbs_a_rigid_feast(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Ossians")
    cult = await make(session, "The Bright Way", EntityType.CULT, CultStats(followers=100, zeal=50), world_id=realm.world.id)
    rigid = await custom(realm, "Old Harvest", TraditionFunction.SEASONAL_RITE, rigidity=90)
    loose = await custom(realm, "New Games", TraditionFunction.FESTIVAL, rigidity=5)
    await link(session, folk.id, rigid.id, BondKind.CELEBRATES)
    await link(session, folk.id, loose.id, BondKind.CELEBRATES)
    absorbed = await traditions.absorb_festivals(context(session, epoch=4), folk, cult.id)
    assert [item.id for item in absorbed] == [rigid.id]


def test_ritual_scars_lend_presence_where_ordinary_scars_cost_it() -> None:
    rules = Rules()
    mark = SimpleNamespace(cause_kind=HarmCause.RITUAL, visible=True, state=InjuryState.HEALED_SCAR, kind=None, part="face", cause_node_id=None)
    wound = SimpleNamespace(cause_kind=HarmCause.BATTLE, visible=True, state=InjuryState.HEALED_SCAR, kind=None, part="face", cause_node_id=None)
    ritual = presence_pct(rules, None, [cast(InjuryRow, mark)], [], role=None, patron_id=None)
    plain = presence_pct(rules, None, [cast(InjuryRow, wound)], [], role=None, patron_id=None)
    assert ritual == 100 + rules.traditions.ritual_presence_pct
    assert ritual > plain


async def test_a_custom_kept_out_of_its_time_is_kept_after_the_note_that_its_time_did_not_come(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Ossians")
    await culture(session, folk.id)
    feast = await custom(realm, "Midwinter Fires", TraditionFunction.FESTIVAL, calendar_slot=CalendarSlot.MIDWINTER)
    await link(session, folk.id, feast.id, BondKind.CELEBRATES)
    ctx = context(session, epoch=4)
    participation = await traditions.participate(ctx, feast, folk)
    participation.participation, participation.locked = 100, ["participation"]
    await traditions.celebrate(ctx, feast, folk, await RegionAtlas.load(session))
    closed = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "tradition.slot_closed"))
    kept = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "tradition.kept_untimely"))
    assert closed is not None and kept is not None
    assert await session.scalar(select(IncidentRow).where(IncidentRow.kind == "tradition.kept")) is None
    assert kept.cause_incident_id == closed.id
    assert (kept.year or 0, kept.season or 0) >= (closed.year or 0, closed.season or 0)
