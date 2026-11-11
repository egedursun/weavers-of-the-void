from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.urban import CrimeStance, MarketPlay, OrderLaw, RacketKind, TransportKind, UrbanService
from aerona.engine.urban import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class DistrictEdit(Edited):
    district_id: int


class TownEdit(Edited):
    settlement_id: int


class TownTarget(Command):
    settlement_id: int


class Placement(Command):
    structure_id: int
    district_id: int | None = None


class ServiceDraft(Command):
    district_id: int
    service: UrbanService
    coverage: int = Field(default=50, ge=0, le=SPAN)


class ServiceEdit(Edited):
    district_id: int
    service: UrbanService


class ServiceTarget(Command):
    district_id: int
    service: UrbanService


class TurfDraft(Command):
    district_id: int
    faction_id: int
    strength: int = Field(default=50, ge=0, le=SPAN)


class TurfEdit(Edited):
    district_id: int
    faction_id: int


class TurfTarget(Command):
    district_id: int
    faction_id: int


class RacketDraft(Command):
    faction_id: int
    settlement_id: int
    racket: RacketKind
    income: int = Field(default=10, ge=0, le=100000)


class RacketEdit(Edited):
    faction_id: int
    settlement_id: int
    racket: RacketKind


class RacketTarget(Command):
    faction_id: int
    settlement_id: int
    racket: RacketKind


class PayrollDraft(Command):
    faction_id: int
    official_id: int
    bribe: int = Field(default=5, ge=0, le=100000)


class PayrollEdit(Edited):
    faction_id: int
    official_id: int


class PayrollTarget(Command):
    faction_id: int
    official_id: int


class StanceDraft(Command):
    polity_id: int
    faction_id: int
    stance: CrimeStance
    strength: int = Field(default=50, ge=0, le=SPAN)


class StanceEdit(Edited):
    polity_id: int
    faction_id: int


class StanceTarget(Command):
    polity_id: int
    faction_id: int


class LawDraft(Command):
    faction_id: int
    law: OrderLaw
    strength: int = Field(default=50, ge=0, le=SPAN)


class LawEdit(Edited):
    faction_id: int
    law: OrderLaw


class LawTarget(Command):
    faction_id: int
    law: OrderLaw


class Trial(Command):
    faction_id: int
    law: OrderLaw
    accused_id: int


class TrialTarget(Command):
    trial_id: int


class PostDraft(Command):
    owner_id: int
    host_id: int


class PostEdit(Edited):
    structure_id: int


class PostTarget(Command):
    structure_id: int


class RouteTarget(Command):
    route_id: int


class ConvoyEdit(Edited):
    convoy_id: int


class ConvoyTarget(Command):
    convoy_id: int


class FleetDraft(Command):
    owner_id: int
    kind: TransportKind
    count: int = Field(default=10, ge=0, le=100000)


class FleetEdit(Edited):
    owner_id: int
    kind: TransportKind


class FleetTarget(Command):
    owner_id: int
    kind: TransportKind


class PlayDraft(Command):
    holder_id: int
    settlement_id: int
    commodity: CommodityKind
    play: MarketPlay
    strength: int = Field(default=50, ge=0, le=SPAN)


class PlayEdit(Edited):
    holder_id: int
    settlement_id: int
    commodity: CommodityKind
    play: MarketPlay


class PlayTarget(Command):
    holder_id: int
    settlement_id: int
    commodity: CommodityKind
    play: MarketPlay


@player_action("district_urban:edit", ActionKind.EDIT_RECORD)
async def edit_district(scope: PlayerScope, command: DistrictEdit) -> Effect:
    ctx = await scope.context("district_urban_edit")
    await control.edit_district(ctx, command.district_id, command.values, command.release)
    return Effect("The district is set so.")


