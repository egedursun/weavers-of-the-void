from pydantic import Field
from sqlalchemy import select

from aerona.catalog.intrigue import FAVOUR_LABELS, HOOK_DEMAND_LABELS, IDENTITY_LABELS, PHASE_LABELS, SCHEMES, SECRETS, belief_label
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SCHEME_FIELDS, SECRET_FIELDS, BeliefRow, FavourRow, HookRow, IdentityRow, SchemeRow, SecretRow, TrueNameRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, HookDemand, HookSource, HookStrength, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.engine.intrigue.favours import call_favour, owe, use_hook
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.names import name_bearer, rename, teach_name
from aerona.engine.intrigue.schemes import begin_scheme
from aerona.engine.intrigue.secrets import expose, grant_hook, keep_secret
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class KeepSecret(Command):
    holder_id: int
    kind: IntrigueSecret
    about_id: int | None = None
    severity: int | None = Field(default=None, ge=0, le=SPAN)
    known_by: list[int] = Field(default_factory=list)


class SecretTarget(Command):
    secret_id: int


class EditSecret(Command):
    secret_id: int
    severity: int | None = Field(default=None, ge=0, le=SPAN)
    known_by: list[int] | None = None
    hold: bool = True


class GrantHook(Command):
    holder_id: int
    target_id: int
    strength: HookStrength = HookStrength.WEAK
    source: HookSource = HookSource.SECRET


class HookTarget(Command):
    hook_id: int


class EditHook(Command):
    hook_id: int
    strength: HookStrength | None = None
    last_demand: HookDemand | None = None
    clear_demand: bool = False
    hold: bool = True


class UseHook(Command):
    hook_id: int
    demand: HookDemand


class OweFavour(Command):
    owed_by_id: int
    owed_to_id: int
    magnitude: int = Field(default=20, ge=1, le=SPAN)
    origin: FavourOrigin = FavourOrigin.GIFT


class FavourTarget(Command):
    favour_id: int


class EditFavour(Command):
    favour_id: int
    magnitude: int | None = Field(default=None, ge=1, le=SPAN)
    hold: bool = True


class CallFavour(Command):
    favour_id: int
    honour: bool = True


class AssumeIdentity(Command):
    mortal_id: int
    false_name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    reason: IdentityReason = IdentityReason.EXILE
    cover_role: str | None = Field(default=None, max_length=60)
    community_id: int | None = None


class IdentityTarget(Command):
    mortal_id: int


class EditIdentity(Command):
    mortal_id: int
    false_name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    cover_role: str | None = Field(default=None, max_length=60)
    community_id: int | None = None
    exposure: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class BeginScheme(Command):
    owner_id: int
    kind: PlotKind
    target_id: int | None = None


class SchemeTarget(Command):
    scheme_id: int


class EditScheme(Command):
    scheme_id: int
    phase: SchemePhase | None = None
    power: int | None = Field(default=None, ge=0, le=10000)
    secrecy: int | None = Field(default=None, ge=0, le=SPAN)
    progress: int | None = Field(default=None, ge=0, le=SPAN)
    agents: list[int] | None = None
    discovered_by: list[int] | None = None
    hold: bool = True


class SetTrueName(Command):
    bearer_id: int
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    language_id: int | None = None
    hold: bool = True


class TrueNameTarget(Command):
    bearer_id: int


class TeachTrueName(Command):
    bearer_id: int
    learner_id: int
    forget: bool = False


class SetBelief(Command):
    holder_id: int
    subject_id: int
    attribute: str = Field(min_length=1, max_length=60)
    value: int
    confidence: int = Field(default=80, ge=0, le=SPAN)
    source: BeliefSource = BeliefSource.OBSERVATION
    false: bool = False
    hold: bool = True


class BeliefTarget(Command):
    belief_id: int


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def node(scope: PlayerScope, node_id: int | None, label: str) -> NodeRow:
    found = await scope.session.get(NodeRow, node_id) if node_id is not None else None
    if found is None:
        raise ValidationFailedError(f"{label} must be a living thing of the cosmos.")
    return found


async def nodes(scope: PlayerScope, ids: list[int]) -> list[int]:
    for node_id in ids:
        await node(scope, node_id, "Everyone who knows")
    return sorted(set(ids))


