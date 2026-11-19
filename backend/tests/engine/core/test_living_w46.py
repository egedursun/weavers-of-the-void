import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import BOND_KINDS
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.agrarian import PerennialRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, LivingLineSourceRow, LivingLineTraitRow, LivingProfileRow
from aerona.db.tables.polity import TreatyClauseRow
from aerona.domain.enums.agrarian import PerennialKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import DomesticationStage
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.living import CultivationMethod, GrowthStage, LineTrait, LivingCraftStance, Metabolism
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import ClauseKind
from aerona.domain.models.entity_stats import DiseaseStats, SpeciesStats, StructureStats, TreatyStats
from aerona.engine.disease.designed import designed_aim
from aerona.engine.disease.emergence import ensure_profile
from aerona.engine.living.backfill import LEGACY_FIXUP, legacy_backfill
from aerona.engine.living.kin import clone, sampled
from aerona.engine.living.lines import LineDraft, escape, make_line
from aerona.engine.living.production import blight_monocultures, keep_living_works
from aerona.engine.living.profiles import keep_profiles
from aerona.engine.living.society import living_stance
from aerona.engine.minds.war_methods import method_breached
from aerona.engine.powers.control import add_part
from aerona.engine.primitives.stats import stat_or
from aerona.services.player.living import BANK_PARTS, LINE_PARTS
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at

STRUCTURE_STATS = StructureStats(splendor=40, durability=40, function=40)
COUGH = DiseaseStats(virulence=30, lethality=20, infected=0, dead=0)


async def works(session: AsyncSession, world: CoreWorld, town_id: int, name: str = "the green hall") -> EntityRow:
    return await entity(session, name, EntityType.STRUCTURE, STRUCTURE_STATS, world_id=world.world.id, location_id=town_id)


def alive(thing_id: int, **values: object) -> LivingProfileRow:
    return LivingProfileRow(
        thing_node_id=thing_id,
        metabolism=values.get("metabolism", Metabolism.LIGHT),
        growth_stage=values.get("growth_stage", GrowthStage.SEED),
        size_pct=20,
        regeneration=20,
        health=values.get("health", 100),
        bond=50,
        lifespan_years=values.get("lifespan_years", 40),
        age_seasons=values.get("age_seasons", 0),
        planted_epoch=1,
        locked=[],
    )


def line_of(name: str, owner_id: int | None, species_id: int | None) -> LivingLineRow:
    return LivingLineRow(
        name=name,
        method=CultivationMethod.SELECTIVE_BREEDING,
        stability=70,
        owner_node_id=owner_id,
        maker_node_id=owner_id,
        species_entity_id=species_id,
        locked=[],
    )


