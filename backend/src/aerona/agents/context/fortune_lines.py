from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import MishapRow
from aerona.db.tables.fortune import FortuneProfileRow

RECENT = 3
FEW = 4


def believed(fortune: int) -> str:
    if fortune >= 30:
        return "things have been going your way"
    if fortune <= -30:
        return "luck has been against you"
    return "your luck runs as it runs for anyone"


async def mortal_fortune_lines(scope: Scope, me: EntityRow) -> list[str]:
    profile = await scope.session.get(FortuneProfileRow, me.id)
    found = [believed(profile.fortune if profile is not None else 0)]
    epoch = profile.updated_epoch if profile is not None else 0
    rows = await scope.session.scalars(
        select(MishapRow).where(MishapRow.settlement_entity_id == me.location_id, MishapRow.epoch >= epoch - RECENT).order_by(MishapRow.id.desc()).limit(FEW)
    )
    for row in rows:
        who = "you" if row.victim_node_id == me.id else "someone near you"
        found.append(f"lately {who} suffered {an(spoken(row.kind))}{', and it took a life' if row.died else ''}")
    return found
