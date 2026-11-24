from aerona.catalog.relations import CIRCLES, CONTESTS, STAKE_LABELS
from aerona.catalog.renown import CONTEST_RENOWN
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.relations import CircleKind, ContestKind, ContestStake
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.relations.contests import Bout, prowess, win_land, win_own_freedom
from tests.engine.society.factories import Realm, context, mortal


def test_nine_contests_nine_stakes_and_ten_circles() -> None:
    assert len(CONTESTS) == len(ContestKind) == 11 == len(STAKE_LABELS) == len(ContestStake)
    assert set(CONTEST_RENOWN) == set(ContestKind)
    assert len(CIRCLES) == len(CircleKind) == 12
    assert CIRCLES[CircleKind.SPORT_CLUB].fields and CIRCLES[CircleKind.GAMING_CIRCLE].wagers
    assert CONTESTS[ContestKind.RACE].races and CONTESTS[ContestKind.CRAFT_CONTEST].crafted


async def test_a_race_reads_endurance_and_the_racer_contends(realm: Realm) -> None:
    runner = await mortal(realm, "Runner", agility=90)
    assert await prowess(context(realm.session), runner, ContestKind.RACE) > 0


async def test_land_staked_moves_to_the_winner(realm: Realm) -> None:
    winner, loser = await mortal(realm, "Winner"), await mortal(realm, "Loser")
    await connect(realm.session, loser.id, realm.region.id, BondKind.OWNS, 1)
    await realm.session.flush()
    await win_land(context(realm.session), Bout(ContestKind.RACE, ContestStake.LAND, winner, loser), winner, loser)
    assert [bond.target_node_id for bond in await active_bonds(realm.session, [BondKind.OWNS], sources=[winner.id])] == [realm.region.id]
    assert not await active_bonds(realm.session, [BondKind.OWNS], sources=[loser.id])


async def test_a_captive_who_wins_its_freedom_goes_free(realm: Realm) -> None:
    captive, keeper = await mortal(realm, "Captive"), await mortal(realm, "Keeper")
    row = CaptiveRow(captive_entity_id=captive.id, captor_entity_id=keeper.id, taken_epoch=1, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    await win_own_freedom(context(realm.session), Bout(ContestKind.RACE, ContestStake.FREEDOM, captive, keeper), captive, keeper)
    assert row.status is not CaptiveStatus.HELD
