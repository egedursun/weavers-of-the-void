from pydantic import Field
from sqlalchemy import select

from aerona.catalog.renown import AXIS_LABELS, CURRENCY_LABELS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.renown import DeedClaimRow, DeedRow, LoreTradeRow, ReputationRow, RulerCurrencyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, Currency, ReputationAxis
from aerona.engine.renown.book import reputation_row
from aerona.engine.renown.claims import punish
from aerona.engine.renown.currencies import purse_of
from aerona.engine.renown.deeds import DeedTally, credit, expose, new_claim, record_deed
from aerona.engine.renown.lore import trade, value_of
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
CURRENCIES = tuple(currency.value for currency in Currency)


class SetReputation(Command):
    subject_id: int
    community_id: int
    axis: ReputationAxis
    skill: SkillKind | None = None
    value: int = Field(ge=0, le=SPAN)
    hold: bool = True


class ReputationTarget(Command):
    reputation_id: int


class SetStanding(Command):
    subject_id: int
    prestige: int | None = Field(default=None, ge=0, le=SPAN)
    piety: int | None = Field(default=None, ge=0, le=SPAN)
    dread: int | None = Field(default=None, ge=0, le=SPAN)
    tyranny: int | None = Field(default=None, ge=0, le=SPAN)
    trust: int | None = Field(default=None, ge=0, le=SPAN)
    learning: int | None = Field(default=None, ge=0, le=SPAN)
    silenced_until: int | None = Field(default=None, ge=0)
    hold: bool = True


class StandingTarget(Command):
    subject_id: int


class RecordDeed(Command):
    doer_id: int
    axis: ReputationAxis
    magnitude: int = Field(ge=1, le=SPAN)
    act: ActKind | None = None
    skill: SkillKind | None = None
    place_id: int | None = None
    token: bool = False


class EditDeed(Command):
    deed_id: int
    magnitude: int | None = Field(default=None, ge=0, le=SPAN)
    token: bool | None = None
    note: str | None = Field(default=None, max_length=120)
    hold: bool = True


class DeedTarget(Command):
    deed_id: int


class SetDeedClaim(Command):
    deed_id: int
    claimant_id: int
    kind: ClaimKind
    status: ClaimStatus = ClaimStatus.STANDING
    hold: bool = True


class DeedClaimTarget(Command):
    claim_id: int


class TradeLore(Command):
    seller_id: int
    buyer_id: int
    kind: KnowledgeKind
    key: str = Field(min_length=1, max_length=120)
    subject_id: int | None = None


class TradeTarget(Command):
    trade_id: int


async def node(scope: PlayerScope, node_id: int) -> None:
    if await scope.session.get(NodeRow, node_id) is None:
        raise ValidationFailedError("That record does not exist.")


