from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import FaithClimateRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.transform import TransformTrigger
from aerona.domain.models.entity_stats import CultStats, IdeologyStats
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.mythic.heroquests import renown_of
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import RecordSpec
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.renown.book import acclaim
from aerona.engine.services.war import ongoing_wars
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, bonds_from, end, make

Push = tuple[int, TransformTrigger]


async def adherents_of(ctx: TickContext, ideology_id: int) -> list[IdeologyAdherentRow]:
    statement = select(IdeologyAdherentRow).where(IdeologyAdherentRow.ideology_entity_id == ideology_id).order_by(IdeologyAdherentRow.adherent_entity_id)
    return list(await ctx.session.scalars(statement))


async def in_crisis(ctx: TickContext, community_id: int) -> bool:
    community = await ctx.session.get(EntityRow, community_id)
    if community is None or community.status is not EntityStatus.CANON:
        return False
    if stat_or(community, "prosperity", ctx.rules.society.default_stat) < ctx.rules.knowledge.dark_age_prosperity:
        return True
    return bool(await ongoing_wars(ctx.session, community.id))


async def sacralisation_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    found: dict[int, Push] = {}
    for ideology in await canon(ctx.session, [EntityType.IDEOLOGY]):
        profile = await ctx.session.get(IdeologyProfileRow, ideology.id)
        if profile is None or profile.founder_entity_id is None:
            continue
        if await renown_of(ctx, profile.founder_entity_id) < table.sacralisation_veneration:
            continue
        adherents = await adherents_of(ctx, ideology.id)
        for row in adherents:
            if await in_crisis(ctx, row.adherent_entity_id):
                found[ideology.id] = (PERCENT, TransformTrigger.ENGINE)
                break
    return found


async def ideology_check(ctx: TickContext, ideology_id: int) -> str | None:
    ideology = await ctx.session.get(EntityRow, ideology_id)
    if ideology is None or ideology.entity_type is not EntityType.IDEOLOGY or ideology.status is not EntityStatus.CANON:
        return "Only a living teaching can become a faith."
    return None


async def sacralise(ctx: TickContext, ideology_id: int, ledger: Ledger) -> int:
    ideology = await ctx.session.get_one(EntityRow, ideology_id)
    profile = await ctx.session.get(IdeologyProfileRow, ideology.id)
    adherents = await adherents_of(ctx, ideology.id)
    followers = sum(
        stat(community, "population") or 0 for community in [await ctx.session.get(EntityRow, row.adherent_entity_id) for row in adherents] if community
    )
    cult = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=await NameRepository(ctx.session).unique_name(f"Faith of {ideology.name}"),
            body=f"The teaching {ideology.name}, worshipped by those who held to it.",
            stats=CultStats(followers=max(1, followers), zeal=PERCENT // 2, influence=clamp_percent(stat_or(ideology, "appeal", PERCENT // 2))),
            power=ideology.power_level,
            world_id=ideology.world_id,
            location_id=ideology.location_id,
        ),
    )
    founder = await ctx.session.get(EntityRow, profile.founder_entity_id) if profile is not None and profile.founder_entity_id is not None else None
    if founder is not None:
        await bind(ctx, ledger, (cult.id, founder.id, BondKind.WORSHIPS), f"{founder.name}, the venerated founder")
    for row in adherents:
        await bind(ctx, ledger, (row.adherent_entity_id, cult.id, BondKind.MEMBER_OF), f"once held to {ideology.name}")
    await bind(ctx, ledger, (cult.id, ideology.id, BondKind.DESCENDS_FROM), f"grew out of the teaching {ideology.name}")
    end(ctx, ledger, ideology, EntityStatus.DESTROYED)
    return cult.id


async def secular_pull(ctx: TickContext, town_ids: list[int]) -> int:
    if not town_ids:
        return 0
    rows = list(await ctx.session.scalars(select(FaithClimateRow).where(FaithClimateRow.community_entity_id.in_(town_ids))))
    if not rows:
        return 0
    pulls = [-(row.literacy_pull + row.science_pull + row.prosperity_pull + row.city_pull + row.silence_pull) for row in rows]
    return sum(pulls) // len(pulls)


async def secularisation_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    book = await FaithBook.load(ctx.session)
    found: dict[int, Push] = {}
    for cult_id, church in sorted(book.churches.items()):
        towns = [member.id for member in church.members if member.entity_type is EntityType.SETTLEMENT]
        pull = await secular_pull(ctx, towns)
        if pull > 0:
            found[cult_id] = (clamp_percent(pull * PERCENT // table.secularisation_pressure), TransformTrigger.ENGINE)
    return found


async def cult_check(ctx: TickContext, cult_id: int) -> str | None:
    cult = await ctx.session.get(EntityRow, cult_id)
    if cult is None or cult.entity_type is not EntityType.CULT or cult.status is not EntityStatus.CANON:
        return "Only a living faith can let go of its worship."
    return None


async def secularise(ctx: TickContext, cult_id: int, ledger: Ledger) -> int:
    cult = await ctx.session.get_one(EntityRow, cult_id)
    church = (await FaithBook.load(ctx.session)).churches.get(cult.id)
    members = church.members if church is not None else []
    ideology = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.IDEOLOGY,
            name=await NameRepository(ctx.session).unique_name(f"Teaching of {cult.name}"),
            body=f"The teachings of {cult.name}, kept after its worship was let go.",
            stats=IdeologyStats(adherents=len(members), appeal=clamp_percent(stat_or(cult, "influence", PERCENT // 2))),
            power=cult.power_level,
            world_id=cult.world_id,
            location_id=cult.location_id,
        ),
    )
    profile = IdeologyProfileRow(
        ideology_entity_id=ideology.id, value_delta={}, tenets=[], founder_entity_id=None, appeal={}, texts=[], updated_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(profile)
    await ctx.session.flush()
    ledger.added(profile)
    for member in members:
        row = IdeologyAdherentRow(
            ideology_entity_id=ideology.id,
            adherent_entity_id=member.id,
            strength=clamp_percent(stat_or(cult, "zeal", PERCENT // 2)),
            state=False,
            since_epoch=ctx.epoch,
        )
        ctx.session.add(row)
        await ctx.session.flush()
        ledger.added(row)
    loss = ctx.rules.transform.secularisation_pressure
    for bond in await bonds_from(ctx, cult.id, (BondKind.WORSHIPS,)):
        for member in members:
            await acclaim(ctx.session, bond.target_node_id, member.id, ReputationAxis.PIETY, amount=-loss / len(members), epoch=ctx.epoch)
    await bind(ctx, ledger, (ideology.id, cult.id, BondKind.DESCENDS_FROM), f"the teachings of {cult.name}")
    end(ctx, ledger, cult, EntityStatus.DESTROYED)
    return ideology.id
