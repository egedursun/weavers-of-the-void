from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.structures import HOLY_HOUSES
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import BattleRow, SiegeRow, TributeRow, WarRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.integrity import HarmForce
from aerona.domain.enums.war import TributeStatus, WarEnding
from aerona.engine.body.afflictions import desecration_curse
from aerona.engine.context import TickContext
from aerona.engine.dominion.curses import curse_desecrator
from aerona.engine.economy.loot import loot_temple
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.hooks import desecrated
from aerona.engine.mythic.servitors import turned_back
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.population_history import loss_pct, median_of, population_at
from aerona.engine.primitives.queries import add_flag, canon, connect, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import retire, retire_in
from aerona.engine.primitives.stats import headcount_bounds, set_stats, shift_stat, stat
from aerona.engine.services.war import end_tribute
from aerona.engine.structures.damage import harm, ruin_profile
from aerona.engine.structures.readers import kind_of
from aerona.rules.registry import Rules

LEFT_BEHIND_TYPES = frozenset({EntityType.STRUCTURE, EntityType.ITEM})
COLLAPSE_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
BREAKAWAY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION, EntityType.CULT})


@dataclass(frozen=True)
class PopulationHistory:
    before: dict[int, int] | None
    last: dict[int, int] | None


async def population_history(ctx: TickContext) -> PopulationHistory:
    window = ctx.rules.life_cycles.decline_epochs
    return PopulationHistory(await population_at(ctx.session, ctx.epoch - window), await population_at(ctx.session, ctx.epoch - 1))


def end_cost(rules: Rules, entity: EntityRow) -> int:
    cycles = rules.life_cycles
    return cycles.end_cost + entity.power_level * cycles.end_cost_per_power


def is_declining(rules: Rules, now: int, before: int, last: int) -> bool:
    return loss_pct(now, before) >= rules.life_cycles.decline_loss_pct and now <= last


async def turn_to_ruin(ctx: TickContext, settlement: EntityRow, sentence: str) -> list[EntityRow]:
    remains = [item for item in await EntityRepository(ctx.session).contents(settlement.id) if item.entity_type in LEFT_BEHIND_TYPES]
    await add_flag(ctx.session, settlement.id, EntityFlag.ABANDONED, ctx.epoch)
    await add_flag(ctx.session, settlement.id, EntityFlag.RUIN, ctx.epoch)
    await retire(ctx.session, settlement, ctx.epoch, f"Epoch {ctx.epoch}: {sentence}; it turned to ruin.", append=True, close_bonds=True)
    return remains


def _nearest(atlas: RegionAtlas, settlement: EntityRow, others: list[EntityRow]) -> EntityRow | None:
    region = atlas.top_region(settlement.id)
    candidates = [other for other in others if other.id != settlement.id and other.status is EntityStatus.CANON and other.world_id == settlement.world_id]
    return min(
        candidates,
        key=lambda other: (atlas.top_region(other.id) != region, atlas.distance(other.id, settlement.id), -(stat(other, "population") or 0), other.id),
        default=None,
    )


