from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import several, spoken
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.mind import Profession
from aerona.engine.body.customs import people_of


async def mortal_dead_lines(scope: Scope, me: EntityRow) -> list[str]:
    people = await people_of(scope.session, me)
    if people is None:
        return []
    found: list[str] = []
    culture = await scope.session.get(PeopleCultureRow, people.id)
    if culture is not None:
        found.append(f"{await named(scope, people.id)} keep their dead by {spoken(culture.remains_treatment)} under the rite of {spoken(culture.funeral_rite)}")
    for row in await scope.session.scalars(select(DeathWorkRow).where(DeathWorkRow.people_entity_id == people.id).order_by(DeathWorkRow.id)):
        guild = f", kept by {await named(scope, row.guild_node_id)}" if row.guild_node_id is not None else ""
        found.append(
            f"the {spoken(row.role)} is {spoken(row.standing)}: purity {row.purity}, fee {row.fee}, {several(row.workers, 'worker', 'workers')}{guild}"
        )
    profile = await scope.session.get(MortalProfileRow, me.id)
    if profile is not None and profile.profession is Profession.DEATH_WORKER:
        found.append("you do the work of the dead")
    return found
