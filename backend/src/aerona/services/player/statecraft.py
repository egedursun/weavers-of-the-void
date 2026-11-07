from pydantic import Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.crises import DEMAND_TEXT, CrisisTally, Verdict
from aerona.engine.polity.crisis_outcomes import settle
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
CRISIS_FIELDS = ("escalation", "state", "amount", "subject_node_id")
POLITY = frozenset({EntityType.POLITY})


class SetRegard(Command):
    holder_id: int
    subject_id: int
    threat: int | None = Field(default=None, ge=0, le=SPAN)
    trust: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class RegardTarget(Command):
    holder_id: int
    subject_id: int


class EditDiplomacy(Command):
    polity_id: int
    capacity: int | None = Field(default=None, ge=0, le=SPAN)
    relations: int | None = Field(default=None, ge=0, le=SPAN)
    strain: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class OpenCrisis(Command):
    demander_id: int
    target_id: int
    demand: CrisisDemand
    subject_id: int | None = None
    amount: int = Field(default=0, ge=0, le=1_000_000)


class CrisisTarget(Command):
    crisis_id: int


class EditCrisis(Command):
    crisis_id: int
    escalation: int | None = Field(default=None, ge=0, le=20)
    amount: int | None = Field(default=None, ge=0, le=1_000_000)
    subject_id: int | None = None
    hold: bool = True


class HoldCrisis(Command):
    crisis_id: int
    hold: bool = True


class ResolveCrisis(Command):
    crisis_id: int
    state: CrisisState


class SetBacker(Command):
    crisis_id: int
    backer_id: int
    side: CrisisSide
    promised: int = Field(default=0, ge=0, le=SPAN)
    swing: bool = False
    hold: bool = True


class BackerTarget(Command):
    crisis_id: int
    backer_id: int


class SetSphere(Command):
    power_id: int
    client_id: int
    strength: int = Field(ge=0, le=SPAN)
    hold: bool = True


class SphereTarget(Command):
    power_id: int
    client_id: int


