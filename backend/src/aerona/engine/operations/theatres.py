from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CampaignFrontRow
from aerona.db.tables.operations import TheatreRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.military.units import regrow, stacks_of, sync
from aerona.engine.mind.book import skill_level
from aerona.engine.notes import note
from aerona.engine.operations.fields import keep
from aerona.engine.operations.supply import train_of
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.relations.persuasion import office_holder
from aerona.engine.services.war import OngoingWar, ongoing_wars


@dataclass
class TheatreTally:
    theatres: int = 0
    misjudged: int = 0
    reinforced: int = 0


async def war_soldiers(ctx: TickContext, war_id: int, owner_id: int) -> tuple[int, list[ArmyRow]]:
    rows = list(
        await ctx.session.scalars(
            select(ArmyRow).where(ArmyRow.war_id == war_id, ArmyRow.owner_entity_id == owner_id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)
        )
    )
    total = 0
    for row in rows:
        army = await ctx.session.get(EntityRow, row.entity_id)
        total += stat_or(army, "size", 0) if army is not None else 0
    return total, rows


async def front_of(ctx: TickContext, item: OngoingWar, enemy_id: int, atlas: RegionAtlas) -> int | None:
    front = await ctx.session.scalar(
        select(CampaignFrontRow.first_region_id).where(CampaignFrontRow.war_id == item.war.id).order_by(CampaignFrontRow.last_epoch.desc()).limit(1)
    )
    return int(front) if front is not None else atlas.top_region(enemy_id)


async def theatre_of(ctx: TickContext, owner_id: int, war_id: int) -> TheatreRow:
    row = await ctx.session.scalar(select(TheatreRow).where(TheatreRow.owner_entity_id == owner_id, TheatreRow.war_id == war_id))
    if row is None:
        row = TheatreRow(owner_entity_id=owner_id, war_id=war_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def allocate(ctx: TickContext, owner: EntityRow, wars: list[OngoingWar], atlas: RegionAtlas, tally: TheatreTally) -> None:
    table = ctx.rules.theatres
    marshal = await office_holder(ctx.session, owner.id, OfficeKind.MARSHAL, OfficeKind.RULER)
    strategy = await skill_level(ctx.session, marshal, SkillKind.STRATEGY) if marshal is not None else 0
    error = table.error_pct * max(0, PERCENT - strategy) // PERCENT
    rows: list[tuple[TheatreRow, list[ArmyRow]]] = []
    for item in wars:
        enemy_id = item.defender_id if item.attacker_id == owner.id else item.attacker_id
        mine, armies = await war_soldiers(ctx, item.war.id, owner.id)
        theirs, _ = await war_soldiers(ctx, item.war.id, enemy_id)
        row = await theatre_of(ctx, owner.id, item.war.id)
        true = clamp_int(theirs * PERCENT // max(1, mine + theirs), 0, PERCENT)
        drift = ctx.rng(f"theatre.{owner.id}.{item.war.id}.{ctx.epoch}").integer(-error, error)
        keep(row, "front_region_entity_id", await front_of(ctx, item, enemy_id, atlas))
        keep(row, "marshal_entity_id", marshal)
        keep(row, "true_threat", true)
        keep(row, "believed_threat", clamp_int(true + drift, 0, PERCENT))
        keep(row, "misjudged", abs(row.believed_threat - row.true_threat) >= table.misjudge_gap)
        row.updated_epoch = ctx.epoch
        rows.append((row, armies))
        tally.theatres += 1
        tally.misjudged += row.misjudged
    believed = sum(row.believed_threat + 1 for row, _ in rows)
    folk = await folk_of(ctx, owner)
    people = sum(stat_or(item, "population", 0) for item in folk)
    reserves = people * table.reserve_per_thousand // 1000
    levies = people * table.levy_per_thousand // 1000
    assets = sum(asset.count for asset in await train_of(ctx, owner.id))
    for row, armies in rows:
        keep(row, "priority", clamp_int((row.believed_threat + 1) * PERCENT // believed, 0, PERCENT))
        keep(row, "reserves", reserves * row.priority // PERCENT)
        keep(row, "levies", levies * row.priority // PERCENT)
        keep(row, "transport", assets * row.priority // PERCENT)
        await reinforce(ctx, folk, row, armies, tally)
        if row.misjudged and row.priority >= PERCENT // 2:
            await note(
                ctx,
                f"{owner.name} misread its fronts and sent its reserves where the danger was smaller.",
                key="theatres.misjudged",
                ids=[owner.id, *([row.marshal_entity_id] if row.marshal_entity_id else [])],
            )


async def folk_of(ctx: TickContext, owner: EntityRow) -> list[EntityRow]:
    if stat_or(owner, "population", 0) > 0:
        return [owner]
    realm = (await RealmBook.load(ctx.session)).realms.get(owner.id)
    members = sorted(realm.members) if realm is not None else []
    return [item for member in members if (item := await ctx.session.get(EntityRow, member)) is not None]


async def reinforce(ctx: TickContext, folk: list[EntityRow], row: TheatreRow, armies: list[ArmyRow], tally: TheatreTally) -> None:
    added = (row.reserves + row.levies) * ctx.rules.theatres.reinforce_pct // PERCENT
    target = next((item for item in armies if not held(item.entity_id)), None)
    source = max(folk, key=lambda item: stat_or(item, "population", 0), default=None)
    if added <= 0 or target is None or source is None or held(source.id):
        return
    army = await ctx.session.get(EntityRow, target.entity_id)
    stacks = [stack for stack in await stacks_of(ctx.session, target.entity_id) if "count" not in stack.locked]
    added = min(added, stat_or(source, "population", 0))
    if army is None or not stacks or added <= 0:
        return
    regrow(stacks, added)
    sync(army, await stacks_of(ctx.session, target.entity_id), ctx.rules)
    shift_stat(source, "population", -added)
    tally.reinforced += added


async def keep_theatres(ctx: TickContext, tally: TheatreTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    by_owner: dict[int, list[OngoingWar]] = {}
    for item in await ongoing_wars(ctx.session):
        for side in item.sides:
            by_owner.setdefault(side, []).append(item)
    for owner_id, wars in sorted(by_owner.items()):
        owner = await ctx.session.get(EntityRow, owner_id)
        if owner is None or held(owner_id):
            continue
        await allocate(ctx, owner, wars, atlas, tally)
