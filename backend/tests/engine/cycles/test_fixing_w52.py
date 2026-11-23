from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.crimes import CRIMES
from aerona.catalog.life_traits import ACT_KIND_TRAITS
from aerona.db.tables.arts import BetRow, ClubRow, MatchRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.arts import ClubKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.engine.arts.control import fix_contest
from aerona.engine.arts.sport import SportTally, play
from tests.engine.core.factories import CoreWorld, mortal
from tests.engine.core.test_cycles_w21 import context
from tests.engine.cycles.test_clubs_w52 import club


def test_fixing_is_both_an_act_and_a_crime() -> None:
    assert ActKind.FIXING_CONTESTS in ACT_KIND_TRAITS
    assert CRIMES[CrimeKind.FIXING_CONTESTS].severity > 0


async def test_a_fixed_contest_is_won_by_the_fixed_side_and_when_found_out_voids_the_wagers(session: AsyncSession, world: CoreWorld) -> None:
    home = await club(session, world, ClubKind.RACING)
    away = ClubRow(faction_entity_id=(await mortal(session, "Away", world, None)).id, kind=ClubKind.RACING, rating=100, fandom=10, locked=[])
    session.add(away)
    await session.flush()
    fixer = await mortal(session, "Fixer", world, None)
    ctx = await context(session, clubs={"fixing_detect_pct": 100})
    first = MatchRow(home_entity_id=home.faction_entity_id, away_entity_id=away.faction_entity_id, epoch=1, locked=[])
    session.add(first)
    await session.flush()
    await fix_contest(ctx, fixer.id, first.id, home.faction_entity_id)
    tally = SportTally()
    match = await play(ctx, None, home, away, tally)
    assert match.winner_entity_id == home.faction_entity_id and match.fixed_by_entity_id == fixer.id
    assert match.fixing_exposed and tally.fixed == 1 and tally.exposed == 1
    assert home.fixed_by_entity_id is None
    bets = list(await session.scalars(select(BetRow).where(BetRow.match_id == match.id)))
    assert all(bet.won is None for bet in bets)
    assert "club.fixing_exposed" in set(await session.scalars(select(IncidentRow.kind)))
