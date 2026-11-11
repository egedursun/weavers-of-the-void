from aerona.core.errors import ValidationFailedError
from aerona.core.total import partial
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import (
    CARRIER_FIELDS,
    CYCLE_FIELDS,
    MARK_FIELDS,
    RESEARCH_FIELDS,
    RESPONSE_FIELDS,
    SERVICE_FIELDS,
    TRAIT_FIELDS,
    CarrierRow,
    CureResearchRow,
    EcosystemServiceRow,
    LineageMarkRow,
    PlagueResponseRow,
    SpeciesTraitRow,
    WorldCycleRow,
)
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, PlagueResponse
from aerona.domain.enums.happening import LandAct
from aerona.engine.context import TickContext
from aerona.engine.cosmos.cycles import BALANCE
from aerona.engine.disease.research import SEATS_OF_LEARNING
from aerona.engine.disease.responses import take_up
from aerona.engine.divine.control import apply
from aerona.engine.ecology.evolution import seed_traits
from aerona.engine.ecology.feral import release_herd
from aerona.engine.ecology.lineages import mark
from aerona.engine.environment.shaping import LandOutcome, reshape_ground
from aerona.engine.gatherings.control import Values, allowed, entity, found
from aerona.engine.gods.worship import creator_node_id

ECOLOGY_FIELDS = ("keystone", "feral_epoch")
OUTCOME_REASONS = partial(
    LandOutcome,
    {
        LandOutcome.NO_RIVER: "No river there can leave its bed: it needs a flowing river and a free neighbouring land.",
        LandOutcome.NO_COAST: "That land has no coast to sink.",
        LandOutcome.UNCHANGED: "The land is already so, or it is held.",
    },
    without={LandOutcome.DONE},
)


async def of_type(ctx: TickContext, entity_id: int, kinds: frozenset[EntityType], label: str) -> EntityRow:
    row = await entity(ctx, entity_id, label)
    if row.entity_type not in kinds:
        raise ValidationFailedError(f"{row.name} is not {label}.")
    return row


async def species_profile(ctx: TickContext, species_id: int) -> SpeciesProfileRow:
    await of_type(ctx, species_id, frozenset({EntityType.SPECIES}), "a species")
    return await found(ctx, SpeciesProfileRow, species_id, "species profile")


async def set_trait(ctx: TickContext, species_id: int, region_id: int, trait: EvolvedTrait, *, mean: int, variance: int | None) -> SpeciesTraitRow:
    species = await of_type(ctx, species_id, frozenset({EntityType.SPECIES}), "a species")
    profile = await species_profile(ctx, species_id)
    await of_type(ctx, region_id, frozenset({EntityType.REGION}), "a region")
    row = await ctx.session.get(SpeciesTraitRow, (species_id, region_id, trait))
    if row is None:
        rows = {item.trait: item for item in await seed_traits(ctx.session, species, profile, region_id, ctx.epoch)}
        row = rows[trait]
    values: dict[str, int] = {"mean": mean}
    if variance is not None:
        values["variance"] = variance
    apply(row, values, [])
    await ctx.session.flush()
    return row


async def edit_trait(ctx: TickContext, species_id: int, region_id: int, trait: EvolvedTrait, *, values: Values, release: list[str]) -> SpeciesTraitRow:
    row = apply(await found(ctx, SpeciesTraitRow, (species_id, region_id, trait), "trait"), allowed(values, TRAIT_FIELDS, "trait"), release)
    await ctx.session.flush()
    return row


async def delete_traits(ctx: TickContext, species_id: int, region_id: int, trait: EvolvedTrait | None) -> int:
    traits = [trait] if trait is not None else list(EvolvedTrait)
    removed = 0
    for item in traits:
        row = await ctx.session.get(SpeciesTraitRow, (species_id, region_id, item))
        if row is not None:
            await ctx.session.delete(row)
            removed += 1
    if not removed:
        raise ValidationFailedError("That species carries no such trait in that land.")
    await ctx.session.flush()
    return removed


async def mark_line(ctx: TickContext, species_id: int, package: PackageKind, *, blessing: bool, source_node_id: int | None) -> LineageMarkRow:
    species = await of_type(ctx, species_id, frozenset({EntityType.SPECIES}), "a species")
    row = await mark(ctx, species, package, blessing=blessing, source_node_id=source_node_id)
    apply(row, {"blessing": blessing, "source_node_id": source_node_id}, [])
    await ctx.session.flush()
    return row


async def edit_mark(ctx: TickContext, species_id: int, package: PackageKind, values: Values, release: list[str]) -> LineageMarkRow:
    row = apply(await found(ctx, LineageMarkRow, (species_id, package), "lineage mark"), allowed(values, MARK_FIELDS, "lineage mark"), release)
    await ctx.session.flush()
    return row


async def delete_mark(ctx: TickContext, species_id: int, package: PackageKind) -> None:
    await ctx.session.delete(await found(ctx, LineageMarkRow, (species_id, package), "lineage mark"))
    await ctx.session.flush()


async def edit_ecology(ctx: TickContext, species_id: int, values: Values, release: list[str]) -> SpeciesProfileRow:
    row = apply(await species_profile(ctx, species_id), allowed(values, ECOLOGY_FIELDS, "species"), release)
    await ctx.session.flush()
    return row


async def set_service(ctx: TickContext, region_id: int, role: KeystoneRole, strength: int, species_id: int | None) -> EcosystemServiceRow:
    await of_type(ctx, region_id, frozenset({EntityType.REGION}), "a region")
    if species_id is not None:
        await of_type(ctx, species_id, frozenset({EntityType.SPECIES}), "a species")
    row = await ctx.session.get(EcosystemServiceRow, (region_id, role))
    if row is None:
        row = EcosystemServiceRow(region_entity_id=region_id, role=role, strength=0, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"strength": strength, "species_entity_id": species_id}, [])
    await ctx.session.flush()
    return row


