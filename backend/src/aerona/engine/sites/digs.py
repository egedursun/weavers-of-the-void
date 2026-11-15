from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import EXCAVATION_FLAGS, EXCAVATION_PLACES, STAGE_ORDER, STAGE_SKILLS, STAGE_TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sites import BattlefieldFeatureRow, ExcavationRow, ExcavationStageRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import ItemClass, ItemDeed, Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.faith import BindingKind, SpiritAlignment
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.site import BattlefieldFeature, ExcavationFind, ExcavationRisk, ExcavationStage, ExcavationStatus
from aerona.domain.models.entity_stats import ItemStats, SpiritStats
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.features import add_stock
from aerona.engine.cosmos.routes import reveal_hidden_route
from aerona.engine.environment.book import add_scar
from aerona.engine.history.collections import open_collection
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore import items
from aerona.engine.lore.research_depth import add_progress
from aerona.engine.means.containers import read_marks
from aerona.engine.military.engineering import earthworks_of
from aerona.engine.mind.book import skill_level
from aerona.engine.notes import note
from aerona.engine.orders.savings import unearth_hoards
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.renown.currencies import realm_of_community

RISKS = (ExcavationRisk.CURSE, ExcavationRisk.SPIRIT, ExcavationRisk.COLLAPSE)
FINDS = (ExcavationFind.ARTIFACT, ExcavationFind.BOOK, ExcavationFind.TECHNIQUE, ExcavationFind.REGALIA, ExcavationFind.ROUTE_MAP)
CURSES = (PackageKind.HUNGER_CURSE, PackageKind.POSSESSION, PackageKind.VOID_TAINT)
FIND_CLASSES = {
    ExcavationFind.ARTIFACT: ItemClass.IDOL,
    ExcavationFind.BOOK: ItemClass.BOOK,
    ExcavationFind.TECHNIQUE: ItemClass.TOOL,
    ExcavationFind.REGALIA: ItemClass.CROWN,
    ExcavationFind.ROUTE_MAP: ItemClass.MAP,
}
LOST_TECHNIQUES = (Technique.ARCH, Technique.CARTOGRAPHY, Technique.WARDING, Technique.ALCHEMY, Technique.ASTRONOMY_INSTRUMENTS, Technique.WRITTEN_LAW)


@dataclass
class DigTally:
    begun: int = 0
    advanced: int = 0
    finds: int = 0
    risks: int = 0
    finished: int = 0
    abandoned: int = 0
    graves: int = 0
    haunted: int = 0
    gleaned: int = 0
    fortified: int = 0


async def scholar_near(ctx: TickContext, atlas: RegionAtlas, site: EntityRow) -> EntityRow | None:
    region = atlas.top_region(site.id)
    best: tuple[int, int, EntityRow] | None = None
    for mortal in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.world_id == site.world_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    ):
        if held(mortal.id) or atlas.top_region(mortal.id) != region:
            continue
        lore = await skill_level(ctx.session, mortal.id, SkillKind.LORE)
        if lore >= ctx.rules.excavations.start_lore and (best is None or (lore, -mortal.id) > (best[0], best[1])):
            best = (lore, -mortal.id, mortal)
    return best[2] if best is not None else None


async def plan_stages(ctx: TickContext, dig: ExcavationRow) -> None:
    table = ctx.rules.excavations
    draw = ctx.rng(f"dig.stages.{dig.id}")
    for index, stage in enumerate(STAGE_ORDER):
        ctx.session.add(
            ExcavationStageRow(
                excavation_id=dig.id,
                stage=stage,
                skill=STAGE_SKILLS[stage],
                technique=STAGE_TECHNIQUES.get(stage),
                difficulty=clamp_int(table.difficulty_base + table.difficulty_step * index, 0, PERCENT),
                risk=draw.pick(list(RISKS)) if draw.chance(table.risk_pct) else ExcavationRisk.NONE,
                find=draw.pick(list(FINDS)) if draw.chance(table.find_pct) else ExcavationFind.NOTHING,
                locked=[],
            )
        )
    await ctx.session.flush()


async def begin(ctx: TickContext, site: EntityRow, leader: EntityRow, sponsor_id: int | None, *, by_player: bool = False) -> ExcavationRow:
    dig = ExcavationRow(site_entity_id=site.id, leader_entity_id=leader.id, sponsor_node_id=sponsor_id, started_epoch=ctx.epoch, locked=[])
    ctx.session.add(dig)
    await ctx.session.flush()
    await plan_stages(ctx, dig)
    members = {leader.id: CollectionRole.LEADER, **({sponsor_id: CollectionRole.MEMBER} if sponsor_id is not None and sponsor_id != leader.id else {})}
    collection = await open_collection(ctx, CollectionKind.EXCAVATION, world_id=site.world_id, members=members, places=[site.id], source_key=f"dig.{dig.id}")
    dig.collection_id = collection.id if collection is not None else None
    await note(
        ctx,
        f"{leader.name} began to dig at {site.name}{' at the word of the gods' if by_player else ''}.",
        key="excavation.begun",
        ids=[leader.id, site.id],
        roles={leader.id: IncidentRole.ACTOR, site.id: IncidentRole.PLACE},
    )
    return dig


