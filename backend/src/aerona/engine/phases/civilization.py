from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import TIER_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmic_state import CivilizationTierLockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, ThreadLinkRole, ThreadStatus
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import COMMUNITY_TYPES, CivilizationTier, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import CaptiveStatus, DebtStatus, WarCause
from aerona.domain.models.entity_stats import FactionStats, ItemStats, KnowledgeStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import RouteBook, method_label, world_name
from aerona.engine.cosmos.tiers import TierScene, may, planned_tiers, tier_lock, tier_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mortal.kin import fosterers_of, parents_of
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import BondIndex, active_bonds, canon
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import headcount, put_stat, stat, stat_or
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war
from aerona.rules.registry import Rules

T = CivilizationTier
TIER_TYPES = frozenset({EntityType.PEOPLE, EntityType.FACTION, EntityType.SETTLEMENT})
GOODS_TYPES = frozenset({EntityType.RESOURCE, EntityType.ITEM, EntityType.VESSEL, EntityType.STRUCTURE})
VALUE_KEYS = ("might", "damage", "protection", "splendor", "speed")
WEALTH_KEY = "wealth"
PROSPERITY_KEY = "prosperity"
AGE_KEY = "age"
SILVER = "silver"
GRAIN = "grain"


def tier_name(tier: int) -> str:
    return TIER_LABELS[T(tier)].lower()


async def _dwell_blocked(ctx: TickContext, entity: EntityRow, old: int, new: int) -> bool:
    direction = 1 if new > old else -1
    previous = entity.civ_tier_previous
    last_direction = direction if previous is None or previous == old else (1 if old > previous else -1)
    recent = entity.civ_tier_epoch is not None and ctx.epoch - entity.civ_tier_epoch < ctx.rules.civilization.stage_min_epochs
    return recent and last_direction != direction


async def apply_tier(ctx: TickContext, entity: EntityRow, new: int, *, forced: bool = False) -> bool:
    old = tier_of(entity)
    if entity.civ_tier is None:
        entity.civ_tier = old
    if new == old or (not forced and await _dwell_blocked(ctx, entity, old, new)):
        return False
    entity.civ_tier_epoch = ctx.epoch
    entity.civ_tier_previous = old
    entity.civ_tier = new
    repository = EntityRepository(ctx.session)
    if new > old and new >= T.KINGDOM:
        await note(ctx, f"{entity.name} rose: now {an(tier_name(new))}.", key="civilization.rose", ids=[entity.id])
        await ctx.chronicle(ChronicleKind.CIVILIZATION, f"{entity.name} became {an(tier_name(new))}.", template_key="civilization.tier", entity_ids=[entity.id])
        if new >= T.WORLD_EMPIRE:
            await repository.add_flag(entity.id, EntityFlag.EMPIRE, ctx.epoch)
    if new < old and old >= T.KINGDOM:
        await note(ctx, f"{entity.name} declined: now {an(tier_name(new))}.", key="civilization.declined", ids=[entity.id])
    if new < T.WORLD_EMPIRE <= old:
        await repository.remove_flag(entity.id, EntityFlag.EMPIRE)
    return True


async def update_tiers(ctx: TickContext) -> int:
    scene = await TierScene.load(ctx.session, ctx.rules)
    candidates = await canon(ctx.session, TIER_TYPES)
    targets, forced = planned_tiers(scene, candidates)
    changed = 0
    for entity in unheld(candidates):
        locked = await tier_lock(ctx.session, entity.id)
        new = locked if locked is not None else targets[entity.id]
        if await apply_tier(ctx, entity, new, forced=locked is None and entity.id in forced):
            changed += 1
    return changed


async def colony_independence(ctx: TickContext) -> int:
    civ = ctx.rules.civilization
    rng = ctx.rng("independence")
    freed = 0
    for colony in await EntityRepository(ctx.session).with_flag(EntityFlag.COLONY):
        if colony.entity_type is not EntityType.SETTLEMENT or ctx.epoch - colony.birth_epoch < civ.colony_independence_min_age:
            continue
        bond = next(iter(await active_bonds(ctx.session, [BondKind.RULES], targets=[colony.id])), None)
        mother = await ctx.session.get(EntityRow, bond.source_node_id) if bond is not None else None
        if bond is None or mother is None or mother.status is not EntityStatus.CANON:
            continue
        far = mother.world_id != colony.world_id
        await change_relation(
            ctx, mother.id, colony.id, -(civ.colony_far_cooling if far else civ.colony_near_cooling), MemoryKind.ILL_WILL, note="distance from the homeland"
        )
        chance = (civ.colony_far_independence_chance if far else civ.colony_near_independence_chance) / PERCENT
        chance += (stat_or(colony, PROSPERITY_KEY, civ.colony_prosperity_base) - civ.colony_prosperity_base) / civ.colony_prosperity_divisor
        chance += civ.colony_grudge_bonus_pct / PERCENT if await relation(ctx.session, ctx.rules, mother.id, colony.id) < 0 else 0
        if rng.probability(chance):
            await declare_independence(ctx, colony, mother, bond, war=rng.chance(civ.independence_war_chance))
            freed += 1
    return freed