@player_action("town_urban:edit", ActionKind.EDIT_RECORD)
async def edit_town(scope: PlayerScope, command: TownEdit) -> Effect:
    ctx = await scope.context("town_urban_edit")
    await control.edit_town(ctx, command.settlement_id, command.values, command.release)
    return Effect("The town is set so.", command.settlement_id)


@player_action("structure:place", ActionKind.EDIT_RECORD)
async def place_structure(scope: PlayerScope, command: Placement) -> Effect:
    ctx = await scope.context("structure_place")
    await control.place_structure(ctx, command.structure_id, command.district_id)
    return Effect("The structure stands in that district now.", command.structure_id)


@player_action("slums:clear", ActionKind.EDIT_RECORD)
async def clear_slums(scope: PlayerScope, command: TownTarget) -> Effect:
    ctx = await scope.context("slums_clear")
    await control.clear(ctx, command.settlement_id)
    return Effect("The slums are cleared; their folk are homeless now.", command.settlement_id)


@player_action("district_service:set", ActionKind.EDIT_RECORD)
async def set_service(scope: PlayerScope, command: ServiceDraft) -> Effect:
    ctx = await scope.context("district_service_set")
    await control.set_service(ctx, command.district_id, command.service, command.coverage)
    return Effect("The district's service is set and held.")


@player_action("district_service:edit", ActionKind.EDIT_RECORD)
async def edit_service(scope: PlayerScope, command: ServiceEdit) -> Effect:
    ctx = await scope.context("district_service_edit")
    await control.edit_service(ctx, command.district_id, command.service, command.values, command.release)
    return Effect("The district's service is set so.")


@player_action("district_service:delete", ActionKind.EDIT_RECORD)
async def delete_service(scope: PlayerScope, command: ServiceTarget) -> Effect:
    ctx = await scope.context("district_service_delete")
    await control.delete_service(ctx, command.district_id, command.service)
    return Effect("The district's service is drawn anew.")


@player_action("turf:set", ActionKind.EDIT_RECORD)
async def set_turf(scope: PlayerScope, command: TurfDraft) -> Effect:
    ctx = await scope.context("turf_set")
    await control.set_turf(ctx, command.district_id, command.faction_id, command.strength)
    return Effect("The organisation holds those streets.", command.faction_id)


@player_action("turf:edit", ActionKind.EDIT_RECORD)
async def edit_turf(scope: PlayerScope, command: TurfEdit) -> Effect:
    ctx = await scope.context("turf_edit")
    await control.edit_turf(ctx, command.district_id, command.faction_id, command.values, command.release)
    return Effect("The turf is set so.", command.faction_id)


@player_action("turf:delete", ActionKind.EDIT_RECORD)
async def delete_turf(scope: PlayerScope, command: TurfTarget) -> Effect:
    ctx = await scope.context("turf_delete")
    await control.delete_turf(ctx, command.district_id, command.faction_id)
    return Effect("The organisation is driven from those streets.", command.faction_id)


@player_action("racket:set", ActionKind.EDIT_RECORD)
async def set_racket(scope: PlayerScope, command: RacketDraft) -> Effect:
    ctx = await scope.context("racket_set")
    await control.set_racket(ctx, command.faction_id, command.settlement_id, command.racket, command.income)
    return Effect("The racket runs.", command.faction_id)


@player_action("racket:edit", ActionKind.EDIT_RECORD)
async def edit_racket(scope: PlayerScope, command: RacketEdit) -> Effect:
    ctx = await scope.context("racket_edit")
    await control.edit_racket(ctx, (command.faction_id, command.settlement_id, command.racket), command.values, command.release)
    return Effect("The racket is set so.", command.faction_id)


@player_action("racket:delete", ActionKind.EDIT_RECORD)
async def delete_racket(scope: PlayerScope, command: RacketTarget) -> Effect:
    ctx = await scope.context("racket_delete")
    await control.delete_racket(ctx, (command.faction_id, command.settlement_id, command.racket))
    return Effect("The racket is broken.", command.faction_id)


