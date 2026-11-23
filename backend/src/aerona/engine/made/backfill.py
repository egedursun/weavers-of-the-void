from sqlalchemy import select

from aerona.db.tables.body import ProsthesisRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.made import AugmentRow, FabricationRow, PeopleSubstrateRow, ReplicatorLineRow, ReplicatorPresenceRow, SalvageSiteRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import (
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    MadeMindStance,
    RelicStance,
    ReplicatorOutput,
    ReplicatorScale,
    ReplicatorStage,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.minds import MindAffect, MindOrigin, MindPurpose, MindSeat, MindUpkeep
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import GovernmentKind
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.minds.profiles import profile_of
from aerona.engine.primitives.once import once

LEGACY_FIXUP = "made.legacy_backfill"
FULL = 100
LEAN = 25
FARM_SHARE = 10
SALVAGE_YIELD = 50
TERRAFORMER_MASS = 20
RUINS = (PlaceKind.WRECK_SITE, PlaceKind.MEGASTRUCTURE_RUIN)


async def prostheses(ctx: TickContext) -> int:
    made = 0
    made_parts = select(AugmentRow.bearer_node_id, AugmentRow.part, AugmentRow.installed_epoch).where(AugmentRow.make == AugmentMake.MADE)
    fitted: set[tuple[int, BodyPart | None, int]] = {(bearer, part, epoch) for bearer, part, epoch in (await ctx.session.execute(made_parts)).all()}
    for row in list(await ctx.session.scalars(select(ProsthesisRow).order_by(ProsthesisRow.id))):
        if held(row.bearer_node_id) or (row.bearer_node_id, row.part, row.epoch) in fitted:
            continue
        fitted.add((row.bearer_node_id, row.part, row.epoch))
        augment = AugmentRow(
            bearer_node_id=row.bearer_node_id,
            slot=AugmentSlot.PART,
            part=row.part,
            kind=AugmentKind.REPLACEMENT,
            make=AugmentMake.MADE,
            quality=row.quality,
            upkeep=MindUpkeep.NONE,
            integration=row.restored_pct,
            strain=0,
            installed_by_node_id=row.maker_node_id,
            installed_epoch=row.epoch,
            locked=[],
        )
        ctx.session.add(augment)
        made += 1
    return made


async def structures_of(ctx: TickContext, kind: StructureKind) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind == kind, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list(await ctx.session.scalars(statement))


async def region_of(ctx: TickContext, thing: EntityRow) -> int | None:
    place = await ctx.session.get(EntityRow, thing.location_id) if thing.location_id is not None else None
    if place is not None and place.entity_type is EntityType.SETTLEMENT:
        return place.location_id
    return place.id if place is not None else None


async def terraformers(ctx: TickContext) -> int:
    made = 0
    named = set(await ctx.session.scalars(select(ReplicatorLineRow.name).where(ReplicatorLineRow.output == ReplicatorOutput.TERRAFORMING)))
    for works in await structures_of(ctx, StructureKind.TERRAFORMER):
        region = await region_of(ctx, works)
        if region is None or held(works.id) or f"the terraforming of {works.name}" in named:
            continue
        line = ReplicatorLineRow(
            name=f"the terraforming of {works.name}",
            scale=ReplicatorScale.WORKS,
            feedstock=MaterialKind.STONE,
            output=ReplicatorOutput.TERRAFORMING,
            growth_pct=5,
            error_pct=0,
            set_id=None,
            containment=FULL,
            kill_switch=True,
            owner_node_id=works.affiliated_entity_id,
            maker_node_id=None,
            mind_node_id=None,
            stage=ReplicatorStage.CONTAINED,
            drifted_from_id=None,
            founded_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(line)
        await ctx.session.flush()
        ctx.session.add(ReplicatorPresenceRow(line_id=line.id, place_node_id=region, mass=TERRAFORMER_MASS, growth=FULL, locked=[]))
        made += 1
    return made


async def farms(ctx: TickContext) -> int:
    made = 0
    for farm in await structures_of(ctx, StructureKind.VERTICAL_FARM):
        town = farm.location_id
        if town is None or held(town) or await ctx.session.get(FabricationRow, town) is not None:
            continue
        ctx.session.add(FabricationRow(settlement_entity_id=town, share_pct=FARM_SHARE, dividend_pct=0, updated_epoch=ctx.epoch, locked=[]))
        made += 1
    return made


async def ruins(ctx: TickContext) -> int:
    made = 0
    for place in list(await ctx.session.scalars(select(PlaceProfileRow).where(PlaceProfileRow.kind.in_(RUINS)).order_by(PlaceProfileRow.entity_id))):
        if held(place.entity_id) or await ctx.session.get(SalvageSiteRow, place.entity_id) is not None:
            continue
        ctx.session.add(
            SalvageSiteRow(site_entity_id=place.entity_id, yield_left=SALVAGE_YIELD, rights_holder_node_id=None, last_salvaged_epoch=None, locked=[])
        )
        made += 1
    return made


async def machine_ruled(ctx: TickContext, core: EntityRow) -> bool:
    polity = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == core.location_id).limit(1))
    profile = await ctx.session.get(PolityProfileRow, polity) if polity is not None else None
    return profile is not None and profile.government is GovernmentKind.MACHINE_RULE


