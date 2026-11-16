from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.made import (
    AugmentRow,
    InformationTrustRow,
    MadeRealmRow,
    MadeRelicRow,
    ReplicatorLineRow,
    ReplicatorPresenceRow,
    SalvageSiteRow,
)
from aerona.db.tables.minds import MindLawRow, MindProfileRow, MindStateRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.made import ReplicatorStage
from aerona.domain.enums.minds import MindOrigin, MindSeat
from aerona.engine.networks.book import running
from aerona.engine.sacred.places import town_of

LIST_LINES = 3
LOW_TRUST = 30
PLAIN_SEATS = frozenset({MindSeat.BODY, MindSeat.NONE})
WILLED = (MindWill.FULL, MindWill.EXCEEDING)
LIVE_LINES = (ReplicatorStage.WORKING, ReplicatorStage.SPREADING, ReplicatorStage.RUNAWAY)
CARRIES = ("messages", "records", "control", "money", "minds", "opinion")


async def own_mind_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    mind = await scope.session.get(MindProfileRow, me.id)
    if mind is not None and (mind.seat not in PLAIN_SEATS or mind.origin is not MindOrigin.BORN or mind.dormant):
        place = f" in {await named(scope, mind.seat_node_id)}" if mind.seat_node_id not in {None, me.id} else ""
        found.append(f"your mind runs {words(mind.seat.value)}{place}, {words(mind.origin.value)}, will {words(mind.will.value)}, stability {mind.stability}")
    for state in await scope.session.scalars(
        select(MindStateRow).where(MindStateRow.owner_node_id == me.id).order_by(MindStateRow.id.desc()).limit(LIST_LINES)
    ):
        found.append(f"you hold a saved mind of {await named(scope, state.mind_node_id)} from epoch {state.taken_epoch} (state {state.id})")
    made = select(MindProfileRow).where(MindProfileRow.made_by_node_id == me.id).order_by(MindProfileRow.node_id).limit(LIST_LINES)
    for row in await scope.session.scalars(made):
        found.append(
            f"you made the mind of {await named(scope, row.node_id)} (mind {row.node_id}): will {words(row.will.value)}, bond with you {row.maker_bond}"
        )
    for augment in await scope.session.scalars(select(AugmentRow).where(AugmentRow.bearer_node_id == me.id).order_by(AugmentRow.id).limit(LIST_LINES)):
        found.append(f"you bear an augment (augment {augment.id}): {words(augment.kind.value)}, integration {augment.integration}, strain {augment.strain}")
    shares = select(CompanyShareRow).where(CompanyShareRow.holder_node_id == me.id).order_by(CompanyShareRow.company_entity_id).limit(LIST_LINES)
    for share in await scope.session.scalars(shares):
        found.append(f"you hold {share.share} of 100 parts of {await named(scope, share.company_entity_id)} (company {share.company_entity_id})")
    return found


async def home_lines(scope: Scope, town: EntityRow) -> list[str]:
    found: list[str] = []
    joined = select(NetworkProfileRow).join(NetworkNodeRow, NetworkNodeRow.network_entity_id == NetworkProfileRow.network_entity_id)
    for network in await scope.session.scalars(
        joined.where(NetworkNodeRow.member_node_id == town.id).order_by(NetworkProfileRow.network_entity_id).limit(LIST_LINES)
    ):
        carried = [item for item in CARRIES if getattr(network, f"carries_{item}")]
        state = "running" if running(network, scope.epoch) else f"down until epoch {network.down_until_epoch}"
        found.append(
            f"your home is on {await named(scope, network.network_entity_id)} (network {network.network_entity_id}), "
            f"carrying {', '.join(carried) or 'nothing'}; {state}"
        )
    trust = await scope.session.get(InformationTrustRow, town.id)
    if trust is not None and trust.information_trust < LOW_TRUST:
        found.append(f"few in your home trust what is written: trust {trust.information_trust}")
    things = select(EntityRow.id).where(EntityRow.location_id == town.id)
    for relic in await scope.session.scalars(
        select(MadeRelicRow).where(MadeRelicRow.thing_node_id.in_(things), MadeRelicRow.is_relic.is_(True)).limit(LIST_LINES)
    ):
        found.append(
            f"{await named(scope, relic.thing_node_id)} (relic {relic.thing_node_id}) is a relic of a lost making, "
            f"{words(relic.function_state.value)}, understood {relic.understood_pct}"
        )
    for site in await scope.session.scalars(
        select(SalvageSiteRow).where(SalvageSiteRow.site_entity_id.in_(things), SalvageSiteRow.yield_left > 0).limit(LIST_LINES)
    ):
        found.append(f"{await named(scope, site.site_entity_id)} (site {site.site_entity_id}) can still be salvaged")
    if town.location_id is not None:
        here = select(ReplicatorPresenceRow.line_id).where(ReplicatorPresenceRow.place_node_id == town.location_id)
        for line in await scope.session.scalars(
            select(ReplicatorLineRow).where(ReplicatorLineRow.id.in_(here), ReplicatorLineRow.stage.in_(LIVE_LINES)).limit(LIST_LINES)
        ):
            found.append(f"a self-making line, {line.name} (line {line.id}), is {words(line.stage.value)} in your land, containment {line.containment}")
    kept = select(MadeRealmRow).where(MadeRealmRow.host_node_id == town.id).limit(LIST_LINES)
    for realm in await scope.session.scalars(kept):
        found.append(f"a made realm (realm {realm.dimension_id}) runs on your home for {words(realm.realm_purpose.value)}{', sealed' if realm.sealed else ''}")
    return found


async def mortal_minds_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await town_of(scope.session, me)
    return [*await own_mind_lines(scope, me), *(await home_lines(scope, town) if town is not None else [])]


async def son_minds_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    world = son.current_world_id
    if world is None:
        return []
    found: list[str] = []
    law = await session.get(MindLawRow, world)
    if law is not None:
        found.append(
            f"on this world made minds may have {words(law.made_minds.value)}, their souls are {words(law.made_mind_souls.value)}, "
            f"and a soul on copying {words(law.soul_continuity.value)}"
        )
    willed = (
        select(MindProfileRow)
        .join(EntityRow, EntityRow.id == MindProfileRow.node_id)
        .where(
            EntityRow.world_id == world, EntityRow.status == EntityStatus.CANON, MindProfileRow.made_by_node_id.is_not(None), MindProfileRow.will.in_(WILLED)
        )
        .order_by(MindProfileRow.node_id)
        .limit(LIST_LINES)
    )
    for row in await session.scalars(willed):
        found.append(
            f"the made mind of {await named(scope, row.node_id)} (mind {row.node_id}) has {words(row.will.value)} will, bond with its maker {row.maker_bond}"
        )
    networks = select(NetworkProfileRow).join(EntityRow, EntityRow.id == NetworkProfileRow.network_entity_id).where(EntityRow.world_id == world)
    for network in await session.scalars(networks.order_by(NetworkProfileRow.capacity.desc()).limit(LIST_LINES)):
        state = "running" if running(network, scope.epoch) else "down"
        found.append(f"{await named(scope, network.network_entity_id)} (network {network.network_entity_id}) is {state}, capacity {network.capacity}")
    lines = select(ReplicatorLineRow).where(ReplicatorLineRow.stage.in_((ReplicatorStage.SPREADING, ReplicatorStage.RUNAWAY))).order_by(ReplicatorLineRow.id)
    for line in await session.scalars(lines.limit(LIST_LINES)):
        found.append(f"the self-making line {line.name} (line {line.id}) is {words(line.stage.value)}, containment {line.containment}")
    return found
