from collections import Counter
from dataclasses import dataclass

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import EXCAVATION_FLAGS, EXCAVATION_PLACES, STAGE_ORDER, STAGE_SKILLS, STAGE_TECHNIQUES
from aerona.catalog.life.sites import (
    CURSES,
    DIG_RISKS,
    EVERY_BATTLE_FEATURES,
    FEATURES,
    FIND_ANOMALIES,
    FIND_CLASSES,
    FINDS,
    FOUND_PLANS,
    LOST_TECHNIQUES,
    RISKS,
)
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.gatherings import CollectionMemberRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.region import RegionMemoryRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sites import BattlefieldFeatureRow, ExcavationRow, ExcavationStageRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import ItemDeed, Technique
from aerona.domain.enums.discovery import BlueprintKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.faith import BindingKind, SpiritAlignment
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import MemoryOrigin, RegionMemoryKind
from aerona.domain.enums.site import BattlefieldFeature, ExcavationFind, ExcavationRisk, ExcavationStage, ExcavationStatus
from aerona.domain.models.entity_stats import ItemStats, SpiritStats
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.features import add_stock
from aerona.engine.cosmos.routes import reveal_hidden_route
from aerona.engine.disease.control import loose
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.region_control import add_memory
from aerona.engine.grave_goods.robbery import unearth_graves
from aerona.engine.history.collections import open_collection
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore import items
from aerona.engine.lore.blueprints import found_design
from aerona.engine.lore.research_depth import add_progress
from aerona.engine.means.containers import read_marks
from aerona.engine.military.engineering import earthworks_of
from aerona.engine.mind.book import skill_level
from aerona.engine.mind.memories import remember
from aerona.engine.orders.savings import unearth_hoards
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import FactInput
from aerona.engine.recording.record import record as record_incident
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.sites.accounts import ground_risks, remnant_near, sealed_disease, unsettle_accounts
from aerona.rules.model import keyed


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


def sleeping_at(site_id: int) -> Select[MindProfileRow]:
    here = select(EntityRow.id).where(EntityRow.location_id == site_id, EntityRow.status == EntityStatus.CANON)
    return select(MindProfileRow).where(MindProfileRow.dormant.is_(True), MindProfileRow.node_id.in_(here)).order_by(MindProfileRow.node_id)


async def sleepers_at(ctx: TickContext, site_id: int) -> bool:
    return await ctx.session.scalar(select(func.count()).select_from(sleeping_at(site_id).subquery())) != 0


async def wake_sleepers(ctx: TickContext, site: EntityRow, leader: EntityRow) -> int:
    woken = 0
    for mind in list(await ctx.session.scalars(sleeping_at(site.id))):
        if held(mind.node_id) or "dormant" in mind.locked:
            continue
        mind.dormant = False
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=mind.node_id,
            subject_id=leader.id,
            kind=MemoryKind.MEMORY_GAP,
            magnitude=-ctx.rules.minds.gap_memory_weight,
            epoch=ctx.epoch,
            note=f"woken in the ruin of {site.name}",
        )
        woken += 1
    return woken