async def abandon_declining(ctx: TickContext, history: PopulationHistory, atlas: RegionAtlas) -> int:
    cycles = ctx.rules.life_cycles
    if history.before is None or history.last is None:
        return 0
    settlements = await canon(ctx.session, [EntityType.SETTLEMENT])
    sheltered = await flags_by_entity(ctx.session, EntityFlag.PROTECTED_FROM_RUIN)
    by_world: dict[int, list[int]] = defaultdict(list)
    for settlement in settlements:
        by_world[settlement.world_id].append(stat(settlement, "population") or 0)
    rng = ctx.rng("abandon")
    abandoned = 0
    for settlement in settlements:
        if abandoned >= cycles.abandon_cap:
            break
        now = stat(settlement, "population") or 0
        before, last = history.before.get(settlement.id), history.last.get(settlement.id)
        if before is None or last is None or settlement.id in sheltered or ctx.epoch - settlement.birth_epoch < cycles.abandon_grace_epochs:
            continue
        if len(by_world[settlement.world_id]) <= 1 or not is_declining(ctx.rules, now, before, last):
            continue
        if now >= median_of(by_world[settlement.world_id]) * cycles.relative_threshold_pct / 100:
            continue
        if (stat(settlement, "prosperity") or 0) > cycles.abandon_max_prosperity or not rng.chance(cycles.abandon_chance):
            continue
        target = _nearest(atlas, settlement, settlements)
        migrants = round_half_up(now * cycles.abandon_migration_pct / 100)
        remains = await turn_to_ruin(ctx, settlement, f"its people dwindled from {before} to {now} and grew poor; the last families left it")
        by_world[settlement.world_id].remove(now)
        moved = ""
        if target is not None and migrants > 0:
            low, high = headcount_bounds(ctx.rules, target)
            set_stats(target, population=clamp_int((stat(target, "population") or 0) + migrants, low, high))
            await connect(ctx.session, settlement.id, target.id, BondKind.MIGRATED_TO, ctx.epoch, description="migration from the ruin")
            moved = f"; its last {several(migrants, 'person', 'people')} moved to {target.name}"
        left = f" Left behind: {', '.join(item.name for item in remains)}." if remains else ""
        ids = [settlement.id, *([target.id] if target is not None else []), *(item.id for item in remains)]
        await note(ctx, f"{settlement.name} dwindled and emptied, and fell to ruin{moved}.{left}", key="life_cycles.abandoned", ids=ids)
        abandoned += 1
    ctx.count("abandoned", abandoned)
    return abandoned


async def _flag_epoch(ctx: TickContext, entity_id: int, flag: EntityFlag) -> int | None:
    row = await ctx.session.get(EntityFlagRow, (entity_id, flag))
    return row.epoch if row is not None else None


async def collapse(ctx: TickContext, community: EntityRow, reason: str) -> str:
    cycles = ctx.rules.life_cycles
    bonds = BondRepository(ctx.session)
    broken: list[EntityRow] = []
    for bond in await bonds.outgoing(community.id, BondKind.RULES):
        subject = await living_entity(ctx.session, bond.target_node_id)
        if subject is None or subject.entity_type not in BREAKAWAY_TYPES:
            continue
        await bonds.deactivate(bond, ctx.epoch, f"collapse of {community.name}")
        shift_stat(subject, "prosperity", -cycles.collapse_chain_prosperity)
        broken.append(subject)
    tributes = list(
        await ctx.session.scalars(select(TributeRow).where(TributeRow.receiver_entity_id == community.id, TributeRow.status == TributeStatus.ACTIVE))
    )
    for row in tributes:
        await end_tribute(ctx, row, TributeStatus.REVOLTED, f"collapse of {community.name}")
    for bond in await bonds.incoming(community.id, BondKind.PAYS_TRIBUTE):
        await bonds.deactivate(bond, ctx.epoch, f"collapse of {community.name}")
    for faction in await EntityRepository(ctx.session).contents(community.id):
        if faction.entity_type is EntityType.FACTION:
            shift_stat(faction, "sway", -cycles.collapse_sway_loss)
    await remove_flag(ctx.session, community.id, EntityFlag.DISSOLVED)
    await add_flag(ctx.session, community.id, EntityFlag.DISSOLVED, ctx.epoch)
    broke = f" {', '.join(subject.name for subject in broken)} broke away from its rule." if broken else ""
    paid = " Those who paid it tribute stopped paying." if tributes else ""
    text = f"{community.name} collapsed: {reason}.{broke}{paid}"
    await note(ctx, text, key="life_cycles.collapse", ids=[community.id, *(subject.id for subject in broken), *(row.payer_entity_id for row in tributes)])
    return text


