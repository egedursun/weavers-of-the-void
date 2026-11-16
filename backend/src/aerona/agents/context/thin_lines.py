from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.cosmography import CelestialReadingRow
from aerona.db.tables.culture import ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.folkways import BiasWeightRow, DietRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.thin_sections import ConstitutionRow, JourneyEncounterRow, RelationComponentRow
from aerona.domain.enums.culture import ProphecyState
from aerona.domain.enums.military import FeudStatus
from aerona.domain.enums.polity import OathStatus
from aerona.domain.enums.travel import JourneyStatus
from aerona.engine.body.customs import people_of
from aerona.engine.environment.knowledge import polity_of
from aerona.engine.folkways.biases import MIDDLE
from aerona.engine.sacred.places import town_of

LIST_LINES = 3
STRONG = 20


async def constitution_line(scope: Scope, polity_id: int | None) -> list[str]:
    row = await scope.session.get(ConstitutionRow, polity_id) if polity_id is not None else None
    if row is None:
        return []
    creed = f", written for {await named(scope, row.ideology_entity_id)}" if row.ideology_entity_id is not None else ""
    return [
        f"constitution of {await named(scope, polity_id)}: chosen by {words(row.selectorate.value)}, offices {row.offices}, rights {row.rights} of 100{creed}"
    ]


async def diet_lines(scope: Scope, town: EntityRow | None) -> list[str]:
    diet = await scope.session.get(DietRow, town.id) if town is not None else None
    if town is None or diet is None:
        return []
    leanest = await scope.session.scalar(select(WorldSeasonRow.growth).where(WorldSeasonRow.world_id == town.world_id).order_by(WorldSeasonRow.growth).limit(1))
    lean = f", leanest season growth {leanest} of 100" if leanest is not None else ""
    return [f"diet of {town.name}: energy {diet.energy}, fresh food {diet.fresh}, preserved food {diet.preserved}, minerals {diet.mineral}{lean}"]


async def bias_lines(scope: Scope, holder_id: int, whose: str) -> list[str]:
    found: list[str] = []
    for row in await scope.session.scalars(select(BiasWeightRow).where(BiasWeightRow.holder_node_id == holder_id).order_by(BiasWeightRow.bias)):
        if abs(row.weight - MIDDLE) >= STRONG:
            last = f", last bent a choice of {words(row.last_decision.value)} by {row.last_shift}" if row.last_decision is not None else ""
            found.append(f"{whose} bias {words(row.bias.value)}: {row.weight} of 100{last}")
    return found[: LIST_LINES * 2]


async def oath_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    sworn = select(OathRow).where(OathRow.swearer_entity_id == me.id, OathRow.status == OathStatus.SWORN).order_by(OathRow.id).limit(LIST_LINES)
    for oath in await scope.session.scalars(sworn):
        witness = f", witnessed by {await named(scope, oath.witness_node_id)}" if oath.witness_node_id is not None else ""
        penalty = f", penalty if broken: {words(oath.penalty.value)}" if oath.penalty is not None else ""
        found.append(f"your oath of {words(oath.kind.value)}{witness}{penalty}")
    return found


async def feud_lines(scope: Scope, sides: list[int]) -> list[str]:
    found: list[str] = []
    query = (
        select(FeudRow)
        .where(or_(FeudRow.first_entity_id.in_(sides), FeudRow.second_entity_id.in_(sides)), FeudRow.status == FeudStatus.ACTIVE)
        .order_by(FeudRow.intensity.desc(), FeudRow.id)
        .limit(LIST_LINES)
    )
    for row in await scope.session.scalars(query):
        mediator = f", mediator {await named(scope, row.mediator_node_id)}" if row.mediator_node_id is not None else ""
        pair = f"{await named(scope, row.first_entity_id)} and {await named(scope, row.second_entity_id)}"
        found.append(f"feud of {pair}: level {words(row.level.value)}, intensity {row.intensity}{mediator}")
    return found


async def prophecy_lines(scope: Scope, hearers: list[int]) -> list[str]:
    found: list[str] = []
    rows = await scope.session.scalars(
        select(ProphecyConditionRow).where(ProphecyConditionRow.state == ProphecyState.PENDING).order_by(ProphecyConditionRow.prophecy_entity_id)
    )
    for row in rows:
        if not set(row.audience) & set(hearers):
            continue
        rival = f", rival of {await named(scope, row.rival_entity_id)}" if row.rival_entity_id is not None else ""
        forged = ", forged" if row.forged else ""
        found.append(f"prophecy {await named(scope, row.prophecy_entity_id)}: retold {row.retold} times{forged}{rival}")
        if len(found) >= LIST_LINES:
            break
    return found