async def declare_independence(ctx: TickContext, colony: EntityRow, mother: EntityRow, bond: BondRow, *, war: bool) -> str:
    repository = EntityRepository(ctx.session)
    await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "independence")
    await repository.remove_flag(colony.id, EntityFlag.COLONY)
    await repository.add_flag(colony.id, EntityFlag.INDEPENDENT, ctx.epoch)
    fought = war and await declare_war(ctx, mother.id, colony.id, "war of independence", cause=WarCause.INDEPENDENCE)
    tail = "; the motherland declared it an enemy" if fought else " and the motherland had to let it go"
    text = f"{colony.name} declared its independence from {mother.name}{tail}."
    await ctx.chronicle(ChronicleKind.CIVILIZATION, text, template_key="civilization.independence", entity_ids=[colony.id, mother.id])
    await note(ctx, text, key="civilization.independence_note", ids=[colony.id, mother.id])
    return text


async def _federated(session: AsyncSession) -> tuple[set[int], int]:
    federations = {item.id for item in await canon(session, [EntityType.FACTION]) if item.engine_kind is EngineKind.INTERWORLD_FEDERATION}
    members = {bond.source_node_id for bond in await active_bonds(session, [BondKind.MEMBER_OF], targets=list(federations))} if federations else set()
    return members, len(federations)


async def found_federation_of(ctx: TickContext, members: list[EntityRow]) -> EntityRow:
    civ = ctx.rules.civilization
    first = members[0]
    federation = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{first.name} Federation",
            entity_type=EntityType.FACTION,
            body=f"{', '.join(item.name for item in members)} swore to each other across the worlds and founded a federation.",
            stats=FactionStats(strength=civ.federation_strength, wealth=civ.federation_wealth, sway=civ.federation_sway),
            power=civ.federation_power,
            world_id=first.world_id,
            location_id=first.location_id if first.entity_type is not EntityType.SETTLEMENT else first.id,
            subtype="interworld federation",
            engine_kind=EngineKind.INTERWORLD_FEDERATION,
            flags=(EntityFlag.FEDERATION,),
        ),
    )
    for member in members:
        await BondRepository(ctx.session).connect(BondDraft(member.id, federation.id, BondKind.MEMBER_OF, ctx.epoch, "federation oath"))
    text = f"An interworld federation was founded: {', '.join(item.name for item in members)}."
    await ctx.chronicle(ChronicleKind.CIVILIZATION, text, template_key="civilization.federation", entity_ids=[federation.id, *(item.id for item in members)])
    return federation


async def federations(ctx: TickContext) -> EntityRow | None:
    civ = ctx.rules.civilization
    members_already, count = await _federated(ctx.session)
    if count >= civ.federation_max:
        return None
    allies = await BondIndex.load(ctx.session, [BondKind.ALLY])
    rng = ctx.rng("federation")
    for node in await canon(ctx.session, COMMUNITY_TYPES):
        if node.id in members_already or not may(ctx.rules, node, TierCapability.FEDERATION):
            continue
        partner_ids = {bond.other_end(node.id) for bond in allies.touching(node.id, BondKind.ALLY)}
        partners = [await ctx.session.get(EntityRow, item) for item in sorted(partner_ids - members_already)]
        members = [
            node,
            *(item for item in partners if item is not None and item.status is EntityStatus.CANON and may(ctx.rules, item, TierCapability.FEDERATION)),
        ]
        if len(members) < civ.federation_min_members or len({item.world_id for item in members}) < civ.federation_min_worlds:
            continue
        if not rng.chance(civ.federation_chance):
            continue
        return await found_federation_of(ctx, members)
    return None


