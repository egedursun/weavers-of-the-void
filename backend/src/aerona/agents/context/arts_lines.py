from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.catalog.life.agents import OPEN
from aerona.core.grammar import several
from aerona.db.tables.arts import ArtPriceRow, ClubRow, CollectorRow, ForgeryRow
from aerona.db.tables.constructs import ConstructRow, InstructionSetRow, RemadeRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.sacred import BirthSignRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.arts import ForgeryStatus
from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.sacred.places import town_of

LIST_LINES = 3


async def work_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    collector = await session.get(CollectorRow, me.id)
    if collector is not None:
        found.append(f"you deal in works as {words(collector.role.value)}, with an eye of {collector.connoisseurship}")
    for profile, price in await session.execute(
        select(ArtworkProfileRow, ArtPriceRow)
        .join(ArtPriceRow, ArtPriceRow.artwork_entity_id == ArtworkProfileRow.artwork_entity_id)
        .where(ArtworkProfileRow.author_entity_id == me.id)
        .order_by(ArtPriceRow.price.desc())
        .limit(LIST_LINES)
    ):
        found.append(f"your work {await named(scope, profile.artwork_entity_id)} (work {profile.artwork_entity_id}) is valued at {price.price}")
    for row in await session.scalars(
        select(ForgeryRow).where(ForgeryRow.forger_entity_id == me.id, ForgeryRow.status == ForgeryStatus.HIDDEN).order_by(ForgeryRow.id).limit(LIST_LINES)
    ):
        found.append(f"your forgery of {await named(scope, row.original_entity_id)} still passes for the real thing")
    return found


async def body_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    remade = await session.get(RemadeRow, me.id)
    if remade is not None:
        taken = words(remade.lost_function.value) if remade.lost_function is not None else "nothing"
        given = words(remade.forced_function.value) if remade.forced_function is not None else "nothing"
        found.append(f"the law remade your body: it took your {taken} and forced {given} on you; grievance {remade.grievance}")
    sign = await session.get(BirthSignRow, me.id)
    if sign is not None:
        ruler = await named(scope, sign.ruling_celestial_entity_id) if sign.ruling_celestial_entity_id is not None else "no body of the sky"
        dread = "a dreaded sign" if sign.dreaded else "an ordinary sign"
        found.append(f"you were born under {dread} ruled by {ruler}, {words(sign.influence.value)}, fortune {sign.fortune}")
    for rules, body in await session.execute(
        select(InstructionSetRow, EntityRow)
        .join(EntityRow, EntityRow.id == InstructionSetRow.owner_entity_id)
        .where(InstructionSetRow.holder_node_id == me.id, EntityRow.status == EntityStatus.CANON)
        .order_by(InstructionSetRow.id)
        .limit(LIST_LINES)
    ):
        construct = await session.get(ConstructRow, body.id)
        mind = await session.get(MindProfileRow, body.id)
        will = words(mind.will.value) if mind is not None else "unknown"
        state = f": power {construct.power}, decay {construct.decay}, will {will}" if construct is not None else ""
        found.append(f"{body.name} (construct {body.id}) answers you through its {words(rules.command_token.value)}{state}")
    return found


async def hunt_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for row in await session.scalars(
        select(MonsterContractRow).where(MonsterContractRow.hunter_entity_id == me.id, MonsterContractRow.status == ContractStatus.TAKEN).limit(LIST_LINES)
    ):
        found.append(f"you hunt {await named(scope, row.beast_entity_id)} for a bounty of {row.bounty}; your study of it stands at {row.study}")
    for row, beast in await session.execute(
        select(MonsterContractRow, EntityRow)
        .join(EntityRow, EntityRow.id == MonsterContractRow.beast_entity_id)
        .where(MonsterContractRow.status == ContractStatus.POSTED, EntityRow.world_id == me.world_id)
        .order_by(MonsterContractRow.bounty.desc(), MonsterContractRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"contract {row.id}: {await named(scope, row.community_entity_id)} offers {row.bounty} for {beast.name}")
    return found


async def club_lines(scope: Scope, town: EntityRow) -> list[str]:
    found: list[str] = []
    for club, profile in await scope.session.execute(
        select(ClubRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == ClubRow.faction_entity_id)
        .where(FactionProfileRow.home_entity_id == town.id)
        .order_by(ClubRow.fandom.desc())
        .limit(LIST_LINES)
    ):
        line = f", its fans split by {words(club.line.value)}" if club.line.value != "none" else ""
        wins_counted = several(club.wins, "win", "wins")
        losses_counted = several(club.losses, "loss", "losses")
        found.append(f"{await named(scope, profile.faction_entity_id)} plays in your town: {wins_counted}, {losses_counted}, fandom {club.fandom}{line}")
    return found


async def mortal_arts_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await town_of(scope.session, me)
    return [
        *await work_lines(scope, me),
        *await body_lines(scope, me),
        *await hunt_lines(scope, me),
        *(await club_lines(scope, town) if town is not None else []),
    ]


async def son_arts_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    if son.current_world_id is None:
        return found
    world = son.current_world_id
    for construct, body in await session.execute(
        select(ConstructRow, EntityRow)
        .join(EntityRow, EntityRow.id == ConstructRow.entity_id)
        .where(EntityRow.world_id == world, EntityRow.status == EntityStatus.CANON)
        .order_by(ConstructRow.power.desc())
        .limit(LIST_LINES)
    ):
        mind = await session.get(MindProfileRow, body.id)
        will = words(mind.will.value) if mind is not None else "unknown"
        found.append(f"{body.name} (construct {body.id}): power {construct.power}, decay {construct.decay}, will {will}")
    for row, beast in await session.execute(
        select(MonsterContractRow, EntityRow)
        .join(EntityRow, EntityRow.id == MonsterContractRow.beast_entity_id)
        .where(EntityRow.world_id == world, MonsterContractRow.status.in_(OPEN))
        .order_by(MonsterContractRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"a bounty of {several(row.bounty, 'stand', 'stands')} on {beast.name} ({words(row.status.value)})")
    hidden = list(
        await session.execute(
            select(ForgeryRow, EntityRow)
            .join(EntityRow, EntityRow.id == ForgeryRow.item_entity_id)
            .where(EntityRow.world_id == world, ForgeryRow.status == ForgeryStatus.HIDDEN)
            .order_by(ForgeryRow.id)
            .limit(LIST_LINES)
        )
    )
    for forgery, item in hidden:
        found.append(f"forgery {forgery.id}: {item.name} passes for the real thing")
    return found
