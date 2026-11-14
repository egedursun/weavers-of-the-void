from sqlalchemy import func, select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.core.grammar import agree, several
from aerona.db.tables.belonging import HeldIdentityRow, PeerGroupRow, PeerMemberRow, SanctuaryRow, SatireRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.belonging.refuge import OPEN_STATES, refuge_of
from aerona.engine.cycles.book import realm_of

LIST_LINES = 3
RECENT = 1


async def identity_lines(scope: Scope, holder_id: int) -> list[str]:
    rows = await scope.session.scalars(
        select(HeldIdentityRow)
        .where(HeldIdentityRow.holder_entity_id == holder_id, (HeldIdentityRow.value_node_id.is_not(None)) | (HeldIdentityRow.value_label.is_not(None)))
        .order_by(HeldIdentityRow.salience.desc(), HeldIdentityRow.layer)
        .limit(LIST_LINES)
    )
    found = []
    for row in rows:
        value = await named(scope, row.value_node_id) if row.value_node_id is not None else words(row.value_label or "")
        found.append(f"your {row.layer.value} ({value}) matters {row.salience} out of 100 to you")
    return found


async def mortal_belonging_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found = await identity_lines(scope, me.id)
    group = await session.scalar(
        select(PeerGroupRow).join(PeerMemberRow, PeerMemberRow.group_id == PeerGroupRow.id).where(PeerMemberRow.mortal_entity_id == me.id).limit(1)
    )
    if group is not None:
        friends = list(
            await session.scalars(
                select(PeerMemberRow.mortal_entity_id)
                .where(PeerMemberRow.group_id == group.id, PeerMemberRow.mortal_entity_id != me.id)
                .order_by(PeerMemberRow.mortal_entity_id)
                .limit(LIST_LINES)
            )
        )
        playmates = ", ".join([await named(scope, friend) for friend in friends]) or "no one named"
        found.append(
            f"you play {words(group.play.value).lower()} with the children of your town ({playmates}){'; there is no time to play' if group.deprived else ''}"
        )
    refuge = await refuge_of(session, me.id)
    if refuge is not None:
        found.append(f"you shelter in {await named(scope, refuge.host_entity_id)} ({words(refuge.state.value).lower()})")
    jester = await session.scalar(select(OfficeRow.polity_entity_id).where(OfficeRow.kind == OfficeKind.JESTER, OfficeRow.holder_entity_id == me.id).limit(1))
    if jester is not None:
        found.append(f"you serve the court of {await named(scope, jester)} as its jester, licensed to mock its ruler")
    realm = await realm_of(session, me.location_id) if me.location_id is not None else None
    if realm is not None:
        mocked = await session.scalar(select(func.count(SatireRow.id)).where(SatireRow.polity_entity_id == realm, SatireRow.epoch >= scope.epoch - RECENT))
        if mocked:
            found.append(f"your ruler has been mocked {several(mocked, 'time', 'times')} of late")
    return found


async def son_belonging_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    session = scope.session
    lands = select(EntityRow.id).where(EntityRow.world_id == son.current_world_id)
    sheltered = await session.scalar(select(func.count(SanctuaryRow.id)).where(SanctuaryRow.host_entity_id.in_(lands), SanctuaryRow.state.in_(OPEN_STATES)))
    found = [f"{several(sheltered, 'fugitive', 'fugitives')} {agree(sheltered, 'is', 'are')} sheltered in sanctuary"] if sheltered else []
    for row in await session.scalars(
        select(HeldIdentityRow)
        .where(HeldIdentityRow.holder_entity_id.in_(lands), HeldIdentityRow.salience >= scope.rules.identities.fault_at)
        .order_by(HeldIdentityRow.salience.desc(), HeldIdentityRow.holder_entity_id)
        .limit(LIST_LINES)
    ):
        found.append(f"{await named(scope, row.holder_entity_id)} cares most about its {row.layer.value} ({row.salience} out of 100)")
    return found
