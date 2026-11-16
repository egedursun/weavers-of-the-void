from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.constructs import ConstructRow, InstructionSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import AugmentRow, DataStoreContentRow, DataStoreRow, IntrusionRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkOutageRow, NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.made import Attribution, Authenticity, DataContent, IntrusionAim, IntrusionApproach, IntrusionOutcome, IntrusionTarget
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.networks import OutageCause
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.economy.routes import enemies_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import best_skill
from aerona.engine.minds.values import best_level
from aerona.engine.networks.book import shake_ledger
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.services.community_relations import change_relation

APPROACH_SKILLS = {
    IntrusionApproach.TECHNICAL: (SkillKind.COMPUTING, SkillKind.CRYPTOGRAPHY, SkillKind.ELECTRONICS),
    IntrusionApproach.SOCIAL: (SkillKind.DECEPTION, SkillKind.INTRIGUE),
    IntrusionApproach.INSIDER: (SkillKind.INTRIGUE,),
    IntrusionApproach.RITE: (SkillKind.RITUAL, SkillKind.SPELLCRAFT),
    IntrusionApproach.POWER: (SkillKind.SPELLCRAFT, SkillKind.SPIRIT_SPEAKING),
}
AIM_HARM = {IntrusionAim.READ: 2, IntrusionAim.ALTER: 4, IntrusionAim.DENY: 5, IntrusionAim.SEIZE: 8, IntrusionAim.PLANT: 3, IntrusionAim.EXTORT: 6}


@dataclass(frozen=True)
class Attempt:
    actor_id: int | None
    target: IntrusionTarget
    target_node_id: int | None
    approach: IntrusionApproach
    aim: IntrusionAim
    blamed_id: int | None = None


async def security_of(ctx: TickContext, target: IntrusionTarget, node_id: int | None) -> int:
    if node_id is None:
        return 0
    if target is IntrusionTarget.NETWORK:
        network = await ctx.session.get(NetworkProfileRow, node_id)
        return network.security if network is not None else 0
    if target is IntrusionTarget.DATA_STORE:
        store = await ctx.session.get(DataStoreRow, node_id)
        return store.security if store is not None else 0
    node = await ctx.session.scalar(
        select(NetworkNodeRow.security).where(NetworkNodeRow.member_node_id == node_id).order_by(NetworkNodeRow.security.desc()).limit(1)
    )
    return int(node or 0)


async def edge_of(ctx: TickContext, attempt: Attempt) -> int:
    if attempt.actor_id is None:
        return 0
    table = ctx.rules.intrusion
    skill = await best_skill(ctx.session, attempt.actor_id, APPROACH_SKILLS[attempt.approach])
    level = await best_level(ctx.session, attempt.actor_id)
    spies = await ctx.session.scalar(
        select(SpyNetworkRow.depth).where(SpyNetworkRow.owner_entity_id == attempt.actor_id).order_by(SpyNetworkRow.depth.desc()).limit(1)
    )
    edge = round_half_up((skill + level * 10) * table.skill_pct / PERCENT) + int(spies or 0) // 4
    return edge + (table.insider_bonus if attempt.approach is IntrusionApproach.INSIDER else 0)


async def deny(ctx: TickContext, network_id: int) -> None:
    network = await ctx.session.get(NetworkProfileRow, network_id)
    if network is None or held(network_id):
        return
    network.down_until_epoch = max(network.down_until_epoch, ctx.epoch + 1)
    ctx.session.add(
        NetworkOutageRow(network_entity_id=network_id, cause=OutageCause.INTRUSION, epoch=ctx.epoch, epochs=1, severity=ctx.rules.intrusion.outage_severity)
    )
    await shake_ledger(ctx.session, ctx.rules, network_id)