async def collapses(ctx: TickContext, history: PopulationHistory) -> int:
    cycles = ctx.rules.life_cycles
    if history.before is None:
        return 0
    rng = ctx.rng("collapse")
    collapsed = 0
    for community in await canon(ctx.session, COLLAPSE_TYPES):
        if collapsed >= cycles.collapse_cap:
            break
        now, before = stat(community, "population") or 0, history.before.get(community.id)
        if before is None or loss_pct(now, before) < cycles.collapse_loss_pct:
            continue
        prosperity = stat(community, "prosperity")
        if prosperity is not None and prosperity > cycles.collapse_max_prosperity:
            continue
        since = await _flag_epoch(ctx, community.id, EntityFlag.DISSOLVED)
        if since is not None and ctx.epoch - since < cycles.collapse_grace_epochs:
            continue
        if not rng.chance(cycles.collapse_chance):
            continue
        await collapse(
            ctx, community, f"in {several(cycles.decline_epochs, 'epoch', 'epochs')} its people fell from {before} to {now} and its stores ran empty"
        )
        collapsed += 1
    ctx.count("collapsed", collapsed)
    return collapsed


async def raze(ctx: TickContext, structure: EntityRow, sentence: str, cause_id: int | None = None, destroyer_id: int | None = None) -> None:
    holy = await kind_of(ctx.session, structure.id) in HOLY_HOUSES
    if holy and destroyer_id is not None and await turned_back(ctx, [structure.id, structure.location_id], f"raze.guard.{structure.id}.{ctx.epoch}"):
        await note(ctx, f"A servitor turned back those who came to raze {structure.name}.", key="mythic.servitor_guarded", ids=[structure.id])
        return
    await add_flag(ctx.session, structure.id, EntityFlag.RAZED, ctx.epoch)
    await ruin_profile(ctx.session, structure.id)
    await retire_in(ctx, structure, sentence, EntityStatus.DESTROYED, close_bonds=True)
    bonds = BondRepository(ctx.session)
    if cause_id is not None:
        await bonds.connect(BondDraft(cause_id, structure.id, BondKind.CAUSED, ctx.epoch, "was destroyed"))
    if destroyer_id is not None:
        await bonds.connect(BondDraft(destroyer_id, structure.id, BondKind.DESTROYED, ctx.epoch, "looted in conquest"))
        keeper = await living_entity(ctx.session, structure.location_id)
        if holy and keeper is not None:
            await curse_desecrator(ctx, keeper.id, destroyer_id)
            await desecrated(ctx, keeper.id, destroyer_id, note=structure.name)
            await desecration_curse(ctx, structure, destroyer_id)


async def siege_wear(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    rows = await ctx.session.execute(
        select(BattleRow.record_entity_id, SiegeRow.besieged_entity_id, WarRow.event_entity_id)
        .join(SiegeRow, SiegeRow.id == BattleRow.siege_id)
        .join(WarRow, WarRow.id == BattleRow.war_id)
        .where(BattleRow.epoch == ctx.epoch)
        .order_by(BattleRow.id)
    )
    wonders = await flags_by_entity(ctx.session, EntityFlag.WONDER)
    rng = ctx.rng("siege_wear")
    razed = 0
    for record_id, besieged_id, war_event_id in rows:
        cause = await living_entity(ctx.session, record_id) or await living_entity(ctx.session, war_event_id)
        cause_name = cause.name if cause is not None else "the siege"
        for structure in await EntityRepository(ctx.session).contents(besieged_id):
            if structure.entity_type is not EntityType.STRUCTURE or not rng.chance(cycles.siege_damage_chance):
                continue
            profile = await ctx.session.get(StructureProfileRow, structure.id)
            if profile is not None:
                if not await harm(ctx, structure, profile, cycles.siege_durability_loss, cause=cause_name, force=HarmForce.SIEGE, quiet=True):
                    continue
            else:
                remaining = (stat(structure, "durability") or 0) - cycles.siege_durability_loss
                set_stats(structure, durability=max(0, remaining))
                if remaining > 0:
                    continue
            await raze(ctx, structure, f"collapsed during {cause_name}", cause.id if cause is not None else None)
            wonder = "; one of the wonders of the world is now rubble" if structure.id in wonders else ""
            ids = [*([cause.id] if cause is not None else []), structure.id]
            await note(ctx, f"{structure.name} fell during {cause_name}{wonder}.", key="life_cycles.siege_razed", ids=ids, feed=FeedCategory.WAR)
            razed += 1
    ctx.count("siege_razed", razed)
    return razed


async def conquest_looting(ctx: TickContext) -> int:
    cycles = ctx.rules.life_cycles
    wars = list(await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch == ctx.epoch, WarRow.ending == WarEnding.CONQUEST).order_by(WarRow.id)))
    wonders = await flags_by_entity(ctx.session, EntityFlag.WONDER)
    rng = ctx.rng("looting")
    looted = 0
    for war in wars:
        victor, loser = await living_entity(ctx.session, war.victor_entity_id), await living_entity(ctx.session, war.loser_entity_id)
        if victor is None or loser is None:
            continue
        for structure in await EntityRepository(ctx.session).contents(loser.id):
            if structure.id not in wonders or structure.entity_type is not EntityType.STRUCTURE or not rng.chance(cycles.conquest_loot_chance):
                continue
            if await kind_of(ctx.session, structure.id) in HOLY_HOUSES:
                await loot_temple(ctx, structure, victor)
            await raze(ctx, structure, f"looted and razed in the conquest by {victor.name}", war.event_entity_id, victor.id)
            text = f"When {victor.name} conquered {loser.name}, its soldiers looted the wonder {structure.name} and tore it down."
            await note(ctx, text, key="life_cycles.looted", ids=[victor.id, loser.id, structure.id], feed=FeedCategory.WAR)
            looted += 1
    ctx.count("looted", looted)
    return looted


