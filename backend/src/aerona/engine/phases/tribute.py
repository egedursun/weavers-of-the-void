from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.warfare import TributeRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import TreatyKind, TreatyStatus
from aerona.domain.enums.war import TributeStatus, WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import greed_drive
from aerona.engine.phase import Phase
from aerona.engine.polity.accords import end_treaty, treaty_between
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import declare_war, end_tribute, impose_tribute, is_community


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
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.defense",
    "table.bonds",
    "table.ciphers",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.geasa",
    "table.goods_flows",
    "table.held_identities",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.minds",
    "table.mortal_profiles",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.signal_links",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.tributes",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
    "table.world_seasons",
)
@writes(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.messages",
    "table.mortal_profiles",
    "table.oaths",
    "table.polity_regard",
    "table.reputations",
    "table.thoughts",
    "table.treaty_breaches",
    "table.treaty_profiles",
    "table.tributes",
)
async def tribute(ctx: TickContext) -> None:
    rules = ctx.rules.campaigns
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
        if held(*pair):
            continue
        payer, receiver = await living_entity(ctx.session, row.payer_entity_id), await living_entity(ctx.session, row.receiver_entity_id)
        pact = await treaty_between(ctx.session, row.payer_entity_id, row.receiver_entity_id, [TreatyKind.TRIBUTE, TreatyKind.VASSALAGE])
        if payer is None or receiver is None or pact is None:
            await end_tribute(ctx, row, TributeStatus.ENDED, "tribute ended")
            if payer is not None and receiver is not None:
                await change_relation(ctx, payer.id, receiver.id, rules.tribute_end_relation, MemoryKind.FREED_US, note="tribute ended")
                await _note(ctx, f"The tribute {payer.name} paid to {receiver.name} ended.", "tribute.ended", (payer.id, receiver.id))
            continue
        if row.since_epoch == ctx.epoch:
            continue
        greed = await greed_drive(ctx.session, ctx.rules, receiver.id)
        if await strength.power(payer) > await strength.power(receiver) * rules.tribute_revolt_strength_pct / PERCENT and rng.chance(
            rules.tribute_revolt_chance * greed
        ):
            await breach(ctx, pact, payer.id, clause=None, reason="it grew strong and refused the tribute")
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
    pact = await treaty_between(ctx.session, row.payer_entity_id, row.receiver_entity_id, [TreatyKind.TRIBUTE])
    if pact is not None:
        await end_treaty(ctx, pact, TreatyStatus.FULFILLED, "the tribute was forgiven")
    if payer is not None and receiver is not None:
        await change_relation(ctx, payer.id, receiver.id, ctx.rules.campaigns.tribute_end_relation, MemoryKind.GIFTED_ME, note="tribute forgiven")
        await _note(ctx, f"The tribute {payer.name} paid to {receiver.name} was forgiven.", "tribute.forgiven", (payer.id, receiver.id))
    return row


PHASES = (Phase("tribute", tribute),)
