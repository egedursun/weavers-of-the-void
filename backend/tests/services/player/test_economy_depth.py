import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.economy import (
    CommunityStockRow,
    CurrencyRow,
    LoanRow,
    MarketPriceHoldRow,
    NodeMaterialRow,
    ResourceProfileRow,
    ResourceWorkerRow,
    WorkshopDesignRow,
    WorkshopRow,
    WorldMaterialRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import CommodityKind, LoanStatus, MaterialFamily, MaterialSlot, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import FactionStats, ItemStats
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import economy, economy_depth
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity

DEPTH_ACTIONS = (
    "material:create",
    "material:delete",
    "material:hold",
    "material:release",
    "node_material:set",
    "node_material:release",
    "node_material:clear",
    "stock:set",
    "stock:release",
    "workshop:edit",
    "workshop:release",
    "resource:create",
    "resource:edit",
    "resource:release",
    "resource:delete",
    "resource:workers",
    "market:hold_price",
    "market:release_price",
    "currency:create",
    "currency:release",
    "currency:delete",
    "loan:grant",
    "loan:edit",
    "loan:release",
    "loan:delete",
    "workshop_design:create",
    "workshop_design:edit",
    "workshop_design:release",
    "workshop_design:delete",
)


async def town(session: AsyncSession, world: PlayerWorld, name: str = "Brennhold") -> EntityRow:
    return await make_entity(session, name, EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)


def test_every_depth_action_is_in_the_catalog() -> None:
    assert [action for action in DEPTH_ACTIONS if action not in ACTIONS_BY_ID] == []


async def test_a_material_is_forged_edited_held_released_and_unmade(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    created = await economy_depth.create_material(
        scope,
        economy_depth.CreateMaterial(
            world_id=world.world.id,
            name="Hallowed Iron",
            family=MaterialFamily.METAL,
            base_kind=MaterialKind.IRON,
            values={"sanctity": 90, "rarity": 70},
            branch=KnowledgeBranch.METALLURGY,
            level=3,
            place_id=world.region.id,
        ),
    )
    row = await session.get(WorldMaterialRow, created.values["world_material_id"])
    assert row is not None and row.sanctity == 90 and row.deposit_entity_id is not None and created.created_ids == [row.deposit_entity_id]
    await economy.edit_material(
        scope,
        economy.EditMaterial(
            world_id=world.world.id, world_material_id=row.id, values={"decay": 3}, family=MaterialFamily.PRECIOUS, description="It hums.", hold=True
        ),
    )
    assert row.decay == 3 and row.family is MaterialFamily.PRECIOUS and row.description == "It hums." and row.held
    await economy_depth.release_material(scope, economy_depth.MaterialTarget(world_id=world.world.id, world_material_id=row.id))
    assert not row.held
    await economy.edit_material(scope, economy.EditMaterial(world_id=world.world.id, material=MaterialKind.GOLD, values={"rarity": 99}, clear_branch=True))
    await economy_depth.hold_material(scope, economy_depth.MaterialTarget(world_id=world.world.id, material=MaterialKind.GOLD))
    reverted = await economy_depth.delete_material(scope, economy_depth.MaterialTarget(world_id=world.world.id, material=MaterialKind.GOLD))
    assert "catalog" in reverted.message
    await economy_depth.delete_material(scope, economy_depth.MaterialTarget(world_id=world.world.id, world_material_id=row.id))
    assert await session.get(WorldMaterialRow, row.id) is None


async def test_creating_a_material_is_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    created = await economy_depth.create_material(
        scope, economy_depth.CreateMaterial(world_id=world.world.id, name="Ashglass", family=MaterialFamily.EXOTIC, values={"edge": 90})
    )
    assert created.ledger_entry_id is not None
    changes = await changes_of(session, created.ledger_entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == []
    assert await session.scalar(select(WorldMaterialRow.id).where(WorldMaterialRow.name == "Ashglass")) is None


async def test_a_slot_material_is_set_held_released_and_cleared(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    sword = await make_entity(
        session, "Kinslayer", EntityType.ITEM, world_id=world.world.id, location_id=home.id, stats=ItemStats(damage=40, protection=0, might=0, curse=0)
    )
    await economy_depth.set_slot(scope, economy_depth.SlotMaterial(node_id=sword.id, material=MaterialKind.SILVER))
    row = await session.get(NodeMaterialRow, (sword.id, MaterialSlot.BODY))
    assert row is not None and row.material is MaterialKind.SILVER and row.held
    await economy_depth.release_slot(scope, economy_depth.SlotTarget(node_id=sword.id))
    assert not row.held
    await economy_depth.clear_slot(scope, economy_depth.SlotTarget(node_id=sword.id))
    assert await session.get(NodeMaterialRow, (sword.id, MaterialSlot.BODY)) is None
    with pytest.raises(ValidationFailedError):
        await economy_depth.set_slot(scope, economy_depth.SlotMaterial(node_id=sword.id))


async def test_stores_workshops_and_hoards_take_world_materials_and_holds(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    created = await economy_depth.create_material(
        scope, economy_depth.CreateMaterial(world_id=world.world.id, name="Moonsilver", family=MaterialFamily.PRECIOUS, base_kind=MaterialKind.SILVER)
    )
    substance = int(created.values["world_material_id"] or 0)
    await economy.grant_stock(scope, economy.GrantStock(community_id=home.id, commodity=CommodityKind.ORE, quantity=20, world_material_id=substance))
    outcome = await economy_depth.set_stock(
        scope, economy_depth.SetStock(community_id=home.id, commodity=CommodityKind.ORE, world_material_id=substance, quantity=33, quality=90, hold=True)
    )
    lot = await session.get(CommunityStockRow, outcome.values["lot_id"])
    assert lot is not None and lot.quantity == 33 and lot.held and lot.world_material_id == substance
    await economy_depth.release_stock(scope, economy_depth.StockTarget(lot_id=lot.id))
    assert not lot.held
    hoard = await economy.inject_hoard(scope, economy.InjectHoard(community_id=home.id, world_material_id=substance, units=12))
    assert hoard.values["added"] == 12
    await economy.set_workshop(scope, economy.SetWorkshop(community_id=home.id, kind=WorkshopKind.SHIPYARD, level=2))
    await economy_depth.edit_workshop(scope, economy_depth.EditWorkshop(community_id=home.id, kind=WorkshopKind.SHIPYARD, fleet=4, idle_epochs=1, hold=True))
    yard = await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == home.id, WorkshopRow.kind == WorkshopKind.SHIPYARD))
    assert yard is not None and yard.fleet == 4 and yard.held
    await economy_depth.release_workshop(scope, economy_depth.WorkshopTarget(community_id=home.id, kind=WorkshopKind.SHIPYARD))
    assert not yard.held


async def test_a_deposit_is_set_edited_held_worked_and_unmade(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    made = await economy_depth.create_resource(
        scope,
        economy_depth.CreateResource(
            place_id=world.region.id,
            name="Deepiron Vein",
            commodity=CommodityKind.ORE,
            material=MaterialKind.IRON,
            required_branch=KnowledgeBranch.METALLURGY,
            required_level=3,
        ),
    )
    resource_id = made.created_ids[0]
    profile = await session.get(ResourceProfileRow, resource_id)
    assert profile is not None and profile.required_level == 3
    await economy_depth.edit_resource(
        scope,
        economy_depth.EditResourceDepth(
            resource_id=resource_id, required_level=1, byproduct_material=MaterialKind.SULFUR, byproduct_pct=7, sealed_until_epoch=9, hold=True
        ),
    )
    assert profile.required_level == 1 and profile.byproduct_material is MaterialKind.SULFUR and profile.sealed_until_epoch == 9 and profile.held
    await economy_depth.edit_resource(scope, economy_depth.EditResourceDepth(resource_id=resource_id, unseal=True, clear_branch=True))
    assert profile.sealed_until_epoch is None and profile.required_branch is None
    await economy_depth.release_resource(scope, economy_depth.ResourceTarget(resource_id=resource_id))
    assert not profile.held
    await economy_depth.set_workers(scope, economy_depth.SetWorkers(resource_id=resource_id, community_id=home.id, workers=55))
    workers = await session.get(ResourceWorkerRow, (resource_id, home.id))
    assert workers is not None and workers.workers == 55 and workers.held
    await economy_depth.delete_resource(scope, economy_depth.ResourceTarget(resource_id=resource_id))
    deposit = await session.get(EntityRow, resource_id)
    assert deposit is not None and deposit.status is EntityStatus.DESTROYED


async def test_market_prices_are_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    await economy_depth.hold_price(scope, economy_depth.HoldPrice(market_id=home.id, commodity=CommodityKind.GRAIN, price=3, supply=500))
    hold = await session.get(MarketPriceHoldRow, (home.id, CommodityKind.GRAIN))
    assert hold is not None and hold.price == 3 and hold.supply == 500
    await economy_depth.release_price(scope, economy_depth.PriceTarget(market_id=home.id, commodity=CommodityKind.GRAIN))
    assert await session.get(MarketPriceHoldRow, (home.id, CommodityKind.GRAIN)) is None


async def test_a_coin_is_struck_renamed_held_and_melted(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    struck = await economy_depth.create_currency(
        scope, economy_depth.CreateCurrency(issuer_id=home.id, name="Brenn Crown", metal=MaterialKind.GOLD, purity=95, trust=80, supply=500)
    )
    coin = await session.get(CurrencyRow, struck.values["currency_id"])
    assert coin is not None and coin.metal is MaterialKind.GOLD and coin.item_entity_id is not None
    body = await session.get(NodeMaterialRow, (coin.item_entity_id, MaterialSlot.BODY))
    assert body is not None and body.material is MaterialKind.GOLD
    await economy.edit_currency(scope, economy.EditCurrency(currency_id=coin.id, name="Brenn Mark", metal=MaterialKind.SILVER, hold=True))
    assert coin.name == "Brenn Mark" and coin.metal is MaterialKind.SILVER and coin.held
    await economy_depth.release_currency(scope, economy_depth.CurrencyTarget(currency_id=coin.id))
    assert not coin.held
    await economy_depth.delete_currency(scope, economy_depth.CurrencyTarget(currency_id=coin.id))
    assert await session.get(CurrencyRow, coin.id) is None


async def test_a_loan_is_made_edited_held_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    guild = await make_entity(session, "Ledger Guild", EntityType.FACTION, world_id=world.world.id, location_id=home.id, stats=FactionStats(wealth=80))
    made = await economy_depth.grant_loan(scope, economy_depth.GrantLoan(lender_id=guild.id, borrower_id=home.id, principal=40, interest_pct=15, term_epochs=4))
    loan = await session.get(LoanRow, made.values["loan_id"])
    assert loan is not None and loan.principal == 40 and loan.status is LoanStatus.OPEN
    await economy_depth.edit_loan(scope, economy_depth.EditLoan(loan_id=loan.id, principal=60, interest_pct=5, due_epoch=20, repaid=10, hold=True))
    assert (loan.principal, loan.interest_pct, loan.due_epoch, loan.repaid, loan.held) == (60, 5, 20, 10, True)
    await economy_depth.release_loan(scope, economy_depth.LoanTarget(loan_id=loan.id))
    assert not loan.held
    with pytest.raises(ValidationFailedError):
        await economy_depth.grant_loan(scope, economy_depth.GrantLoan(lender_id=home.id, borrower_id=home.id, principal=5))
    await economy_depth.delete_loan(scope, economy_depth.LoanTarget(loan_id=loan.id))
    assert await session.get(LoanRow, loan.id) is None


async def test_a_workshop_design_is_drawn_assigned_held_and_torn_up(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    home = await town(session, world)
    drawn = await economy_depth.create_design(
        scope,
        economy_depth.CreateWorkshopDesign(
            world_id=world.world.id, base_kind=WorkshopKind.FORGE, name="Bellows Forge", values={"capacity_pct": 200, "quality_bonus": 15}
        ),
    )
    design = await session.get(WorkshopDesignRow, drawn.values["design_id"])
    assert design is not None and design.capacity_pct == 200 and design.output_pct == 100
    await economy.set_workshop(scope, economy.SetWorkshop(community_id=home.id, kind=WorkshopKind.FORGE, level=2))
    await economy_depth.edit_workshop(scope, economy_depth.EditWorkshop(community_id=home.id, kind=WorkshopKind.FORGE, design_id=design.id))
    forge = await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == home.id, WorkshopRow.kind == WorkshopKind.FORGE))
    assert forge is not None and forge.design_id == design.id
    with pytest.raises(ValidationFailedError):
        await economy.set_workshop(scope, economy.SetWorkshop(community_id=home.id, kind=WorkshopKind.MILL, level=1))
        await economy_depth.edit_workshop(scope, economy_depth.EditWorkshop(community_id=home.id, kind=WorkshopKind.MILL, design_id=design.id))
    await economy_depth.edit_design(scope, economy_depth.EditWorkshopDesign(design_id=design.id, values={"output_pct": 150}, hold=True))
    assert design.output_pct == 150 and design.held
    await economy_depth.release_design(scope, economy_depth.DesignTarget(design_id=design.id))
    assert not design.held
    await economy_depth.delete_design(scope, economy_depth.DesignTarget(design_id=design.id))
    await session.refresh(forge)
    assert forge.design_id is None