async def seize(ctx: TickContext, attempt: Attempt) -> None:
    node_id = attempt.target_node_id
    if node_id is None or attempt.actor_id is None or held(node_id):
        return
    mind = await ctx.session.get(MindProfileRow, node_id)
    if attempt.target in {IntrusionTarget.MADE_MIND, IntrusionTarget.CONSTRUCT} and mind is not None and "made_by_node_id" not in mind.locked:
        mind.made_by_node_id, mind.maker_bond = attempt.actor_id, 0
    for orders in await ctx.session.scalars(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == node_id)):
        if "holder_node_id" not in orders.locked:
            orders.holder_node_id = attempt.actor_id
    network = await ctx.session.get(NetworkProfileRow, node_id)
    if network is not None and "owner_node_id" not in network.locked:
        network.owner_node_id = attempt.actor_id
    store = await ctx.session.get(DataStoreRow, node_id)
    if store is not None and "owner_node_id" not in store.locked:
        store.owner_node_id = attempt.actor_id
    state = await ctx.session.get(MindStateRow, node_id) if attempt.target is IntrusionTarget.SAVED_STATE else None
    if state is not None and "owner_node_id" not in state.locked:
        state.owner_node_id = attempt.actor_id


async def owner_of(ctx: TickContext, attempt: Attempt) -> EntityRow | None:
    node_id = attempt.target_node_id
    if node_id is None:
        return None
    for table, column in ((NetworkProfileRow, "owner_node_id"), (DataStoreRow, "owner_node_id"), (ConstructRow, "maker_entity_id")):
        row = await ctx.session.get(table, node_id)
        if row is not None and getattr(row, column) is not None:
            return await ctx.session.get(EntityRow, getattr(row, column))
    augment = await ctx.session.get(AugmentRow, node_id) if attempt.target is IntrusionTarget.AUGMENT else None
    if augment is not None:
        return await ctx.session.get(EntityRow, augment.bearer_node_id)
    return await ctx.session.get(EntityRow, node_id)


async def copy_contents(ctx: TickContext, store_id: int, actor_id: int) -> int:
    own = await ctx.session.scalar(select(DataStoreRow).where(DataStoreRow.owner_node_id == actor_id).order_by(DataStoreRow.id).limit(1))
    if own is None:
        own = DataStoreRow(holder_node_id=actor_id, security=0, owner_node_id=actor_id, locked=[])
        ctx.session.add(own)
        await ctx.session.flush()
    taken = 0
    wanted = (DataContent.SECRET, DataContent.KNOWLEDGE, DataContent.IDENTITY)
    for row in list(
        await ctx.session.scalars(select(DataStoreContentRow).where(DataStoreContentRow.store_id == store_id, DataStoreContentRow.content.in_(wanted)))
    ):
        ctx.session.add(
            DataStoreContentRow(store_id=own.id, content=row.content, subject_node_id=row.subject_node_id, reference=row.reference, epoch=ctx.epoch, locked=[])
        )
        taken += 1
    return taken


async def land(ctx: TickContext, attempt: Attempt, victim: EntityRow | None) -> None:
    node_id = attempt.target_node_id
    if attempt.aim is IntrusionAim.DENY and attempt.target is IntrusionTarget.NETWORK and node_id is not None:
        await deny(ctx, node_id)
    elif attempt.aim is IntrusionAim.SEIZE:
        await seize(ctx, attempt)
    elif attempt.aim is IntrusionAim.EXTORT and victim is not None and attempt.actor_id is not None and not held(victim.id):
        actor = await ctx.session.get(EntityRow, attempt.actor_id)
        if actor is not None and await take_coin(ctx.session, ctx.rules, victim, ctx.rules.intrusion.extort_take):
            await give_coin(ctx.session, ctx.rules, actor, ctx.rules.intrusion.extort_take)
    elif attempt.aim in {IntrusionAim.ALTER, IntrusionAim.PLANT} and victim is not None:
        accounts = await ctx.session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == victim.id).order_by(AccountRow.id.desc()).limit(1))
        for account in accounts:
            if "authenticity" not in account.locked:
                account.authenticity = Authenticity.ALTERED if attempt.aim is IntrusionAim.ALTER else Authenticity.FORGED
    elif attempt.aim is IntrusionAim.READ and attempt.target is IntrusionTarget.DATA_STORE and node_id is not None and attempt.actor_id is not None:
        await copy_contents(ctx, node_id, attempt.actor_id)


