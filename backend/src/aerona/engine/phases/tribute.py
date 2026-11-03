from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import TributeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import TributeStatus, WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import greed_drive
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import active_tribute, declare_war, end_tribute, impose_tribute, is_community


async def adopt_untracked_tributes(ctx: TickContext) -> int:
    bonds = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.PAYS_TRIBUTE, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    adopted = 0
    for bond in list(bonds):
        if await active_tribute(ctx.session, bond.source_node_id, bond.target_node_id) is not None:
            continue
        ctx.session.add(
            TributeRow(
                payer_entity_id=bond.source_node_id,
                receiver_entity_id=bond.target_node_id,
                war_id=bond.war_id,
                bond_id=bond.id,
                status=TributeStatus.ACTIVE,
                since_epoch=bond.epoch,
            )
        )
        adopted += 1
    await ctx.session.flush()
    return adopted


async def _flow(ctx: TickContext, payer: EntityRow, receiver: EntityRow, greed: float) -> None:
    rules = ctx.rules.campaigns
    flow = round_half_up(rules.tribute_flow * greed)
    if shift_stat(payer, "prosperity", -flow) is not None:
        add_prosperity(ctx.rules, receiver, flow)
    if shift_stat(payer, "wealth", -flow) is not None:
        shift_stat(receiver, "wealth", flow)
    payer_society = await ctx.session.get(CommunitySocietyRow, payer.id)
    receiver_society = await ctx.session.get(CommunitySocietyRow, receiver.id)
    if payer_society is None or receiver_society is None:
        return
    goods = round_half_up(payer_society.stock_goods * min(PERCENT, rules.tribute_goods_pct * greed) / PERCENT)
    if goods > 0:
        payer_society.stock_goods -= goods
        receiver_society.stock_goods = min(ctx.rules.society.stockpile_cap, receiver_society.stock_goods + goods)


async def _note(ctx: TickContext, text: str, key: str, ids: tuple[int, ...]) -> None:
    await ctx.chronicle(ChronicleKind.WAR, text, template_key=key, entity_ids=ids, feed_category=FeedCategory.WAR)


@reads(
    "cult.followers",
    "cult.zeal",
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "item.damage",
    "item.might",
    "item.protection",
    "people.martiality",
    "people.prosperity",
    "people.wealth",
    "settlement.defense",
    "table.bonds",
    "table.community_relations",
    "table.community_societies",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.personality_values",
    "table.traits",
    "table.tributes",
)
@writes(
    "faction.wealth",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_societies",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.tributes",
)
@reads(
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "item.damage",
    "item.might",
    "item.protection",
    "people.martiality",
    "people.prosperity",
    "people.wealth",
    "settlement.defense",
)
@writes("faction.wealth")
async def tribute(ctx: TickContext) -> None:
    rules = ctx.rules.campaigns
    ctx.count("tributes_adopted", await adopt_untracked_tributes(ctx))
    active = select(TributeRow).where(TributeRow.status == TributeStatus.ACTIVE)
    rows = list(await ctx.session.scalars(active.order_by(TributeRow.since_epoch.desc(), TributeRow.id.desc())))
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    rng = ctx.rng("revolt")
    seen: set[tuple[int, int]] = set()
    for row in rows:
        pair = (row.payer_entity_id, row.receiver_entity_id)
        if pair in seen:
            await end_tribute(ctx, row, TributeStatus.ENDED, "duplicate tribute")
            continue
        seen.add(pair)
        payer, receiver = await living_entity(ctx.session, row.payer_entity_id), await living_entity(ctx.session, row.receiver_entity_id)
        if payer is None or receiver is None:
            await end_tribute(ctx, row, TributeStatus.ENDED, "a side is gone")
            continue
        age = ctx.epoch - row.since_epoch
        if age >= rules.tribute_epochs:
            await end_tribute(ctx, row, TributeStatus.ENDED, "tribute ended")
            await change_relation(ctx, payer.id, receiver.id, rules.tribute_end_relation, MemoryKind.FREED_US, note="tribute ended")
            await _note(ctx, f"The tribute {payer.name} paid to {receiver.name} ended after {age} epochs.", "tribute.ended", (payer.id, receiver.id))
            continue
        if row.since_epoch == ctx.epoch:
            continue
        greed = await greed_drive(ctx.session, ctx.rules, receiver.id)
        await _flow(ctx, payer, receiver, greed)
        ctx.count("tributes_paid")
        if await strength.power(payer) > await strength.power(receiver) * rules.tribute_revolt_strength_pct / PERCENT and rng.chance(
            rules.tribute_revolt_chance * greed
        ):
            await end_tribute(ctx, row, TributeStatus.REVOLTED, "tribute revolt")
            await change_relation(ctx, payer.id, receiver.id, -rules.tribute_revolt_relation, MemoryKind.FOUGHT_US, note="tribute revolt")
            war = await declare_war(ctx, payer.id, receiver.id, "tribute revolt", cause=WarCause.TRIBUTE_REVOLT)
            tail = "; the two sides declared each other enemies" if war else ""
            await _note(ctx, f"{payer.name} grew strong and refused to pay tribute to {receiver.name}{tail}.", "tribute.revolt", (payer.id, receiver.id))
            ctx.count("tribute_revolts")


async def decree_tribute(ctx: TickContext, payer_id: int, receiver_id: int) -> TributeRow:
    payer, receiver = await living_entity(ctx.session, payer_id), await living_entity(ctx.session, receiver_id)
    if payer is None or receiver is None or not is_community(payer) or not is_community(receiver):
        raise ValidationFailedError("Tribute binds two living communities.")
    if payer.id == receiver.id:
        raise ValidationFailedError("A community cannot pay tribute to itself.")
    row = await impose_tribute(ctx, payer, receiver, None, "by decree")
    await _note(ctx, f"By decree {payer.name} pays tribute to {receiver.name}.", "tribute.decree", (payer.id, receiver.id))
    return row


async def forgive_tribute(ctx: TickContext, tribute_id: int) -> TributeRow:
    row = await ctx.session.get(TributeRow, tribute_id)
    if row is None:
        raise NotFoundError("No such tribute.")
    if row.status is not TributeStatus.ACTIVE:
        raise ConflictError("That tribute is no longer paid.")
    await end_tribute(ctx, row, TributeStatus.ENDED, "forgiven by decree")
    payer, receiver = await living_entity(ctx.session, row.payer_entity_id), await living_entity(ctx.session, row.receiver_entity_id)
    if payer is not None and receiver is not None:
        await change_relation(ctx, payer.id, receiver.id, ctx.rules.campaigns.tribute_end_relation, MemoryKind.GIFTED_ME, note="tribute forgiven")
        await _note(ctx, f"The tribute {payer.name} paid to {receiver.name} was forgiven.", "tribute.forgiven", (payer.id, receiver.id))
    return row


PHASES = (Phase("tribute", tribute),)