async def plan_stages(ctx: TickContext, dig: ExcavationRow) -> None:
    table = ctx.rules.excavations
    draw = ctx.rng(f"dig.stages.{dig.id}")
    finds = (*FINDS, ExcavationFind.WAKING) if await sleepers_at(ctx, dig.site_entity_id) else FINDS
    site = await ctx.session.get(EntityRow, dig.site_entity_id)
    grounds = await ground_risks(ctx, site) if site is not None else []
    for index, stage in enumerate(STAGE_ORDER):
        risk = draw.pick(list(RISKS)) if draw.chance(table.risk_pct) else ExcavationRisk.NONE
        for ground in grounds:
            rule = DIG_RISKS[ground].rule
            if rule is not None and draw.chance(keyed(ctx.rules.sites, rule.removesuffix("_pct"), "pct")):
                risk = ground
        ctx.session.add(
            ExcavationStageRow(
                excavation_id=dig.id,
                stage=stage,
                skill=STAGE_SKILLS[stage],
                technique=STAGE_TECHNIQUES.get(stage),
                difficulty=clamp_int(table.difficulty_base + table.difficulty_step * index, 0, PERCENT),
                risk=risk,
                find=draw.pick(list(finds)) if draw.chance(table.find_pct) else ExcavationFind.NOTHING,
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
    await record_incident(
        ctx, "excavation.begun", roles={IncidentRole.ACTOR: leader.id, IncidentRole.PLACE: site.id, IncidentRole.PATRON: sponsor_id}, place=site.id
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
    sites = ctx.rng("dig.order").shuffled(await dig_sites(ctx.session))
    per_world = Counter(site.world_id for site in sites)
    for site in sites:
        if held(site.id) or await ctx.session.scalar(select(ExcavationRow.id).where(ExcavationRow.site_entity_id == site.id).limit(1)) is not None:
            continue
        room = scaled_cap(table.open_max, table.open_site_divisor, per_world[site.world_id])
        if await open_digs(ctx, site.world_id) >= room or not ctx.rng(f"dig.start.{site.id}.{ctx.epoch}").chance(table.start_pct):
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


async def suffer(ctx: TickContext, dig: ExcavationRow, risk: ExcavationRisk, site: EntityRow, leader: EntityRow) -> dict[str, FactInput]:
    table = ctx.rules.excavations
    if risk is ExcavationRisk.CURSE:
        package = ctx.rng(f"dig.curse.{dig.id}.{dig.stage.value}").pick(list(CURSES))
        await afflict(ctx, leader, package, Transmission.CURSE, source_node_id=site.id)
        return {"risk": risk, "cursed": leader.id}
    if risk is ExcavationRisk.SPIRIT:
        spirit = await raise_spirit(ctx, site, origin="loosed by a dig")
        return {"risk": risk, "spirit": spirit.id}
    if risk is ExcavationRisk.COLLAPSE:
        await apply_hits(ctx, leader, Harm(table.collapse_hp, HarmCause.ACCIDENT, f"was buried when the dig at {site.name} fell in"))
        if ctx.rng(f"dig.collapse.{dig.id}.{dig.stage.value}").chance(table.collapse_end_pct) and "status" not in dig.locked:
            dig.status, dig.ended_epoch = ExcavationStatus.COLLAPSED, ctx.epoch
        return {"risk": risk, "harm": table.collapse_hp}
    return await suffer_ground(ctx, dig, risk, site, leader)


async def suffer_ground(ctx: TickContext, dig: ExcavationRow, risk: ExcavationRisk, site: EntityRow, leader: EntityRow) -> dict[str, FactInput]:
    table = ctx.rules.excavations
    if risk is ExcavationRisk.FLOODING:
        await apply_hits(ctx, leader, Harm(table.collapse_hp // 2, HarmCause.ACCIDENT, f"was caught when water broke into the dig at {site.name}"))
        if "progress" not in dig.locked:
            dig.progress = dig.progress // 2
        if "status" not in dig.locked:
            dig.status = ExcavationStatus.STALLED
        await tell_risk(ctx, dig, risk, site, leader)
        return {"risk": risk, "harm": table.collapse_hp // 2}
    if risk is ExcavationRisk.GAS:
        await apply_hits(ctx, leader, Harm(table.collapse_hp, HarmCause.ACCIDENT, f"breathed the bad air of the dig at {site.name}"))
        if ctx.rng(f"dig.gas.{dig.id}.{dig.stage.value}").chance(table.collapse_end_pct) and "status" not in dig.locked:
            dig.status, dig.ended_epoch = ExcavationStatus.COLLAPSED, ctx.epoch
        await tell_risk(ctx, dig, risk, site, leader)
        return {"risk": risk, "harm": table.collapse_hp}
    if risk is ExcavationRisk.DISEASE:
        atlas = await RegionAtlas.load(ctx.session)
        region_id = atlas.top_region(site.id)
        if region_id is not None and not held(region_id):
            await loose(ctx, region_id, disease_id=await sealed_disease(ctx, site), severity=table.find_power, son_id=None)
        await tell_risk(ctx, dig, risk, site, leader)
        return {"risk": risk}
    return {}


async def tell_risk(ctx: TickContext, dig: ExcavationRow, risk: ExcavationRisk, site: EntityRow, leader: EntityRow) -> None:
    await record_incident(
        ctx,
        "dig.risk",
        roles={IncidentRole.ACTOR: leader.id, IncidentRole.PLACE: site.id, IncidentRole.PATRON: dig.sponsor_node_id},
        facts={"risk": risk, "stage": dig.stage},
        place=site.id,
    )


async def unearth(ctx: TickContext, dig: ExcavationRow, stage: ExcavationStageRow, site: EntityRow, leader: EntityRow) -> dict[str, FactInput]:
    places = [place for place in (site.id, site.location_id) if place is not None]
    hoard = await unearth_hoards(ctx, places, leader)
    graves = await unearth_graves(ctx, places, leader)
    marked = await read_marks(ctx, site)
    found: dict[str, FactInput] = {
        **({"hoard": hoard} if hoard else {}),
        **({"marks": int(marked)} if marked else {}),
        **({"graves": graves} if graves else {}),
    }
    if stage.find is ExcavationFind.NOTHING:
        return found
    if stage.find is ExcavationFind.WAKING:
        woken = await wake_sleepers(ctx, site, leader)
        return {**found, **({"find": stage.find, "woken": woken} if woken else {})}
    shaken = await unsettle_accounts(ctx, leader, FIND_ANOMALIES[stage.find], site.id) if stage.find in FIND_ANOMALIES else 0
    if stage.find is ExcavationFind.REMAINS:
        mourners = await gleaner_of(ctx, site)
        if mourners is not None and not held(mourners.id):
            shift_stat(mourners, "piety", ctx.rules.sites.remains_piety)
        return {**found, "find": stage.find, "shaken": shaken}
    keeper = dig.sponsor_node_id or leader.id
    technique = ctx.rng(f"dig.technique.{dig.id}.{stage.id}").pick(list(LOST_TECHNIQUES))
    if stage.find is ExcavationFind.TECHNIQUE:
        await add_progress(ctx, keeper if (await ctx.session.get(EntityRow, keeper)) is not None else leader.id, technique, ctx.rules.excavations.find_power)
    item = await create_record(
        ctx,
        RecordSpec(
            name=f"{spoken(stage.find).capitalize()} of {site.name}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(might=ctx.rules.excavations.find_power),
            body=f"Found by {leader.name} in the {spoken(stage.stage)} of {site.name}.",
            power=max(1, ctx.rules.excavations.find_power // 10),
            world_id=site.world_id,
            location_id=site.id,
        ),
    )
    await items.profile_of(ctx, item, FIND_CLASSES[stage.find])
    await items.give(ctx, item, keeper, ItemDeed.OWNED, f"unearthed at {site.name}")
    stage.find_entity_id = item.id
    if stage.find in FOUND_PLANS:
        work = await ctx.session.get(StructureProfileRow, site.id)
        holder = await ctx.session.get(EntityRow, keeper) or leader
        plan = BlueprintKind.STRUCTURE if work is not None else BlueprintKind.ARTIFACT_PATTERN
        await found_design(ctx, holder, site, plan, work.kind.value if work is not None else FIND_CLASSES[stage.find].value)
    if stage.find is ExcavationFind.ROUTE_MAP:
        hidden = await ctx.session.scalar(
            select(RouteRow.id).where(RouteRow.known.is_(False), (RouteRow.world_a_id == site.world_id) | (RouteRow.world_b_id == site.world_id)).limit(1)
        )
        if hidden is not None:
            await reveal_hidden_route(ctx, int(hidden), site.id)
    return {**found, "find": stage.find, "item": item.id, "shaken": shaken}


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
    harmed = await suffer(ctx, dig, stage.risk, site, leader)
    tally.risks += stage.risk is not ExcavationRisk.NONE
    found = await unearth(ctx, dig, stage, site, leader)
    tally.finds += bool(found)
    if found and dig.collection_id is not None:
        member = await ctx.session.get(CollectionMemberRow, (dig.collection_id, leader.id))
        if member is not None:
            member.role = CollectionRole.FINDER
    order = list(STAGE_ORDER)
    if dig.status is not ExcavationStatus.COLLAPSED:
        dig.progress = 0
        if dig.stage is ExcavationStage.INNER_SANCTUM:
            dig.status, dig.ended_epoch = ExcavationStatus.FINISHED, ctx.epoch
            tally.finished += 1
        else:
            dig.stage = order[order.index(dig.stage) + 1]
    await record_incident(
        ctx,
        f"excavation.{stage.stage.value}",
        roles={IncidentRole.ACTOR: leader.id, IncidentRole.PLACE: site.id, IncidentRole.PATRON: dig.sponsor_node_id},
        facts={"stage": stage.stage, **harmed, **found},
        place=site.id,
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
        remnant = await remnant_near(ctx, place) if place is not None else None
        features = [
            *EVERY_BATTLE_FEATURES,
            *([BattlefieldFeature.EARTHWORKS] if fortified else []),
            *([BattlefieldFeature.ORDNANCE] if remnant is not None else []),
            *([BattlefieldFeature.MEMORIAL] if dead >= ctx.rules.sites.memorial_dead else []),
        ]
        for feature in features:
            ctx.session.add(
                BattlefieldFeatureRow(
                    place_entity_id=place_id,
                    feature=feature,
                    strength=strength,
                    battle_id=battle.id,
                    remnant_id=remnant.id if feature is BattlefieldFeature.ORDNANCE and remnant is not None else None,
                    epoch=ctx.epoch,
                    locked=[],
                )
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
            await record_incident(ctx, "battlefield.haunted", roles={IncidentRole.SUBJECT: spirit.id}, facts={"battlefield": place.id}, place=place.id)
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
        if row.feature is BattlefieldFeature.ORDNANCE:
            await ordnance_harms(ctx, row, place)
        if row.feature is BattlefieldFeature.MEMORIAL:
            await memorial_draws(ctx, row, place)
        if "strength" not in row.locked and FEATURES[row.feature].decays:
            row.strength = clamp_int(row.strength - table.feature_decay, 0, PERCENT)


async def ordnance_harms(ctx: TickContext, row: BattlefieldFeatureRow, place: EntityRow) -> None:
    remnant = await ctx.session.get(WarRemnantRow, row.remnant_id) if row.remnant_id is not None else None
    if remnant is not None and "strength" not in row.locked:
        row.strength = clamp_int(remnant.density * (PERCENT - remnant.cleared) // PERCENT, 0, PERCENT)
    elif remnant is None and "strength" not in row.locked:
        row.strength = clamp_int(row.strength - ctx.rules.excavations.feature_decay, 0, PERCENT)
    crossers = await gleaner_of(ctx, place)
    if crossers is None or held(crossers.id) or not ctx.rng(f"ordnance.{row.id}.{ctx.epoch}").chance(row.strength):
        return
    population = stat(crossers, "population") or 0
    dead = min(max(0, population - 1), round_half_up(ctx.rules.sites.ordnance_harm * row.strength / PERCENT))
    if dead <= 0:
        return
    with flowing(FlowCategory.DISASTER):
        shift_stat(crossers, "population", -dead)
    await record_incident(
        ctx,
        "battlefield.ordnance",
        roles={IncidentRole.VICTIM: crossers.id, IncidentRole.PLACE: place.id},
        facts={"feature": row.feature, "dead": dead, "strength": row.strength},
        place=place.id,
    )


async def memorial_draws(ctx: TickContext, row: BattlefieldFeatureRow, place: EntityRow) -> None:
    pilgrims = await gleaner_of(ctx, place)
    if pilgrims is not None and not held(pilgrims.id):
        shift_stat(pilgrims, "piety", round_half_up(ctx.rules.sites.memorial_piety * row.strength / PERCENT))
    atlas = await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(place.id)
    if region_id is None or held(region_id):
        return
    key = f"memorial.{row.id}"
    if await ctx.session.scalar(select(RegionMemoryRow.id).where(RegionMemoryRow.region_entity_id == region_id, RegionMemoryRow.source_key == key)) is not None:
        return
    memory = await add_memory(ctx.session, region_id, RegionMemoryKind.BATTLE, row.strength, f"the memorial at {place.name}", epoch=ctx.epoch, held=False)
    memory.source_key, memory.origin = key, MemoryOrigin.DERIVED