async def living(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.status is not EntityStatus.CANON:
        raise ValidationFailedError("That record is not alive in the world.")
    return found


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


@player_action("renown:set", ActionKind.OTHER)
async def set_reputation(scope: PlayerScope, command: SetReputation) -> Effect:
    await node(scope, command.subject_id)
    await node(scope, command.community_id)
    if command.subject_id == command.community_id:
        raise ValidationFailedError("A community holds no reputation of itself.")
    row = await reputation_row(scope.session, command.subject_id, command.community_id, command.axis, command.skill)
    if row is None:
        row = ReputationRow(
            subject_node_id=command.subject_id,
            community_node_id=command.community_id,
            axis=command.axis,
            skill=command.skill,
            value=0,
            heard_epoch=await scope.epoch(),
            locked=[],
        )
        scope.session.add(row)
    row.value, row.heard_epoch = command.value, await scope.epoch()
    row.locked = held(row.locked, ["value"], command.hold)
    await scope.session.flush()
    return Effect(f"{AXIS_LABELS[command.axis]} is now {command.value:d} there.", target_node_id=command.subject_id, values={"reputation_id": row.id})


@player_action("renown:remove", ActionKind.OTHER)
async def remove_reputation(scope: PlayerScope, command: ReputationTarget) -> Effect:
    row = await scope.session.get(ReputationRow, command.reputation_id)
    if row is None:
        raise NotFoundError("No such reputation.")
    subject = row.subject_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The reputation was forgotten.", target_node_id=subject)


@player_action("standing:set", ActionKind.OTHER)
async def set_currency(scope: PlayerScope, command: SetStanding) -> Effect:
    await living(scope, command.subject_id)
    row = await purse_of(scope.session, command.subject_id, await scope.epoch())
    if row is None:
        raise ValidationFailedError("That ruler is held; their standing cannot change.")
    touched = [name for name in CURRENCIES if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if command.silenced_until is not None:
        row.silenced_until = command.silenced_until
        touched.append("silenced_until")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    told = ", ".join(f"{CURRENCY_LABELS[Currency(name)].lower()} {getattr(row, name)}" for name in CURRENCIES)
    return Effect(f"Standing set: {told}.", target_node_id=command.subject_id)


@player_action("standing:remove", ActionKind.OTHER)
async def remove_currency(scope: PlayerScope, command: StandingTarget) -> Effect:
    row = await scope.session.get(RulerCurrencyRow, command.subject_id)
    if row is None:
        raise NotFoundError("That ruler holds no prestige, piety, dread or tyranny.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("Their standing as a ruler was wiped clean.", target_node_id=command.subject_id)


@player_action("deed:record", ActionKind.OTHER)
async def add_deed(scope: PlayerScope, command: RecordDeed) -> Effect:
    await living(scope, command.doer_id)
    if command.place_id is not None:
        await node(scope, command.place_id)
    ctx = await scope.context("deed:record")
    deed = await record_deed(
        ctx, command.doer_id, command.axis, command.magnitude, act=command.act, skill=command.skill, place_id=command.place_id, token=command.token
    )
    if deed is None:
        raise ValidationFailedError("A held doer cannot be credited with a deed.")
    if command.place_id is not None:
        deed.witnesses += 1
        await credit(ctx, deed, command.place_id, command.magnitude, witnessed=True)
    await scope.session.flush()
    return Effect(f"A deed of {AXIS_LABELS[command.axis].lower()} was set down.", target_node_id=command.doer_id, values={"deed_id": deed.id})


async def deed_row(scope: PlayerScope, deed_id: int) -> DeedRow:
    row = await scope.session.get(DeedRow, deed_id)
    if row is None:
        raise NotFoundError("No such deed.")
    return row


@player_action("deed:edit", ActionKind.OTHER)
async def edit_deed(scope: PlayerScope, command: EditDeed) -> Effect:
    row = await deed_row(scope, command.deed_id)
    touched: list[str] = []
    if command.magnitude is not None:
        row.magnitude = command.magnitude
        touched.append("magnitude")
    if command.token is not None:
        row.token = command.token
    if command.note is not None:
        row.note = command.note
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect("The deed was retold.", target_node_id=row.doer_node_id)


@player_action("deed:remove", ActionKind.OTHER)
async def remove_deed(scope: PlayerScope, command: DeedTarget) -> Effect:
    row = await deed_row(scope, command.deed_id)
    doer = row.doer_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The deed was struck from memory.", target_node_id=doer)


@player_action("deed_claim:set", ActionKind.OTHER)
async def set_claim(scope: PlayerScope, command: SetDeedClaim) -> Effect:
    deed = await deed_row(scope, command.deed_id)
    claimant = await living(scope, command.claimant_id)
    row = await scope.session.scalar(select(DeedClaimRow).where(DeedClaimRow.deed_id == deed.id, DeedClaimRow.claimant_node_id == claimant.id))
    if row is None:
        row = new_claim(deed.id, claimant.id, command.kind, await scope.epoch())
        scope.session.add(row)
    row.kind, row.status = command.kind, command.status
    row.locked = held(row.locked, ["status"], command.hold)
    await scope.session.flush()
    return Effect(f"{claimant.name} now holds {an(spoken(command.kind))} claim to the deed.", target_node_id=claimant.id, values={"claim_id": row.id})


async def claim_row(scope: PlayerScope, claim_id: int) -> DeedClaimRow:
    row = await scope.session.get(DeedClaimRow, claim_id)
    if row is None:
        raise NotFoundError("No such claim.")
    return row


@player_action("deed_claim:expose", ActionKind.OTHER)
async def expose_claim(scope: PlayerScope, command: DeedClaimTarget) -> Effect:
    row = await claim_row(scope, command.claim_id)
    deed = await deed_row(scope, row.deed_id)
    if row.kind is not ClaimKind.FALSE or row.status is ClaimStatus.EXPOSED:
        raise ValidationFailedError("Only a believed false claim can be exposed.")
    ctx = await scope.context("deed_claim:expose")
    await expose(ctx, deed, row, DeedTally())
    await punish(ctx, row)
    return Effect("The false claim was exposed.", target_node_id=row.claimant_node_id)


@player_action("deed_claim:remove", ActionKind.OTHER)
async def remove_claim(scope: PlayerScope, command: DeedClaimTarget) -> Effect:
    row = await claim_row(scope, command.claim_id)
    claimant = row.claimant_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The claim was withdrawn.", target_node_id=claimant)


@player_action("lore_trade:make", ActionKind.OTHER)
async def trade_lore(scope: PlayerScope, command: TradeLore) -> Effect:
    seller, buyer = await living(scope, command.seller_id), await living(scope, command.buyer_id)
    if seller.id == buyer.id:
        raise ValidationFailedError(f"{seller.name} cannot trade lore with themselves.")
    if command.kind is KnowledgeKind.TECHNIQUE and command.key not in {technique.value for technique in Technique}:
        raise ValidationFailedError(f"'{command.key}' is not a technique that can be traded.")
    if command.kind is not KnowledgeKind.TECHNIQUE and command.subject_id is None:
        raise ValidationFailedError("Choose the site, region or prophecy the lore is about.")
    if command.subject_id is not None:
        await node(scope, command.subject_id)
    ctx = await scope.context("lore_trade:make")
    item = (command.kind, command.key, command.subject_id)
    row = await trade(ctx, seller, buyer, item, value=await value_of(ctx, item))
    if row is None:
        raise ValidationFailedError(f"{buyer.name} already holds that lore, or it cannot be given.")
    return Effect(f"{seller.name} passed lore to {buyer.name} for {spoken(row.price)}.", target_node_id=buyer.id, values={"trade_id": row.id})


@player_action("lore_trade:remove", ActionKind.OTHER)
async def remove_trade(scope: PlayerScope, command: TradeTarget) -> Effect:
    row = await scope.session.get(LoreTradeRow, command.trade_id)
    if row is None:
        raise NotFoundError("No such trade.")
    buyer = row.buyer_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The record of the trade was struck.", target_node_id=buyer)