async def found_row[T](scope: PlayerScope, table: type[T], key: int, label: str) -> T:
    row = await scope.session.get(table, key)
    if row is None:
        raise NotFoundError(f"No such {label}.")
    return row


async def mortal(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can live under a false name.")
    return found


@player_action("secret:keep", ActionKind.EDIT_RECORD)
async def keep(scope: PlayerScope, command: KeepSecret) -> Effect:
    holder = await node(scope, command.holder_id, "The holder")
    if command.about_id is not None:
        await node(scope, command.about_id, "What the secret concerns")
    ctx = await manual_context(scope.session, "secret.keep")
    row = await keep_secret(
        ctx, holder.id, command.kind, about_id=command.about_id, severity=command.severity, known_by=tuple(await nodes(scope, command.known_by))
    )
    if row is None:
        raise ValidationFailedError(f"{holder.name} is held against change.")
    return Effect(f"{holder.name} now keeps {SECRETS[command.kind].label.lower()}.", target_node_id=holder.id, values={"secret_id": row.id})


@player_action("secret:edit", ActionKind.EDIT_RECORD)
async def edit_secret(scope: PlayerScope, command: EditSecret) -> Effect:
    row = await found_row(scope, SecretRow, command.secret_id, "secret")
    touched: list[str] = []
    if command.severity is not None:
        row.severity = command.severity
        touched.append("severity")
    if command.known_by is not None:
        row.known_by = sorted({row.holder_node_id, *await nodes(scope, command.known_by)})
        touched.append("known_by")
    if not touched:
        raise ValidationFailedError("Set the weight or who knows.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{SECRETS[row.kind].label}: weight {row.severity}, known to {len(row.known_by)}.", target_node_id=row.holder_node_id)


@player_action("secret:hold", ActionKind.EDIT_RECORD)
async def hold_secret(scope: PlayerScope, command: EditSecret) -> Effect:
    row = await found_row(scope, SecretRow, command.secret_id, "secret")
    row.locked = held(row.locked, list(SECRET_FIELDS), command.hold)
    await scope.session.flush()
    return Effect("The secret is held as it stands." if command.hold else "The secret moves with the world again.", target_node_id=row.holder_node_id)


@player_action("secret:expose", ActionKind.EDIT_RECORD)
async def reveal(scope: PlayerScope, command: SecretTarget) -> Effect:
    row = await found_row(scope, SecretRow, command.secret_id, "secret")
    if not await expose(await manual_context(scope.session, "secret.expose"), row):
        raise ValidationFailedError("That secret is already out, held, or its keeper is held.")
    return Effect(f"{SECRETS[row.kind].label} came to light.", target_node_id=row.holder_node_id)


@player_action("secret:delete", ActionKind.EDIT_RECORD)
async def delete_secret(scope: PlayerScope, command: SecretTarget) -> Effect:
    row = await found_row(scope, SecretRow, command.secret_id, "secret")
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The secret was struck from the world.", target_node_id=holder)


@player_action("hook:grant", ActionKind.EDIT_RECORD)
async def grant(scope: PlayerScope, command: GrantHook) -> Effect:
    holder = await node(scope, command.holder_id, "The holder")
    target = await node(scope, command.target_id, "The target")
    if holder.id == target.id:
        raise ValidationFailedError("No one holds a hook on themselves.")
    ctx = await manual_context(scope.session, "hook.grant")
    row = await grant_hook(ctx, holder.id, target.id, command.source, strong=command.strength is HookStrength.STRONG)
    if row is None:
        raise ValidationFailedError(f"{holder.name} is held against change.")
    row.strength, row.source = command.strength, command.source
    await scope.session.flush()
    return Effect(f"{holder.name} now holds {an(command.strength.value)} hook on {target.name}.", target_node_id=holder.id, values={"hook_id": row.id})


@player_action("hook:edit", ActionKind.EDIT_RECORD)
async def edit_hook(scope: PlayerScope, command: EditHook) -> Effect:
    row = await found_row(scope, HookRow, command.hook_id, "hook")
    if command.strength is not None:
        row.strength = command.strength
    if command.last_demand is not None:
        row.last_demand = command.last_demand
    elif command.clear_demand:
        row.last_demand = None
    row.locked = command.hold
    await scope.session.flush()
    return Effect(f"The hook is {row.strength.value}{' and held' if row.locked else ''}.", target_node_id=row.holder_node_id)


@player_action("hook:use", ActionKind.EDIT_RECORD)
async def press(scope: PlayerScope, command: UseHook) -> Effect:
    row = await found_row(scope, HookRow, command.hook_id, "hook")
    if row.used_epoch is not None:
        raise ValidationFailedError("That hook is already spent.")
    complied = await use_hook(await manual_context(scope.session, "hook.use"), row, command.demand)
    await scope.session.flush()
    verdict = "complied" if complied else "refused"
    return Effect(f"Pressed to {HOOK_DEMAND_LABELS[command.demand].lower()}, the target {verdict}.", target_node_id=row.holder_node_id)


@player_action("hook:delete", ActionKind.EDIT_RECORD)
async def delete_hook(scope: PlayerScope, command: HookTarget) -> Effect:
    row = await found_row(scope, HookRow, command.hook_id, "hook")
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The hook was broken.", target_node_id=holder)


@player_action("favour:owe", ActionKind.EDIT_RECORD)
async def indebt(scope: PlayerScope, command: OweFavour) -> Effect:
    debtor = await node(scope, command.owed_by_id, "The debtor")
    creditor = await node(scope, command.owed_to_id, "The creditor")
    if debtor.id == creditor.id:
        raise ValidationFailedError("No one owes a favour to themselves.")
    row = await owe(await manual_context(scope.session, "favour.owe"), debtor.id, creditor.id, command.origin, command.magnitude)
    if row is None:
        raise ValidationFailedError(f"{debtor.name} is held against change.")
    return Effect(
        f"{debtor.name} owes {creditor.name} a favour for {FAVOUR_LABELS[command.origin].lower()}.", target_node_id=debtor.id, values={"favour_id": row.id}
    )


@player_action("favour:edit", ActionKind.EDIT_RECORD)
async def edit_favour(scope: PlayerScope, command: EditFavour) -> Effect:
    row = await found_row(scope, FavourRow, command.favour_id, "favour")
    if command.magnitude is not None:
        row.magnitude = command.magnitude
    row.locked = command.hold
    await scope.session.flush()
    return Effect(f"The favour weighs {row.magnitude}{' and is held' if row.locked else ''}.", target_node_id=row.owed_by_node_id)


@player_action("favour:call", ActionKind.EDIT_RECORD)
async def call(scope: PlayerScope, command: CallFavour) -> Effect:
    row = await found_row(scope, FavourRow, command.favour_id, "favour")
    if row.called_epoch is not None:
        raise ValidationFailedError("That favour was already called.")
    row.locked = False
    await call_favour(await manual_context(scope.session, "favour.call"), row, honour=command.honour)
    await scope.session.flush()
    return Effect("The favour was honoured." if command.honour else "The favour was refused.", target_node_id=row.owed_by_node_id)


@player_action("favour:delete", ActionKind.EDIT_RECORD)
async def delete_favour(scope: PlayerScope, command: FavourTarget) -> Effect:
    row = await found_row(scope, FavourRow, command.favour_id, "favour")
    debtor = row.owed_by_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The favour was forgiven and forgotten.", target_node_id=debtor)


@player_action("identity:assume", ActionKind.EDIT_RECORD)
async def mask(scope: PlayerScope, command: AssumeIdentity) -> Effect:
    holder = await mortal(scope, command.mortal_id)
    if command.community_id is not None:
        await node(scope, command.community_id, "The community")
    row = await assume(
        await manual_context(scope.session, "identity.assume"),
        holder,
        command.reason,
        command.false_name,
        cover_role=command.cover_role,
        community_id=command.community_id,
    )
    if row is None:
        raise ValidationFailedError(f"{holder.name} already lives under a false name or is held.")
    return Effect(f"{holder.name} now lives as {command.false_name}: {IDENTITY_LABELS[command.reason].lower()}.", target_node_id=holder.id)


@player_action("identity:edit", ActionKind.EDIT_RECORD)
async def edit_identity(scope: PlayerScope, command: EditIdentity) -> Effect:
    row = await found_row(scope, IdentityRow, command.mortal_id, "false identity")
    touched: list[str] = []
    if command.false_name is not None:
        row.false_name = command.false_name
        touched.append("false_name")
    if command.cover_role is not None:
        row.cover_role = command.cover_role
        touched.append("cover_role")
    if command.community_id is not None:
        row.community_node_id = (await node(scope, command.community_id, "The community")).id
        touched.append("community_node_id")
    if command.exposure is not None:
        row.exposure = command.exposure
        touched.append("exposure")
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"Living as {row.false_name}, {row.exposure}% exposed.", target_node_id=row.mortal_node_id)