async def reveal_previous_creation(ctx: TickContext, world: WorldRow) -> EntityRow | None:
    regions = unheld(await canon(ctx.session, [EntityType.REGION], world.id))
    if not regions or held(world.id):
        return None
    civ = ctx.rules.civilization
    rng = ctx.rng(f"previous_creation.{world.id}")
    region = max(regions, key=lambda item: (stat_or(item, "danger", 0), -item.id))
    creator = await CosmosRepository(ctx.session).creator()
    maker = creator.name if creator is not None else "the creator"
    ruin = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"Ruins beneath {region.name}",
            entity_type=EntityType.PLACE,
            body=(
                f"Beneath {region.name} were found the ruins of a civilization that {maker} created and forgot before this cosmos. "
                "The writing on the stones resembles no language; but the creator's name is written there in another form."
            ),
            stats=PlaceStats(
                danger=clamp_percent(civ.relic_site_danger + rng.die(civ.relic_site_danger_die)),
                fertility=civ.relic_site_fertility,
                mystery=civ.relic_site_mystery,
            ),
            power=civ.relic_site_power,
            world_id=world.id,
            location_id=region.id,
            subtype="ruin of the previous creation",
            flags=(EntityFlag.PREVIOUS_CREATION, EntityFlag.RUIN),
        ),
    )
    relic = await _relic(ctx, region, ruin)
    knowledge = await _ancient_knowledge(ctx, world)
    await BondRepository(ctx.session).connect(BondDraft(ruin.id, knowledge.id, BondKind.SOURCE_OF, ctx.epoch, "hidden in the ruins"))
    thread = ThreadRow(
        epoch=ctx.epoch,
        text=f"Ruins of a previous creation were found in {world.name}. What did {maker} create before this cosmos, and why did they forget it?",
        status=ThreadStatus.OPEN,
    )
    ctx.session.add(thread)
    await ctx.session.flush()
    ctx.session.add_all(
        ThreadLinkRow(thread_id=thread.id, entity_id=item.id, role=ThreadLinkRole.RELATED, epoch=ctx.epoch) for item in (ruin, relic, knowledge)
    )
    text = f"In {world.name}, the ruins of a creation before this cosmos came to light."
    await ctx.chronicle(
        ChronicleKind.PREVIOUS_CREATION, text, template_key="civilization.previous_creation", entity_ids=[ruin.id, relic.id, knowledge.id], world_id=world.id
    )
    return ruin


async def _relic(ctx: TickContext, region: EntityRow, ruin: EntityRow) -> EntityRow:
    civ = ctx.rules.civilization
    dice = ctx.rng(f"relic.{ruin.id}")
    return await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{region.name} Relic",
            entity_type=EntityType.ITEM,
            body="In the deepest part of the ruins, a powerful but cursed object from the hands of a forgotten civilization.",
            stats=ItemStats(
                damage=clamp_percent(civ.heirloom_damage + dice.die(civ.heirloom_damage_die)),
                protection=clamp_percent(civ.heirloom_protection + dice.die(civ.heirloom_protection_die)),
                might=clamp_percent(civ.heirloom_might + dice.die(civ.heirloom_might_die)),
                curse=clamp_percent(civ.heirloom_curse + dice.die(civ.heirloom_curse_die)),
            ),
            power=civ.heirloom_power,
            world_id=ruin.world_id,
            location_id=ruin.id,
            subtype="relic of the previous creation",
            flags=(EntityFlag.PREVIOUS_CREATION, EntityFlag.CURSED),
        ),
    )


async def _ancient_knowledge(ctx: TickContext, world: WorldRow) -> EntityRow:
    civ = ctx.rules.civilization
    forbidden = ctx.rng(f"ancient.{world.id}").chance(civ.ancient_knowledge_forbidden_chance)
    return await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"Knowledge of the Previous Creation ({world.name})",
            entity_type=EntityType.KNOWLEDGE,
            body="A knowledge older than this cosmos, hidden in the ruins.",
            stats=KnowledgeStats(level=civ.ancient_knowledge_level, spread=0),
            power=civ.ancient_knowledge_power,
            world_id=world.id,
            subtype="forgotten knowledge",
            knowledge_branch=KnowledgeBranch.FORBIDDEN if forbidden else KnowledgeBranch.MAGIC,
            flags=(EntityFlag.PREVIOUS_CREATION, EntityFlag.LOST),
        ),
    )


async def previous_creations(ctx: TickContext) -> int:
    marked = {entity.world_id for entity in await EntityRepository(ctx.session).with_flag(EntityFlag.PREVIOUS_CREATION, status=None)}
    found = 0
    for world in await WorldRepository(ctx.session).reachable_worlds():
        if world.id in marked or not ctx.rng(f"previous_roll.{world.id}").chance(ctx.rules.civilization.previous_creation_relic_chance):
            continue
        if await reveal_previous_creation(ctx, world) is not None:
            found += 1
    return found


def wealth_key(entity: EntityRow) -> str | None:
    if stat(entity, WEALTH_KEY) is not None:
        return WEALTH_KEY
    return PROSPERITY_KEY if stat(entity, PROSPERITY_KEY) is not None else None


