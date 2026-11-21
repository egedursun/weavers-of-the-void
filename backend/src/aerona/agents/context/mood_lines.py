from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.engine.feeling_spread.moods import emotion_of


def described(row: FeelingSpreadRow) -> str:
    shown = [
        f"{spoken(feeling)} {strength}"
        for key, strength in sorted((row.feelings or {}).items(), key=lambda item: -item[1])
        if (feeling := emotion_of(key)) is not None
    ]
    return ", ".join(shown) or "calm"


async def mortal_mood_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    if me.location_id is not None:
        place = await session.scalar(select(FeelingSpreadRow).where(FeelingSpreadRow.settlement_entity_id == me.location_id).limit(1))
        if place is not None and place.feelings:
            found.append(f"the mood of the place you stand in: {described(place)}")
    household = await session.scalar(select(HouseholdMemberRow.household_id).where(HouseholdMemberRow.member_node_id == me.id).limit(1))
    if household is not None:
        home = await session.scalar(select(FeelingSpreadRow).where(FeelingSpreadRow.household_id == household).limit(1))
        if home is not None and home.feelings:
            found.append(f"the mood of your household (household {household}): {described(home)}")
    return found
