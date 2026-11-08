from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.polity import ClauseKind
from aerona.engine.context import TickContext
from aerona.engine.military.units import profile_of
from aerona.engine.mind.hooks import judged
from aerona.engine.polity.treaties import breach, clauses_of, in_force
from aerona.engine.primitives.queries import living_entity
from aerona.engine.services.community_relations import change_relation


async def allies_on_side(ctx: TickContext, war: WarRow, side_id: int) -> list[int]:
    own = await ctx.session.get(WarSideRow, (war.id, side_id))
    if own is None:
        return []
    statement = select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.side == own.side, WarSideRow.left_epoch.is_(None))
    rows = await ctx.session.scalars(statement.order_by(WarSideRow.entity_id))
    return [row.entity_id for row in rows if row.entity_id != side_id]


async def allied_armies(ctx: TickContext, war: WarRow, side_id: int) -> list[tuple[EntityRow, ArmyRow]]:
    found: list[tuple[EntityRow, ArmyRow]] = []
    for ally_id in await allies_on_side(ctx, war, side_id):
        statement = select(ArmyRow).where(ArmyRow.owner_entity_id == ally_id, ArmyRow.war_id == war.id, ArmyRow.disbanded_epoch.is_(None))
        for row in await ctx.session.scalars(statement.order_by(ArmyRow.entity_id)):
            army = await living_entity(ctx.session, row.entity_id)
            if army is not None:
                found.append((army, row))
    return found


async def march_with(ctx: TickContext, war: WarRow, side_id: int, leader: ArmyProfileRow) -> int:
    moved = 0
    for army, _ in await allied_armies(ctx, war, side_id):
        owner_row = await ctx.session.get(ArmyRow, army.id)
        owner = await living_entity(ctx.session, owner_row.owner_entity_id) if owner_row is not None else None
        profile = await profile_of(ctx, army, owner)
        if "region_id" in profile.locked:
            continue
        if profile.region_entity_id != leader.region_entity_id:
            profile.region_entity_id = leader.region_entity_id
            moved += 1
        if "stance" not in profile.locked:
            profile.stance = leader.stance
    return moved


async def betrayed_call(ctx: TickContext, ally_id: int, party_id: int) -> bool:
    ally = await living_entity(ctx.session, ally_id)
    party = await living_entity(ctx.session, party_id)
    if ally is None or party is None or held(ally_id, party_id):
        return False
    for profile in await in_force(ctx):
        for clause in await clauses_of(ctx, profile.treaty_entity_id):
            if clause.kind is ClauseKind.CALL_TO_ARMS and clause.obligor_node_id == ally_id and clause.beneficiary_node_id == party_id:
                await breach(ctx, profile, ally_id, clause=clause, reason="it refused the call to arms")
                await judged(ctx, party_id, ally_id, ActKind.BETRAYAL, note="refused the call to arms")
                await change_relation(ctx, party_id, ally_id, -ctx.rules.treaties.refuse_relation_loss, MemoryKind.BETRAYED_ME, note="betrayed the alliance")
                await ctx.chronicle(
                    ChronicleKind.DIPLOMACY,
                    f"{ally.name} would not march when {party.name} called; the alliance is betrayed.",
                    template_key="war.call_betrayed",
                    entity_ids=(ally_id, party_id),
                    feed_category=FeedCategory.WAR,
                )
                ctx.count("calls_betrayed")
                return True
    return False
