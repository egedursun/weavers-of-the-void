from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.warfare import BattleRow, WarRow, WarSideRow
from aerona.domain.enums.war import BattleOutcome
from aerona.rules.registry import Rules
from aerona.services.books.model import BookBuilder
from tests.engine.core.stirring import stir
from tests.engine.integration.factories import seed_rich_cosmos


async def test_a_war_tallies_only_the_battles_that_were_given(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
        war = (await session.scalars(select(WarRow).order_by(WarRow.id))).first()
        assert war is not None
        sides = list(await session.scalars(select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id).order_by(WarSideRow.entity_id)))
        attacker, defender = sides[0], sides[-1]
        for sequence, outcome in enumerate((BattleOutcome.REFUSED, BattleOutcome.REFUSED, BattleOutcome.GREAT_VICTORY), start=1):
            session.add(BattleRow(war_id=war.id, epoch=1, sequence=sequence, winner_entity_id=attacker, loser_entity_id=defender, outcome=outcome, gap=0.0))
        await session.flush()
        builder = BookBuilder(session, Rules())
        await builder.load_common()
        article = next(item for item in await builder.wars() if item.war.id == war.id)
    assert article.fought == 1 and len(article.battles) == 3