async def test_a_seed_ages_every_season_of_an_epoch(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    hall = await works(session, world, town.id)
    session.add(alive(hall.id, lifespan_years=400))
    await session.flush()
    assert await keep_profiles(await at(session, 2)) == 1
    row = await session.get(LivingProfileRow, hall.id)
    assert row is not None and row.age_seasons == 4 * 50 and row.growth_stage is GrowthStage.PRIME and row.size_pct == 30


async def test_an_unfed_living_thing_dies_and_its_record_ends(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    hall = await works(session, world, town.id)
    row = alive(hall.id, metabolism=Metabolism.FEEDING, growth_stage=GrowthStage.GROWN, health=10, age_seasons=10)
    row.feed_commodity = CommodityKind.FODDER
    session.add(row)
    await session.flush()
    await keep_profiles(await at(session, 2))
    row = await session.get(LivingProfileRow, hall.id)
    assert row is not None and row.growth_stage is GrowthStage.DEAD
    assert hall.status is EntityStatus.DESTROYED


async def test_a_line_kept_by_its_maker_escapes_into_the_wild(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    breeder = await mortal(session, "Ila Venn", world, town.id)
    kind = await entity(session, "Marsh striders", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id, location_id=world.regions[1].id)
    line = line_of("the long-legged line", breeder.id, kind.id)
    session.add(line)
    await session.flush()
    assert await escape(await at(session, 2, living_methods={"escape_chance": 100}), line)
    assert line.escaped
    assert await session.get(SpeciesRangeRow, (kind.id, world.regions[0].id)) is not None


async def test_sampling_the_same_organism_again_refreshes_the_kept_sample(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    vault = await works(session, world, town.id, "the seed vault")
    breeder = await mortal(session, "Ila Venn", world, town.id)
    session.add(GeneBankRow(structure_entity_id=vault.id, holder_node_id=breeder.id, upkeep=2, unpaid_epochs=0, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    first = await sampled(ctx, vault.id, breeder.id, 60)
    second = await sampled(ctx, vault.id, breeder.id, 85)
    assert first.id == second.id and second.quality == 85
    count = await session.scalar(select(func.count()).select_from(GeneBankSampleRow).where(GeneBankSampleRow.bank_entity_id == vault.id))
    assert count == 1


async def test_a_part_a_line_or_bank_already_holds_is_refused_rather_than_crashing(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    breeder = await mortal(session, "Ila Venn", world, town.id)
    vault = await works(session, world, town.id, "the seed vault")
    line = line_of("the long-legged line", breeder.id, None)
    session.add(line)
    session.add(GeneBankRow(structure_entity_id=vault.id, holder_node_id=breeder.id, upkeep=2, unpaid_epochs=0, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    await add_part(ctx, LINE_PARTS, "trait", line.id, {"trait": LineTrait.SPEED, "strength": 20})
    with pytest.raises(ValidationFailedError):
        await add_part(ctx, LINE_PARTS, "trait", line.id, {"trait": LineTrait.SPEED, "strength": 40})
    await add_part(ctx, BANK_PARTS, "sample", vault.id, {"organism_node_id": breeder.id, "quality": 70, "taken_epoch": 2})
    with pytest.raises(ValidationFailedError):
        await add_part(ctx, BANK_PARTS, "sample", vault.id, {"organism_node_id": breeder.id, "quality": 50, "taken_epoch": 2})


async def test_a_line_drafted_with_repeated_sources_and_traits_is_made_once_each(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    breeder = await mortal(session, "Ila Venn", world, town.id)
    other = await mortal(session, "Oren Vale", world, town.id)
    draft = LineDraft(
        "the twice-named line", CultivationMethod.ENGINEERING, breeder.id, breeder.id, (other.id, other.id), ((LineTrait.YIELD, 20), (LineTrait.YIELD, 30))
    )
    line = await make_line(await at(session, 2, genome_design={"side_effect_chance": 100}), draft, forced=True)
    sources = await session.scalar(select(func.count()).select_from(LivingLineSourceRow).where(LivingLineSourceRow.line_id == line.id))
    traits = list(await session.scalars(select(LivingLineTraitRow).where(LivingLineTraitRow.line_id == line.id)))
    assert sources == 1
    assert [row.strength for row in traits if row.trait is LineTrait.YIELD] == [50]
    assert len({row.trait for row in traits}) == len(traits)


async def test_a_clone_of_a_clone_lives_shorter_and_both_know_their_source(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    source = await mortal(session, "Ila Venn", world, town.id, lifespan=100)
    ctx = await at(session, 2)
    first = await clone(ctx, source.id, None)
    second = await clone(ctx, first.id, None)
    assert stat_or(first, "lifespan", 0) == 85 and stat_or(second, "lifespan", 0) < stat_or(first, "lifespan", 0)
    bonds = await session.scalar(select(func.count()).select_from(BondRow).where(BondRow.kind == BondKind.CLONE_OF))
    assert bonds == 2
    assert BondKind.CLONE_OF in BOND_KINDS


async def test_a_designed_disease_strikes_those_it_was_made_for_hardest(session: AsyncSession, world: CoreWorld) -> None:
    aimed = await settlement(session, "Greenmere", world, world.regions[0])
    spared = await settlement(session, "Lowmere", world, world.regions[1])
    sickness = await entity(
        session, "the grey cough", EntityType.DISEASE, DiseaseStats(virulence=30, lethality=20, infected=0, dead=0), world_id=world.world.id
    )
    ctx = await at(session, 2)
    profile = await ensure_profile(session, ctx, sickness)
    profile.target_node_id = aimed.id
    await session.flush()
    assert await designed_aim(session, ctx.rules, aimed, sickness.id) > 1.0
    assert await designed_aim(session, ctx.rules, spared, sickness.id) < 1.0


async def test_a_line_grown_alone_across_a_land_is_struck_by_blight(session: AsyncSession, world: CoreWorld) -> None:
    line = line_of("the one crop", None, None)
    session.add(line)
    await session.flush()
    session.add_all(
        PerennialRow(region_entity_id=world.regions[0].id, kind=PerennialKind.ORCHARD, line_id=line.id, area=5, condition=100, planted_epoch=1, locked=[])
        for _ in range(2)
    )
    await session.flush()
    assert await blight_monocultures(await at(session, 2, living={"blight_chance": 100})) == 1
    conditions = list(await session.scalars(select(PerennialRow.condition).where(PerennialRow.line_id == line.id)))
    assert conditions == [60, 60]


async def test_living_works_give_way_to_the_older_method_when_their_living_structures_sicken(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    vats = await works(session, world, town.id, "the vats")
    session.add(alive(vats.id, health=10, growth_stage=GrowthStage.GROWN))
    session.add(CommunityMethodRow(community_node_id=town.id, process=ProcessKind.FARMING, method=MethodKind.VAT_CULTURE, adopted_epoch=1, locked=[]))
    await session.flush()
    assert await keep_living_works(await at(session, 2)) == 1
    method = await session.scalar(select(CommunityMethodRow.method).where(CommunityMethodRow.community_node_id == town.id))
    assert method is not MethodKind.VAT_CULTURE


async def test_the_backfill_gives_bred_species_a_line_once(session: AsyncSession, world: CoreWorld) -> None:
    kinds = list(await session.scalars(select(SpeciesProfileRow).limit(1)))
    if kinds:
        kinds[0].stage = DomesticationStage.BREED
        await session.flush()
    ctx = await at(session, 2)
    await legacy_backfill(ctx)
    assert await legacy_backfill(ctx) == 0
    if kinds:
        assert await session.scalar(select(LivingLineRow.id).where(LivingLineRow.species_entity_id == kinds[0].species_entity_id)) is not None
    assert LEGACY_FIXUP


def test_a_faith_that_prizes_purity_over_craft_calls_living_craft_an_abomination() -> None:
    assert living_stance({ValueAxis.PURITY: 40, ValueAxis.TRADITION: 30}) is LivingCraftStance.ABOMINATION
    assert living_stance({ValueAxis.KNOWLEDGE: 40, ValueAxis.CRAFTSMANSHIP: 30}) is LivingCraftStance.PERMITTED
    assert living_stance({}) is LivingCraftStance.SILENT


async def test_making_a_disease_aimed_at_a_treaty_partner_breaks_the_clause_against_it(session: AsyncSession, world: CoreWorld) -> None:
    ours = await settlement(session, "Greenmere", world, world.regions[0])
    theirs = await settlement(session, "Lowmere", world, world.regions[1])
    maker = await mortal(session, "Ila Venn", world, ours.id)
    line = line_of("the strain behind the grey cough", maker.id, None)
    session.add(line)
    sickness = await entity(session, "the grey cough", EntityType.DISEASE, COUGH, world_id=world.world.id)
    pact = await entity(session, "the clean accord", EntityType.TREATY, TreatyStats(), world_id=world.world.id)
    await session.flush()
    ctx = await at(session, 2)
    profile = await ensure_profile(session, ctx, sickness)
    profile.designed_line_id, profile.target_node_id = line.id, theirs.id
    clause = TreatyClauseRow(treaty_entity_id=pact.id, kind=ClauseKind.NO_DESIGNED_DISEASE, obligor_node_id=ours.id, beneficiary_node_id=theirs.id, locked=[])
    session.add(clause)
    await session.flush()
    assert await method_breached(ctx, clause) == "it made a disease aimed at the other side"
    clause.kind = ClauseKind.NO_PLAGUE_POWERS
    assert await method_breached(ctx, clause) is None