async def desolation(ctx: TickContext, atlas: RegionAtlas) -> int:
    session = ctx.session
    populated = {atlas.top_region(community.id) for community in await canon(session, COMMUNITY_TYPES)}
    ruin_ids = await flags_by_entity(session, EntityFlag.RUIN)
    ruins = await session.scalars(
        select(EntityRow.id).where(EntityRow.id.in_(ruin_ids), EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status != EntityStatus.CANON)
    )
    ruined = {atlas.top_region(ruin_id) for ruin_id in ruins}
    desolate = await flags_by_entity(session, EntityFlag.DESOLATE)
    changed = 0
    for region in unheld(await canon(session, [EntityType.REGION])):
        empty = region.id in ruined and region.id not in populated
        if empty and region.id not in desolate:
            await add_flag(session, region.id, EntityFlag.DESOLATE, ctx.epoch)
            await note(ctx, f"{region.name} became desolate: no one lives there any more, only the ruins stand.", key="life_cycles.desolate", ids=[region.id])
            changed += 1
        elif not empty and region.id in desolate:
            await remove_flag(session, region.id, EntityFlag.DESOLATE)
            await note(ctx, f"{region.name} was settled again; its desolation is over.", key="life_cycles.resettled", ids=[region.id])
            changed += 1
    ctx.count("desolation_changes", changed)
    return changed


@reads(
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "structure.durability",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.map_snapshots",
    "table.node_materials",
    "table.nodes",
    "table.routes",
    "table.tributes",
    "table.wars",
    "table.world_maps",
    "table.world_materials",
)
@writes(
    "structure.durability",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
)
async def settlement_cycles(ctx: TickContext) -> None:
    history = await population_history(ctx)
    atlas = await RegionAtlas.load(ctx.session)
    await abandon_declining(ctx, history, atlas)
    await collapses(ctx, history)
    await siege_wear(ctx)
    await conquest_looting(ctx)
    await desolation(ctx, await RegionAtlas.load(ctx.session))
    await ctx.session.flush()


async def dissolve_community(ctx: TickContext, community_id: int, reason: str) -> EntityRow:
    community = await living_entity(ctx.session, community_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Only a living community can collapse.")
    await collapse(ctx, community, reason)
    return community


async def raze_structure(ctx: TickContext, structure_id: int, reason: str) -> EntityRow:
    structure = await living_entity(ctx.session, structure_id)
    if structure is None or structure.entity_type is not EntityType.STRUCTURE:
        raise ValidationFailedError("Only a standing structure can be razed.")
    await raze(ctx, structure, reason)
    await note(ctx, f"{structure.name} was razed: {reason}.", key="life_cycles.razed_by_hand", ids=[structure.id], kind=ChronicleKind.WORLD)
    return structure


PHASES = (Phase("settlement_cycles", settlement_cycles),)