def wealth_of(entity: EntityRow) -> int | None:
    key = wealth_key(entity)
    return stat(entity, key) if key is not None else None


def transfer(rules: Rules, entity: EntityRow, delta: int) -> None:
    key = wealth_key(entity)
    if key is not None:
        put_stat(rules, entity, key, stat_or(entity, key, 0) + delta)


async def repay(ctx: TickContext, bond: BondRow, debtor: EntityRow, creditor: EntityRow) -> str:
    amount = bond.debt_amount or 0
    paid = amount if wealth_of(debtor) is not None else 0
    transfer(ctx.rules, debtor, -paid)
    transfer(ctx.rules, creditor, paid)
    overdue = bond.debt_status is DebtStatus.OVERDUE
    bond.debt_status = DebtStatus.REPAID
    await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "debt paid")
    await change_relation(ctx, debtor.id, creditor.id, ctx.rules.civilization.loan_repay_relation, MemoryKind.KEPT_OATH, note="debt paid")
    late = " even though it was overdue" if overdue else ""
    text = f"{debtor.name} paid its debt ({amount} {bond.debt_what or SILVER}) to {creditor.name}{late}."
    await ctx.chronicle(ChronicleKind.DEBT, text, template_key="civilization.debt_paid", entity_ids=[debtor.id, creditor.id])
    return text


async def _debt_parties(ctx: TickContext, bond: BondRow) -> tuple[EntityRow, EntityRow] | None:
    debtor, creditor = await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)
    if debtor is None or creditor is None or debtor.status is not EntityStatus.CANON or creditor.status is not EntityStatus.CANON:
        await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "a party is gone")
        return None
    return debtor, creditor


async def repayments(ctx: TickContext) -> int:
    civ = ctx.rules.civilization
    rng = ctx.rng("repay")
    paid = 0
    for bond in await active_bonds(ctx.session, [BondKind.OWES]):
        parties = await _debt_parties(ctx, bond)
        if parties is None or held(*(party.id for party in parties)):
            continue
        have = wealth_of(parties[0])
        if have is not None and have - (bond.debt_amount or 0) < civ.loan_repay_reserve:
            continue
        if rng.chance(civ.loan_repay_chance):
            await repay(ctx, bond, *parties)
            paid += 1
    return paid


async def late_debts(ctx: TickContext) -> int:
    marked = 0
    for bond in await active_bonds(ctx.session, [BondKind.OWES]):
        if bond.debt_status is DebtStatus.OVERDUE or bond.debt_due_epoch is None or bond.debt_due_epoch >= ctx.epoch:
            continue
        parties = await _debt_parties(ctx, bond)
        if parties is None:
            continue
        debtor, creditor = parties
        await change_relation(ctx, creditor.id, debtor.id, -ctx.rules.civilization.loan_default_relation, MemoryKind.CHEATED_US, note="unpaid debt")
        bond.debt_status = DebtStatus.OVERDUE
        debt = f"{bond.debt_amount} {bond.debt_what or SILVER}"
        text = f"{debtor.name} did not pay its debt ({debt}) to {creditor.name} on time (Epoch {bond.debt_due_epoch}); coldness fell between them."
        await ctx.chronicle(ChronicleKind.DEBT, text, template_key="civilization.debt_late", entity_ids=[debtor.id, creditor.id])
        marked += 1
    return marked


async def lend(ctx: TickContext, lender: EntityRow, borrower: EntityRow, amount: int) -> str:
    civ = ctx.rules.civilization
    lent = max(1, min(amount, wealth_of(lender) or amount))
    what = SILVER if wealth_key(lender) == WEALTH_KEY else GRAIN
    due = ctx.epoch + civ.loan_term
    transfer(ctx.rules, lender, -lent)
    transfer(ctx.rules, borrower, lent)
    await BondRepository(ctx.session).connect(
        BondDraft(borrower.id, lender.id, BondKind.OWES, ctx.epoch, f"loan of {lent} {what}", debt_amount=lent, debt_what=what, debt_due_epoch=due)
    )
    owes = next(iter(await active_bonds(ctx.session, [BondKind.OWES], sources=[borrower.id], targets=[lender.id])), None)
    if owes is not None and owes.debt_status is None:
        owes.debt_status = DebtStatus.OPEN
    await change_relation(ctx, lender.id, borrower.id, civ.loan_relation, MemoryKind.GIFTED_ME, note="loan")
    text = f"{lender.name} lent {lent} {what} to {borrower.name}, who was in need; due Epoch {due}."
    await ctx.chronicle(ChronicleKind.DEBT, text, template_key="civilization.loan", entity_ids=[lender.id, borrower.id])
    return text