@player_action("payroll:add", ActionKind.EDIT_RECORD)
async def add_payroll(scope: PlayerScope, command: PayrollDraft) -> Effect:
    ctx = await scope.context("payroll_add")
    await control.add_payroll(ctx, command.faction_id, command.official_id, command.bribe)
    return Effect("The official is on the payroll.", command.official_id)


@player_action("payroll:edit", ActionKind.EDIT_RECORD)
async def edit_payroll(scope: PlayerScope, command: PayrollEdit) -> Effect:
    ctx = await scope.context("payroll_edit")
    await control.edit_payroll(ctx, command.faction_id, command.official_id, command.values, command.release)
    return Effect("The bribe is set so.", command.official_id)


@player_action("payroll:delete", ActionKind.EDIT_RECORD)
async def delete_payroll(scope: PlayerScope, command: PayrollTarget) -> Effect:
    ctx = await scope.context("payroll_delete")
    await control.delete_payroll(ctx, command.faction_id, command.official_id)
    return Effect("The official is off the payroll.", command.official_id)


@player_action("crime_stance:set", ActionKind.EDIT_RECORD)
async def set_stance(scope: PlayerScope, command: StanceDraft) -> Effect:
    ctx = await scope.context("crime_stance_set")
    await control.set_stance(ctx, command.polity_id, command.faction_id, command.stance, command.strength)
    return Effect("The realm takes its stance.", command.polity_id)


@player_action("crime_stance:edit", ActionKind.EDIT_RECORD)
async def edit_stance(scope: PlayerScope, command: StanceEdit) -> Effect:
    ctx = await scope.context("crime_stance_edit")
    await control.edit_stance(ctx, command.polity_id, command.faction_id, command.values, command.release)
    return Effect("The stance is set so.", command.polity_id)


@player_action("crime_stance:delete", ActionKind.EDIT_RECORD)
async def delete_stance(scope: PlayerScope, command: StanceTarget) -> Effect:
    ctx = await scope.context("crime_stance_delete")
    await control.delete_stance(ctx, command.polity_id, command.faction_id)
    return Effect("The realm drops its stance.", command.polity_id)


@player_action("order_law:set", ActionKind.EDIT_RECORD)
async def set_law(scope: PlayerScope, command: LawDraft) -> Effect:
    ctx = await scope.context("order_law_set")
    await control.set_law(ctx, command.faction_id, command.law, command.strength)
    return Effect("The order keeps that law.", command.faction_id)


@player_action("order_law:edit", ActionKind.EDIT_RECORD)
async def edit_law(scope: PlayerScope, command: LawEdit) -> Effect:
    ctx = await scope.context("order_law_edit")
    await control.edit_law(ctx, command.faction_id, command.law, command.values, command.release)
    return Effect("The law is set so.", command.faction_id)


@player_action("order_law:delete", ActionKind.EDIT_RECORD)
async def delete_law(scope: PlayerScope, command: LawTarget) -> Effect:
    ctx = await scope.context("order_law_delete")
    await control.delete_law(ctx, command.faction_id, command.law)
    return Effect("The order drops that law.", command.faction_id)


@player_action("tribunal:convene", ActionKind.EDIT_RECORD)
async def convene(scope: PlayerScope, command: Trial) -> Effect:
    ctx = await scope.context("tribunal_convene")
    await control.convene(ctx, command.faction_id, command.law, command.accused_id)
    return Effect("The tribunal sits and judges.", command.faction_id)


@player_action("tribunal:strike", ActionKind.EDIT_RECORD)
async def strike_trial(scope: PlayerScope, command: TrialTarget) -> Effect:
    ctx = await scope.context("tribunal_strike")
    await control.strike_trial(ctx, command.trial_id)
    return Effect("The judgement is struck from the record.")


@player_action("trading_post:open", ActionKind.EDIT_RECORD)
async def open_trading_post(scope: PlayerScope, command: PostDraft) -> Effect:
    ctx = await scope.context("trading_post_open")
    await control.open_trading_post(ctx, command.owner_id, command.host_id)
    return Effect("The trading post opens.", command.host_id)


