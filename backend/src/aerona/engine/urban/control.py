from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import (
    CONVOY_FIELDS,
    FLEET_FIELDS,
    ORDER_LAW_FIELDS,
    PAYROLL_FIELDS,
    PLAY_FIELDS,
    RACKET_FIELDS,
    SERVICE_FIELDS,
    STANCE_FIELDS,
    TRADING_POST_FIELDS,
    TURF_FIELDS,
    ConvoyRow,
    CrimeStanceRow,
    DistrictServiceRow,
    FleetRow,
    MarketPlayRow,
    OrderLawRow,
    PayrollRow,
    RacketRow,
    TradingPostRow,
    TribunalRow,
    TurfRow,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import CRIME_KINDS, FactionKind
from aerona.domain.enums.urban import CrimeStance, MarketPlay, OrderLaw, RacketKind, TransportKind, UrbanService
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.economy.convoys import ConvoyTally, dispatch
from aerona.engine.factions.mage_orders import OrderTally, try_member
from aerona.engine.factions.trading_posts import open_post
from aerona.engine.gatherings.control import Values, allowed, entity, found
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.settlement.book import town_of
from aerona.engine.urban.housing import clear_slums

DISTRICT_FIELDS = ("housing", "desirability", "land_value")
TOWN_FIELDS = ("morphology", "homeless")


async def of_type(ctx: TickContext, entity_id: int, kinds: frozenset[EntityType], label: str) -> EntityRow:
    row = await entity(ctx, entity_id, label)
    if row.entity_type not in kinds:
        raise ValidationFailedError(f"{row.name} is not {label}.")
    return row


async def faction_of(ctx: TickContext, faction_id: int, kinds: frozenset[FactionKind] | None, label: str) -> FactionProfileRow:
    profile = await found(ctx, FactionProfileRow, faction_id, label)
    if kinds is not None and profile.kind not in kinds:
        raise ValidationFailedError(f"That faction is not {label}.")
    return profile


async def settlement(ctx: TickContext, settlement_id: int) -> EntityRow:
    return await of_type(ctx, settlement_id, frozenset({EntityType.SETTLEMENT}), "a settlement")


async def edit_district(ctx: TickContext, district_id: int, values: Values, release: list[str]) -> DistrictRow:
    row = apply(await found(ctx, DistrictRow, district_id, "district"), allowed(values, DISTRICT_FIELDS, "district"), release)
    await ctx.session.flush()
    return row


async def edit_town(ctx: TickContext, settlement_id: int, values: Values, release: list[str]) -> SettlementProfileRow:
    await settlement(ctx, settlement_id)
    row = apply(await found(ctx, SettlementProfileRow, settlement_id, "settlement profile"), allowed(values, TOWN_FIELDS, "settlement"), release)
    await ctx.session.flush()
    return row


async def place_structure(ctx: TickContext, structure_id: int, district_id: int | None) -> StructureProfileRow:
    profile = await found(ctx, StructureProfileRow, structure_id, "structure")
    if district_id is not None:
        district = await found(ctx, DistrictRow, district_id, "district")
        building = await entity(ctx, structure_id, "structure")
        if building.location_id != district.settlement_entity_id:
            raise ValidationFailedError("That district lies in another town.")
    apply(profile, {"district_id": district_id}, [])
    await ctx.session.flush()
    return profile


async def clear(ctx: TickContext, settlement_id: int) -> int:
    town = await town_of(ctx, await settlement(ctx, settlement_id), await KnowledgeMap.load(ctx.session))
    return await clear_slums(ctx, town)


async def set_service(ctx: TickContext, district_id: int, service: UrbanService, coverage: int) -> DistrictServiceRow:
    await found(ctx, DistrictRow, district_id, "district")
    row = await ctx.session.get(DistrictServiceRow, (district_id, service))
    if row is None:
        row = DistrictServiceRow(district_id=district_id, service=service, coverage=0, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"coverage": coverage}, [])
    await ctx.session.flush()
    return row


async def edit_service(ctx: TickContext, district_id: int, service: UrbanService, values: Values, release: list[str]) -> DistrictServiceRow:
    row = apply(await found(ctx, DistrictServiceRow, (district_id, service), "service"), allowed(values, SERVICE_FIELDS, "service"), release)
    await ctx.session.flush()
    return row


async def delete_service(ctx: TickContext, district_id: int, service: UrbanService) -> None:
    await ctx.session.delete(await found(ctx, DistrictServiceRow, (district_id, service), "service"))
    await ctx.session.flush()


