from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.concealment import HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.powers import GiftedAttitudeRow, MagicSystemRow, PowerRegistryRow, PowerRow, PowerSourceRow, SourceDensityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import PowerState
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas

LIST_LINES = 4
GONE = (PowerState.LOST,)


async def own_power_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    powers = select(PowerRow).where(PowerRow.holder_node_id == me.id, PowerRow.state.not_in(list(GONE))).order_by(PowerRow.id).limit(LIST_LINES)
    for power in await scope.session.scalars(powers):
        found.append(
            f"you hold a power (power {power.id}) to {spoken(power.technique)} {spoken(power.form)}: strength {power.strength}, "
            f"control {power.control}, {spoken(power.state)}, strain {power.strain} of {power.strain_cap}"
        )
    registered = await scope.session.scalar(select(PowerRegistryRow).where(PowerRegistryRow.holder_node_id == me.id).limit(1))
    if registered is not None:
        terms = ", ".join(term for term, on in (("licensed", registered.licensed), ("called to serve in war", registered.conscripted)) if on)
        found.append(f"registered with {await named(scope, registered.polity_entity_id)}{', ' + terms if terms else ''}")
    if me.location_id is not None:
        level = await law_param(scope.session, me.location_id, LawKind.POWER_LAW, "level")
        if level is not None:
            found.append(f"here those with powers are {spoken(str(level))}")
    return found


async def land_lines(scope: Scope, me: EntityRow) -> list[str]:
    atlas = await RegionAtlas.load(scope.session)
    region = atlas.top_region(me.id)
    if region is None:
        return []
    found: list[str] = []
    rows = await scope.session.execute(
        select(SourceDensityRow, PowerSourceRow)
        .join(PowerSourceRow, PowerSourceRow.id == SourceDensityRow.source_id)
        .where(SourceDensityRow.region_entity_id == region)
        .order_by(SourceDensityRow.density.desc())
        .limit(LIST_LINES)
    )
    for density, source in rows.all():
        thin = ", run thin" if density.depleted else ""
        found.append(f"the source {source.name} (source {source.id}) is drawn from {spoken(source.drawn_from)} here at density {density.density}{thin}")
    return found


async def truth_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    kept = select(TruthKeeperRow.truth_id).where(TruthKeeperRow.keeper_node_id == me.id)
    sought = select(TruthSeekerRow.truth_id).where(TruthSeekerRow.seeker_node_id == me.id)
    heard = select(PublicKnowledgeRow.truth_id).where(PublicKnowledgeRow.population_node_id == me.location_id, PublicKnowledgeRow.know_pct > 0)
    truths = select(HiddenTruthRow).where(
        or_(HiddenTruthRow.id.in_(kept), HiddenTruthRow.id.in_(sought), HiddenTruthRow.id.in_(heard), HiddenTruthRow.subject_node_id == me.id)
    )
    for truth in await scope.session.scalars(truths.order_by(HiddenTruthRow.id).limit(LIST_LINES)):
        role = "you keep" if truth.id in set(await scope.session.scalars(kept)) else "you know of"
        found.append(f"{role} a hidden truth (truth {truth.id}): {truth.title}, about {await named(scope, truth.subject_node_id)}, strength {truth.strength}")
    return found


async def mortal_power_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await own_power_lines(scope, me), *await land_lines(scope, me), *await truth_lines(scope, me)]


async def son_power_lines(scope: Scope, son: SonRow) -> list[str]:
    world = son.current_world_id
    if world is None:
        return []
    session = scope.session
    found: list[str] = []
    for system in await session.scalars(select(MagicSystemRow).where(MagicSystemRow.scope_node_id == world).order_by(MagicSystemRow.id).limit(LIST_LINES)):
        found.append(
            f"a system of power, {system.name} (system {system.id}): {spoken(system.structure)}, "
            f"predictability {system.predictability}, prevalence {system.prevalence}"
        )
    granted = select(PowerRow).where(PowerRow.granted_by_node_id == son.id, PowerRow.state.not_in(list(GONE))).order_by(PowerRow.id).limit(LIST_LINES)
    for power in await session.scalars(granted):
        found.append(f"you granted {await named(scope, power.holder_node_id)} a power (power {power.id}) to {spoken(power.technique)} {spoken(power.form)}")
    in_world = select(EntityRow.id).where(EntityRow.world_id == world, EntityRow.status == EntityStatus.CANON)
    truths = select(HiddenTruthRow).where(HiddenTruthRow.subject_node_id.in_(in_world), HiddenTruthRow.revealed.is_(False))
    for truth in await session.scalars(truths.order_by(HiddenTruthRow.id).limit(LIST_LINES)):
        found.append(f"a truth is hidden (truth {truth.id}): {truth.title}, about {await named(scope, truth.subject_node_id)}")
    attitudes = select(GiftedAttitudeRow).where(GiftedAttitudeRow.people_entity_id.in_(in_world)).order_by(GiftedAttitudeRow.people_entity_id)
    for row in await session.scalars(attitudes.limit(LIST_LINES)):
        found.append(f"{await named(scope, row.people_entity_id)} hold the gifted {spoken(row.attitude)}")
    return found