async def reading_lines(scope: Scope, people_id: int | None) -> list[str]:
    if people_id is None:
        return []
    found: list[str] = []
    rows = await scope.session.scalars(
        select(CelestialReadingRow).where(CelestialReadingRow.people_entity_id == people_id).order_by(CelestialReadingRow.celestial_entity_id).limit(LIST_LINES)
    )
    for row in rows:
        seen = "seen" if row.visible else "hidden from view"
        found.append(f"{await named(scope, row.celestial_entity_id)} in your sky: {seen}, read as {words(row.reading.value)}")
    return found


async def journey_lines(scope: Scope, traveller_ids: list[int]) -> list[str]:
    found: list[str] = []
    query = (
        select(JourneyRow)
        .where(JourneyRow.traveller_entity_id.in_(traveller_ids), JourneyRow.status == JourneyStatus.UNDERWAY)
        .order_by(JourneyRow.id)
        .limit(LIST_LINES)
    )
    for row in await scope.session.scalars(query):
        toll = f"supplies {row.supplies} of 100, born on the way {row.births}, died on the way {row.deaths}"
        found.append(f"journey {row.id} to {await named(scope, row.destination_world_id)}: {toll}")
    return found


async def encounter_lines(scope: Scope, world_id: int | None) -> list[str]:
    query = select(JourneyEncounterRow).where(or_(JourneyEncounterRow.world_id.is_(None), JourneyEncounterRow.world_id == world_id))
    rows = await scope.session.scalars(query.order_by(JourneyEncounterRow.weight.desc(), JourneyEncounterRow.id).limit(LIST_LINES))
    return [
        f"road encounter on {words(row.environment.value)} roads: {row.name or words(row.effect.value)}, weight {row.weight}, travellers lost {row.loss_pct}%"
        for row in rows
    ]


async def relation_part_lines(scope: Scope, community_id: int | None) -> list[str]:
    if community_id is None:
        return []
    query = select(RelationComponentRow).where(or_(RelationComponentRow.entity_a_id == community_id, RelationComponentRow.entity_b_id == community_id))
    rows = await scope.session.scalars(query.order_by(RelationComponentRow.value, RelationComponentRow.component).limit(LIST_LINES))
    found: list[str] = []
    for row in rows:
        other = row.entity_b_id if row.entity_a_id == community_id else row.entity_a_id
        found.append(f"relation with {await named(scope, other)}, part {words(row.component.value)}: {spoken(row)}")
    return found


async def mortal_thin_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await town_of(scope.session, me)
    folk = await people_of(scope.session, me)
    home = town.id if town is not None else None
    places = [node for node in (home, folk.id if folk is not None else None) if node is not None]
    return [
        *await diet_lines(scope, town),
        *await bias_lines(scope, me.id, "your"),
        *await oath_lines(scope, me),
        *await feud_lines(scope, places),
        *await prophecy_lines(scope, [me.id, *places]),
        *await reading_lines(scope, folk.id if folk is not None else None),
        *await journey_lines(scope, [me.id, *places]),
        *await constitution_line(scope, await polity_of(scope.session, home)),
        *await relation_part_lines(scope, home),
    ]


async def son_thin_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    realms = (
        select(ConstitutionRow.polity_entity_id)
        .join(EntityRow, EntityRow.id == ConstitutionRow.polity_entity_id)
        .where(EntityRow.world_id == son.current_world_id)
    )
    found: list[str] = []
    for polity_id in list(await scope.session.scalars(realms.order_by(ConstitutionRow.polity_entity_id).limit(LIST_LINES))):
        found.extend(await constitution_line(scope, polity_id))
    peoples = list(await scope.session.scalars(select(EntityRow.id).where(EntityRow.world_id == son.current_world_id).order_by(EntityRow.id)))
    found.extend(await feud_lines(scope, peoples))
    found.extend(await prophecy_lines(scope, peoples))
    found.extend(await encounter_lines(scope, son.current_world_id))
    return found