async def open_digs(ctx: TickContext, world_id: int | None) -> int:
    statement = (
        select(func.count())
        .select_from(ExcavationRow)
        .join(EntityRow, EntityRow.id == ExcavationRow.site_entity_id)
        .where(ExcavationRow.status.in_([ExcavationStatus.OPEN, ExcavationStatus.STALLED]), EntityRow.world_id == world_id)
    )
    return int(await ctx.session.scalar(statement) or 0)


async def wrecked(session: AsyncSession, site_id: int) -> bool:
    vessel = await session.get(VesselProfileRow, site_id)
    return vessel is not None and vessel.status is VesselStatus.WRECKED


async def diggable(session: AsyncSession, site: EntityRow) -> bool:
    place = await session.get(PlaceProfileRow, site.id)
    if place is not None and place.kind in EXCAVATION_PLACES:
        return True
    flagged = await session.scalar(
        select(EntityFlagRow.entity_id).where(EntityFlagRow.entity_id == site.id, EntityFlagRow.flag.in_(list(EXCAVATION_FLAGS))).limit(1)
    )
    return flagged is not None or await wrecked(session, site.id)


async def dig_sites(session: AsyncSession) -> list[EntityRow]:
    places = select(PlaceProfileRow.entity_id).where(PlaceProfileRow.kind.in_(list(EXCAVATION_PLACES)))
    flagged = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag.in_(list(EXCAVATION_FLAGS)))
    wrecks = select(VesselProfileRow.entity_id).where(VesselProfileRow.status == VesselStatus.WRECKED)
    return list(
        await session.scalars(
            select(EntityRow)
            .where(
                or_(
                    and_(EntityRow.id.in_(places), EntityRow.status == EntityStatus.CANON),
                    and_(EntityRow.id.in_(flagged), EntityRow.world_id.is_not(None)),
                    EntityRow.id.in_(wrecks),
                )
            )
            .order_by(EntityRow.id)
        )
    )


async def start_digs(ctx: TickContext, atlas: RegionAtlas, tally: DigTally) -> None:
    table = ctx.rules.excavations
    for site in await dig_sites(ctx.session):
        if held(site.id) or await ctx.session.scalar(select(ExcavationRow.id).where(ExcavationRow.site_entity_id == site.id).limit(1)) is not None:
            continue
        if await open_digs(ctx, site.world_id) >= table.open_max or not ctx.rng(f"dig.start.{site.id}.{ctx.epoch}").chance(table.start_pct):
            continue
        leader = await scholar_near(ctx, atlas, site)
        if leader is None:
            continue
        sponsor = await realm_of_community(ctx.session, leader.location_id) if leader.location_id is not None else None
        await begin(ctx, site, leader, sponsor)
        tally.begun += 1


async def knows(ctx: TickContext, holders: list[int], technique: Technique | None) -> bool:
    if technique is None:
        return True
    return (
        await ctx.session.scalar(
            select(HolderTechniqueRow.holder_entity_id)
            .where(HolderTechniqueRow.holder_entity_id.in_(holders), HolderTechniqueRow.technique == technique)
            .limit(1)
        )
        is not None
    )


async def stage_of(ctx: TickContext, dig: ExcavationRow) -> ExcavationStageRow | None:
    found: ExcavationStageRow | None = await ctx.session.scalar(
        select(ExcavationStageRow).where(ExcavationStageRow.excavation_id == dig.id, ExcavationStageRow.stage == dig.stage).limit(1)
    )
    return found