def held(locked: list[str] | None, fields: list[str] | tuple[str, ...], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def realm(scope: PlayerScope, entity_id: int, label: str) -> EntityRow:
    found = await scope.session.get(EntityRow, entity_id)
    if found is None or found.entity_type not in POLITY:
        raise ValidationFailedError(f"{label} must be a realm.")
    return found


async def crisis_of(scope: PlayerScope, crisis_id: int) -> CrisisRow:
    row = await scope.session.get(CrisisRow, crisis_id)
    if row is None:
        raise NotFoundError("No such crisis.")
    return row


@player_action("regard:set", ActionKind.EDIT_RECORD)
async def set_regard(scope: PlayerScope, command: SetRegard) -> Effect:
    holder = await realm(scope, command.holder_id, "The realm that feels it")
    subject = await realm(scope, command.subject_id, "The realm it is felt for")
    if holder.id == subject.id:
        raise ValidationFailedError("A realm holds no regard for itself.")
    row = await scope.session.get(PolityRegardRow, (holder.id, subject.id))
    if row is None:
        row = PolityRegardRow(holder_entity_id=holder.id, subject_entity_id=subject.id, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched: list[str] = []
    if command.threat is not None:
        row.threat = command.threat
        touched.append("threat")
    if command.trust is not None:
        row.trust = command.trust
        touched.append("trust")
    if not touched:
        raise ValidationFailedError("Set a threat or a trust.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{holder.name} now feels threat {row.threat} and trust {row.trust} toward {subject.name}.", target_node_id=holder.id)


@player_action("regard:remove", ActionKind.EDIT_RECORD)
async def remove_regard(scope: PlayerScope, command: RegardTarget) -> Effect:
    row = await scope.session.get(PolityRegardRow, (command.holder_id, command.subject_id))
    if row is None:
        raise NotFoundError("That realm holds no regard for the other.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The regard was wiped clean.", target_node_id=command.holder_id)


@player_action("diplomacy:edit", ActionKind.EDIT_RECORD)
async def edit_diplomacy(scope: PlayerScope, command: EditDiplomacy) -> Effect:
    found = await realm(scope, command.polity_id, "The realm")
    row = await scope.session.get(DiplomacyProfileRow, found.id)
    if row is None:
        row = DiplomacyProfileRow(polity_entity_id=found.id, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched: list[str] = []
    for key in ("capacity", "relations", "strain"):
        value = getattr(command, key)
        if value is not None:
            setattr(row, key, value)
            touched.append(key)
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{found.name} keeps {row.relations} relations of a capacity of {row.capacity}.", target_node_id=found.id)


@player_action("crisis:open", ActionKind.EDIT_RECORD)
async def open_crisis(scope: PlayerScope, command: OpenCrisis) -> Effect:
    demander = await realm(scope, command.demander_id, "The demanding realm")
    target = await realm(scope, command.target_id, "The realm under demand")
    if demander.id == target.id:
        raise ValidationFailedError("A realm makes no demand of itself.")
    if command.subject_id is not None and await scope.session.get(NodeRow, command.subject_id) is None:
        raise ValidationFailedError("The subject of the demand must be a thing of the cosmos.")
    row = CrisisRow(
        demander_entity_id=demander.id,
        target_entity_id=target.id,
        demand=command.demand,
        subject_node_id=command.subject_id,
        amount=command.amount,
        opened_epoch=await scope.epoch(),
        locked=[],
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"{demander.name} demands that {target.name} {DEMAND_TEXT[command.demand]}.", target_node_id=demander.id, values={"crisis_id": row.id})


@player_action("crisis:edit", ActionKind.EDIT_RECORD)
async def edit_crisis(scope: PlayerScope, command: EditCrisis) -> Effect:
    row = await crisis_of(scope, command.crisis_id)
    touched: list[str] = []
    if command.escalation is not None:
        row.escalation = command.escalation
        touched.append("escalation")
    if command.amount is not None:
        row.amount = command.amount
        touched.append("amount")
    if command.subject_id is not None:
        if await scope.session.get(NodeRow, command.subject_id) is None:
            raise ValidationFailedError("The subject of the demand must be a thing of the cosmos.")
        row.subject_node_id = command.subject_id
        touched.append("subject_node_id")
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The crisis stands at step {row.escalation}.", target_node_id=row.demander_entity_id)


@player_action("crisis:hold", ActionKind.EDIT_RECORD)
async def hold_crisis(scope: PlayerScope, command: HoldCrisis) -> Effect:
    row = await crisis_of(scope, command.crisis_id)
    row.locked = held(row.locked, CRISIS_FIELDS, command.hold)
    await scope.session.flush()
    return Effect("The crisis is frozen where it stands." if command.hold else "The crisis runs its course again.", target_node_id=row.demander_entity_id)


@player_action("crisis:resolve", ActionKind.EDIT_RECORD)
async def resolve_crisis(scope: PlayerScope, command: ResolveCrisis) -> Effect:
    row = await crisis_of(scope, command.crisis_id)
    if row.state is not CrisisState.ESCALATING:
        raise ValidationFailedError("That crisis is already over.")
    if command.state is CrisisState.ESCALATING:
        raise ValidationFailedError("Choose how the crisis ends.")
    ctx = await manual_context(scope.session, "crisis.resolve")
    await settle(ctx, await RealmBook.load(scope.session), Verdict(row, command.state), CrisisTally())
    await scope.session.flush()
    return Effect(f"The crisis ended: {row.state.value.replace('_', ' ')}.", target_node_id=row.demander_entity_id, values={"state": row.state.value})


@player_action("crisis:delete", ActionKind.EDIT_RECORD)
async def delete_crisis(scope: PlayerScope, command: CrisisTarget) -> Effect:
    row = await crisis_of(scope, command.crisis_id)
    demander = row.demander_entity_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The crisis was struck from the record.", target_node_id=demander)


@player_action("backer:set", ActionKind.EDIT_RECORD)
async def set_backer(scope: PlayerScope, command: SetBacker) -> Effect:
    row = await crisis_of(scope, command.crisis_id)
    backer = await realm(scope, command.backer_id, "The backer")
    if backer.id in (row.demander_entity_id, row.target_entity_id):
        raise ValidationFailedError("The sides of a crisis cannot back it.")
    found = await scope.session.get(CrisisBackerRow, (row.id, backer.id))
    if found is None:
        found = CrisisBackerRow(crisis_id=row.id, backer_entity_id=backer.id, side=command.side)
        scope.session.add(found)
    found.side, found.promised, found.swing, found.locked = command.side, command.promised, command.swing, command.hold
    await scope.session.flush()
    return Effect(f"{backer.name} backs the {command.side.value} for a share of {command.promised}.", target_node_id=backer.id)


@player_action("backer:remove", ActionKind.EDIT_RECORD)
async def remove_backer(scope: PlayerScope, command: BackerTarget) -> Effect:
    found = await scope.session.get(CrisisBackerRow, (command.crisis_id, command.backer_id))
    if found is None:
        raise NotFoundError("That realm does not back this crisis.")
    await scope.session.delete(found)
    await scope.session.flush()
    return Effect("The backer withdrew.", target_node_id=command.backer_id)


@player_action("sphere:set", ActionKind.EDIT_RECORD)
async def set_sphere(scope: PlayerScope, command: SetSphere) -> Effect:
    power = await realm(scope, command.power_id, "The power")
    client = await realm(scope, command.client_id, "The client")
    if power.id == client.id:
        raise ValidationFailedError("A realm is not its own client.")
    found = await scope.session.get(SphereRow, (power.id, client.id))
    if found is None:
        found = SphereRow(power_entity_id=power.id, client_entity_id=client.id, since_epoch=await scope.epoch())
        scope.session.add(found)
    found.strength, found.locked = command.strength, command.hold
    await scope.session.flush()
    return Effect(f"{client.name} stands in the sphere of {power.name} with strength {command.strength}.", target_node_id=power.id)


@player_action("sphere:remove", ActionKind.EDIT_RECORD)
async def remove_sphere(scope: PlayerScope, command: SphereTarget) -> Effect:
    found = await scope.session.get(SphereRow, (command.power_id, command.client_id))
    if found is None:
        raise NotFoundError("That realm is not in this sphere.")
    await scope.session.delete(found)
    await scope.session.flush()
    return Effect("The client slipped out of the sphere.", target_node_id=command.power_id)
