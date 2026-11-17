import math
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import or_, select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import LawProfileRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import WarEnding
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import asabiyya_factor
from aerona.engine.demography.kinship import assimilation_factor
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.language import intelligibility
from aerona.engine.mind.drives import closeness
from aerona.engine.mind.space import value_distance
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.life_cycles import turn_to_ruin
from aerona.engine.phases.religion_spread import SCHISM_SUBTYPE
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.phases.warfare import is_uprising
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import is_living_god
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.population_history import median_of
from aerona.engine.primitives.queries import add_flag, canon, connect, living_entity, spoken_language
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import headcount_bounds, set_stats, shift_stat, stat
from aerona.engine.services.community_relations import relation
from aerona.rules.registry import Rules

CARRIER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
CARRIER_BONDS = (BondKind.PRODUCED, BondKind.CELEBRATES, BondKind.TELLS_OF, BondKind.OWNS, BondKind.RELATED, BondKind.BUILT)
SWALLOWING_KINDS = frozenset({EngineKind.EARTHQUAKE, EngineKind.FLOOD})
OWNING_BONDS = (BondKind.OWNS, BondKind.HOLDS_CAPTIVE)
SCHISM_REASON = "schism"


class RecordEnd(StrEnum):
    REPEAL = "repeal"
    ABANDON = "abandon"
    FORGET = "forget"
    DISBAND = "disband"
    LOSE = "lose"
    ASSIMILATE = "assimilate"


END_TYPES: dict[RecordEnd, frozenset[EntityType]] = {
    RecordEnd.REPEAL: frozenset({EntityType.LAW}),
    RecordEnd.ABANDON: frozenset({EntityType.SETTLEMENT}),
    RecordEnd.FORGET: frozenset({EntityType.ARTWORK, EntityType.TRADITION, EntityType.LEGEND}),
    RecordEnd.DISBAND: frozenset({EntityType.CULT}),
    RecordEnd.LOSE: frozenset({EntityType.ITEM}),
    RecordEnd.ASSIMILATE: frozenset({EntityType.PEOPLE}),
}
END_FLAGS: dict[RecordEnd, EntityFlag] = {
    RecordEnd.REPEAL: EntityFlag.REPEALED,
    RecordEnd.ABANDON: EntityFlag.ABANDONED,
    RecordEnd.FORGET: EntityFlag.FORGOTTEN,
    RecordEnd.DISBAND: EntityFlag.DISBANDED,
    RecordEnd.LOSE: EntityFlag.LOST,
    RecordEnd.ASSIMILATE: EntityFlag.ASSIMILATED,
}


def resisted(stat_value: int | None, share_pct: int) -> float:
    return max(0.0, 1 - clamp_int(stat_value or 0, 0, 100) * share_pct / (100 * 100))


def chance_round(ctx: TickContext, value: float, stream: str) -> int:
    whole = math.floor(value)
    return whole + (1 if ctx.rng(stream).random() < value - whole else 0)


async def end_record(ctx: TickContext, entity: EntityRow, flag: EntityFlag, sentence: str, status: EntityStatus = EntityStatus.DEAD) -> None:
    await add_flag(ctx.session, entity.id, flag, ctx.epoch)
    await retire_in(ctx, entity, sentence, status, close_bonds=True)


async def conquered_this_epoch(ctx: TickContext) -> set[int]:
    losers = set(await ctx.session.scalars(select(WarRow.loser_entity_id).where(WarRow.ended_epoch == ctx.epoch, WarRow.ending == WarEnding.CONQUEST)))
    ruled = await ctx.session.scalars(
        select(BondRow.target_node_id).where(BondRow.kind == BondKind.RULES, BondRow.epoch == ctx.epoch, BondRow.description.like("conquest%"))
    )
    return {item for item in losers if item is not None} | set(ruled)


