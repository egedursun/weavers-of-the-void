from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.life.living import SEED_DUES_FERTILITYS
from aerona.catalog.methods import METHODS
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import PerennialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.living import LivingLineRow, LivingProfileRow
from aerona.db.tables.networks import NetworkOutageRow, NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.living import LineTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.networks import NetworkCarrier
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.living.traits import eased, traits_of
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.recording.record import FactInput, record
from aerona.engine.services.community_relations import change_relation

LIVING_METHODS = frozenset({MethodKind.CULTURED_CROPS, MethodKind.GROWN_TIMBER, MethodKind.FIBRE_FROM_LIFE, MethodKind.VAT_CULTURE, MethodKind.BIOREACTOR})


def plain_method(process: ProcessKind) -> MethodKind | None:
    return next((spec.kind for spec in METHODS.values() if spec.process is process and spec.technique is None and spec.kind not in LIVING_METHODS), None)


async def works_sick(ctx: TickContext, community_id: int) -> bool:
    floor = ctx.rules.living_production.sick_works_pct
    healths = list(
        await ctx.session.scalars(
            select(LivingProfileRow.health)
            .join(EntityRow, EntityRow.id == LivingProfileRow.thing_node_id)
            .where(EntityRow.location_id == community_id, EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON)
        )
    )
    return bool(healths) and max(healths) < floor


async def keep_living_works(ctx: TickContext) -> int:
    lapsed = 0
    rows = await ctx.session.scalars(select(CommunityMethodRow).where(CommunityMethodRow.method.in_(list(LIVING_METHODS))).order_by(CommunityMethodRow.id))
    for row in list(rows):
        if held(row.community_node_id) or "method" in row.locked or not await works_sick(ctx, row.community_node_id):
            continue
        fallback = plain_method(row.process)
        if fallback is None:
            continue
        old = row.method
        row.method, row.adopted_epoch = fallback, ctx.epoch
        lapsed += 1
        town = await ctx.session.get(EntityRow, row.community_node_id)
        await record(
            ctx,
            "living.works_lapsed",
            roles={IncidentRole.SUBJECT: row.community_node_id},
            facts={"old_method": old, "new_method": fallback},
            place=town.id if town else None,
        )
    return lapsed


async def blight_monocultures(ctx: TickContext) -> int:
    table = ctx.rules.living
    area: dict[int, int] = defaultdict(int)
    by_line: dict[tuple[int, int], list[PerennialRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(PerennialRow).order_by(PerennialRow.id)):
        area[row.region_entity_id] += row.area
        if row.line_id is not None:
            by_line[(row.region_entity_id, row.line_id)].append(row)
    struck = 0
    for (region_id, line_id), plantings in sorted(by_line.items()):
        share = sum(row.area for row in plantings) * PERCENT // max(1, area[region_id])
        if share < table.monoculture_share or held(region_id):
            continue
        if not ctx.rng(f"living.blight.{region_id}.{line_id}.{ctx.epoch}").chance(table.blight_chance):
            continue
        harm = eased(table.blight_harm, (await traits_of(ctx.session, line_id)).get(LineTrait.DISEASE_RESISTANCE, 0))
        for row in plantings:
            if "condition" not in row.locked:
                row.condition = clamp_percent(row.condition - harm)
        line = await ctx.session.get(LivingLineRow, line_id)
        facts: dict[str, FactInput] = {"harm": harm, "plantings": len(plantings), **({"line": line.name} if line else {})}
        await record(ctx, "living.blight", roles={IncidentRole.PLACE: region_id}, facts=facts, place=region_id)
        struck += 1
    return struck


async def seed_dues(ctx: TickContext) -> int:
    table = ctx.rules.living_production
    paid = 0
    bound = select(LivingLineRow.id).where(LivingLineRow.fertility.in_(SEED_DUES_FERTILITYS), LivingLineRow.owner_node_id.is_not(None))
    for row in list(await ctx.session.scalars(select(PerennialRow).where(PerennialRow.line_id.in_(bound)).order_by(PerennialRow.id))):
        line = await ctx.session.get(LivingLineRow, row.line_id)
        grower = await ctx.session.get(EntityRow, row.owner_node_id) if row.owner_node_id is not None else None
        owner = await ctx.session.get(EntityRow, line.owner_node_id) if line is not None and line.owner_node_id is not None else None
        if grower is None or owner is None or grower.id == owner.id or held(grower.id) or held(owner.id):
            continue
        if await take_coin(ctx.session, ctx.rules, grower, table.seed_due):
            await give_coin(ctx.session, ctx.rules, owner, table.seed_due)
            await change_relation(ctx, grower.id, owner.id, table.seed_regard, MemoryKind.GOODWILL, note="depends on its line")
            paid += 1
    return paid


async def heal_living_links(ctx: TickContext) -> int:
    grown = select(NetworkProfileRow.network_entity_id).where(NetworkProfileRow.carrier == NetworkCarrier.GROWN_LINK)
    healed = 0
    for outage in list(await ctx.session.scalars(select(NetworkOutageRow).where(NetworkOutageRow.network_entity_id.in_(grown), NetworkOutageRow.epochs > 1))):
        if held(outage.network_entity_id):
            continue
        outage.epochs = max(1, outage.epochs - ctx.rules.living.link_heal)
        healed += 1
    return healed