@player_action("trading_post:edit", ActionKind.EDIT_RECORD)
async def edit_trading_post(scope: PlayerScope, command: PostEdit) -> Effect:
    ctx = await scope.context("trading_post_edit")
    await control.edit_trading_post(ctx, command.structure_id, command.values, command.release)
    return Effect("The trading post is set so.", command.structure_id)


@player_action("trading_post:close", ActionKind.EDIT_RECORD)
async def close_trading_post(scope: PlayerScope, command: PostTarget) -> Effect:
    ctx = await scope.context("trading_post_close")
    await control.close_trading_post(ctx, command.structure_id)
    return Effect("The trading post closes.", command.structure_id)


@player_action("convoy:send", ActionKind.EDIT_RECORD)
async def send_convoy(scope: PlayerScope, command: RouteTarget) -> Effect:
    ctx = await scope.context("convoy_send")
    await control.send_convoy(ctx, command.route_id)
    return Effect("A convoy sets out.", command.route_id)


@player_action("convoy:edit", ActionKind.EDIT_RECORD)
async def edit_convoy(scope: PlayerScope, command: ConvoyEdit) -> Effect:
    ctx = await scope.context("convoy_edit")
    await control.edit_convoy(ctx, command.convoy_id, command.values, command.release)
    return Effect("The convoy is set so.")


@player_action("convoy:delete", ActionKind.EDIT_RECORD)
async def delete_convoy(scope: PlayerScope, command: ConvoyTarget) -> Effect:
    ctx = await scope.context("convoy_delete")
    await control.delete_convoy(ctx, command.convoy_id)
    return Effect("The convoy is struck from the road.")


@player_action("fleet:set", ActionKind.EDIT_RECORD)
async def set_fleet(scope: PlayerScope, command: FleetDraft) -> Effect:
    ctx = await scope.context("fleet_set")
    await control.set_fleet(ctx, command.owner_id, command.kind, command.count)
    return Effect("The fleet is set and held.", command.owner_id)


@player_action("fleet:edit", ActionKind.EDIT_RECORD)
async def edit_fleet(scope: PlayerScope, command: FleetEdit) -> Effect:
    ctx = await scope.context("fleet_edit")
    await control.edit_fleet(ctx, command.owner_id, command.kind, command.values, command.release)
    return Effect("The fleet is set so.", command.owner_id)


@player_action("fleet:delete", ActionKind.EDIT_RECORD)
async def delete_fleet(scope: PlayerScope, command: FleetTarget) -> Effect:
    ctx = await scope.context("fleet_delete")
    await control.delete_fleet(ctx, command.owner_id, command.kind)
    return Effect("The fleet is gone.", command.owner_id)


@player_action("market_play:set", ActionKind.EDIT_RECORD)
async def set_play(scope: PlayerScope, command: PlayDraft) -> Effect:
    ctx = await scope.context("market_play_set")
    await control.set_play(ctx, command.holder_id, command.settlement_id, command.commodity, command.play, strength=command.strength)
    return Effect("The market is played.", command.settlement_id)


@player_action("market_play:edit", ActionKind.EDIT_RECORD)
async def edit_play(scope: PlayerScope, command: PlayEdit) -> Effect:
    ctx = await scope.context("market_play_edit")
    await control.edit_play(ctx, (command.holder_id, command.settlement_id, command.commodity, command.play), command.values, command.release)
    return Effect("The play is set so.", command.settlement_id)


@player_action("market_play:delete", ActionKind.EDIT_RECORD)
async def delete_play(scope: PlayerScope, command: PlayTarget) -> Effect:
    ctx = await scope.context("market_play_delete")
    await control.delete_play(ctx, (command.holder_id, command.settlement_id, command.commodity, command.play))
    return Effect("The play ends.", command.settlement_id)