async def set_turf(ctx: TickContext, district_id: int, faction_id: int, strength: int) -> TurfRow:
    await found(ctx, DistrictRow, district_id, "district")
    await faction_of(ctx, faction_id, CRIME_KINDS, "a criminal organisation")
    row = await ctx.session.get(TurfRow, (district_id, faction_id))
    if row is None:
        row = TurfRow(district_id=district_id, faction_entity_id=faction_id, strength=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def edit_turf(ctx: TickContext, district_id: int, faction_id: int, values: Values, release: list[str]) -> TurfRow:
    row = apply(await found(ctx, TurfRow, (district_id, faction_id), "turf"), allowed(values, TURF_FIELDS, "turf"), release)
    await ctx.session.flush()
    return row


async def delete_turf(ctx: TickContext, district_id: int, faction_id: int) -> None:
    await ctx.session.delete(await found(ctx, TurfRow, (district_id, faction_id), "turf"))
    await ctx.session.flush()


async def set_racket(ctx: TickContext, faction_id: int, settlement_id: int, racket: RacketKind, income: int) -> RacketRow:
    await faction_of(ctx, faction_id, CRIME_KINDS, "a criminal organisation")
    await settlement(ctx, settlement_id)
    row = await ctx.session.get(RacketRow, (faction_id, settlement_id, racket))
    if row is None:
        row = RacketRow(faction_entity_id=faction_id, settlement_entity_id=settlement_id, racket=racket, income=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"income": income}, [])
    await ctx.session.flush()
    return row


async def edit_racket(ctx: TickContext, key: tuple[int, int, RacketKind], values: Values, release: list[str]) -> RacketRow:
    row = apply(await found(ctx, RacketRow, key, "racket"), allowed(values, RACKET_FIELDS, "racket"), release)
    await ctx.session.flush()
    return row


async def delete_racket(ctx: TickContext, key: tuple[int, int, RacketKind]) -> None:
    await ctx.session.delete(await found(ctx, RacketRow, key, "racket"))
    await ctx.session.flush()


async def add_payroll(ctx: TickContext, faction_id: int, official_id: int, bribe: int) -> PayrollRow:
    await faction_of(ctx, faction_id, CRIME_KINDS, "a criminal organisation")
    await of_type(ctx, official_id, frozenset({EntityType.MORTAL}), "a mortal")
    row = await ctx.session.get(PayrollRow, (faction_id, official_id))
    if row is None:
        row = PayrollRow(faction_entity_id=faction_id, official_entity_id=official_id, bribe=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"bribe": bribe}, [])
    await ctx.session.flush()
    return row


async def edit_payroll(ctx: TickContext, faction_id: int, official_id: int, values: Values, release: list[str]) -> PayrollRow:
    row = apply(await found(ctx, PayrollRow, (faction_id, official_id), "payroll"), allowed(values, PAYROLL_FIELDS, "payroll"), release)
    await ctx.session.flush()
    return row


async def delete_payroll(ctx: TickContext, faction_id: int, official_id: int) -> None:
    await ctx.session.delete(await found(ctx, PayrollRow, (faction_id, official_id), "payroll"))
    await ctx.session.flush()


