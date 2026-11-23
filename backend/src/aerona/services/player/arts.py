from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.arts import ArtMarketRole, CanonPath, ClubKind, ForgeryKind
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.arts import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

MANY = 1_000_000
SPAN = 100


class PriceDraft(Command):
    artwork_id: int
    price: int | None = Field(default=None, ge=0, le=MANY)


class ArtworkTarget(Command):
    artwork_id: int


class ArtworkEdit(Edited):
    artwork_id: int


class SaleDraft(Command):
    artwork_id: int
    buyer_id: int
    price: int | None = Field(default=None, ge=0, le=MANY)


class SaleTarget(Command):
    sale_id: int


class SaleEdit(Edited):
    sale_id: int


class CollectorDraft(Command):
    holder_id: int
    role: ArtMarketRole | None = None
    taste_id: int | None = None


class HolderTarget(Command):
    holder_id: int


class HolderEdit(Edited):
    holder_id: int


class ForgeryDraft(Command):
    original_id: int
    forger_id: int
    kind: ForgeryKind | None = None


class ForgeryTarget(Command):
    forgery_id: int


class ForgeryExposure(Command):
    forgery_id: int
    expert_id: int | None = None


class ForgeryEdit(Edited):
    forgery_id: int


class CanonDraft(Command):
    people_id: int
    artwork_id: int
    path: CanonPath = CanonPath.RENOWN


class CanonTarget(Command):
    people_id: int
    artwork_id: int


class CanonEdit(Edited):
    people_id: int
    artwork_id: int


class MovementDraft(Command):
    town_id: int


class FactionTarget(Command):
    faction_id: int


class FactionEdit(Edited):
    faction_id: int


class ManifestoLine(Command):
    faction_id: int
    axis: ValueAxis
    value: int | None = Field(default=None, ge=-SPAN, le=SPAN)


class ClubDraft(Command):
    town_id: int
    kind: ClubKind | None = None


class LeagueDraft(Command):
    realm_id: int
    town_id: int | None = None


class MatchDraft(Command):
    home_id: int
    away_id: int
    winner_id: int | None = None


class MatchTarget(Command):
    match_id: int


class MatchEdit(Edited):
    match_id: int


class BetDraft(Command):
    match_id: int
    town_id: int
    club_id: int
    stake: int | None = Field(default=None, ge=0, le=MANY)


class BetTarget(Command):
    bet_id: int


class BetEdit(Edited):
    bet_id: int


@player_action("art_price:set", ActionKind.EDIT_RECORD)
async def art_price_set(scope: PlayerScope, command: PriceDraft) -> Effect:
    row = await control.price_work(await scope.context("art_price_set"), command.artwork_id, command.price)
    return Effect(f"The work is valued at {row.price}.", command.artwork_id)


@player_action("art_price:edit", ActionKind.EDIT_RECORD)
async def art_price_edit(scope: PlayerScope, command: ArtworkEdit) -> Effect:
    await control.edit_record(await scope.context("art_price_edit"), "art_price", command.artwork_id, command.values, command.release)
    return Effect("The price of the work is set so.", command.artwork_id)


@player_action("art_price:delete", ActionKind.EDIT_RECORD)
async def art_price_delete(scope: PlayerScope, command: ArtworkTarget) -> Effect:
    await control.delete_record(await scope.context("art_price_delete"), "art_price", command.artwork_id)
    return Effect("The work has no price on the market.", command.artwork_id)


@player_action("art_sale:create", ActionKind.EDIT_RECORD)
async def art_sale_create(scope: PlayerScope, command: SaleDraft) -> Effect:
    row = await control.sell_work(await scope.context("art_sale_create"), command.artwork_id, command.buyer_id, command.price)
    return Effect("The work changes hands.", command.artwork_id, values={"sale_id": row.id})


@player_action("art_sale:edit", ActionKind.EDIT_RECORD)
async def art_sale_edit(scope: PlayerScope, command: SaleEdit) -> Effect:
    row = await control.edit_record(await scope.context("art_sale_edit"), "art_sale", command.sale_id, command.values, command.release)
    return Effect("The sale is set so.", getattr(row, "artwork_entity_id", None))


