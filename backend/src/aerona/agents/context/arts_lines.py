from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.catalog.life.agents import OPEN
from aerona.catalog.market_kinds import CLUBS, FORGERIES, ROLES, WAYS
from aerona.catalog.orders import ORDER_CONDITIONS, ORDER_TIMES
from aerona.core.grammar import several, spoken
from aerona.db.tables.arts import ArtPriceRow, ClubRow, CollectorRow, ForgeryRow, MatchRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow, RemadeRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.crafts import IncorporealRightRow
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
        found.append(f"you work in the art market as {ROLES[collector.role].label.lower()}, with an eye of {collector.connoisseurship}")
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
        found.append(f"your forgery of {await named(scope, row.original_entity_id)} ({FORGERIES[row.kind].label.lower()}) still passes for the real thing")
    for right in await session.scalars(
        select(IncorporealRightRow).where(IncorporealRightRow.holder_node_id == me.id).order_by(IncorporealRightRow.id).limit(LIST_LINES)
    ):
        found.append(f"you hold the right to {right.name} ({spoken(right.kind)}), gained as {WAYS[right.acquired].label.lower()}")
    return found


async def body_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    remade = await session.get(RemadeRow, me.id)
    if remade is not None:
        taken = spoken(remade.lost_function) if remade.lost_function is not None else "nothing"
        given = spoken(remade.forced_function) if remade.forced_function is not None else "nothing"
        found.append(f"the law remade your body: it took your {taken} and forced {given} on you; grievance {remade.grievance}")
    sign = await session.get(BirthSignRow, me.id)
    if sign is not None:
        ruler = await named(scope, sign.ruling_celestial_entity_id) if sign.ruling_celestial_entity_id is not None else "no body of the sky"
        dread = "a dreaded sign" if sign.dreaded else "an ordinary sign"
        found.append(f"you were born under {dread} ruled by {ruler}, {spoken(sign.influence)}, fortune {sign.fortune}")
    for rules, body in await session.execute(
        select(InstructionSetRow, EntityRow)
        .join(EntityRow, EntityRow.id == InstructionSetRow.owner_entity_id)
        .where(InstructionSetRow.holder_node_id == me.id, EntityRow.status == EntityStatus.CANON)
        .order_by(InstructionSetRow.id)
        .limit(LIST_LINES)
    ):
        construct = await session.get(ConstructRow, body.id)
        mind = await session.get(MindProfileRow, body.id)
        will = spoken(mind.will) if mind is not None else "unknown"
        state = f": power {construct.power}, decay {construct.decay}, will {will}" if construct is not None else ""
        orders = await session.scalars(
            select(InstructionOrderRow)
            .where(InstructionOrderRow.set_id == rules.id, InstructionOrderRow.lapsed.is_(False))
            .order_by(InstructionOrderRow.priority)
        )
        kept = "; ".join(
            f"{spoken(order.kind)} {ORDER_CONDITIONS[order.condition].label.lower()}"
            + (f" {ORDER_TIMES[order.times].label.lower()}" if order.times is not None else "")
            for order in orders
        )
        orders_line = f"; its orders: {kept}" if kept else ""
        found.append(f"{body.name} (construct {body.id}) answers you through its {spoken(rules.command_token)}{state}{orders_line}")
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
        line = f", its fans split by {spoken(club.line)}" if club.line.value != "none" else ""
        wins_counted = several(club.wins, "win", "wins")
        losses_counted = several(club.losses, "loss", "losses")
        kind = CLUBS[club.kind].label.lower()
        found.append(
            f"{await named(scope, profile.faction_entity_id)} ({kind}) plays in your town: {wins_counted}, {losses_counted}, fandom {club.fandom}{line}"
        )
        exposed = await scope.session.scalar(
            select(MatchRow.id)
            .where(MatchRow.fixing_exposed.is_(True), (MatchRow.home_entity_id == club.faction_entity_id) | (MatchRow.away_entity_id == club.faction_entity_id))
            .limit(1)
        )
        if exposed is not None:
            found.append(f"{await named(scope, profile.faction_entity_id)} is suspected of fixed contests")
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
        will = spoken(mind.will) if mind is not None else "unknown"
        found.append(f"{body.name} (construct {body.id}): power {construct.power}, decay {construct.decay}, will {will}")
    for row, beast in await session.execute(
        select(MonsterContractRow, EntityRow)
        .join(EntityRow, EntityRow.id == MonsterContractRow.beast_entity_id)
        .where(EntityRow.world_id == world, MonsterContractRow.status.in_(OPEN))
        .order_by(MonsterContractRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"a bounty of {several(row.bounty, 'stand', 'stands')} on {beast.name} ({spoken(row.status)})")
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