async def _loan_candidate(ctx: TickContext) -> tuple[EntityRow, EntityRow] | None:
    civ = ctx.rules.civilization
    communities = [item for item in unheld(await canon(ctx.session, COMMUNITY_TYPES)) if wealth_key(item) is not None]
    lenders = sorted(
        (item for item in communities if (wealth_of(item) or 0) >= civ.loan_lender_min and may(ctx.rules, item, TierCapability.LOAN)),
        key=lambda item: (-(wealth_of(item) or 0), item.id),
    )
    atlas = await RegionAtlas.load(ctx.session)
    bonds = BondRepository(ctx.session)
    for lender in lenders:
        for borrower in communities:
            if borrower.id == lender.id or borrower.world_id != lender.world_id or (wealth_of(borrower) or 0) > civ.loan_borrower_max:
                continue
            if atlas.distance(lender.id, borrower.id) > civ.loan_distance or await bonds.exists_between(lender.id, borrower.id, BondKind.ENEMY):
                continue
            if await active_bonds(ctx.session, [BondKind.OWES], sources=[borrower.id], targets=[lender.id]):
                continue
            return lender, borrower
    return None


async def spontaneous_loans(ctx: TickContext) -> None:
    await repayments(ctx)
    await late_debts(ctx)
    candidate = await _loan_candidate(ctx)
    if candidate is not None and ctx.rng("loan").chance(ctx.rules.civilization.loan_chance):
        text = await lend(ctx, *candidate, ctx.rules.civilization.loan_amount)
        await note(ctx, text, key="civilization.loan_note", ids=[candidate[0].id, candidate[1].id])


def good_value(entity: EntityRow) -> int:
    value = stat(entity, "value")
    if value is not None:
        return value
    return max((stat(entity, key) or 0 for key in VALUE_KEYS), default=0)


async def owned_goods(ctx: TickContext, owner_id: int) -> list[EntityRow]:
    goods = []
    for bond in await active_bonds(ctx.session, [BondKind.OWNS], sources=[owner_id]):
        item = await ctx.session.get(EntityRow, bond.target_node_id)
        if item is not None and item.status is EntityStatus.CANON and item.entity_type in GOODS_TYPES:
            goods.append(item)
    return goods


async def swap_goods(ctx: TickContext, first: EntityRow, second: EntityRow, first_good: EntityRow, second_good: EntityRow) -> str:
    bonds = BondRepository(ctx.session)
    await bonds.close_between(first.id, first_good.id, [BondKind.OWNS], ctx.epoch, "bartered away")
    await bonds.close_between(second.id, second_good.id, [BondKind.OWNS], ctx.epoch, "bartered away")
    await bonds.connect(BondDraft(first.id, second_good.id, BondKind.OWNS, ctx.epoch, "barter"))
    await bonds.connect(BondDraft(second.id, first_good.id, BondKind.OWNS, ctx.epoch, "barter"))
    await change_relation(ctx, first.id, second.id, ctx.rules.civilization.barter_relation, MemoryKind.TRADED_WITH, note="barter")
    text = f"{first.name} and {second.name} bartered: {first_good.name} for {second_good.name}."
    await ctx.chronicle(ChronicleKind.TRADE, text, template_key="civilization.barter", entity_ids=[first.id, second.id, first_good.id, second_good.id])
    return text


async def _barter_candidate(ctx: TickContext) -> tuple[EntityRow, EntityRow, EntityRow, EntityRow] | None:
    gap = ctx.rules.civilization.barter_max_value_diff
    bonds = BondRepository(ctx.session)
    for bond in await active_bonds(ctx.session, [BondKind.TRADES_WITH]):
        first, second = await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)
        if first is None or second is None or first.id == second.id or first.status is not EntityStatus.CANON or second.status is not EntityStatus.CANON:
            continue
        if await bonds.exists_between(first.id, second.id, BondKind.ENEMY):
            continue
        for mine in await owned_goods(ctx, first.id):
            theirs = next((item for item in await owned_goods(ctx, second.id) if abs(good_value(item) - good_value(mine)) <= gap), None)
            if theirs is not None:
                return first, second, mine, theirs
    return None


async def spontaneous_barter(ctx: TickContext) -> None:
    candidate = await _barter_candidate(ctx)
    if candidate is not None and ctx.rng("barter").chance(ctx.rules.civilization.barter_chance):
        await note(ctx, await swap_goods(ctx, *candidate), key="civilization.barter_note", ids=[item.id for item in candidate])