async def edit_service(ctx: TickContext, region_id: int, role: KeystoneRole, values: Values, release: list[str]) -> EcosystemServiceRow:
    row = apply(await found(ctx, EcosystemServiceRow, (region_id, role), "service"), allowed(values, SERVICE_FIELDS, "service"), release)
    await ctx.session.flush()
    return row


async def delete_service(ctx: TickContext, region_id: int, role: KeystoneRole) -> None:
    await ctx.session.delete(await found(ctx, EcosystemServiceRow, (region_id, role), "service"))
    await ctx.session.flush()


async def release(ctx: TickContext, community_id: int, species_id: int) -> int | None:
    herd = await found(ctx, HerdRow, (community_id, species_id), "herd")
    row = await release_herd(ctx, herd)
    return row.region_entity_id if row is not None else None


async def disease(ctx: TickContext, disease_id: int) -> EntityRow:
    return await of_type(ctx, disease_id, frozenset({EntityType.DISEASE}), "a disease")


async def add_carrier(ctx: TickContext, mortal_id: int, disease_id: int) -> CarrierRow:
    mortal = await of_type(ctx, mortal_id, frozenset({EntityType.MORTAL}), "a mortal")
    await disease(ctx, disease_id)
    row = await ctx.session.get(CarrierRow, (mortal.id, disease_id))
    if row is None:
        row = CarrierRow(
            mortal_entity_id=mortal.id, disease_entity_id=disease_id, home_region_id=None, identified=False, seeded=0, since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def edit_carrier(ctx: TickContext, mortal_id: int, disease_id: int, values: Values, release: list[str]) -> CarrierRow:
    row = apply(await found(ctx, CarrierRow, (mortal_id, disease_id), "carrier"), allowed(values, CARRIER_FIELDS, "carrier"), release)
    await ctx.session.flush()
    return row


async def delete_carrier(ctx: TickContext, mortal_id: int, disease_id: int) -> None:
    await ctx.session.delete(await found(ctx, CarrierRow, (mortal_id, disease_id), "carrier"))
    await ctx.session.flush()


async def set_response(ctx: TickContext, community_id: int, disease_id: int, response: PlagueResponse, strength: int) -> PlagueResponseRow:
    community = await of_type(ctx, community_id, frozenset(COMMUNITY_TYPES), "a community")
    await disease(ctx, disease_id)
    row = await take_up(ctx, community, disease_id, response, strength=strength)
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def edit_response(
    ctx: TickContext, community_id: int, disease_id: int, response: PlagueResponse, *, values: Values, release: list[str]
) -> PlagueResponseRow:
    row = apply(
        await found(ctx, PlagueResponseRow, (community_id, disease_id, response), "plague response"),
        allowed(values, RESPONSE_FIELDS, "plague response"),
        release,
    )
    await ctx.session.flush()
    return row


async def delete_response(ctx: TickContext, community_id: int, disease_id: int, response: PlagueResponse) -> None:
    await ctx.session.delete(await found(ctx, PlagueResponseRow, (community_id, disease_id, response), "plague response"))
    await ctx.session.flush()


async def start_research(ctx: TickContext, institution_id: int, disease_id: int) -> CureResearchRow:
    await entity(ctx, institution_id, "institution")
    profile = await ctx.session.get(StructureProfileRow, institution_id)
    if profile is None or profile.kind not in SEATS_OF_LEARNING:
        raise ValidationFailedError("Only a hospital, academy or monastery can seek a cure.")
    await disease(ctx, disease_id)
    row = await ctx.session.get(CureResearchRow, (institution_id, disease_id))
    if row is None:
        row = CureResearchRow(institution_entity_id=institution_id, disease_entity_id=disease_id, points=0, specimens=0, started_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def edit_research(ctx: TickContext, institution_id: int, disease_id: int, values: Values, release: list[str]) -> CureResearchRow:
    row = apply(await found(ctx, CureResearchRow, (institution_id, disease_id), "cure research"), allowed(values, RESEARCH_FIELDS, "cure research"), release)
    await ctx.session.flush()
    return row


async def delete_research(ctx: TickContext, institution_id: int, disease_id: int) -> None:
    await ctx.session.delete(await found(ctx, CureResearchRow, (institution_id, disease_id), "cure research"))
    await ctx.session.flush()


async def edit_cycle(ctx: TickContext, world_id: int, values: Values, release: list[str]) -> WorldCycleRow:
    row = await ctx.session.get(WorldCycleRow, world_id)
    if row is None:
        row = WorldCycleRow(world_id=world_id, carbon=BALANCE, water=BALANCE, nutrients=BALANCE, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, CYCLE_FIELDS, "world cycle"), release)
    await ctx.session.flush()
    return row


async def reset_cycle(ctx: TickContext, world_id: int) -> None:
    await ctx.session.delete(await found(ctx, WorldCycleRow, world_id, "world cycle"))
    await ctx.session.flush()


async def shape_land(ctx: TickContext, region_id: int, act: LandAct, target_region_id: int | None, *, fiery: bool) -> EntityRow:
    region = await of_type(ctx, region_id, frozenset({EntityType.REGION}), "a region")
    ground = await found(ctx, RegionEnvironmentRow, region_id, "surveyed land")
    god_id = await creator_node_id(ctx.session)
    if god_id is None:
        raise ValidationFailedError("The Creator has no place in the world to act from.")
    outcome = await reshape_ground(ctx, region, ground, act, god_id=god_id, fiery=fiery, target_region_id=target_region_id)
    if outcome is not LandOutcome.DONE:
        raise ValidationFailedError(OUTCOME_REASONS[outcome])
    return region