async def cores(ctx: TickContext) -> int:
    made = 0
    for core in await structures_of(ctx, StructureKind.AI_CORE):
        if held(core.id):
            continue
        mind = await profile_of(ctx.session, ctx.rules, core.id, ctx.epoch)
        if mind.seat is not MindSeat.NONE:
            continue
        mind.seat, mind.seat_node_id, mind.origin = MindSeat.STRUCTURE, core.id, MindOrigin.MADE
        mind.will, mind.affect, mind.upkeep = MindWill.INSTRUCTED, MindAffect.MODELLED, MindUpkeep.ENERGY
        mind.purpose = MindPurpose.SOVEREIGN if await machine_ruled(ctx, core) else MindPurpose.STEWARD
        mind.copyable = mind.restorable = mind.transferable = mind.perfect_recall = True
        made += 1
    return made


def stance(values: dict[ValueAxis, int]) -> MadeMindStance:
    order = values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.PURITY, 0)
    open_mind = values.get(ValueAxis.XENOPHILIA, 0) + values.get(ValueAxis.KNOWLEDGE, 0)
    if order >= LEAN * 2 and order > open_mind:
        return MadeMindStance.ABOMINATION
    if open_mind >= LEAN * 2:
        return MadeMindStance.KIN
    if values.get(ValueAxis.LAW, 0) >= LEAN * 2:
        return MadeMindStance.REGULATED
    if values.get(ValueAxis.CRAFTSMANSHIP, 0) >= LEAN:
        return MadeMindStance.TOOL
    return MadeMindStance.SILENT


def relic_stance(values: dict[ValueAxis, int]) -> RelicStance:
    if values.get(ValueAxis.PIETY, 0) >= LEAN and values.get(ValueAxis.KNOWLEDGE, 0) < 0:
        return RelicStance.SACRED
    if values.get(ValueAxis.PURITY, 0) >= LEAN * 2:
        return RelicStance.FORBIDDEN
    if values.get(ValueAxis.KNOWLEDGE, 0) >= LEAN:
        return RelicStance.TOOL
    return RelicStance.HERITAGE


async def doctrines(ctx: TickContext) -> int:
    set_from = 0
    for doctrine in list(await ctx.session.scalars(select(CultDoctrineRow).order_by(CultDoctrineRow.cult_entity_id))):
        if held(doctrine.cult_entity_id):
            continue
        values = dict(await values_for(ctx.session, doctrine.cult_entity_id))
        kept = set(doctrine.locked or [])
        for column in ("made_mind_stance", "copy_stance", "augment_stance", "made_afterlife_stance"):
            if column not in kept:
                setattr(doctrine, column, stance(values))
        if "relic_stance" not in kept:
            doctrine.relic_stance = relic_stance(values)
        set_from += 1
    return set_from


@once
async def substrates(ctx: TickContext) -> int:
    made = 0
    peoples = select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    counted = set(await ctx.session.scalars(select(PeopleSubstrateRow.people_entity_id)))
    for people in list(await ctx.session.scalars(peoples)):
        if people in counted or held(people):
            continue
        ctx.session.add(PeopleSubstrateRow(people_entity_id=people, seat=MindSeat.BODY, origin=MindOrigin.BORN, share_pct=FULL, locked=[]))
        made += 1
    return made


async def keep_made_kinds(ctx: TickContext) -> int:
    return await prostheses(ctx) + await terraformers(ctx) + await farms(ctx) + await ruins(ctx) + await cores(ctx) + await doctrines(ctx)


async def legacy_backfill(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return 0
    result = {
        "prostheses": await prostheses(ctx),
        "terraformers": await terraformers(ctx),
        "farms": await farms(ctx),
        "ruins": await ruins(ctx),
        "cores": await cores(ctx),
        "doctrines": await doctrines(ctx),
        "substrates": await substrates(ctx),
    }
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