async def adopt(ctx: TickContext, adopter: EntityRow, child: EntityRow) -> str:
    await BondRepository(ctx.session).connect(BondDraft(child.id, adopter.id, BondKind.FOSTERED_BY, ctx.epoch, "adopted: left alone, taken in"))
    await change_relation(ctx, adopter.id, child.id, ctx.rules.civilization.adoption_relation, MemoryKind.GOODWILL, note="adoption")
    text = f"{adopter.name} adopted the orphaned {child.name}."
    await ctx.chronicle(ChronicleKind.LINEAGE, text, template_key="civilization.adoption", entity_ids=[adopter.id, child.id])
    return text


async def _orphan(ctx: TickContext, child: EntityRow) -> bool:
    for parent_id in [*await parents_of(ctx.session, child.id), *await fosterers_of(ctx.session, child.id)]:
        parent = await ctx.session.get(EntityRow, parent_id)
        if parent is not None and parent.entity_type is EntityType.MORTAL and parent.status is EntityStatus.CANON:
            return False
    return True


async def _adoption_candidate(ctx: TickContext) -> tuple[EntityRow, EntityRow] | None:
    civ = ctx.rules.civilization
    captives = set(await ctx.session.scalars(select(CaptiveRow.captive_entity_id).where(CaptiveRow.status == CaptiveStatus.HELD)))
    mortals = [item for item in await canon(ctx.session, [EntityType.MORTAL]) if stat(item, AGE_KEY) is not None and item.id not in captives]
    children = sorted(
        (item for item in mortals if stat_or(item, AGE_KEY, 0) <= civ.adoption_max_child_age), key=lambda item: (stat_or(item, AGE_KEY, 0), item.id)
    )
    atlas = await RegionAtlas.load(ctx.session)
    bonds = BondRepository(ctx.session)
    for child in children:
        if not await _orphan(ctx, child):
            continue
        for adopter in mortals:
            if (
                adopter.id == child.id
                or adopter.world_id != child.world_id
                or stat_or(adopter, AGE_KEY, 0) - stat_or(child, AGE_KEY, 0) < civ.adoption_min_age_gap
            ):
                continue
            near = adopter.location_id == child.location_id and adopter.location_id is not None
            if not near and atlas.distance(adopter.id, child.id) > civ.adoption_distance:
                continue
            if (
                await bonds.exists_between(adopter.id, child.id, BondKind.PARENT_OF)
                or await bonds.exists_between(adopter.id, child.id, BondKind.FOSTERED_BY)
                or await bonds.exists_between(adopter.id, child.id, BondKind.ENEMY)
            ):
                continue
            return adopter, child
    return None


async def spontaneous_adoption(ctx: TickContext) -> None:
    candidate = await _adoption_candidate(ctx)
    if candidate is not None and ctx.rng("adoption").chance(ctx.rules.civilization.adoption_chance):
        await note(ctx, await adopt(ctx, *candidate), key="civilization.adoption_note", ids=[candidate[0].id, candidate[1].id])


@dataclass(frozen=True)
class TreatyOffer:
    first: EntityRow
    second: EntityRow
    kind: BondKind
    relation: int
    method: str


async def sign_treaty(ctx: TickContext, offer: TreatyOffer) -> str:
    clauses = [Clause(ClauseKind.TRADE_RIGHTS, offer.first.id, offer.second.id), Clause(ClauseKind.NON_AGGRESSION, offer.first.id, offer.second.id)]
    if offer.kind is BondKind.ALLY:
        clauses.extend([Clause(ClauseKind.CALL_TO_ARMS, offer.first.id, offer.second.id), Clause(ClauseKind.CALL_TO_ARMS, offer.second.id, offer.first.id)])
    await sign(
        ctx,
        TreatyKind.INTERWORLD,
        [(offer.first.id, PartyRole.SIGNATORY), (offer.second.id, PartyRole.SIGNATORY)],
        clauses=clauses,
        until=ctx.epoch + ctx.rules.treaties.alliance_epochs,
    )
    if offer.kind is BondKind.ALLY:
        await sign(
            ctx,
            TreatyKind.ALLIANCE_DEFENSIVE,
            [(offer.first.id, PartyRole.SIGNATORY), (offer.second.id, PartyRole.SIGNATORY)],
            clauses=clauses[2:],
            until=ctx.epoch + ctx.rules.treaties.alliance_epochs,
            witnessed=False,
        )
    await change_relation(ctx, offer.first.id, offer.second.id, ctx.rules.civilization.treaty_relation, MemoryKind.ALLIED_WITH, note="interworld treaty")
    kind = "alliance" if offer.kind is BondKind.ALLY else "trade"
    first_world, second_world = await world_name(ctx.session, offer.first.world_id), await world_name(ctx.session, offer.second.world_id)
    parties = f"{offer.first.name} of the world {first_world} and {offer.second.name} of the world {second_world}"
    text = f"{parties} made an interworld {kind} treaty over the {offer.method} route between them."
    await ctx.chronicle(ChronicleKind.DIPLOMACY, text, template_key="civilization.treaty", entity_ids=[offer.first.id, offer.second.id])
    return text


