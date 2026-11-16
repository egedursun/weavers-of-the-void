from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agrarian import (
    AidKind,
    CentralityRank,
    CommonsKind,
    CommonsRule,
    KeystoneUse,
    LandUseRing,
    NutrientKind,
    PerennialKind,
    PreparednessKind,
    RebuildCause,
    RebuildPlan,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.engine.agrarian import control
from aerona.engine.primitives.records import definite
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000_000
NAME = 200


class RegionTarget(Command):
    region_id: int


class RegionEdit(Edited):
    region_id: int


class RingDraft(Command):
    region_id: int
    ring: LandUseRing = LandUseRing.GRAIN
    market_id: int | None = None


class SettlementTarget(Command):
    settlement_id: int


class SettlementEdit(Edited):
    settlement_id: int


class CentralDraft(Command):
    settlement_id: int
    rank: CentralityRank = CentralityRank.WEEKLY
    centrality: int = Field(default=50, ge=0, le=SPAN)


class NutrientDraft(Command):
    region_id: int
    nutrient: NutrientKind = NutrientKind.FIXED
    stock: int = Field(default=50, ge=0, le=SPAN)


class NutrientTarget(Command):
    region_id: int
    nutrient: NutrientKind


class NutrientEdit(Edited):
    region_id: int
    nutrient: NutrientKind


class IntensityDraft(Command):
    region_id: int
    intensity: int = Field(default=40, ge=0, le=SPAN)
    research_boost: int = Field(default=20, ge=0, le=SPAN)


class PlantingDraft(Command):
    region_id: int
    kind: PerennialKind = PerennialKind.ORCHARD
    species_id: int | None = None
    owner_id: int | None = None
    area: int = Field(default=5, ge=1, le=SPAN)
    line_id: int | None = None


class PlantingTarget(Command):
    perennial_id: int


class PlantingEdit(Edited):
    perennial_id: int


class CommonsDraft(Command):
    region_id: int
    kind: CommonsKind = CommonsKind.PASTURE
    rule: CommonsRule = CommonsRule.CUSTOMARY
    steward_id: int | None = None


class CommonsTarget(Command):
    commons_id: int


class CommonsEdit(Edited):
    commons_id: int


class EnclosureDraft(Command):
    commons_id: int
    encloser_id: int


class ReserveDraft(Command):
    region_id: int
    holder_id: int
    species_id: int | None = None
    strictness: int = Field(default=60, ge=0, le=SPAN)


class ReserveTarget(Command):
    reserve_id: int


class ReserveEdit(Edited):
    reserve_id: int


class PeopleTarget(Command):
    people_id: int


class PeopleEdit(Edited):
    people_id: int


class FamineDraft(Command):
    people_id: int
    memory: int = Field(default=50, ge=0, le=SPAN)
    famine_foods: bool = True
    storage: int = Field(default=40, ge=0, le=SPAN)


class WorkDraft(Command):
    settlement_id: int
    kind: PreparednessKind = PreparednessKind.LEVEE
    level: int = Field(default=1, ge=1, le=5)


class WorkTarget(Command):
    settlement_id: int
    kind: PreparednessKind


class WorkEdit(Edited):
    settlement_id: int
    kind: PreparednessKind


class AidDraft(Command):
    giver_id: int
    settlement_id: int
    kind: AidKind = AidKind.GOODS
    amount: int = Field(default=200, ge=0, le=MANY)


class AidTarget(Command):
    aid_id: int


class AidEdit(Edited):
    aid_id: int


class RebuildDraft(Command):
    settlement_id: int
    cause: RebuildCause = RebuildCause.FIRE
    plan: RebuildPlan = RebuildPlan.PLANNED


class RebuildTarget(Command):
    rebuild_id: int


class RebuildEdit(Edited):
    rebuild_id: int


class KeystoneDraft(Command):
    world_id: int
    name: str = Field(min_length=1, max_length=NAME)
    use: KeystoneUse = KeystoneUse.RITE
    producer_id: int | None = None
    source_region_id: int | None = None
    commodity: CommodityKind | None = None
    cult_id: int | None = None


class KeystoneTarget(Command):
    keystone_id: int


class KeystoneEdit(Edited):
    keystone_id: int


class BrandDraft(Command):
    workshop_id: int
    name: str = Field(min_length=1, max_length=NAME)


class BrandTarget(Command):
    brand_id: int


class BrandEdit(Edited):
    brand_id: int


@player_action("land_ring:set", ActionKind.EDIT_RECORD)
async def land_ring_set(scope: PlayerScope, command: RingDraft) -> Effect:
    await control.set_ring(await scope.context("land_ring_set"), command.region_id, {"ring": command.ring.value, "market_entity_id": command.market_id})
    return Effect("The land's ring of use around its market is set.", command.region_id)


@player_action("land_ring:edit", ActionKind.EDIT_RECORD)
async def land_ring_edit(scope: PlayerScope, command: RegionEdit) -> Effect:
    await control.edit_record(await scope.context("land_ring_edit"), "land_ring", command.region_id, command.values, command.release)
    return Effect("The land's ring of use is set so.", command.region_id)


@player_action("land_ring:delete", ActionKind.EDIT_RECORD)
async def land_ring_delete(scope: PlayerScope, command: RegionTarget) -> Effect:
    await control.delete_record(await scope.context("land_ring_delete"), "land_ring", command.region_id)
    return Effect("The land's ring of use will be read anew.", command.region_id)


@player_action("central_place:set", ActionKind.EDIT_RECORD)
async def central_place_set(scope: PlayerScope, command: CentralDraft) -> Effect:
    values = {"rank": command.rank.value, "centrality": command.centrality}
    await control.set_central(await scope.context("central_place_set"), command.settlement_id, values)
    return Effect("The settlement's rank among central places is set.", command.settlement_id)


@player_action("central_place:edit", ActionKind.EDIT_RECORD)
async def central_place_edit(scope: PlayerScope, command: SettlementEdit) -> Effect:
    await control.edit_record(await scope.context("central_place_edit"), "central_place", command.settlement_id, command.values, command.release)
    return Effect("The central place is set so.", command.settlement_id)


@player_action("central_place:delete", ActionKind.EDIT_RECORD)
async def central_place_delete(scope: PlayerScope, command: SettlementTarget) -> Effect:
    await control.delete_record(await scope.context("central_place_delete"), "central_place", command.settlement_id)
    return Effect("The settlement's rank will be read anew.", command.settlement_id)


@player_action("soil_nutrient:set", ActionKind.EDIT_RECORD)
async def soil_nutrient_set(scope: PlayerScope, command: NutrientDraft) -> Effect:
    await control.set_nutrient(await scope.context("soil_nutrient_set"), command.region_id, command.nutrient, {"stock": command.stock})
    return Effect("The soil's stock is set.", command.region_id)


@player_action("soil_nutrient:edit", ActionKind.EDIT_RECORD)
async def soil_nutrient_edit(scope: PlayerScope, command: NutrientEdit) -> Effect:
    key = (command.region_id, command.nutrient)
    await control.edit_record(await scope.context("soil_nutrient_edit"), "soil_nutrient", key, command.values, command.release)
    return Effect("The soil's stock is set so.", command.region_id)


@player_action("soil_nutrient:delete", ActionKind.EDIT_RECORD)
async def soil_nutrient_delete(scope: PlayerScope, command: NutrientTarget) -> Effect:
    await control.delete_record(await scope.context("soil_nutrient_delete"), "soil_nutrient", (command.region_id, command.nutrient))
    return Effect("The soil's stock will be read anew from its natural soil.", command.region_id)


@player_action("intensification:set", ActionKind.EDIT_RECORD)
async def intensification_set(scope: PlayerScope, command: IntensityDraft) -> Effect:
    values = {"intensity": command.intensity, "research_boost": command.research_boost}
    await control.set_intensity(await scope.context("intensification_set"), command.region_id, values)
    return Effect("How hard the land is worked is set.", command.region_id)


@player_action("intensification:edit", ActionKind.EDIT_RECORD)
async def intensification_edit(scope: PlayerScope, command: RegionEdit) -> Effect:
    await control.edit_record(await scope.context("intensification_edit"), "intensification", command.region_id, command.values, command.release)
    return Effect("The farming of the land is set so.", command.region_id)


@player_action("intensification:delete", ActionKind.EDIT_RECORD)
async def intensification_delete(scope: PlayerScope, command: RegionTarget) -> Effect:
    await control.delete_record(await scope.context("intensification_delete"), "intensification", command.region_id)
    return Effect("The pressure on the land will be read anew.", command.region_id)


@player_action("perennial:plant", ActionKind.EDIT_RECORD)
async def perennial_plant(scope: PlayerScope, command: PlantingDraft) -> Effect:
    row = await control.plant(
        await scope.context("perennial_plant"),
        command.region_id,
        command.kind,
        species_id=command.species_id,
        owner_id=command.owner_id,
        area=command.area,
        line_id=command.line_id,
    )
    return Effect("A long-lived planting is set in the ground.", command.region_id, values={"perennial_id": row.id})


@player_action("perennial:edit", ActionKind.EDIT_RECORD)
async def perennial_edit(scope: PlayerScope, command: PlantingEdit) -> Effect:
    row = await control.edit_record(await scope.context("perennial_edit"), "perennial", command.perennial_id, command.values, command.release)
    return Effect("The planting is set so.", getattr(row, "region_entity_id", None))


@player_action("perennial:fell", ActionKind.EDIT_RECORD)
async def perennial_fell(scope: PlayerScope, command: PlantingTarget) -> Effect:
    row = await control.fell(await scope.context("perennial_fell"), command.perennial_id)
    return Effect("The plantings of the land are cut down.", row.region_entity_id)


@player_action("perennial:delete", ActionKind.EDIT_RECORD)
async def perennial_delete(scope: PlayerScope, command: PlantingTarget) -> Effect:
    await control.delete_record(await scope.context("perennial_delete"), "perennial", command.perennial_id)
    return Effect("The planting is gone.")


@player_action("commons:create", ActionKind.EDIT_RECORD)
async def commons_create(scope: PlayerScope, command: CommonsDraft) -> Effect:
    row = await control.open_commons(await scope.context("commons_create"), command.region_id, command.kind, command.rule, command.steward_id)
    return Effect("A common is held by the folk of the land.", command.region_id, values={"commons_id": row.id})


@player_action("commons:edit", ActionKind.EDIT_RECORD)
async def commons_edit(scope: PlayerScope, command: CommonsEdit) -> Effect:
    row = await control.edit_record(await scope.context("commons_edit"), "commons", command.commons_id, command.values, command.release)
    return Effect("The common is set so.", getattr(row, "region_entity_id", None))


@player_action("commons:enclose", ActionKind.EDIT_RECORD)
async def commons_enclose(scope: PlayerScope, command: EnclosureDraft) -> Effect:
    row = await control.enclose_common(await scope.context("commons_enclose"), command.commons_id, command.encloser_id)
    return Effect("The common is enclosed and those who used it are driven off.", row.region_entity_id)


@player_action("commons:delete", ActionKind.EDIT_RECORD)
async def commons_delete(scope: PlayerScope, command: CommonsTarget) -> Effect:
    await control.delete_record(await scope.context("commons_delete"), "commons", command.commons_id)
    return Effect("The common is no more.")


@player_action("game_reserve:declare", ActionKind.EDIT_RECORD)
async def game_reserve_declare(scope: PlayerScope, command: ReserveDraft) -> Effect:
    row = await control.declare_reserve(
        await scope.context("game_reserve_declare"), command.region_id, command.holder_id, command.species_id, command.strictness
    )
    return Effect("The game of the land is reserved.", command.region_id, values={"reserve_id": row.id})


@player_action("game_reserve:edit", ActionKind.EDIT_RECORD)
async def game_reserve_edit(scope: PlayerScope, command: ReserveEdit) -> Effect:
    row = await control.edit_record(await scope.context("game_reserve_edit"), "game_reserve", command.reserve_id, command.values, command.release)
    return Effect("The game reserve is set so.", getattr(row, "region_entity_id", None))


@player_action("game_reserve:delete", ActionKind.EDIT_RECORD)
async def game_reserve_delete(scope: PlayerScope, command: ReserveTarget) -> Effect:
    await control.delete_record(await scope.context("game_reserve_delete"), "game_reserve", command.reserve_id)
    return Effect("The game laws of the land are lifted.")


@player_action("famine_lore:set", ActionKind.EDIT_RECORD)
async def famine_lore_set(scope: PlayerScope, command: FamineDraft) -> Effect:
    values = {"memory": command.memory, "famine_foods": command.famine_foods, "storage": command.storage}
    await control.set_famine(await scope.context("famine_lore_set"), command.people_id, values)
    return Effect("What the people remember of hunger is set.", command.people_id)


@player_action("famine_lore:edit", ActionKind.EDIT_RECORD)
async def famine_lore_edit(scope: PlayerScope, command: PeopleEdit) -> Effect:
    await control.edit_record(await scope.context("famine_lore_edit"), "famine_lore", command.people_id, command.values, command.release)
    return Effect("The famine lore is set so.", command.people_id)


@player_action("famine_lore:delete", ActionKind.EDIT_RECORD)
async def famine_lore_delete(scope: PlayerScope, command: PeopleTarget) -> Effect:
    await control.delete_record(await scope.context("famine_lore_delete"), "famine_lore", command.people_id)
    return Effect("The people's memory of hunger will be read anew.", command.people_id)


@player_action("preparedness:build", ActionKind.EDIT_RECORD)
async def preparedness_build(scope: PlayerScope, command: WorkDraft) -> Effect:
    await control.build_work(await scope.context("preparedness_build"), command.settlement_id, command.kind, command.level)
    return Effect("The town's works against disaster are raised.", command.settlement_id)


@player_action("preparedness:edit", ActionKind.EDIT_RECORD)
async def preparedness_edit(scope: PlayerScope, command: WorkEdit) -> Effect:
    key = (command.settlement_id, command.kind)
    await control.edit_record(await scope.context("preparedness_edit"), "preparedness", key, command.values, command.release)
    return Effect("The work against disaster is set so.", command.settlement_id)


@player_action("preparedness:delete", ActionKind.EDIT_RECORD)
async def preparedness_delete(scope: PlayerScope, command: WorkTarget) -> Effect:
    await control.delete_record(await scope.context("preparedness_delete"), "preparedness", (command.settlement_id, command.kind))
    return Effect("The work against disaster is torn down.", command.settlement_id)


@player_action("relief:send", ActionKind.EDIT_RECORD)
async def relief_send(scope: PlayerScope, command: AidDraft) -> Effect:
    row = await control.send_aid(await scope.context("relief_send"), command.giver_id, command.settlement_id, command.kind, command.amount)
    text = "The aid was turned away." if row.refused else "Aid reaches the town."
    return Effect(text, command.settlement_id, values={"aid_id": row.id})


@player_action("relief:edit", ActionKind.EDIT_RECORD)
async def relief_edit(scope: PlayerScope, command: AidEdit) -> Effect:
    row = await control.edit_record(await scope.context("relief_edit"), "relief", command.aid_id, command.values, command.release)
    return Effect("The record of aid is set so.", getattr(row, "receiver_entity_id", None))


@player_action("relief:delete", ActionKind.EDIT_RECORD)
async def relief_delete(scope: PlayerScope, command: AidTarget) -> Effect:
    await control.delete_record(await scope.context("relief_delete"), "relief", command.aid_id)
    return Effect("The record of aid is struck out.")


@player_action("reconstruction:begin", ActionKind.EDIT_RECORD)
async def reconstruction_begin(scope: PlayerScope, command: RebuildDraft) -> Effect:
    row = await control.begin_rebuild(await scope.context("reconstruction_begin"), command.settlement_id, command.cause, command.plan)
    return Effect("The town begins to rebuild.", command.settlement_id, values={"rebuild_id": row.id})


@player_action("reconstruction:edit", ActionKind.EDIT_RECORD)
async def reconstruction_edit(scope: PlayerScope, command: RebuildEdit) -> Effect:
    row = await control.edit_record(await scope.context("reconstruction_edit"), "reconstruction", command.rebuild_id, command.values, command.release)
    return Effect("The rebuilding is set so.", getattr(row, "settlement_entity_id", None))


@player_action("reconstruction:finish", ActionKind.EDIT_RECORD)
async def reconstruction_finish(scope: PlayerScope, command: RebuildTarget) -> Effect:
    row = await control.finish_rebuild(await scope.context("reconstruction_finish"), command.rebuild_id)
    return Effect("The town stands rebuilt.", row.settlement_entity_id)


@player_action("reconstruction:delete", ActionKind.EDIT_RECORD)
async def reconstruction_delete(scope: PlayerScope, command: RebuildTarget) -> Effect:
    await control.delete_record(await scope.context("reconstruction_delete"), "reconstruction", command.rebuild_id)
    return Effect("The rebuilding is abandoned.")


@player_action("keystone:designate", ActionKind.EDIT_RECORD)
async def keystone_designate(scope: PlayerScope, command: KeystoneDraft) -> Effect:
    row = await control.designate_keystone(
        await scope.context("keystone_designate"),
        command.world_id,
        command.name,
        use=command.use,
        producer_id=command.producer_id,
        source_id=command.source_region_id,
        commodity=command.commodity,
        cult_id=command.cult_id,
    )
    return Effect(f"{definite(row.name)} is what the world depends on.", command.source_region_id, values={"keystone_id": row.id})


@player_action("keystone:edit", ActionKind.EDIT_RECORD)
async def keystone_edit(scope: PlayerScope, command: KeystoneEdit) -> Effect:
    row = await control.edit_record(await scope.context("keystone_edit"), "keystone", command.keystone_id, command.values, command.release)
    return Effect("The keystone resource is set so.", getattr(row, "source_region_entity_id", None))


@player_action("keystone:delete", ActionKind.EDIT_RECORD)
async def keystone_delete(scope: PlayerScope, command: KeystoneTarget) -> Effect:
    await control.delete_record(await scope.context("keystone_delete"), "keystone", command.keystone_id)
    return Effect("The world no longer depends on one resource.")


@player_action("brand:found", ActionKind.EDIT_RECORD)
async def brand_found(scope: PlayerScope, command: BrandDraft) -> Effect:
    row = await control.found_brand(await scope.context("brand_found"), command.workshop_id, command.name)
    return Effect("The workshop's makers are known by name.", row.community_entity_id, values={"brand_id": row.id})


@player_action("brand:edit", ActionKind.EDIT_RECORD)
async def brand_edit(scope: PlayerScope, command: BrandEdit) -> Effect:
    row = await control.edit_record(await scope.context("brand_edit"), "brand", command.brand_id, command.values, command.release)
    return Effect("The brand is set so.", getattr(row, "community_entity_id", None))


@player_action("brand:delete", ActionKind.EDIT_RECORD)
async def brand_delete(scope: PlayerScope, command: BrandTarget) -> Effect:
    await control.delete_record(await scope.context("brand_delete"), "brand", command.brand_id)
    return Effect("The brand is forgotten.")