@player_action("identity:unmask", ActionKind.EDIT_RECORD)
async def unmask_identity(scope: PlayerScope, command: IdentityTarget) -> Effect:
    row = await found_row(scope, IdentityRow, command.mortal_id, "false identity")
    if row.exposed_epoch is not None:
        raise ValidationFailedError("That false name is already seen through.")
    ctx = await manual_context(scope.session, "identity.unmask")
    row.exposure, row.exposed_epoch = SPAN, ctx.epoch
    for secret in await scope.session.scalars(
        select(SecretRow).where(SecretRow.holder_node_id == row.mortal_node_id, SecretRow.kind == IntrigueSecret.FALSE_IDENTITY)
    ):
        await expose(ctx, secret)
    await scope.session.flush()
    return Effect(f"The mask of {row.false_name} fell away.", target_node_id=row.mortal_node_id)


@player_action("identity:delete", ActionKind.EDIT_RECORD)
async def delete_identity(scope: PlayerScope, command: IdentityTarget) -> Effect:
    row = await found_row(scope, IdentityRow, command.mortal_id, "false identity")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The false name was struck; the mortal lives under their own again.", target_node_id=command.mortal_id)


@player_action("scheme:begin", ActionKind.EDIT_RECORD)
async def plot(scope: PlayerScope, command: BeginScheme) -> Effect:
    owner = await scope.session.get(EntityRow, command.owner_id)
    if owner is None:
        raise ValidationFailedError("The schemer must be a living record.")
    target = await scope.session.get(EntityRow, command.target_id) if command.target_id is not None else None
    if SCHEMES[command.kind].needs_target and target is None:
        raise ValidationFailedError(f"{an(SCHEMES[command.kind].label.lower(), capital=True)} needs a target.")
    row = await begin_scheme(await manual_context(scope.session, "scheme.begin"), owner, command.kind, target)
    if row is None:
        raise ValidationFailedError("The schemer or the target is held against change.")
    return Effect(f"{owner.name} began {an(SCHEMES[command.kind].label.lower())}.", target_node_id=owner.id, values={"scheme_id": row.id})