async def set_stance(ctx: TickContext, polity_id: int, faction_id: int, stance: CrimeStance, strength: int) -> CrimeStanceRow:
    await of_type(ctx, polity_id, frozenset({EntityType.POLITY}), "a realm")
    await faction_of(ctx, faction_id, CRIME_KINDS, "a criminal organisation")
    row = await ctx.session.get(CrimeStanceRow, (polity_id, faction_id))
    if row is None:
        row = CrimeStanceRow(polity_entity_id=polity_id, faction_entity_id=faction_id, stance=stance, strength=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.stance = stance
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def edit_stance(ctx: TickContext, polity_id: int, faction_id: int, values: Values, release: list[str]) -> CrimeStanceRow:
    row = apply(await found(ctx, CrimeStanceRow, (polity_id, faction_id), "stance"), allowed(values, (*STANCE_FIELDS, "stance"), "stance"), release)
    await ctx.session.flush()
    return row


async def delete_stance(ctx: TickContext, polity_id: int, faction_id: int) -> None:
    await ctx.session.delete(await found(ctx, CrimeStanceRow, (polity_id, faction_id), "stance"))
    await ctx.session.flush()


async def set_law(ctx: TickContext, faction_id: int, law: OrderLaw, strength: int) -> OrderLawRow:
    await faction_of(ctx, faction_id, frozenset({FactionKind.MAGE_ORDER}), "a magical order")
    row = await ctx.session.get(OrderLawRow, (faction_id, law))
    if row is None:
        row = OrderLawRow(faction_entity_id=faction_id, law=law, strength=0, locked=[])
        ctx.session.add(row)
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def edit_law(ctx: TickContext, faction_id: int, law: OrderLaw, values: Values, release: list[str]) -> OrderLawRow:
    row = apply(await found(ctx, OrderLawRow, (faction_id, law), "order law"), allowed(values, ORDER_LAW_FIELDS, "order law"), release)
    await ctx.session.flush()
    return row


async def delete_law(ctx: TickContext, faction_id: int, law: OrderLaw) -> None:
    await ctx.session.delete(await found(ctx, OrderLawRow, (faction_id, law), "order law"))
    await ctx.session.flush()


async def convene(ctx: TickContext, faction_id: int, law: OrderLaw, accused_id: int) -> TribunalRow:
    order = await entity(ctx, faction_id, "magical order")
    row = await found(ctx, OrderLawRow, (faction_id, law), "order law")
    await of_type(ctx, accused_id, frozenset({EntityType.MORTAL}), "a mortal")
    await try_member(ctx, order, row, accused_id, OrderTally())
    await ctx.session.flush()
    trial = await ctx.session.scalar(select(TribunalRow).where(TribunalRow.faction_entity_id == faction_id).order_by(TribunalRow.id.desc()).limit(1))
    if trial is None:
        raise ValidationFailedError("The tribunal could not sit; the accused is held by another hand.")
    return trial


async def strike_trial(ctx: TickContext, trial_id: int) -> None:
    await ctx.session.delete(await found(ctx, TribunalRow, trial_id, "tribunal"))
    await ctx.session.flush()


async def open_trading_post(ctx: TickContext, owner_id: int, host_id: int) -> TradingPostRow:
    owner = await entity(ctx, owner_id, "merchant house")
    await faction_of(ctx, owner_id, None, "a merchant house")
    host = await settlement(ctx, host_id)
    return await open_post(ctx, owner, host)


async def edit_trading_post(ctx: TickContext, structure_id: int, values: Values, release: list[str]) -> TradingPostRow:
    row = apply(await found(ctx, TradingPostRow, structure_id, "trading post"), allowed(values, TRADING_POST_FIELDS, "trading post"), release)
    await ctx.session.flush()
    return row


async def close_trading_post(ctx: TickContext, structure_id: int) -> None:
    await ctx.session.delete(await found(ctx, TradingPostRow, structure_id, "trading post"))
    await ctx.session.flush()


async def send_convoy(ctx: TickContext, route_id: int) -> ConvoyRow:
    route = await entity(ctx, route_id, "trade route")
    profile = await found(ctx, TradeRouteProfileRow, route_id, "trade route")
    await dispatch(ctx, route, profile, ConvoyTally())
    await ctx.session.flush()
    row = await ctx.session.scalar(select(ConvoyRow).where(ConvoyRow.route_entity_id == route_id).order_by(ConvoyRow.id.desc()).limit(1))
    if row is None:
        raise ValidationFailedError("No convoy could set out on that route.")
    return row


async def edit_convoy(ctx: TickContext, convoy_id: int, values: Values, release: list[str]) -> ConvoyRow:
    row = apply(await found(ctx, ConvoyRow, convoy_id, "convoy"), allowed(values, CONVOY_FIELDS, "convoy"), release)
    await ctx.session.flush()
    return row


async def delete_convoy(ctx: TickContext, convoy_id: int) -> None:
    await ctx.session.delete(await found(ctx, ConvoyRow, convoy_id, "convoy"))
    await ctx.session.flush()


async def set_fleet(ctx: TickContext, owner_id: int, kind: TransportKind, count: int) -> FleetRow:
    await entity(ctx, owner_id, "owner")
    row = await ctx.session.get(FleetRow, (owner_id, kind))
    if row is None:
        row = FleetRow(owner_entity_id=owner_id, kind=kind, count=0, age=0, condition=100, locked=[])
        ctx.session.add(row)
    apply(row, {"count": count}, [])
    await ctx.session.flush()
    return row


async def edit_fleet(ctx: TickContext, owner_id: int, kind: TransportKind, values: Values, release: list[str]) -> FleetRow:
    row = apply(await found(ctx, FleetRow, (owner_id, kind), "fleet"), allowed(values, FLEET_FIELDS, "fleet"), release)
    await ctx.session.flush()
    return row


async def delete_fleet(ctx: TickContext, owner_id: int, kind: TransportKind) -> None:
    await ctx.session.delete(await found(ctx, FleetRow, (owner_id, kind), "fleet"))
    await ctx.session.flush()


async def set_play(ctx: TickContext, holder_id: int, settlement_id: int, commodity: CommodityKind, play: MarketPlay, *, strength: int) -> MarketPlayRow:
    await entity(ctx, holder_id, "merchant house")
    await settlement(ctx, settlement_id)
    row = await ctx.session.get(MarketPlayRow, (holder_id, settlement_id, commodity, play))
    if row is None:
        row = MarketPlayRow(
            holder_entity_id=holder_id,
            settlement_entity_id=settlement_id,
            commodity=commodity,
            play=play,
            strength=0,
            since_epoch=ctx.epoch,
            until_epoch=ctx.epoch + ctx.rules.manipulation.length,
            locked=[],
        )
        ctx.session.add(row)
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def edit_play(ctx: TickContext, key: tuple[int, int, CommodityKind, MarketPlay], values: Values, release: list[str]) -> MarketPlayRow:
    row = apply(await found(ctx, MarketPlayRow, key, "market play"), allowed(values, PLAY_FIELDS, "market play"), release)
    await ctx.session.flush()
    return row


async def delete_play(ctx: TickContext, key: tuple[int, int, CommodityKind, MarketPlay]) -> None:
    await ctx.session.delete(await found(ctx, MarketPlayRow, key, "market play"))
    await ctx.session.flush()
