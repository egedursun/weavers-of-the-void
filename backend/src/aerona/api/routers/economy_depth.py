from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.economy import names_of, rules_of
from aerona.api.schemas.economy import DebtLawView, MarketHoldsView, NodeMaterialsView, PremiumView, SlotView, WorkshopDesignView
from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.laws import LAW_PARAMS
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.economy import CommunityStockRow, MarketPriceHoldRow, NodeMaterialRow, WorkshopDesignRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import LawJurisdictionRow, LawProfileRow
from aerona.domain.enums.economy import FoeNature, MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import DebtRemedy, LawKind
from aerona.engine.economy.materials import (
    MaterialBook,
    MaterialProps,
    armour_protection,
    battle_wear,
    holy_edge,
    hull_guard,
    hull_wear,
    price_premium,
    rust_wear,
    weapon_damage,
    wind_guard,
    worth_factor,
)
from aerona.engine.economy.provenance import wanted_slots
from aerona.engine.economy.sanctity import natures_of
from aerona.rules.registry import Rules

router = APIRouter(tags=["economy"])
QUALITY = 50
FULL_FOES = frozenset(FoeNature)


def effects_of(rules: Rules, entity: EntityRow, slot: MaterialSlot, props: MaterialProps) -> dict[str, int]:
    if slot is MaterialSlot.HULL:
        return {"risk_kept_pct": round(hull_guard(rules, props) * PERCENT), "armour_wear": hull_wear(rules, props, rules.travel.vessel_armor_loss)}
    if slot is MaterialSlot.FABRIC:
        light = props.weight <= rules.materials.fabric_light_weight
        return {"wind_kept_pct": round(wind_guard(rules, props) * PERCENT), "stage_saved": 1 if light else 0}
    found = {
        "worth_pct": round(worth_factor(rules, props) * PERCENT),
        "battle_wear": battle_wear(rules, props),
        "wet_wear": rust_wear(rules, props),
        "price_pct": round(price_premium(rules, props) * PERCENT),
    }
    if entity.entity_type in (EntityType.ITEM, EntityType.ARMY):
        found["damage"] = weapon_damage(rules, props, QUALITY)
        found["protection"] = armour_protection(rules, props, QUALITY)
        found["holy_edge_pct"] = round(holy_edge(rules, props, FULL_FOES) * PERCENT)
    return found


@router.get("/nodes/{node_id}/materials", response_model=NodeMaterialsView)
async def node_materials(services: ServicesDep, node_id: int = Path(ge=1)) -> NodeMaterialsView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, node_id)
        if entity is None:
            raise NotFoundError("No such record.")
        rules, _ = await rules_of(session)
        book = await MaterialBook.load(session)
        rows = list(await session.scalars(select(NodeMaterialRow).where(NodeMaterialRow.node_id == node_id).order_by(NodeMaterialRow.slot)))
        slots: list[SlotView] = []
        for row in rows:
            props = book.props(entity.world_id, row.material, row.world_material_id)
            if props is None:
                continue
            slots.append(
                SlotView(
                    slot=row.slot,
                    material=row.material,
                    world_material_id=row.world_material_id,
                    label=props.label,
                    family=props.family,
                    held=row.held,
                    hardness=props.hardness,
                    toughness=props.toughness,
                    weight=props.weight,
                    sanctity=props.sanctity,
                    corruption=props.corruption,
                    rarity=props.rarity,
                    base_value=props.base_value,
                    decay=props.decay,
                    effects=effects_of(rules, entity, row.slot, props),
                )
            )
        wanted = list(await wanted_slots(session, entity))
        if entity.entity_type is EntityType.ARMY:
            wanted = [MaterialSlot.WEAPONS, MaterialSlot.ARMOUR]
        taken = {row.slot for row in rows}
        return NodeMaterialsView(
            node_id=node_id,
            entity_type=entity.entity_type,
            world_id=entity.world_id,
            slots=slots,
            open_slots=[slot for slot in wanted if slot not in taken],
            foe_natures=sorted(await natures_of(session, entity)),
        )