@player_action("art_sale:delete", ActionKind.EDIT_RECORD)
async def art_sale_delete(scope: PlayerScope, command: SaleTarget) -> Effect:
    await control.delete_record(await scope.context("art_sale_delete"), "art_sale", command.sale_id)
    return Effect("The sale is struck from the record.")


@player_action("collector:create", ActionKind.EDIT_RECORD)
async def collector_create(scope: PlayerScope, command: CollectorDraft) -> Effect:
    await control.add_collector(await scope.context("collector_create"), command.holder_id, command.role, command.taste_id)
    return Effect("A new collector enters the market.", command.holder_id)


@player_action("collector:edit", ActionKind.EDIT_RECORD)
async def collector_edit(scope: PlayerScope, command: HolderEdit) -> Effect:
    await control.edit_record(await scope.context("collector_edit"), "collector", command.holder_id, command.values, command.release)
    return Effect("The collector is set so.", command.holder_id)


@player_action("collector:delete", ActionKind.EDIT_RECORD)
async def collector_delete(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_record(await scope.context("collector_delete"), "collector", command.holder_id)
    return Effect("The collector leaves the market.", command.holder_id)


@player_action("forgery:create", ActionKind.EDIT_RECORD)
async def forgery_create(scope: PlayerScope, command: ForgeryDraft) -> Effect:
    row = await control.forge_work(await scope.context("forgery_create"), command.original_id, command.forger_id, command.kind)
    return Effect("A forgery is made.", command.forger_id, values={"forgery_id": row.id})


@player_action("forgery:expose", ActionKind.EDIT_RECORD)
async def forgery_expose(scope: PlayerScope, command: ForgeryExposure) -> Effect:
    row = await control.expose_forgery(await scope.context("forgery_expose"), command.forgery_id, command.expert_id)
    return Effect("The forgery is shown for what it is.", row.item_entity_id)


@player_action("forgery:edit", ActionKind.EDIT_RECORD)
async def forgery_edit(scope: PlayerScope, command: ForgeryEdit) -> Effect:
    row = await control.edit_record(await scope.context("forgery_edit"), "forgery", command.forgery_id, command.values, command.release)
    return Effect("The forgery is set so.", getattr(row, "item_entity_id", None))


@player_action("forgery:delete", ActionKind.EDIT_RECORD)
async def forgery_delete(scope: PlayerScope, command: ForgeryTarget) -> Effect:
    await control.delete_record(await scope.context("forgery_delete"), "forgery", command.forgery_id)
    return Effect("The forgery is struck from the record.")


@player_action("canon_work:create", ActionKind.EDIT_RECORD)
async def canon_work_create(scope: PlayerScope, command: CanonDraft) -> Effect:
    await control.canonise(await scope.context("canon_work_create"), command.people_id, command.artwork_id, command.path)
    return Effect("The work enters the canon.", command.artwork_id)


@player_action("canon_work:edit", ActionKind.EDIT_RECORD)
async def canon_work_edit(scope: PlayerScope, command: CanonEdit) -> Effect:
    key = (command.people_id, command.artwork_id)
    await control.edit_record(await scope.context("canon_work_edit"), "canon_work", key, command.values, command.release)
    return Effect("The canon work is set so.", command.artwork_id)


@player_action("canon_work:delete", ActionKind.EDIT_RECORD)
async def canon_work_delete(scope: PlayerScope, command: CanonTarget) -> Effect:
    await control.drop_canon(await scope.context("canon_work_delete"), command.people_id, command.artwork_id)
    return Effect("The work leaves the canon.", command.artwork_id)


@player_action("art_movement:create", ActionKind.EDIT_RECORD)
async def art_movement_create(scope: PlayerScope, command: MovementDraft) -> Effect:
    row = await control.start_movement(await scope.context("art_movement_create"), command.town_id)
    return Effect("The makers of the town band into a movement.", command.town_id, created_ids=(row.faction_entity_id,))


@player_action("art_movement:edit", ActionKind.EDIT_RECORD)
async def art_movement_edit(scope: PlayerScope, command: FactionEdit) -> Effect:
    await control.edit_record(await scope.context("art_movement_edit"), "art_movement", command.faction_id, command.values, command.release)
    return Effect("The movement is set so.", command.faction_id)


@player_action("art_movement:delete", ActionKind.EDIT_RECORD)
async def art_movement_delete(scope: PlayerScope, command: FactionTarget) -> Effect:
    await control.delete_record(await scope.context("art_movement_delete"), "art_movement", command.faction_id)
    return Effect("The faction keeps no art movement.", command.faction_id)


@player_action("art_movement:manifesto", ActionKind.EDIT_RECORD)
async def art_movement_manifesto(scope: PlayerScope, command: ManifestoLine) -> Effect:
    await control.set_manifesto(await scope.context("art_movement_manifesto"), command.faction_id, command.axis, command.value)
    return Effect("The manifesto is rewritten.", command.faction_id)


@player_action("club:create", ActionKind.EDIT_RECORD)
async def club_create(scope: PlayerScope, command: ClubDraft) -> Effect:
    row = await control.start_club(await scope.context("club_create"), command.town_id, command.kind)
    return Effect("A club is founded.", command.town_id, created_ids=(row.faction_entity_id,))


@player_action("club:edit", ActionKind.EDIT_RECORD)
async def club_edit(scope: PlayerScope, command: FactionEdit) -> Effect:
    await control.edit_record(await scope.context("club_edit"), "club", command.faction_id, command.values, command.release)
    return Effect("The club is set so.", command.faction_id)


@player_action("club:delete", ActionKind.EDIT_RECORD)
async def club_delete(scope: PlayerScope, command: FactionTarget) -> Effect:
    await control.delete_record(await scope.context("club_delete"), "club", command.faction_id)
    return Effect("The faction keeps no club.", command.faction_id)


@player_action("league:create", ActionKind.EDIT_RECORD)
async def league_create(scope: PlayerScope, command: LeagueDraft) -> Effect:
    row = await control.start_league(await scope.context("league_create"), command.realm_id, command.town_id)
    return Effect("The realm gains a league.", command.realm_id, created_ids=(row.faction_entity_id,))


@player_action("league:edit", ActionKind.EDIT_RECORD)
async def league_edit(scope: PlayerScope, command: FactionEdit) -> Effect:
    await control.edit_record(await scope.context("league_edit"), "league", command.faction_id, command.values, command.release)
    return Effect("The league is set so.", command.faction_id)


@player_action("league:delete", ActionKind.EDIT_RECORD)
async def league_delete(scope: PlayerScope, command: FactionTarget) -> Effect:
    await control.delete_record(await scope.context("league_delete"), "league", command.faction_id)
    return Effect("The faction keeps no league.", command.faction_id)


@player_action("match:create", ActionKind.EDIT_RECORD)
async def match_create(scope: PlayerScope, command: MatchDraft) -> Effect:
    row = await control.stage_match(await scope.context("match_create"), command.home_id, command.away_id, command.winner_id)
    return Effect("The match is played.", row.winner_entity_id, values={"match_id": row.id})


@player_action("match:edit", ActionKind.EDIT_RECORD)
async def match_edit(scope: PlayerScope, command: MatchEdit) -> Effect:
    row = await control.edit_record(await scope.context("match_edit"), "match", command.match_id, command.values, command.release)
    return Effect("The match is set so.", getattr(row, "home_entity_id", None))


@player_action("match:delete", ActionKind.EDIT_RECORD)
async def match_delete(scope: PlayerScope, command: MatchTarget) -> Effect:
    await control.delete_record(await scope.context("match_delete"), "match", command.match_id)
    return Effect("The match is struck from the record.")


@player_action("bet:create", ActionKind.EDIT_RECORD)
async def bet_create(scope: PlayerScope, command: BetDraft) -> Effect:
    row = await control.place_bet(await scope.context("bet_create"), command.match_id, command.town_id, command.club_id, command.stake)
    return Effect("The town wagers on the match.", command.town_id, values={"bet_id": row.id})


@player_action("bet:edit", ActionKind.EDIT_RECORD)
async def bet_edit(scope: PlayerScope, command: BetEdit) -> Effect:
    row = await control.edit_record(await scope.context("bet_edit"), "bet", command.bet_id, command.values, command.release)
    return Effect("The bet is set so.", getattr(row, "settlement_entity_id", None))


@player_action("bet:delete", ActionKind.EDIT_RECORD)
async def bet_delete(scope: PlayerScope, command: BetTarget) -> Effect:
    await control.delete_record(await scope.context("bet_delete"), "bet", command.bet_id)
    return Effect("The bet is struck from the record.")