def repeal_chance(rules: Rules, law: EntityRow, *, orphaned: bool, conquered: float, rebels: bool) -> tuple[float, str | None]:
    cycles = rules.life_cycles
    if orphaned:
        return float(cycles.repeal_orphan_chance), "its settlement is gone"
    unjust = (stat(law, "justice") or 0) < cycles.unjust_justice
    chance, reason = 0.0, None
    if conquered > 0:
        chance, reason = chance + cycles.repeal_conquest_chance * conquered, "the new masters did not recognise it"
    if unjust:
        chance, reason = chance + cycles.repeal_unjust_chance, reason or "the people could not bear its injustice"
    if rebels and unjust:
        chance, reason = chance + cycles.repeal_rebels_bonus, "the rebels burned it"
    return chance * resisted(stat(law, "rigidity"), cycles.rigidity_resistance_pct), reason


async def laws(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    conquered = await conquered_this_epoch(ctx)
    rebels = {faction.location_id for faction in await canon(ctx.session, [EntityType.FACTION]) if is_uprising(faction) and faction.location_id is not None}
    rng = ctx.rng("repeal")
    repealed = 0
    for law in await canon(ctx.session, [EntityType.LAW]):
        place = await ctx.session.get(EntityRow, law.location_id) if law.location_id is not None else None
        unjust = (stat(law, "justice") or 0) < cycles.unjust_justice
        oppressive = unjust and (stat(law, "rigidity") or 0) >= cycles.oppression_rigidity
        if oppressive and place is not None and place.status is EntityStatus.CANON and place.entity_type is EntityType.SETTLEMENT:
            shift_stat(place, "prosperity", -cycles.oppression_prosperity)
        if repealed >= cycles.repeal_cap or ctx.epoch - law.birth_epoch < cycles.law_grace_epochs:
            continue
        orphaned = place is not None and place.status is not EntityStatus.CANON
        profile = await ctx.session.get(LawProfileRow, law.id)
        if profile is not None and "repeal" in profile.locked:
            continue
        clash = profile.conflict / 100 if profile is not None else (1.0 if place is not None and place.id in conquered else 0.0)
        chance, reason = repeal_chance(ctx.rules, law, orphaned=orphaned, conquered=clash, rebels=place is not None and place.id in rebels)
        if not chance or reason is None or not rng.chance(chance):
            continue
        await end_record(ctx, law, EntityFlag.REPEALED, f"repealed; {reason}")
        repealed += 1
        await note(ctx, f"The law {law.name} was repealed: {reason}.", key="institutions.repealed", ids=[law.id, *([place.id] if place is not None else [])])
    ctx.count("repealed", repealed)
    return repealed


async def worshipped(ctx: TickContext, entity_id: int) -> int | None:
    bonds = await BondRepository(ctx.session).outgoing(entity_id, BondKind.WORSHIPS)
    return bonds[0].target_node_id if bonds else None


async def schism_parent(ctx: TickContext, sect: EntityRow) -> EntityRow | None:
    statement = (
        select(BondRow)
        .where(
            BondRow.kind == BondKind.ENEMY,
            BondRow.description == SCHISM_REASON,
            or_(BondRow.source_node_id == sect.id, BondRow.target_node_id == sect.id),
        )
        .order_by(BondRow.id)
    )
    bond = await ctx.session.scalar(statement.limit(1))
    if bond is None:
        return None
    other = bond.target_node_id if bond.source_node_id == sect.id else bond.source_node_id
    return await living_entity(ctx.session, other)


async def join_cult(ctx: TickContext, cult: EntityRow, into: EntityRow, *, reconciled: bool) -> None:
    low, high = headcount_bounds(ctx.rules, into)
    joining = stat(cult, "followers") or 0
    set_stats(into, followers=clamp_int((stat(into, "followers") or 0) + joining, low, high))
    await connect(ctx.session, cult.id, into.id, BondKind.PART_OF, ctx.epoch, description="returned to its mother cult" if reconciled else "merged")
    sentence = f"made peace with {into.name} and returned to it" if reconciled else f"merged with {into.name}"
    await end_record(ctx, cult, EntityFlag.MERGED, sentence)
    text = (
        f"{cult.name} made peace with {into.name}, which it had split from; {several(joining, 'follower', 'followers')} returned to their old congregation."
        if reconciled
        else f"{cult.name} merged with {into.name}, which worships the same god; its followers are now theirs."
    )
    await note(ctx, text, key="institutions.cult_merged", ids=[cult.id, into.id])


@dataclass(frozen=True)
class CultBoard:
    cults: list[EntityRow]
    medians: dict[int, int]
    gods: dict[int, int | None]


async def _merge_target(ctx: TickContext, cult: EntityRow, board: CultBoard, ended: set[int]) -> tuple[EntityRow, bool] | None:
    cycles = ctx.rules.life_cycles
    rng = ctx.rng(f"cult_merge.{cult.id}")
    if cult.subtype == SCHISM_SUBTYPE:
        parent = await schism_parent(ctx, cult)
        at_peace = parent is not None and not await BondRepository(ctx.session).active_between(cult.id, parent.id, [BondKind.ENEMY])
        if parent is not None and at_peace and (stat(parent, "zeal") or 0) < cycles.cult_zeal_block and rng.chance(cycles.cult_reconcile_chance):
            return parent, True
    god = board.gods.get(cult.id)
    if god is None:
        return None
    followers = stat(cult, "followers") or 0
    larger = [
        other
        for other in board.cults
        if other.id != cult.id
        and other.id not in ended
        and other.world_id == cult.world_id
        and (stat(other, "followers") or 0) * cycles.cult_merge_ratio_pct / 100 > followers
        and (stat(other, "zeal") or 0) < cycles.cult_zeal_block
        and board.gods.get(other.id) == god
    ]
    best = max(larger, key=lambda other: (stat(other, "followers") or 0, -other.id), default=None)
    return (best, False) if best is not None and rng.chance(cycles.cult_merge_chance) else None


async def cults(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    living = await canon(ctx.session, [EntityType.CULT])
    by_world: dict[int, list[int]] = defaultdict(list)
    for cult in living:
        by_world[cult.world_id].append(stat(cult, "followers") or 0)
    eligible = [cult for cult in living if ctx.epoch - cult.birth_epoch >= cycles.cult_grace_epochs and cult.engine_kind is not EngineKind.RESURRECTION_ORDER]
    board = CultBoard(
        eligible, {world: median_of(values) for world, values in by_world.items()}, {cult.id: await worshipped(ctx, cult.id) for cult in eligible}
    )
    ended: set[int] = set()
    merged = disbanded = 0
    for cult in eligible:
        if merged >= cycles.cult_cap:
            break
        if cult.id in ended or (stat(cult, "zeal") or 0) >= cycles.cult_zeal_block:
            continue
        target = await _merge_target(ctx, cult, board, ended)
        if target is None or target[0].id in ended:
            continue
        await join_cult(ctx, cult, target[0], reconciled=target[1])
        ended.add(cult.id)
        merged += 1
    for cult in eligible:
        if disbanded >= cycles.cult_cap:
            break
        if cult.id in ended:
            continue
        small = (stat(cult, "followers") or 0) < board.medians.get(cult.world_id, 0) * cycles.cult_small_pct / 100
        if not small and (stat(cult, "influence") or 0) >= cycles.cult_weak_influence:
            continue
        home = await ctx.session.get(EntityRow, cult.location_id) if cult.location_id is not None else None
        orphaned = board.gods.get(cult.id) is None or (home is not None and home.status is not EntityStatus.CANON)
        if not ctx.rng(f"cult_disband.{cult.id}").chance(cycles.cult_disband_chance + (cycles.cult_godless_bonus if orphaned else 0)):
            continue
        reason = "it had no god or home left to worship" if orphaned else "its last followers went to other faiths"
        await end_record(ctx, cult, EntityFlag.DISBANDED, f"disbanded; {reason}")
        ended.add(cult.id)
        disbanded += 1
        await note(ctx, f"{cult.name} disbanded; {reason}.", key="institutions.cult_disbanded", ids=[cult.id, *([home.id] if home is not None else [])])
    ctx.count("cults_merged", merged)
    ctx.count("cults_disbanded", disbanded)
    return merged + disbanded


async def tongues(ctx: TickContext, entity_id: int) -> set[int]:
    return {bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(entity_id, BondKind.SPEAKS)}


async def absorb_people(ctx: TickContext, people: EntityRow, into: EntityRow, *, union: bool, reason: str) -> None:
    cycles = ctx.rules.life_cycles
    low, high = headcount_bounds(ctx.rules, into)
    set_stats(
        into, population=clamp_int((stat(into, "population") or 0) + round_half_up((stat(people, "population") or 0) * cycles.people_kept_pct / 100), low, high)
    )
    bonds = BondRepository(ctx.session)
    for bond in await bonds.outgoing(people.id, BondKind.KNOWS):
        knowledge = await living_entity(ctx.session, bond.target_node_id)
        if knowledge is not None:
            await teach(ctx, into.id, knowledge, f"came from {people.name}")
    for kind in (BondKind.RULES, BondKind.OWNS):
        for bond in await bonds.outgoing(people.id, kind):
            await bonds.deactivate(bond, ctx.epoch, f"passed to {into.name}")
            if bond.target_node_id != into.id:
                await bonds.connect(BondDraft(into.id, bond.target_node_id, kind, ctx.epoch, f"passed from {people.name}"))
    await connect(ctx.session, people.id, into.id, BondKind.PART_OF, ctx.epoch, description="united" if union else "assimilated")
    await end_record(ctx, people, EntityFlag.MERGED if union else EntityFlag.ASSIMILATED, reason)


async def folds_in(ctx: TickContext, people: EntityRow, into: EntityRow, *, shared: bool) -> bool:
    table = ctx.rules.peoples
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    if not shared or culture is None or culture.cohesion >= table.assimilation_cohesion:
        return False
    return value_distance(await culture_of(ctx.session, people.id), await culture_of(ctx.session, into.id)) < table.assimilation_distance


async def word_share(ctx: TickContext, first: int, second: int) -> float:
    ours, theirs = await spoken_language(ctx.session, first), await spoken_language(ctx.session, second)
    floor = ctx.rules.interpreters.assimilation_pct / PERCENT
    if ours is None or theirs is None:
        return 1.0
    return floor + (1 - floor) * await intelligibility(ctx.session, ctx.rules, ours.id, theirs.id, ctx.epoch) / PERCENT


async def joining(ctx: TickContext, people: EntityRow, largest: EntityRow, *, ratio: float) -> bool | None:
    cycles = ctx.rules.life_cycles
    shared = bool(await tongues(ctx, people.id) & await tongues(ctx, largest.id))
    rng = ctx.rng(f"peoples.{people.id}")
    kinship = await closeness(ctx.session, people.id, largest.id) * assimilation_factor(ctx.rules, await ctx.session.get(UnionCustomRow, people.id))
    kinship /= max(0.1, await asabiyya_factor(ctx.session, [people.id], ctx.rules.asabiyya.assimilation_weight))
    if await folds_in(ctx, people, largest, shared=shared):
        return False if rng.chance(cycles.assimilation_chance * 2 * kinship) else None
    if ratio <= cycles.assimilation_ratio_pct:
        rules_it = bool(await BondRepository(ctx.session).active_between(largest.id, people.id, [BondKind.RULES]))
        chance = cycles.assimilation_chance + (cycles.assimilation_rule_bonus if rules_it else 0) + (cycles.assimilation_language_bonus if shared else 0)
        understood = 1.0 if shared else await word_share(ctx, people.id, largest.id)
        regard = max(0.0, 1 + await relation(ctx.session, ctx.rules, people.id, largest.id) / PERCENT * cycles.assimilation_opinion_pct / PERCENT)
        return False if rng.chance(chance * kinship * understood * regard) else None
    if ratio >= cycles.union_ratio_pct and shared and await relation(ctx.session, ctx.rules, people.id, largest.id) >= cycles.union_relation:
        same_god = await BondRepository(ctx.session).patron(people.id) == await BondRepository(ctx.session).patron(largest.id)
        return True if same_god and rng.chance(cycles.union_chance * kinship) else None
    return None


async def peoples(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    atlas = await RegionAtlas.load(ctx.session)
    living = await canon(ctx.session, [EntityType.PEOPLE])
    by_region: dict[int, list[EntityRow]] = defaultdict(list)
    for people in living:
        region = atlas.top_region(people.id)
        if region is not None:
            by_region[region].append(people)
    ended: set[int] = set()
    done = 0
    for people in living:
        if done >= cycles.people_cap:
            break
        if people.id in ended or ctx.epoch - people.birth_epoch < cycles.people_grace_epochs:
            continue
        size = stat(people, "population") or 0
        region = atlas.top_region(people.id)
        bigger = [
            other for other in by_region.get(region or 0, []) if other.id != people.id and other.id not in ended and (stat(other, "population") or 0) > size
        ]
        largest = max(bigger, key=lambda other: (stat(other, "population") or 0, -other.id), default=None)
        if largest is None:
            continue
        verdict = await joining(ctx, people, largest, ratio=size * 100 / max(1, stat(largest, "population") or 0))
        if verdict is None:
            continue
        union = verdict
        reason = f"united with {largest.name} into one people" if union else f"melted into {largest.name}"
        await absorb_people(ctx, people, largest, union=union, reason=reason)
        ended.add(people.id)
        done += 1
        text = (
            f"{people.name} and {largest.name} married into each other and joined their homelands: one people now, called {largest.name}."
            if union
            else f"Over the generations {people.name} melted into {largest.name}; its tongue and name live on only in what others remember."
        )
        await note(ctx, text, key="institutions.people_union" if union else "institutions.people_assimilated", ids=[people.id, largest.id])
    ctx.count("peoples_joined", done)
    return done


@reads(
    "cult.followers",
    "cult.influence",
    "cult.zeal",
    "knowledge.spread",
    "law.justice",
    "law.rigidity",
    "people.population",
    "table.bonds",
    "table.community_relations",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.law_profiles",
    "table.nodes",
    "table.routes",
    "table.wars",
    "table.world_maps",
)
@writes(
    "cult.followers",
    "knowledge.spread",
    "people.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.routes",
)
async def institution_cycles(ctx: TickContext) -> None:
    await laws(ctx)
    await cults(ctx)
    await peoples(ctx)
    await ctx.session.flush()


async def carriers(ctx: TickContext, work: EntityRow) -> int:
    sources = set()
    for bond in await BondRepository(ctx.session).incoming(work.id):
        if bond.kind not in CARRIER_BONDS:
            continue
        source = await living_entity(ctx.session, bond.source_node_id)
        if source is not None and source.entity_type in CARRIER_TYPES:
            sources.add(source.id)
    gods = 0
    for bond in await BondRepository(ctx.session).outgoing(work.id, BondKind.TELLS_OF):
        if await is_living_god(ctx.session, bond.target_node_id):
            gods += 1
    home = await living_entity(ctx.session, work.location_id)
    return len(sources) + gods + (1 if home is not None and home.entity_type in COMMUNITY_TYPES else 0)


async def works(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    forgotten = 0
    lasting = {row.artwork_entity_id: not row.performed for row in await ctx.session.scalars(select(ArtworkProfileRow))}
    for work in await canon(ctx.session, [EntityType.ARTWORK]):
        count = await carriers(ctx, work)
        written = lasting.get(work.id, False)
        gain = min(cycles.work_carrier_cap, count) * cycles.work_renown_gain
        fading = (cycles.work_fade + (0 if count else cycles.work_orphan_fade)) * (1 - cycles.written_resistance_pct / 100 if written else 1)
        fade = chance_round(ctx, fading, f"work_fade.{work.id}")
        before = stat(work, "renown") or 0
        renown = clamp_int(before + gain - fade, 0, 100)
        influence = stat(work, "influence")
        current = influence if influence is not None else before
        step = min(cycles.work_influence_step, abs(renown - current))
        set_stats(work, renown=renown, influence=clamp_int(current + (step if renown >= current else -step), 0, 100))
        if count or renown > cycles.work_forget_renown or ctx.epoch - work.birth_epoch < cycles.work_grace_epochs:
            continue
        await end_record(ctx, work, EntityFlag.FORGOTTEN, "no one was left to sing, keep or remember it; forgotten")
        forgotten += 1
        tail = "its last copy was lost too" if written else "the last who knew it died"
        await note(ctx, f"{work.name} was forgotten; {tail}.", key="institutions.work_forgotten", ids=[work.id])
    ctx.count("works_forgotten", forgotten)
    return forgotten


async def owned_items(ctx: TickContext) -> set[int]:
    owned: set[int] = set()
    for bond in await ctx.session.scalars(select(BondRow).where(BondRow.kind.in_(OWNING_BONDS), BondRow.state == BondState.ACTIVE)):
        if await living_entity(ctx.session, bond.source_node_id) is not None:
            owned.add(bond.target_node_id)
    bound = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.INSIDE, BondRow.role == BondRole.SPIRIT_BINDING, BondRow.state == BondState.ACTIVE
        )
    )
    for source, target in bound:
        owned.update((source, target))
    return owned


async def items(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    held = await owned_items(ctx)
    lost = 0
    for item in await canon(ctx.session, [EntityType.ITEM]):
        if lost >= cycles.item_cap:
            break
        if item.id in held or ctx.epoch - item.birth_epoch < cycles.item_grace_epochs:
            continue
        place = await living_entity(ctx.session, item.location_id)
        if place is not None and place.entity_type in COMMUNITY_TYPES:
            continue
        if not ctx.rng(f"item_loss.{item.id}").chance(cycles.item_loss_chance * resisted(stat(item, "might"), cycles.item_might_resistance_pct)):
            continue
        where = await ctx.session.get(EntityRow, item.location_id) if item.location_id is not None else None
        at = f" in {where.name}" if where is not None else ""
        await end_record(ctx, item, EntityFlag.LOST, f"lay unowned{at} until its trail was lost")
        lost += 1
        await note(
            ctx, f"{item.name} lay unowned{at} and was lost; no one saw it last.", key="institutions.item_lost", ids=[item.id, *([where.id] if where else [])]
        )
    ctx.count("items_lost", lost)
    return lost


def swallow_sentence(event: EntityRow | None) -> str:
    if event is None:
        return "the earth opened and swallowed it"
    return f"{event.name} drowned it" if event.engine_kind is EngineKind.FLOOD else f"the earth split open in {event.name} and swallowed it"


async def swallow(ctx: TickContext, place: EntityRow, event: EntityRow | None) -> int:
    moved = await EntityRepository(ctx.session).transfer_contents(place, ctx.epoch)
    await end_record(ctx, place, EntityFlag.LOST_IN_DISASTER, swallow_sentence(event), EntityStatus.DESTROYED)
    if event is not None:
        await BondRepository(ctx.session).connect(BondDraft(event.id, place.id, BondKind.CAUSED, ctx.epoch, "swallowed"))
    return moved


async def swallowed_places(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    events = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.EVENT,
            EntityRow.birth_epoch == ctx.epoch,
            EntityRow.engine_kind.in_(list(SWALLOWING_KINDS)),
            EntityRow.location_id.is_not(None),
        )
        .order_by(EntityRow.id)
    )
    swallowed = 0
    for event in list(events):
        if swallowed >= cycles.swallow_cap:
            break
        if (stat(event, "severity") or 0) < cycles.swallow_severity:
            continue
        places = [item for item in await EntityRepository(ctx.session).contents(event.location_id or 0) if item.entity_type is EntityType.PLACE]
        rng = ctx.rng(f"swallow.{event.id}")
        if not places or not rng.chance(cycles.swallow_chance):
            continue
        place = rng.pick(places)
        moved = await swallow(ctx, place, event)
        region = await ctx.session.get(EntityRow, event.location_id) if event.location_id is not None else None
        scattered = f"; what stood in it was scattered across {region.name}" if moved and region is not None else ""
        await note(ctx, f"{event.name} swallowed {place.name}; it is no more{scattered}.", key="institutions.place_swallowed", ids=[event.id, place.id])
        swallowed += 1
    ctx.count("places_swallowed", swallowed)
    return swallowed


@reads(
    "artwork.influence",
    "artwork.renown",
    "event.severity",
    "item.might",
    "table.artwork_profiles",
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
    "table.routes",
)
@writes(
    "artwork.influence",
    "artwork.renown",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def culture_cycles(ctx: TickContext) -> None:
    await works(ctx)
    await items(ctx)
    await swallowed_places(ctx)
    await ctx.session.flush()


async def assimilation_target(ctx: TickContext, people: EntityRow) -> EntityRow:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(people.id)
    others = [
        other
        for other in await canon(ctx.session, [EntityType.PEOPLE])
        if other.id != people.id and region is not None and atlas.top_region(other.id) == region
    ]
    target = max(others, key=lambda other: (stat(other, "population") or 0, -other.id), default=None)
    if target is None:
        raise ValidationFailedError(f"No other people lives in the region of {people.name} for it to melt into.")
    return target


async def order_end(ctx: TickContext, entity_id: int, end: RecordEnd, reason: str) -> EntityRow:
    entity = await living_entity(ctx.session, entity_id)
    if entity is None:
        raise ValidationFailedError("This record is not in the world.")
    if entity.entity_type not in END_TYPES[end]:
        allowed = ", ".join(sorted(item.value for item in END_TYPES[end]))
        raise ValidationFailedError(f"That end cannot be ordered for {entity.name} (needs {allowed}).")
    if end is RecordEnd.ABANDON:
        if len(await canon(ctx.session, [EntityType.SETTLEMENT], entity.world_id)) <= 1:
            raise ValidationFailedError(f"{entity.name} is the last settlement of its world; abandoning it would empty the world.")
        await turn_to_ruin(ctx, entity, f"{reason}; its people left their home")
    elif end is RecordEnd.ASSIMILATE:
        target = await assimilation_target(ctx, entity)
        await absorb_people(ctx, entity, target, union=False, reason=f"{reason}; it melted into {target.name}")
    else:
        await end_record(ctx, entity, END_FLAGS[end], reason)
    return entity


async def merge_cult_by_hand(ctx: TickContext, cult_id: int, into_id: int) -> EntityRow:
    cult, into = await living_entity(ctx.session, cult_id), await living_entity(ctx.session, into_id)
    if cult is None or into is None or cult.entity_type is not EntityType.CULT or into.entity_type is not EntityType.CULT or cult.id == into.id:
        raise ValidationFailedError("Choose two different living cults.")
    await join_cult(ctx, cult, into, reconciled=cult.subtype == SCHISM_SUBTYPE and (await schism_parent(ctx, cult)) == into)
    return into


async def unite_peoples(ctx: TickContext, people_id: int, into_id: int) -> EntityRow:
    people, into = await living_entity(ctx.session, people_id), await living_entity(ctx.session, into_id)
    if people is None or into is None or people.entity_type is not EntityType.PEOPLE or into.entity_type is not EntityType.PEOPLE or people.id == into.id:
        raise ValidationFailedError("Choose two different living peoples.")
    await absorb_people(ctx, people, into, union=True, reason=f"united with {into.name} into one people")
    text = f"{people.name} and {into.name} joined their homelands: one people now, called {into.name}."
    await note(ctx, text, key="institutions.people_union", ids=[people.id, into.id])
    return into


async def swallow_place_by_hand(ctx: TickContext, place_id: int) -> EntityRow:
    place = await living_entity(ctx.session, place_id)
    if place is None or place.entity_type is not EntityType.PLACE:
        raise ValidationFailedError("Only a living place can be swallowed.")
    await swallow(ctx, place, None)
    await note(ctx, f"The earth opened and swallowed {place.name}; it is no more.", key="institutions.place_swallowed", ids=[place.id])
    return place


INSTITUTION_PHASES = (Phase("institution_cycles", institution_cycles),)
CULTURE_PHASES = (Phase("culture_cycles", culture_cycles),)
PHASES = INSTITUTION_PHASES + CULTURE_PHASES
