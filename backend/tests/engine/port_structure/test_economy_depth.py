from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_tables import ORIGIN_BASE
from aerona.catalog.materials import MATERIALS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.economy import CommunityStockRow, LoanRow, NodeMaterialRow, ResourceProfileRow, WorkshopRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.economy import CommodityKind, FoeNature, GoodsFlow, LoanStatus, MaterialFamily, MaterialOrigin, MaterialSlot, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.polity import DebtRemedy, LawKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.war import CaptiveStatus, DebtStatus
from aerona.domain.models.entity_stats import EntityStats, FactionStats, ItemStats, ResourceStats, SpeciesStats, StructureStats, VesselStats
from aerona.engine.cosmos.vessels import set_vessel_kind
from aerona.engine.economy import control_depth
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.control_depth import Substance
from aerona.engine.economy.deposits import has_substance, new_substance
from aerona.engine.economy.extraction import knowledge_gate
from aerona.engine.economy.loot import loot_temples
from aerona.engine.economy.markets import quote_market
from aerona.engine.economy.materials import (
    MaterialBook,
    MaterialProps,
    battle_wear,
    draw_strength,
    forge_heat,
    forge_level,
    forgeable,
    from_spec,
    holy_edge,
    hull_guard,
    light_fabric,
    price_premium,
    rig_of,
    rust_wear,
    set_node_material,
    sharpness,
    unmet_need,
    weapon_damage,
    wind_guard,
    worth_factor,
)
from aerona.engine.economy.money import MoneyTally
from aerona.engine.economy.provenance import ensure_materials, sweep_materials
from aerona.engine.economy.realm_credit import collect_from_realms, lend_to_realms
from aerona.engine.economy.sanctity import holy_strike, natures_of
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.economy.survey import DEPTH_FIXUP, PROFILE_FIXUP, depth_backfill, profile_resources
from aerona.engine.economy.workshop_designs import NewDesign, capacity_scale, create_design, output_scale, workshop_store_units
from aerona.engine.phases.market import market
from aerona.engine.phases.production import species_products
from aerona.engine.phases.society_economy import default_society, save_society
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import found_polity
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

M = MaterialKind


def props(kind: MaterialKind) -> MaterialProps:
    return from_spec(MATERIALS[kind])


async def made(session: AsyncSession, world: CoreWorld, name: str, entity_type: EntityType, stats: EntityStats, *, at: int) -> EntityRow:
    ctx = await manual_context(session, "make", Rules())
    return await create_record(
        ctx, RecordSpec(name=name, entity_type=entity_type, stats=stats, body=f"{name}.", power=2, world_id=world.world.id, location_id=at)
    )


async def slot(session: AsyncSession, node_id: int, which: MaterialSlot = MaterialSlot.BODY) -> NodeMaterialRow | None:
    return await session.get(NodeMaterialRow, (node_id, which))