async def intrude(ctx: TickContext, attempt: Attempt) -> IntrusionRow:
    if attempt.target_node_id is not None and held(attempt.target_node_id):
        raise ValidationFailedError("That target is held against the world.")
    table = ctx.rules.intrusion
    rng = ctx.rng(f"intrusion.{attempt.actor_id}.{attempt.target_node_id}.{attempt.aim.value}.{ctx.epoch}")
    edge = await edge_of(ctx, attempt)
    security = await security_of(ctx, attempt.target, attempt.target_node_id)
    succeeded = rng.chance(clamp_percent(PERCENT // 2 + edge - security))
    detection = clamp_percent(table.detection_base + (0 if succeeded else table.detection_base) + AIM_HARM[attempt.aim] * 3 - edge // 4)
    found = rng.chance(detection)
    attribution, blamed = Attribution.UNKNOWN, None
    if found and rng.chance(table.attribution_chance):
        attribution, blamed = Attribution.KNOWN, attempt.actor_id
        if attempt.blamed_id is not None or rng.chance(table.false_flag_chance):
            attribution, blamed = Attribution.FALSE_FLAG, attempt.blamed_id
    elif found:
        attribution = Attribution.SUSPECTED
    outcome = IntrusionOutcome.CAUGHT if found and not succeeded else IntrusionOutcome.SUCCEEDED if succeeded else IntrusionOutcome.FAILED
    victim = await owner_of(ctx, attempt)
    if succeeded:
        await land(ctx, attempt, victim)
    row = IntrusionRow(
        actor_node_id=attempt.actor_id,
        target=attempt.target,
        target_node_id=attempt.target_node_id,
        approach=attempt.approach,
        aim=attempt.aim,
        stealth=clamp_percent(PERCENT - detection),
        detection=detection,
        attribution=attribution,
        blamed_node_id=blamed,
        outcome=outcome,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if victim is not None and blamed is not None and blamed != victim.id:
        await change_relation(ctx, victim.id, blamed, -AIM_HARM[attempt.aim], MemoryKind.SPIED_ON_US, note="blamed for an intrusion")
    ids = [node for node in (attempt.actor_id, attempt.target_node_id) if node is not None]
    await note(ctx, "An intrusion was made." if not found else "An intrusion was found.", key=f"intrusion.{outcome.value}", ids=ids)
    return row


async def target_of_foe(ctx: TickContext, foe: int) -> tuple[IntrusionTarget, int] | None:
    network = await ctx.session.scalar(
        select(NetworkProfileRow.network_entity_id).where(NetworkProfileRow.owner_node_id == foe).order_by(NetworkProfileRow.network_entity_id).limit(1)
    )
    if network is not None:
        return IntrusionTarget.NETWORK, int(network)
    store = await ctx.session.scalar(select(DataStoreRow.id).where(DataStoreRow.owner_node_id == foe).order_by(DataStoreRow.id).limit(1))
    if store is not None:
        return IntrusionTarget.DATA_STORE, int(store)
    return None


@reads("table.bonds", "table.data_store_contents", "table.data_stores", "table.holder_levels", "table.network_profiles", "table.skills", "table.spy_networks")
@writes(
    "table.accounts",
    "table.data_store_contents",
    "table.data_stores",
    "table.instruction_sets",
    "table.intrusions",
    "table.memories",
    "table.mind_profiles",
    "table.network_outages",
    "table.network_profiles",
)
async def foes_intrude(ctx: TickContext) -> None:
    table = ctx.rules.intrusion
    for actor, foe in sorted(await enemies_of(ctx)):
        if held(actor) or held(foe) or await best_level(ctx.session, actor) <= 0:
            continue
        if not ctx.rng(f"intrusion.try.{actor}.{foe}.{ctx.epoch}").chance(table.detection_base // 3):
            continue
        found = await target_of_foe(ctx, foe)
        if found is None:
            continue
        target, node = found
        aim = IntrusionAim.DENY if target is IntrusionTarget.NETWORK else IntrusionAim.READ
        await intrude(ctx, Attempt(actor, target, node, IntrusionApproach.TECHNICAL, aim))
        ctx.count("intrusions")