async def _offer_for(ctx: TickContext, first: EntityRow, second: EntityRow, method: str) -> TreatyOffer | None:
    civ = ctx.rules.civilization
    bonds = BondRepository(ctx.session)
    if await bonds.exists_between(first.id, second.id, BondKind.ENEMY) or await bonds.exists_between(first.id, second.id, BondKind.ALLY):
        return None
    value = await relation(ctx.session, ctx.rules, first.id, second.id)
    trading = await bonds.exists_between(first.id, second.id, BondKind.TRADES_WITH)
    if not trading and value >= civ.treaty_trade_min_relation:
        return TreatyOffer(first, second, BondKind.TRADES_WITH, value, method)
    if trading and value >= civ.treaty_alliance_min_relation:
        return TreatyOffer(first, second, BondKind.ALLY, value, method)
    return None


async def _top_communities(ctx: TickContext, world_id: int) -> list[EntityRow]:
    communities = [item for item in await canon(ctx.session, COMMUNITY_TYPES, world_id) if may(ctx.rules, item, TierCapability.INTERWORLD_TREATY)]
    return sorted(communities, key=lambda item: (-headcount(item), item.id))[: ctx.rules.civilization.treaty_candidates]


async def spontaneous_treaty(ctx: TickContext) -> None:
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    best: TreatyOffer | None = None
    for route in book.open_known():
        if route.world_a_id == route.world_b_id:
            continue
        for first in await _top_communities(ctx, route.world_a_id):
            for second in await _top_communities(ctx, route.world_b_id):
                if held(first.id, second.id):
                    continue
                offer = await _offer_for(ctx, first, second, method_label(route.method))
                if offer is not None and (best is None or offer.relation > best.relation):
                    best = offer
    if best is not None and ctx.rng("treaty").chance(ctx.rules.civilization.treaty_chance):
        await note(ctx, await sign_treaty(ctx, best), key="civilization.treaty_note", ids=[best.first.id, best.second.id])


@reads(
    "faction.wealth",
    "item.damage",
    "item.might",
    "item.protection",
    "language.complexity",
    "mortal.age",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "resource.value",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.captives",
    "table.civilization_tier_locks",
    "table.community_relations",
    "table.community_stocks",
    "table.cosmos",
    "table.culture_values",
    "table.currencies",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.held_identities",
    "table.holder_levels",
    "table.item_profiles",
    "table.language_grammar",
    "table.language_intelligibility",
    "table.language_profiles",
    "table.language_registers",
    "table.lexemes",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_materials",
    "table.nodes",
    "table.personality_values",
    "table.region_environment",
    "table.relationships",
    "table.reputations",
    "table.resource_profiles",
    "table.routes",
    "table.ruler_currencies",
    "table.skills",
    "table.speaker_cohorts",
    "table.traits",
    "table.tributes",
    "table.vessel_profiles",
    "table.world_maps",
    "table.world_materials",
)
@writes(
    "faction.wealth",
    "people.wealth",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_grammar",
    "table.language_intelligibility",
    "table.memories",
    "table.name_registry",
    "table.node_materials",
    "table.thread_links",
    "table.threads",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
)
async def civilization_phase(ctx: TickContext) -> None:
    await update_tiers(ctx)
    await colony_independence(ctx)
    found = await federations(ctx)
    if found is not None:
        await note(ctx, f"{found.name} was founded across the worlds.", key="civilization.federation_note", ids=[found.id])
    await previous_creations(ctx)
    await spontaneous_loans(ctx)
    await spontaneous_barter(ctx)
    await spontaneous_adoption(ctx)
    await spontaneous_treaty(ctx)
    await ctx.session.flush()


