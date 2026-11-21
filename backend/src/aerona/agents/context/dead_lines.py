from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import several, spoken
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.mind import Profession
from aerona.engine.body.customs import people_of
from aerona.engine.mortal.kin import close_kin_of


async def grave_lines(scope: Scope, me: EntityRow) -> list[str]:
    kin = await close_kin_of(scope.session, me.id)
    here = select(EntityRow.id).where(EntityRow.location_id == me.location_id) if me.location_id is not None else None
    near = GraveGoodsRow.dead_entity_id.in_(kin) if here is None else GraveGoodsRow.dead_entity_id.in_(kin) | GraveGoodsRow.dead_entity_id.in_(here)
    query = select(GraveGoodsRow).where(near, GraveGoodsRow.robbed_epoch.is_(None), GraveGoodsRow.found_epoch.is_(None)).order_by(GraveGoodsRow.id)
    found: list[str] = []
    for row in await scope.session.scalars(query):
        own = " (your kin)" if row.dead_entity_id in kin else ""
        things = several(len(row.items or []), "thing", "things")
        found.append(f"grave {row.id} of {await named(scope, row.dead_entity_id)}{own}: goods worth {row.goods_value} and {things}, kept {spoken(row.guard)}")
    return found


async def mortal_dead_lines(scope: Scope, me: EntityRow) -> list[str]:
    people = await people_of(scope.session, me)
    found: list[str] = await grave_lines(scope, me)
    if people is None:
        return found
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