async def test_every_new_made_thing_takes_a_material_from_its_makers_stores(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brennhold", world, world.regions[0])
    ctx = await manual_context(session, "stock", Rules())
    await goods_of(session, ctx.epoch).add(town.id, CommodityKind.ORE, 50, GoodsFlow.PLAYER, material=M.FLINT)
    blade = await made(session, world, "Grey Fang", EntityType.ITEM, ItemStats(damage=40, protection=0, might=5, curse=0), at=town.id)
    hall = await made(session, world, "Long Hall", EntityType.STRUCTURE, StructureStats(splendor=20, durability=60, function=30), at=town.id)
    ship = await made(session, world, "Wavecutter", EntityType.VESSEL, VesselStats(speed=40, range=40, crew=20, armor=30), at=town.id)
    found = await slot(session, blade.id)
    assert found is not None and found.material is M.FLINT
    wall = await slot(session, hall.id)
    assert wall is not None and wall.material is M.STONE
    hull, sails = await slot(session, ship.id, MaterialSlot.HULL), await slot(session, ship.id, MaterialSlot.FABRIC)
    assert hull is not None and hull.material is M.WOOD
    assert sails is not None and sails.material is M.CLOTH


async def test_an_explicit_or_held_material_is_never_overwritten(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashwick", world, world.regions[0])
    gate = await made(session, world, "Old Ring", EntityType.VESSEL, VesselStats(speed=10, range=90, crew=0, armor=60), at=town.id)
    await set_vessel_kind(session, gate.id, VehicleKind.GATE)
    await set_node_material(session, gate.id, MaterialSlot.HULL, M.OBSIDIAN)
    assert await ensure_materials(session, gate) == 0
    hull = await slot(session, gate.id, MaterialSlot.HULL)
    assert hull is not None and hull.material is M.OBSIDIAN
    hull.held = True
    await set_node_material(session, gate.id, MaterialSlot.HULL, M.WOOD)
    assert hull.material is M.OBSIDIAN
    await set_node_material(session, gate.id, MaterialSlot.HULL, M.WOOD, force=True)
    assert hull.material is M.WOOD


async def test_items_wear_by_their_typed_material(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    assert rust_wear(rules, props(M.IRON)) > 0
    assert rust_wear(rules, props(M.GOLD)) == 0
    assert rust_wear(rules, props(M.WOOD)) > rust_wear(rules, props(M.IRON))
    assert battle_wear(rules, props(M.STEEL)) < battle_wear(rules, props(M.GLASS))
    assert worth_factor(rules, props(M.GOLD)) > 1 > worth_factor(rules, props(M.WOOD))


async def test_rarity_raises_the_price_of_goods_made_of_it(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    assert price_premium(rules, props(M.GEMS)) > price_premium(rules, props(M.SILVER)) > 1 > price_premium(rules, props(M.CLAY))
    rich = await settlement(session, "Golden Quay", world, world.regions[0])
    poor = await settlement(session, "Clay Quay", world, world.regions[1])
    ctx = await manual_context(session, "prices", rules)
    ledger = goods_of(session, ctx.epoch)
    await ledger.add(rich.id, CommodityKind.LUXURIES, 30, GoodsFlow.PLAYER, material=M.GOLD)
    await ledger.add(poor.id, CommodityKind.LUXURIES, 30, GoodsFlow.PLAYER, material=M.GLASS)
    book = await EconomyBook.load(ctx)
    gold = (await quote_market(ctx, book, rich))[CommodityKind.LUXURIES].price
    glass = (await quote_market(ctx, book, poor))[CommodityKind.LUXURIES].price
    assert gold > glass
    await control_depth.hold_price(ctx, rich.id, CommodityKind.LUXURIES, 7, None)
    assert (await quote_market(ctx, book, rich))[CommodityKind.LUXURIES].price == 7


async def test_holy_materials_harm_the_undead_cursed_and_void(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    silver, void = props(M.SILVER), props(M.VOID_GLASS)
    assert holy_edge(rules, silver, frozenset({FoeNature.UNDEAD})) > holy_edge(rules, silver, frozenset({FoeNature.CURSED})) > 1
    assert holy_edge(rules, silver, frozenset()) == 1
    assert holy_edge(rules, void, frozenset({FoeNature.VOID})) < holy_edge(rules, silver, frozenset({FoeNature.VOID}))
    town = await settlement(session, "Lantern", world, world.regions[0])
    ghost = await entity(session, "Pale Wanderer", EntityType.SPECIES, SpeciesStats(danger=60, strength=40), world_id=world.world.id)
    session.add(BodyRow(node_id=ghost.id, plan=BodyPlan.INCORPOREAL, fingers=0))
    await session.flush()
    assert FoeNature.UNDEAD in await natures_of(session, ghost)
    hero = await mortal(session, "Ser Aldo", world, town.id)
    blade = await made(session, world, "Moonedge", EntityType.ITEM, ItemStats(damage=40, protection=0, might=5, curse=0), at=town.id)
    await set_node_material(session, blade.id, MaterialSlot.BODY, M.SILVER, force=True)
    await bond(session, hero.id, blade.id, BondKind.OWNS)
    assert await holy_strike(session, rules, hero.id, ghost) > 1
    assert await holy_strike(session, rules, hero.id, town) == 1


async def test_vessel_hulls_and_sails_change_the_journey(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    assert hull_guard(rules, props(M.STEEL)) < hull_guard(rules, props(M.WOOD)) < 1
    assert wind_guard(rules, props(M.LEATHER)) < wind_guard(rules, props(M.CLOTH))
    assert light_fabric(rules, props(M.CLOTH)) and not light_fabric(rules, props(M.STONE))
    town = await settlement(session, "Harbour", world, world.regions[0])
    ship = await made(session, world, "Saltwing", EntityType.VESSEL, VesselStats(speed=40, range=40, crew=20, armor=30), at=town.id)
    rig = await rig_of(session, ship)
    assert rig is not None and rig.hull is not None and rig.fabric is not None


async def test_wild_herds_fish_and_silk_open_grounds(session: AsyncSession, world: CoreWorld) -> None:
    beast = await entity(session, "Plains Aurochs", EntityType.SPECIES, SpeciesStats(abundance=60), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(BodyRow(node_id=beast.id, plan=BodyPlan.QUADRUPED, fingers=0))
    await session.flush()
    await species_products(await manual_context(session, "yields", Rules()))
    grounds = list(await session.scalars(select(EntityRow).where(EntityRow.maker_entity_id == beast.id, EntityRow.entity_type == EntityType.RESOURCE)))
    profiles = list(await session.scalars(select(ResourceProfileRow).where(ResourceProfileRow.resource_entity_id.in_([ground.id for ground in grounds]))))
    kinds = {profile.commodity for profile in profiles}
    assert {CommodityKind.LIVESTOCK, CommodityKind.MOUNTS} <= kinds


async def test_extraction_is_gated_by_the_required_knowledge(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Delve", world, world.regions[0])
    ctx = await manual_context(session, "gate", Rules())
    book = await EconomyBook.load(ctx)
    profile = ResourceProfileRow(
        resource_entity_id=town.id,
        commodity=CommodityKind.ORE,
        material=M.IRON,
        reserve=100,
        initial_reserve=100,
        richness=50,
        extraction_difficulty=10,
        required_branch=KnowledgeBranch.METALLURGY,
        required_level=3,
        quality=50,
    )
    assert knowledge_gate(ctx.rules, book, profile, town.id) == 0
    assert knowledge_gate(tuned_rules(extraction={"knowledge_short_pct": 50}), book, profile, town.id) > 0
    profile.required_level = 0
    assert knowledge_gate(ctx.rules, book, profile, town.id) == 1


async def debt(session: AsyncSession, debtor: EntityRow, creditor: EntityRow) -> BondRow:
    bond_row = await BondRepository(session).connect(
        BondDraft(debtor.id, creditor.id, BondKind.OWES, 0, "old loan", debt_amount=8, debt_what="silver", debt_due_epoch=0)
    )
    bond_row.debt_status = DebtStatus.OPEN
    return bond_row


async def test_debts_are_counted_in_the_creditors_coin(session: AsyncSession, world: CoreWorld) -> None:
    lender = await settlement(session, "Coinholm", world, world.regions[0])
    debtor = await settlement(session, "Penny", world, world.regions[1])
    ctx = await manual_context(session, "coin", Rules())
    coin = await control_depth.create_currency(ctx, control_depth.NewCoin(lender.id, "Coinholm Mark", M.SILVER, 90, 70, 100))
    await save_society(session, lender.id, default_society(ctx.rules))
    await save_society(session, debtor.id, default_society(ctx.rules))
    row = await session.get(CommunitySocietyRow, lender.id)
    assert row is not None
    row.currency_id = coin.id
    owed = await debt(session, debtor, lender)
    assert owed.debt_currency_id == coin.id


async def test_every_debt_law_settles_debts_its_own_way(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(market={"debt_forgive_relation": 100})
    ctx = await manual_context(session, "law", rules)
    outcomes: dict[DebtRemedy, BondRow] = {}
    for index, remedy in enumerate(DebtRemedy):
        creditor = await settlement(session, f"Lender{index}", world, world.regions[0])
        debtor = await settlement(session, f"Debtor{index}", world, world.regions[1])
        for social_class in (SocialClass.FARMER, SocialClass.ARTISAN):
            session.add(
                CohortRow(
                    community_entity_id=debtor.id,
                    age_band=AgeBand.ADULT,
                    sex=Sex.MALE,
                    social_class=social_class,
                    condition=CohortCondition.NONE,
                    count=600,
                    generation_epoch=1,
                )
            )
        await enact(ctx, debtor, LawKind.DEBT_LAW, {"remedy": remedy.value, "jubilee_epochs": 1})
        outcomes[remedy] = await debt(session, debtor, creditor)
    await session.flush()
    await market(ctx)
    jubilee, bondage = outcomes[DebtRemedy.JUBILEE], outcomes[DebtRemedy.BONDAGE]
    assert jubilee.state is BondState.PAST and jubilee.debt_status is DebtStatus.FORGIVEN
    assert bondage.state is BondState.PAST and bondage.debt_status is DebtStatus.REPAID
    bound = await session.scalar(select(CohortRow).where(CohortRow.social_class == SocialClass.SERF_OR_SLAVE))
    assert bound is not None and bound.count > 0


async def test_the_debtors_prison_takes_a_notable_captive(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(market={"debt_forgive_relation": 100})
    ctx = await manual_context(session, "prison", rules)
    creditor = await settlement(session, "Gaolhold", world, world.regions[0])
    debtor = await settlement(session, "Owington", world, world.regions[1])
    notable = await mortal(session, "Merchant Ilse", world, debtor.id)
    await enact(ctx, debtor, LawKind.DEBT_LAW, {"remedy": DebtRemedy.PRISON.value})
    owed = await debt(session, debtor, creditor)
    await market(ctx)
    assert owed.state is BondState.PAST
    held = await session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == notable.id))
    assert held is not None and held.status is CaptiveStatus.HELD and held.captor_entity_id == creditor.id


async def test_banks_lend_to_realms_and_realms_default_into_debt(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(banking={"polity_lend_chance": 100, "term_years": 50, "polity_repay_pct": 0})
    ctx = await manual_context(session, "realm", rules)
    capital = await settlement(session, "Crownmere", world, world.regions[0])
    guild = await entity(session, "Ledger Guild", EntityType.FACTION, FactionStats(wealth=90, sway=50), world_id=world.world.id, location_id=capital.id)
    guild.engine_kind = EngineKind.MERCHANT_GUILD
    realm = await found_polity(ctx, await RealmBook.load(session), capital)
    realm.profile.debt = 30
    await session.flush()
    book = await EconomyBook.load(ctx)
    tally = MoneyTally()
    await lend_to_realms(ctx, book, tally)
    loan = await session.scalar(select(LoanRow).where(LoanRow.borrower_entity_id == realm.entity.id))
    assert loan is not None and tally.lent == 1
    await session.refresh(realm.profile)
    assert realm.profile.treasury == rules.banking.polity_principal
    realm.profile.treasury = 0
    world.cosmos.epoch = loan.due_epoch
    later = await manual_context(session, "later", rules)
    await collect_from_realms(later, await EconomyBook.load(later), tally)
    assert loan.status is LoanStatus.DEFAULTED
    await session.refresh(realm.profile)
    assert realm.profile.debt > 30


async def test_a_sacked_temple_floods_the_victors_market(session: AsyncSession, world: CoreWorld) -> None:
    victor = await settlement(session, "Raidholm", world, world.regions[0])
    fallen = await settlement(session, "Shrineford", world, world.regions[1])
    ctx = await manual_context(session, "sack", Rules())
    temple = await made(session, world, "Golden Fane", EntityType.STRUCTURE, StructureStats(splendor=60, durability=60, function=30), at=fallen.id)
    temple.engine_kind = EngineKind.TEMPLE
    await set_node_material(session, temple.id, MaterialSlot.BODY, M.GOLD, force=True)
    added = await loot_temples(ctx, fallen, victor)
    assert added > ctx.rules.money.temple_hoard_units
    assert await holding(session, victor.id, CommodityKind.LUXURIES, M.GOLD) == added


async def test_world_materials_are_forged_held_and_unmade(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Forge", world, world.regions[0])
    ctx = await manual_context(session, "forge", Rules())
    row = await control_depth.create_material(
        ctx, Substance(world.world.id, "Dawnsteel", MaterialFamily.EXOTIC, {"sanctity": 95, "hardness": 80}, base_kind=M.STEEL, place_id=world.regions[0].id)
    )
    book = await MaterialBook.load(session)
    found = book.props(world.world.id, world_material_id=row.id)
    assert found is not None and found.sanctity == 95 and found.toughness == MATERIALS[M.STEEL].toughness
    assert row.deposit_entity_id is not None
    blade = await made(session, world, "Dawn", EntityType.ITEM, ItemStats(damage=50, protection=0, might=5, curse=0), at=town.id)
    await control_depth.set_slot(ctx, blade.id, MaterialSlot.BODY, None, row.id, hold=True)
    await control_depth.set_stock(ctx, town.id, CommodityKind.ORE, material=None, world_material_id=row.id, quantity=12, quality=80, hold=True)
    lot = await session.scalar(select(CommunityStockRow).where(CommunityStockRow.world_material_id == row.id))
    assert lot is not None and lot.held
    assert await goods_of(session, ctx.epoch).add(town.id, CommodityKind.ORE, 5, GoodsFlow.EXTRACTION, world_material_id=row.id) == 0
    await control_depth.hold_material(ctx, world.world.id, None, row.id, True)
    assert row.held
    await control_depth.delete_material(ctx, world.world.id, None, row.id)
    rebuilt = await slot(session, blade.id)
    assert rebuilt is not None and rebuilt.world_material_id is None


async def test_the_depth_backfill_runs_once(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Oldtown", world, world.regions[0])
    item = await entity(
        session, "Forgotten Spear", EntityType.ITEM, ItemStats(damage=30, protection=0, might=0, curse=0), world_id=world.world.id, location_id=town.id
    )
    ctx = await manual_context(session, "backfill", Rules())
    result = await depth_backfill(ctx)
    assert result["materials"] >= 1 and await slot(session, item.id) is not None
    assert await session.get(AppliedFixupRow, DEPTH_FIXUP) is not None
    assert await depth_backfill(ctx) == {}
    assert await sweep_materials(session, ctx.rules) == 0


async def test_workshop_designs_scale_capacity_output_and_storage(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "design", Rules())
    design = await create_design(ctx, NewDesign(world.world.id, WorkshopKind.GRANARY, "Deep Silo", {"store_pct": 300, "capacity_pct": 50, "output_pct": 200}))
    workshop = WorkshopRow(community_entity_id=world.people.id, kind=WorkshopKind.GRANARY, level=2, built_epoch=1)
    assert workshop_store_units(workshop, design, 10) == 60
    assert workshop_store_units(workshop, None, 10) == 20
    assert capacity_scale(design) == 0.5 and output_scale(design) == 2.0
    assert workshop_store_units(None, design, 10) == 0


async def test_world_specific_substances_come_from_events_as_pending_named_deposits(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "substance", Rules())
    place = world.regions[0]
    origins = [MaterialOrigin.DEAD_GOD, MaterialOrigin.STAR, MaterialOrigin.BEAST, MaterialOrigin.RIFT, MaterialOrigin.RESEARCH]
    for origin in origins:
        source = (await settlement(session, f"Source {origin.value}", world, place)).id
        row = await new_substance(ctx, origin, place, source_node_id=source)
        assert row.origin is origin and row.family is MaterialFamily.EXOTIC and row.world_id == place.world_id
        base = MATERIALS[ORIGIN_BASE[origin]]
        assert all(0 <= getattr(row, column) <= 100 for column in ("hardness", "toughness", "sanctity", "rarity"))
        assert row.description
        assert await has_substance(ctx, source)
        deposit = await session.get(EntityRow, row.deposit_entity_id)
        assert deposit is not None and deposit.entity_type is EntityType.RESOURCE and deposit.pending_name
        profile = await session.get(ResourceProfileRow, deposit.id)
        assert profile is not None and profile.world_material_id == row.id and profile.commodity is CommodityKind.ORE
        assert base.branch == row.branch
    stored = list(await session.scalars(select(WorldMaterialRow).where(WorldMaterialRow.world_id == place.world_id)))
    assert {item.origin for item in stored} >= set(origins)


async def test_resource_words_are_read_once_and_never_after(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "profiles", Rules())
    old = await made(session, world, "Wheat Field", EntityType.RESOURCE, ResourceStats(abundance=50, value=30, might=10), at=world.regions[0].id)
    await profile_resources(ctx, await EconomyBook.load(ctx))
    first = await session.get(ResourceProfileRow, old.id)
    assert first is not None and first.commodity is CommodityKind.GRAIN
    assert await session.get(AppliedFixupRow, PROFILE_FIXUP) is not None
    late = await made(session, world, "Golden Wheat", EntityType.RESOURCE, ResourceStats(abundance=50, value=30, might=10), at=world.regions[0].id)
    await profile_resources(ctx, await EconomyBook.load(ctx))
    second = await session.get(ResourceProfileRow, late.id)
    assert second is not None and second.commodity is CommodityKind.ORE


def test_material_physics_gate_forging_cap_edges_and_draw_bows() -> None:
    rules = Rules()
    novice = {KnowledgeBranch.METALLURGY: 1}
    master = {KnowledgeBranch.METALLURGY: 3}
    assert forge_heat(rules, master) > forge_heat(rules, novice)
    assert forgeable(rules, props(M.COPPER), novice)
    assert not forgeable(rules, props(M.IRON), novice)
    assert forgeable(rules, props(M.IRON), master)
    assert forgeable(rules, props(M.WOOD), {})
    assert forgeable(rules, props(M.CRYSTAL), {}) and forgeable(rules, props(M.GEMS), {})
    assert unmet_need(rules, props(M.CRYSTAL), {}) is None
    assert unmet_need(rules, props(M.IRON), novice) == (KnowledgeBranch.METALLURGY, forge_level(rules, props(M.IRON)))
    assert forgeable(rules, props(M.IRON), {KnowledgeBranch.METALLURGY: forge_level(rules, props(M.IRON))})
    blunt = replace(props(M.STEEL), max_edge=10)
    assert sharpness(blunt) == 10 < sharpness(props(M.STEEL))
    assert weapon_damage(rules, blunt, 50) < weapon_damage(rules, props(M.STEEL), 50)
    assert draw_strength(props(M.WOOD)) > draw_strength(props(M.STONE)) == 0
    for kind in M:
        spec = MATERIALS[kind]
        assert spec.boiling_point >= spec.melting_point or spec.melting_point == 100