async def _living(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such living record.")
    return entity


async def set_tier(session: AsyncSession, rules: Rules, entity_id: int, tier: int, *, lock: bool) -> EntityRow:
    if tier not in [item.value for item in T]:
        raise ValidationFailedError("No such civilization tier.")
    ctx = await manual_context(session, "tier", rules, key=str(entity_id))
    entity = await _living(session, entity_id)
    if entity.entity_type not in TIER_TYPES:
        raise ValidationFailedError("Only peoples, settlements and factions have a civilization tier.")
    existing = await session.get(CivilizationTierLockRow, entity_id)
    if lock and existing is None:
        session.add(CivilizationTierLockRow(entity_id=entity_id, tier=tier, since_epoch=ctx.epoch))
    elif lock and existing is not None:
        existing.tier = tier
    elif existing is not None:
        await session.delete(existing)
    entity.civ_tier_epoch = None
    await apply_tier(ctx, entity, tier)
    await session.flush()
    return entity


async def grant_independence(session: AsyncSession, rules: Rules, colony_id: int, *, war: bool = False) -> str:
    ctx = await manual_context(session, "independence", rules, key=str(colony_id))
    colony = await _living(session, colony_id)
    bond = next(iter(await active_bonds(session, [BondKind.RULES], targets=[colony.id])), None)
    if bond is None:
        raise ValidationFailedError(f"{colony.name} is ruled by no one.")
    return await declare_independence(ctx, colony, await _living(session, bond.source_node_id), bond, war=war)


async def reclaim_colony(session: AsyncSession, rules: Rules, mother_id: int, colony_id: int) -> None:
    ctx = await manual_context(session, "reclaim", rules, key=f"{mother_id}:{colony_id}")
    mother, colony = await _living(session, mother_id), await _living(session, colony_id)
    await BondRepository(session).connect(BondDraft(mother.id, colony.id, BondKind.RULES, ctx.epoch, "colony beyond the worlds"))
    repository = EntityRepository(session)
    await repository.remove_flag(colony.id, EntityFlag.INDEPENDENT)
    await repository.add_flag(colony.id, EntityFlag.COLONY, ctx.epoch)


async def order_previous_creation(session: AsyncSession, rules: Rules, world_id: int) -> EntityRow:
    ctx = await manual_context(session, "previous_creation", rules, key=str(world_id))
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    ruin = await reveal_previous_creation(ctx, world)
    if ruin is None:
        raise ValidationFailedError("A world without regions hides no ruins.")
    return ruin


async def impose_loan(session: AsyncSession, rules: Rules, lender_id: int, borrower_id: int, amount: int) -> str:
    ctx = await manual_context(session, "loan", rules, key=f"{lender_id}:{borrower_id}")
    return await lend(ctx, await _living(session, lender_id), await _living(session, borrower_id), amount)


async def _debt(session: AsyncSession, bond_id: int) -> BondRow:
    bond = await session.get(BondRow, bond_id)
    if bond is None or bond.kind is not BondKind.OWES or not bond.active:
        raise NotFoundError("No such open debt.")
    return bond


async def forgive_debt(session: AsyncSession, rules: Rules, bond_id: int) -> None:
    ctx = await manual_context(session, "forgive", rules, key=str(bond_id))
    bond = await _debt(session, bond_id)
    bond.debt_status = DebtStatus.FORGIVEN
    await BondRepository(session).deactivate(bond, ctx.epoch, "forgiven")


async def enforce_debt(session: AsyncSession, rules: Rules, bond_id: int) -> str:
    ctx = await manual_context(session, "enforce", rules, key=str(bond_id))
    bond = await _debt(session, bond_id)
    return await repay(ctx, bond, await _living(session, bond.source_node_id), await _living(session, bond.target_node_id))


async def order_barter(session: AsyncSession, rules: Rules, first_id: int, second_id: int) -> str:
    ctx = await manual_context(session, "barter", rules, key=f"{first_id}:{second_id}")
    first, second = await _living(session, first_id), await _living(session, second_id)
    mine, theirs = await owned_goods(ctx, first.id), await owned_goods(ctx, second.id)
    if not mine or not theirs:
        raise ValidationFailedError("Both sides need something to barter.")
    return await swap_goods(ctx, first, second, mine[0], min(theirs, key=lambda item: abs(good_value(item) - good_value(mine[0]))))


async def order_adoption(session: AsyncSession, rules: Rules, adopter_id: int, child_id: int) -> str:
    ctx = await manual_context(session, "adoption", rules, key=f"{adopter_id}:{child_id}")
    return await adopt(ctx, await _living(session, adopter_id), await _living(session, child_id))


async def order_treaty(session: AsyncSession, rules: Rules, first_id: int, second_id: int, *, alliance: bool) -> str:
    ctx = await manual_context(session, "treaty", rules, key=f"{first_id}:{second_id}")
    first, second = await _living(session, first_id), await _living(session, second_id)
    kind = BondKind.ALLY if alliance else BondKind.TRADES_WITH
    return await sign_treaty(ctx, TreatyOffer(first, second, kind, await relation(session, rules, first.id, second.id), "worlds' will"))


async def run_civilization_phase(session: AsyncSession, rules: Rules) -> None:
    await civilization_phase(await manual_context(session, "civilization", rules))


PHASES = (Phase("civilization", civilization_phase),)
