from sqlalchemy import select

from aerona.catalog.fugitives import FUGITIVES, SANCTUARIES
from aerona.catalog.life.domain import CRIME_KINDS
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.urban import CrimeStance
from aerona.engine.belonging.fugitives_w52 import flee, hunt_one
from aerona.engine.factions.underworld_w52 import raise_gangs, stance_for
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, mortal, settlement, tuned

RULES = Rules()


def test_six_crime_kinds_four_stances_six_fugitives_six_refuges() -> None:
    assert {FactionKind.STREET_GANG, FactionKind.TRAFFICKING_RING} <= CRIME_KINDS
    assert len(CrimeStance) == 5 and len(FugitiveKind) == 8 and len(SanctuaryKind) == 8
    assert FUGITIVES[FugitiveKind.RUNAWAY].city_frees and SANCTUARIES[SanctuaryKind.WILDS].hides


async def test_the_young_of_a_lawless_slum_band_into_a_street_gang(realm: Realm) -> None:
    town = await settlement(realm, "Lowlanes")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, crime=70, locked=[], foreigners={}))
    realm.session.add(DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.SLUMS, level=2, built_epoch=1, locked=[]))
    await realm.session.flush()
    ctx = context(realm.session, tuned(underworld={"gang_recruit_pct": 100}))
    assert await raise_gangs(ctx) == 1
    gang = await realm.session.scalar(select(FactionProfileRow).where(FactionProfileRow.kind == FactionKind.STREET_GANG))
    assert gang is not None and gang.home_entity_id == town.id
    assert await raise_gangs(ctx) == 0


async def test_a_realm_picks_among_four_stances(realm: Realm) -> None:
    profile = FactionProfileRow(faction_entity_id=1, kind=FactionKind.SMUGGLING_RING, influence_over={}, locked=[])
    ctx = context(realm.session, RULES)
    assert (await stance_for(ctx, 0, profile, {ValueAxis.LAW: 50, ValueAxis.WEALTH: 10}))[0] is CrimeStance.SUPPRESS
    assert (await stance_for(ctx, 0, profile, {ValueAxis.XENOPHILIA: 40, ValueAxis.WEALTH: 30}))[0] is CrimeStance.LICENSE
    profile.kind = FactionKind.STREET_GANG
    assert (await stance_for(ctx, 0, profile, {ValueAxis.WEALTH: 40}))[0] is CrimeStance.TOLERATE


async def test_a_runaway_flees_and_is_hunted_down(realm: Realm) -> None:
    town = await settlement(realm, "Fields")
    runner = await mortal(realm, "Dess", location_id=town.id)
    ctx = context(realm.session, RULES)
    row = await flee(ctx, runner, FugitiveKind.RUNAWAY, None)
    assert row is not None and await flee(ctx, runner, FugitiveKind.RUNAWAY, None) is None
    assert await hunt_one(ctx, row, certain=True)
    caught = await realm.session.get(FugitiveRow, row.id)
    assert caught is not None and caught.caught_epoch == ctx.epoch
    assert {"fugitive.fled", "fugitive.caught"} <= set(await chronicle_keys(realm.session))