@player_action("scheme:edit", ActionKind.EDIT_RECORD)
async def edit_scheme(scope: PlayerScope, command: EditScheme) -> Effect:
    row = await found_row(scope, SchemeRow, command.scheme_id, "scheme")
    touched = [name for name in ("phase", "power", "secrecy", "progress") if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if command.agents is not None:
        for agent in command.agents:
            await mortal(scope, agent)
        row.agents = sorted(set(command.agents))
        touched.append("agents")
    if command.discovered_by is not None:
        for finder in command.discovered_by:
            if await scope.session.get(NodeRow, finder) is None:
                raise ValidationFailedError("No such record.")
        row.discovered_by = sorted(set(command.discovered_by))
        touched.append("discovered_by")
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{SCHEMES[row.kind].label}: {PHASE_LABELS[row.phase].lower()}, power {row.power}, secrecy {row.secrecy}.", target_node_id=row.owner_node_id)


@player_action("scheme:hold", ActionKind.EDIT_RECORD)
async def hold_scheme(scope: PlayerScope, command: EditScheme) -> Effect:
    row = await found_row(scope, SchemeRow, command.scheme_id, "scheme")
    row.locked = held(row.locked, list(SCHEME_FIELDS), command.hold)
    await scope.session.flush()
    return Effect("The scheme is frozen where it stands." if command.hold else "The scheme moves again.", target_node_id=row.owner_node_id)


@player_action("scheme:delete", ActionKind.EDIT_RECORD)
async def delete_scheme(scope: PlayerScope, command: SchemeTarget) -> Effect:
    row = await found_row(scope, SchemeRow, command.scheme_id, "scheme")
    owner = row.owner_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The scheme was erased from the world.", target_node_id=owner)


@player_action("true_name:set", ActionKind.EDIT_RECORD)
async def name_truly(scope: PlayerScope, command: SetTrueName) -> Effect:
    bearer = await node(scope, command.bearer_id, "The bearer")
    if command.language_id is not None:
        await node(scope, command.language_id, "The language")
    ctx = await manual_context(scope.session, "true_name.set")
    row = await scope.session.get(TrueNameRow, bearer.id)
    if row is None:
        if command.name is None:
            raise ValidationFailedError("Give the true name.")
        row = await name_bearer(ctx, bearer.id, command.name, command.language_id)
        if row is None:
            raise ValidationFailedError(f"{bearer.name} is held against change.")
    elif not await rename(ctx, Namer(scope.session, ctx.rules), row, cause="by the Creator's word", name=command.name):
        raise ValidationFailedError("No new true name could be found in any tongue of its world.")
    if command.language_id is not None:
        row.language_node_id = command.language_id
    row.locked = held(row.locked, ["name"], command.hold)
    await scope.session.flush()
    return Effect(f"The true name of {bearer.name} is {row.name}.", target_node_id=bearer.id)


@player_action("true_name:teach", ActionKind.EDIT_RECORD)
async def teach(scope: PlayerScope, command: TeachTrueName) -> Effect:
    row = await found_row(scope, TrueNameRow, command.bearer_id, "true name")
    learner = await node(scope, command.learner_id, "The learner")
    if command.forget:
        if learner.id == row.bearer_node_id:
            raise ValidationFailedError("A bearer never forgets their own true name.")
        row.known_by = [known for known in row.known_by if known != learner.id]
        for hook in await scope.session.scalars(
            select(HookRow).where(HookRow.holder_node_id == learner.id, HookRow.target_node_id == row.bearer_node_id, HookRow.source == HookSource.TRUE_NAME)
        ):
            await scope.session.delete(hook)
        await scope.session.flush()
        return Effect(f"{learner.name} forgot the true name.", target_node_id=row.bearer_node_id)
    if not await teach_name(await manual_context(scope.session, "true_name.teach"), row, learner.id):
        raise ValidationFailedError(f"{learner.name} already knows it, or the list of knowers is held.")
    await scope.session.flush()
    return Effect(f"{learner.name} learned the true name and holds a strong hook on its bearer.", target_node_id=row.bearer_node_id)


@player_action("true_name:delete", ActionKind.EDIT_RECORD)
async def delete_true_name(scope: PlayerScope, command: TrueNameTarget) -> Effect:
    row = await found_row(scope, TrueNameRow, command.bearer_id, "true name")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The true name was struck; the bearer goes nameless in the deep tongue.", target_node_id=command.bearer_id)


@player_action("belief:set", ActionKind.EDIT_RECORD)
async def set_belief(scope: PlayerScope, command: SetBelief) -> Effect:
    holder = await node(scope, command.holder_id, "The believer")
    subject = await node(scope, command.subject_id, "The subject")
    epoch = await scope.epoch()
    row = await scope.session.scalar(
        select(BeliefRow)
        .where(BeliefRow.holder_node_id == holder.id, BeliefRow.subject_node_id == subject.id, BeliefRow.attribute == command.attribute)
        .limit(1)
    )
    if row is None:
        row = BeliefRow(
            holder_node_id=holder.id, subject_node_id=subject.id, attribute=command.attribute, value=command.value, source=command.source, locked=[]
        )
        scope.session.add(row)
    row.value, row.confidence, row.as_of_epoch, row.source, row.false = command.value, command.confidence, epoch, command.source, command.false
    row.locked = held(row.locked, ["value"], command.hold)
    await scope.session.flush()
    label = belief_label(command.attribute)
    return Effect(
        f"{holder.name} now believes the {label.lower()} of {subject.name} is {command.value} ({command.confidence}% sure).", target_node_id=holder.id
    )


@player_action("belief:delete", ActionKind.EDIT_RECORD)
async def delete_belief(scope: PlayerScope, command: BeliefTarget) -> Effect:
    row = await found_row(scope, BeliefRow, command.belief_id, "belief")
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The belief was wiped from their mind.", target_node_id=holder)