async def raise_spirit(ctx: TickContext, place: EntityRow, *, origin: str) -> EntityRow:
    spirit = await create_record(
        ctx,
        RecordSpec(
            name=f"Spirit of {place.name}",
            entity_type=EntityType.SPIRIT,
            stats=SpiritStats(),
            body=f"A spirit {origin} at {place.name}.",
            power=max(1, ctx.rules.excavations.find_power // 10),
            world_id=place.world_id,
            location_id=place.id,
        ),
    )
    ctx.session.add(
        SpiritProfileRow(
            spirit_entity_id=spirit.id, binding=BindingKind.PLACE, bound_entity_id=place.id, alignment=SpiritAlignment.VENGEFUL, updated_epoch=ctx.epoch
        )
    )
    await ctx.session.flush()
    return spirit


async def suffer(ctx: TickContext, dig: ExcavationRow, risk: ExcavationRisk, site: EntityRow, leader: EntityRow) -> str:
    table = ctx.rules.excavations
    if risk is ExcavationRisk.CURSE:
        package = ctx.rng(f"dig.curse.{dig.id}.{dig.stage.value}").pick(list(CURSES))
        await afflict(ctx, leader, package, Transmission.CURSE, source_node_id=site.id)
        return f"; a curse fell on {leader.name}"
    if risk is ExcavationRisk.SPIRIT:
        spirit = await raise_spirit(ctx, site, origin="loosed by a dig")
        return f"; {spirit.name} was loosed"
    if risk is ExcavationRisk.COLLAPSE:
        await apply_hits(ctx, leader, Harm(table.collapse_hp, HarmCause.ACCIDENT, f"was buried when the dig at {site.name} fell in"))
        if ctx.rng(f"dig.collapse.{dig.id}.{dig.stage.value}").chance(table.collapse_end_pct) and "status" not in dig.locked:
            dig.status, dig.ended_epoch = ExcavationStatus.COLLAPSED, ctx.epoch
        return "; the shaft fell in"
    return ""


async def unearth(ctx: TickContext, dig: ExcavationRow, stage: ExcavationStageRow, site: EntityRow, leader: EntityRow) -> str:
    hoard = await unearth_hoards(ctx, [place for place in (site.id, site.location_id) if place is not None], leader)
    marked = await read_marks(ctx, site)
    found = (f"; they found a buried hoard worth {hoard} coin" if hoard else "") + ("; stamped jars told of the trade that once passed there" if marked else "")
    if stage.find is ExcavationFind.NOTHING:
        return found
    keeper = dig.sponsor_node_id or leader.id
    technique = ctx.rng(f"dig.technique.{dig.id}.{stage.id}").pick(list(LOST_TECHNIQUES))
    if stage.find is ExcavationFind.TECHNIQUE:
        await add_progress(ctx, keeper if (await ctx.session.get(EntityRow, keeper)) is not None else leader.id, technique, ctx.rules.excavations.find_power)
    item = await create_record(
        ctx,
        RecordSpec(
            name=f"{stage.find.value.replace('_', ' ').capitalize()} of {site.name}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(might=ctx.rules.excavations.find_power),
            body=f"Found by {leader.name} in the {stage.stage.value.replace('_', ' ')} of {site.name}.",
            power=max(1, ctx.rules.excavations.find_power // 10),
            world_id=site.world_id,
            location_id=site.id,
        ),
    )
    await items.profile_of(ctx, item, FIND_CLASSES[stage.find])
    await items.give(ctx, item, keeper, ItemDeed.OWNED, f"unearthed at {site.name}")
    stage.find_entity_id = item.id
    if stage.find is ExcavationFind.ROUTE_MAP:
        hidden = await ctx.session.scalar(
            select(RouteRow.id).where(RouteRow.known.is_(False), (RouteRow.world_a_id == site.world_id) | (RouteRow.world_b_id == site.world_id)).limit(1)
        )
        if hidden is not None:
            await reveal_hidden_route(ctx, int(hidden), f"A map unearthed at {site.name}")
    return f"; they found {item.name}{found}"


async def dig_on(ctx: TickContext, dig: ExcavationRow, tally: DigTally) -> None:
    table = ctx.rules.excavations
    site = await ctx.session.get(EntityRow, dig.site_entity_id)
    if site is None or held(site.id) or dig.status not in (ExcavationStatus.OPEN, ExcavationStatus.STALLED):
        return
    leader = await ctx.session.get(EntityRow, dig.leader_entity_id) if dig.leader_entity_id is not None else None
    if leader is None or leader.status is not EntityStatus.CANON or held(leader.id):
        dig.idle_epochs += 1
        if dig.idle_epochs >= table.abandon_after and "status" not in dig.locked:
            dig.status, dig.ended_epoch = ExcavationStatus.ABANDONED, ctx.epoch
            tally.abandoned += 1
        return
    dig.idle_epochs = 0
    stage = await stage_of(ctx, dig)
    if stage is None:
        return
    able = await knows(ctx, [holder for holder in (leader.id, dig.sponsor_node_id) if holder is not None], stage.technique)
    skill = await skill_level(ctx.session, leader.id, stage.skill)
    gain = table.progress_base * skill / PERCENT * (1 if able else table.stalled_pct / PERCENT)
    if "status" not in dig.locked:
        dig.status = ExcavationStatus.OPEN if able else ExcavationStatus.STALLED
    if "progress" not in dig.locked:
        dig.progress = clamp_int(dig.progress + round_half_up(gain * (PERCENT - stage.difficulty) / PERCENT + 1), 0, PERCENT)
    if dig.progress < PERCENT:
        return
    tally.advanced += 1
    stage.resolved_epoch = ctx.epoch
    told = await suffer(ctx, dig, stage.risk, site, leader)
    tally.risks += stage.risk is not ExcavationRisk.NONE
    found = await unearth(ctx, dig, stage, site, leader)
    tally.finds += bool(found)
    order = list(STAGE_ORDER)
    if dig.status is not ExcavationStatus.COLLAPSED:
        dig.progress = 0
        if dig.stage is ExcavationStage.INNER_SANCTUM:
            dig.status, dig.ended_epoch = ExcavationStatus.FINISHED, ctx.epoch
            tally.finished += 1
        else:
            dig.stage = order[order.index(dig.stage) + 1]
    await note(
        ctx,
        f"The dig at {site.name} passed its {stage.stage.value.replace('_', ' ')}{told}{found}.",
        key=f"excavation.{stage.stage.value}",
        ids=[leader.id, site.id, *([stage.find_entity_id] if stage.find_entity_id else [])],
        roles={leader.id: IncidentRole.ACTOR, site.id: IncidentRole.PLACE},
    )


async def tend_digs(ctx: TickContext, tally: DigTally) -> None:
    for dig in list(
        await ctx.session.scalars(
            select(ExcavationRow).where(ExcavationRow.status.in_([ExcavationStatus.OPEN, ExcavationStatus.STALLED])).order_by(ExcavationRow.id)
        )
    ):
        await dig_on(ctx, dig, tally)


async def mark_battlefields(ctx: TickContext, tally: DigTally) -> None:
    table = ctx.rules.excavations
    for battle in await ctx.session.scalars(
        select(BattleRow).where(BattleRow.epoch == ctx.epoch, BattleRow.place_entity_id.is_not(None)).order_by(BattleRow.id)
    ):
        dead = battle.winner_losses + battle.loser_losses
        place_id = battle.place_entity_id
        if place_id is None or held(place_id) or dead < table.battlefield_dead:
            continue
        strength = clamp_int(dead * PERCENT / max(1, table.battlefield_dead * 10), 1, PERCENT)
        place = await ctx.session.get(EntityRow, place_id)
        region = await ctx.session.get(RegionEnvironmentRow, place.location_id) if place is not None and place.location_id is not None else None
        fortified = battle.siege_id is not None or earthworks_of(region) > 0
        for feature in BattlefieldFeature:
            if feature is BattlefieldFeature.EARTHWORKS and not fortified:
                continue
            ctx.session.add(
                BattlefieldFeatureRow(place_entity_id=place_id, feature=feature, strength=strength, battle_id=battle.id, epoch=ctx.epoch, locked=[])
            )
        tally.graves += 1


async def gleaner_of(ctx: TickContext, place: EntityRow) -> EntityRow | None:
    found: EntityRow | None = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.world_id == place.world_id,
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == place.location_id,
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def tend_battlefields(ctx: TickContext, tally: DigTally) -> None:
    table = ctx.rules.excavations
    for row in list(await ctx.session.scalars(select(BattlefieldFeatureRow).where(BattlefieldFeatureRow.strength > 0).order_by(BattlefieldFeatureRow.id))):
        place = await ctx.session.get(EntityRow, row.place_entity_id)
        if place is None or held(place.id) or row.epoch == ctx.epoch:
            continue
        if row.feature is BattlefieldFeature.MASS_GRAVE and ctx.rng(f"grave.{row.id}.{ctx.epoch}").chance(table.grave_haunt_pct * row.strength / PERCENT):
            spirit = await raise_spirit(ctx, place, origin="risen from the mass grave")
            tally.haunted += 1
            await note(ctx, f"{spirit.name} rose from the mass grave of {place.name}.", key="battlefield.haunted", ids=[spirit.id, place.id])
        if row.feature is BattlefieldFeature.EARTHWORKS and place.location_id is not None:
            region = await ctx.session.get(RegionEnvironmentRow, place.location_id)
            if region is not None and not held(place.location_id):
                gap = row.strength - earthworks_of(region)
                tally.fortified += add_scar(region, ScarKind.EARTHWORKS, gap) if gap > 0 else 0
        if row.feature is BattlefieldFeature.SALVAGE_FIELD:
            gleaner = await gleaner_of(ctx, place)
            if gleaner is not None and not held(gleaner.id):
                taken = round_half_up(row.strength * table.salvage_take_pct / PERCENT)
                if taken:
                    await add_stock(ctx, gleaner, CommodityKind.WEAPONS, taken)
                    tally.gleaned += taken
        if "strength" not in row.locked:
            row.strength = clamp_int(row.strength - table.feature_decay, 0, PERCENT)