@router.get("/markets/{market_id}/holds", response_model=MarketHoldsView)
async def market_holds(services: ServicesDep, market_id: int = Path(ge=1)) -> MarketHoldsView:
    async with reader(services) as session:
        market = await session.get(EntityRow, market_id)
        if market is None:
            raise NotFoundError("No such market.")
        rules, _ = await rules_of(session)
        book = await MaterialBook.load(session)
        holds = {row.commodity: row for row in await session.scalars(select(MarketPriceHoldRow).where(MarketPriceHoldRow.market_entity_id == market_id))}
        lots = list(await session.scalars(select(CommunityStockRow).where(CommunityStockRow.community_entity_id == market_id, CommunityStockRow.quantity > 0)))
        premiums: list[PremiumView] = []
        for commodity in COMMODITIES:
            mine = [row for row in lots if row.commodity is commodity]
            weight = sum(row.quantity for row in mine)
            premium = (
                sum(price_premium(rules, book.props(market.world_id, row.material, row.world_material_id)) * row.quantity for row in mine) / weight
                if weight
                else 1.0
            )
            hold = holds.get(commodity)
            premiums.append(
                PremiumView(
                    commodity=commodity,
                    premium_pct=round(premium * PERCENT),
                    held_price=hold.price if hold is not None else None,
                    held_supply=hold.supply if hold is not None else None,
                )
            )
        return MarketHoldsView(market_id=market_id, premiums=premiums)


@router.get("/ledger/debt-laws", response_model=list[DebtLawView])
async def debt_laws(services: ServicesDep) -> list[DebtLawView]:
    async with reader(services) as session:
        statement = (
            select(LawProfileRow, EntityRow)
            .join(EntityRow, EntityRow.id == LawProfileRow.law_entity_id)
            .where(LawProfileRow.kind == LawKind.DEBT_LAW, EntityRow.status == EntityStatus.CANON)
            .order_by(LawProfileRow.law_entity_id)
        )
        found = list(await session.execute(statement))
        holders: dict[int, list[int]] = {}
        for law, _ in found:
            holders[law.law_entity_id] = list(
                await session.scalars(select(LawJurisdictionRow.node_entity_id).where(LawJurisdictionRow.law_entity_id == law.law_entity_id))
            )
        names = await names_of(session, {node for nodes in holders.values() for node in nodes})
        defaults = LAW_PARAMS[LawKind.DEBT_LAW]
        views: list[DebtLawView] = []
        for law, entity in found:
            remedy = str(law.params.get("remedy", defaults["remedy"].default))
            epochs = law.params.get("jubilee_epochs", defaults["jubilee_epochs"].default)
            views.append(
                DebtLawView(
                    law_id=law.law_entity_id,
                    name=entity.name,
                    holders=holders[law.law_entity_id],
                    holder_names=[names.get(node, "") for node in holders[law.law_entity_id]],
                    remedy=DebtRemedy(remedy) if remedy in {item.value for item in DebtRemedy} else DebtRemedy.PRISON,
                    jubilee_epochs=int(epochs) if isinstance(epochs, int) and not isinstance(epochs, bool) else 1,
                    enforcement=law.enforcement,
                )
            )
        return views


@router.get("/worlds/{world_id}/workshop-designs", response_model=list[WorkshopDesignView])
async def workshop_designs(services: ServicesDep, world_id: int = Path(ge=1)) -> list[WorkshopDesignView]:
    async with reader(services) as session:
        rows = list(await session.scalars(select(WorkshopDesignRow).where(WorkshopDesignRow.world_id == world_id).order_by(WorkshopDesignRow.id)))
        used: dict[int, int] = {}
        for design_id in await session.scalars(select(WorkshopRow.design_id).where(WorkshopRow.design_id.is_not(None))):
            if design_id is not None:
                used[design_id] = used.get(design_id, 0) + 1
        return [
            WorkshopDesignView(
                id=row.id,
                world_id=row.world_id,
                base_kind=row.base_kind,
                label=WORKSHOP_LABELS[row.base_kind],
                name=row.name,
                description=row.description,
                output_pct=row.output_pct,
                capacity_pct=row.capacity_pct,
                store_pct=row.store_pct,
                quality_bonus=row.quality_bonus,
                held=row.held,
                workshops=used.get(row.id, 0),
            )
            for row in rows
        ]
