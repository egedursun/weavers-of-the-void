from pydantic import Field
from sqlalchemy import select

from aerona.catalog.tissues import COUNTED_PARTS, DIGIT_LIMBS, digit_keys, digit_label, digit_part
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.tables.body import (
    ARMOUR_COLUMNS,
    CAPACITY_COLUMNS,
    SEVERITY_MAX,
    SEVERITY_MIN,
    BodyCustomRow,
    ConditionRow,
    InjuryRow,
    MaimedCohortRow,
    ProsthesisRow,
)
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mortal import KindVariantRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import (
    BodyBuild,
    BodyFunction,
    BodyPart,
    BodyPlan,
    BodyReading,
    ConditionKind,
    Consciousness,
    DamageType,
    Handedness,
    HarmCause,
    HeightClass,
    InjuryKind,
    InjuryState,
    MaimedKind,
    NerveDamage,
    TissueKind,
    TreatmentStep,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import KindFamily
from aerona.engine.body.book import BODIED, Bearer, anatomy_for, ensure_body
from aerona.engine.body.conditions import end_condition, gain_condition
from aerona.engine.body.customs import CUSTOM_FIELDS, ensure_customs
from aerona.engine.body.digits import full_counts, replan, restore, sync
from aerona.engine.body.healing import INJURY_HOLD, fit_prosthesis, material_workability, mend
from aerona.engine.body.hits import TOTAL_LOSS_KINDS, Harm
from aerona.engine.body.state import PAIN, refresh
from aerona.engine.body.treatment import stanch
from aerona.engine.lifecycle.wounds import apply_hits, wound_sentence
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PART_PATTERN = r"^[a-z][a-z_]*$"
COUNTS = tuple(part for part in COUNTED_PARTS if part not in DIGIT_LIMBS)
DIGITS = frozenset(key for part in DIGIT_LIMBS for key in digit_keys(part))
VITALS = ("blood", "exertion")
EDITABLE = (*CAPACITY_COLUMNS, *ARMOUR_COLUMNS, PAIN, *VITALS, *COUNTS, "hp_max")
CONSCIOUSNESS = "consciousness"
INJURY_FIELDS = (
    "state",
    "severity",
    "function_loss",
    "visible",
    "part",
    "kind",
    "damage_type",
    "infected_epochs",
    "tissue",
    "bleeding",
    "nerve",
    "misdiagnosed",
)


class BearerTarget(Command):
    bearer_id: int


class HealBody(BearerTarget):
    injury_id: int | None = None
    lasting: bool = False


class Maim(BearerTarget):
    part: str = Field(pattern=PART_PATTERN)
    kind: InjuryKind | None = None
    damage_type: DamageType | None = None
    severity: int = Field(ge=SEVERITY_MIN, le=SEVERITY_MAX)
    cause: HarmCause = HarmCause.PLAYER
    lethal: bool = False


class EditInjury(Command):
    injury_id: int
    state: InjuryState | None = None
    severity: int | None = Field(default=None, ge=SEVERITY_MIN, le=SEVERITY_MAX)
    function_loss: int | None = Field(default=None, ge=0, le=PERCENT)
    visible: bool | None = None
    part: BodyPart | None = None
    kind: InjuryKind | None = None
    damage_type: DamageType | None = None
    cause: HarmCause | None = None
    infected_epochs: int | None = Field(default=None, ge=0)
    tissue: TissueKind | None = None
    bleeding: int | None = Field(default=None, ge=0, le=PERCENT)
    nerve: NerveDamage | None = None
    treatments: list[TreatmentStep] | None = None
    misdiagnosed: bool | None = None


class TreatInjury(Command):
    injury_id: int
    step: TreatmentStep


class SetDigit(Command):
    bearer_id: int
    digit: str = Field(pattern=r"^(left|right)_(hand|foot)\.[a-z]+$")
    lost: bool


class SetHandedness(Command):
    bearer_id: int
    handedness: Handedness


class SetConsciousness(Command):
    bearer_id: int
    consciousness: Consciousness
    lock: bool = True


class EditCondition(Command):
    condition_id: int
    severity: int | None = Field(default=None, ge=SEVERITY_MIN, le=SEVERITY_MAX)
    visible: bool | None = None
    part: BodyPart | None = None


class EditProsthesis(Command):
    prosthesis_id: int
    quality: int | None = Field(default=None, ge=0, le=PERCENT)
    restored_pct: int | None = Field(default=None, ge=0, le=PERCENT)
    material: MaterialKind | None = None
    world_material_id: int | None = None


class HoldInjuries(BearerTarget):
    hold: bool = True


class FitProsthesis(Command):
    injury_id: int
    material: MaterialKind
    world_material_id: int | None = None
    quality: int = Field(ge=0, le=PERCENT)
    item_id: int | None = None


class ProsthesisTarget(Command):
    prosthesis_id: int


class AddCondition(BearerTarget):
    kind: ConditionKind
    variant_id: int | None = None
    severity: int = Field(default=SEVERITY_MIN, ge=SEVERITY_MIN, le=SEVERITY_MAX)
    part: str | None = Field(default=None, pattern=PART_PATTERN)


class ConditionTarget(Command):
    condition_id: int


class SetBodyPlan(BearerTarget):
    plan: BodyPlan
    traits: list[BodyFunction] = Field(default_factory=list)


class SetFrame(BearerTarget):
    height_class: HeightClass
    build: BodyBuild


class SetBodyValue(BearerTarget):
    field: str = Field(pattern=PART_PATTERN)
    value: int = Field(ge=0)
    lock: bool = True


class UnlockBodyValue(BearerTarget):
    field: str = Field(pattern=PART_PATTERN)


class SetCustoms(Command):
    people_id: int
    field: str = Field(pattern=PART_PATTERN)
    value: str | bool
    lock: bool = True


class UnlockCustoms(Command):
    people_id: int
    field: str = Field(pattern=PART_PATTERN)


class SetCohort(Command):
    community_id: int
    kind: MaimedKind
    count: int = Field(ge=0)
    veterans: int | None = Field(default=None, ge=0)


async def bearer_of(scope: PlayerScope, node_id: int) -> Bearer:
    session = scope.session
    found: Bearer | None = await session.get(EntityRow, node_id) or await session.get(SonRow, node_id) or await session.get(ForeignGodRow, node_id)
    if found is None:
        raise NotFoundError("No such bearer.")
    if isinstance(found, EntityRow) and found.entity_type not in BODIED:
        raise ValidationFailedError(f"{found.name} has no body.")
    return found


async def _injury(scope: PlayerScope, injury_id: int) -> InjuryRow:
    row = await scope.session.get(InjuryRow, injury_id)
    if row is None:
        raise NotFoundError("No such injury.")
    return row


def _label(text: str) -> str:
    return text.replace("_", " ")


@player_action("body:heal", ActionKind.OTHER)
async def heal_body(scope: PlayerScope, command: HealBody) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    ctx = await scope.context("body_heal")
    if command.injury_id is None:
        mended = await mend(ctx, bearer, lasting=command.lasting)
        if not mended:
            raise ValidationFailedError(f"{bearer.name} has no wounds to heal.")
        return Effect(f"{mended} of {bearer.name}'s wounds were healed.", target_node_id=bearer.id)
    row = await _injury(scope, command.injury_id)
    if row.bearer_node_id != bearer.id:
        raise ValidationFailedError("That injury belongs to someone else.")
    if command.lasting and row.kind in TOTAL_LOSS_KINDS:
        row.kind = InjuryKind.DEEP_CUT
        if row.part in DIGIT_LIMBS:
            restore(await ensure_body(scope.session, scope.rules, bearer, ctx.epoch), row.part, row.digits)
    row.state = InjuryState.HEALED_SCAR
    row.function_loss = 0 if command.lasting else row.function_loss * ctx.rules.healing.scar_residual_pct // PERCENT
    row.infected_epochs = 0
    row.healed_epoch = ctx.epoch
    await refresh(scope.session, scope.rules, bearer, ctx.epoch)
    done = "restored" if command.lasting else "healed"
    return Effect(f"{bearer.name}'s {_label(row.part)} is {done}.", target_node_id=bearer.id)


@player_action("body:maim", ActionKind.OTHER)
async def maim(scope: PlayerScope, command: Maim) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    if isinstance(bearer, EntityRow) and bearer.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError(f"{bearer.name} cannot be wounded.")
    body = await ensure_body(scope.session, scope.rules, bearer, await scope.epoch())
    if anatomy_for(body).part(command.part) is None:
        raise ValidationFailedError(f"{bearer.name}'s body has no {_label(command.part)}.")
    ctx = await scope.context("body_maim")
    harm = Harm(
        command.severity * ctx.rules.injury.severity_step,
        command.cause,
        "was struck down by the hand of the creator",
        damage_type=command.damage_type,
        part=command.part,
        kind=command.kind,
        severity=command.severity,
    )
    wounding = await apply_hits(ctx, bearer, harm, lethal=command.lethal)
    if not wounding.injuries:
        raise ValidationFailedError(f"The blow did not wound {bearer.name}.")
    row = wounding.injuries[0]
    found = anatomy_for(body).part(row.part)
    part = found.label.lower() if found is not None else _label(row.part)
    return Effect(f"{wound_sentence(bearer.name, row.kind, part)}.", target_node_id=bearer.id, values={"injury_id": row.id})


@player_action("body:injury", ActionKind.OTHER)
async def edit_injury(scope: PlayerScope, command: EditInjury) -> Effect:
    row = await _injury(scope, command.injury_id)
    bearer = await bearer_of(scope, row.bearer_node_id)
    for name in INJURY_FIELDS:
        value = getattr(command, name)
        if value is not None:
            setattr(row, name, value)
    if command.cause is not None:
        row.cause_kind = command.cause
    if command.treatments is not None:
        row.treatments = [step.value for step in dict.fromkeys(command.treatments)]
    await refresh(scope.session, scope.rules, bearer, await scope.epoch())
    return Effect(f"The wound to {bearer.name}'s {_label(row.part)} was changed.", target_node_id=bearer.id)


@player_action("body:treat", ActionKind.OTHER)
async def treat_injury(scope: PlayerScope, command: TreatInjury) -> Effect:
    row = await _injury(scope, command.injury_id)
    bearer = await bearer_of(scope, row.bearer_node_id)
    if command.step.value in row.treatments:
        raise ValidationFailedError(f"The wound is already treated with {_label(command.step.value)}.")
    stanch(row, command.step)
    if command.step is TreatmentStep.DIAGNOSE:
        row.misdiagnosed = False
    await refresh(scope.session, scope.rules, bearer, await scope.epoch())
    return Effect(f"The wound to {bearer.name}'s {_label(row.part)} was given {_label(command.step.value)}.", target_node_id=bearer.id)


@player_action("body:digit", ActionKind.OTHER)
async def set_digit(scope: PlayerScope, command: SetDigit) -> Effect:
    if command.digit not in DIGITS:
        raise ValidationFailedError("There is no such finger or toe.")
    bearer = await bearer_of(scope, command.bearer_id)
    epoch = await scope.epoch()
    body = await ensure_body(scope.session, scope.rules, bearer, epoch)
    limb = digit_part(command.digit)
    if limb is None or full_counts(body)[limb] == 0:
        raise ValidationFailedError(f"{bearer.name}'s body has no {_label(limb or command.digit)}.")
    lost = command.digit in body.lost_digits
    if lost == command.lost:
        raise ValidationFailedError(f"{bearer.name}'s {digit_label(command.digit)} is already {'lost' if lost else 'whole'}.")
    body.lost_digits = sorted({*body.lost_digits, command.digit}) if command.lost else [key for key in body.lost_digits if key != command.digit]
    sync(body)
    await refresh(scope.session, scope.rules, bearer, epoch)
    verb = "lost" if command.lost else "has back"
    return Effect(f"{bearer.name} {verb} the {digit_label(command.digit)}.", target_node_id=bearer.id)


@player_action("body:handedness", ActionKind.OTHER)
async def set_handedness(scope: PlayerScope, command: SetHandedness) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    epoch = await scope.epoch()
    body = await ensure_body(scope.session, scope.rules, bearer, epoch)
    body.handedness = command.handedness
    await refresh(scope.session, scope.rules, bearer, epoch)
    lead = "both hands alike" if command.handedness is Handedness.BOTH else f"the {spoken(command.handedness)} hand"
    return Effect(f"{bearer.name} now leads with {lead}.", target_node_id=bearer.id)


@player_action("body:consciousness", ActionKind.OTHER)
async def set_consciousness(scope: PlayerScope, command: SetConsciousness) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    epoch = await scope.epoch()
    body = await ensure_body(scope.session, scope.rules, bearer, epoch)
    body.consciousness = command.consciousness
    locked = set(body.locked)
    if command.lock:
        locked.add(CONSCIOUSNESS)
    else:
        locked.discard(CONSCIOUSNESS)
    body.locked = sorted(locked)
    held = " and held there" if command.lock else ""
    return Effect(f"{bearer.name} is now {_label(command.consciousness.value)}{held}.", target_node_id=bearer.id)


async def world_material(scope: PlayerScope, material_id: int | None) -> WorldMaterialRow | None:
    if material_id is None:
        return None
    found = await scope.session.get(WorldMaterialRow, material_id)
    if found is None:
        raise NotFoundError("No such material.")
    return found


@player_action("body:condition_edit", ActionKind.OTHER)
async def edit_condition(scope: PlayerScope, command: EditCondition) -> Effect:
    row = await scope.session.get(ConditionRow, command.condition_id)
    if row is None:
        raise NotFoundError("No such condition.")
    bearer = await bearer_of(scope, row.bearer_node_id)
    for name in ("severity", "visible", "part"):
        value = getattr(command, name)
        if value is not None:
            setattr(row, name, value)
    await refresh(scope.session, scope.rules, bearer, await scope.epoch())
    return Effect(f"{bearer.name}'s {_label(row.kind.value)} was changed.", target_node_id=bearer.id)


@player_action("body:prosthesis_edit", ActionKind.OTHER)
async def edit_prosthesis(scope: PlayerScope, command: EditProsthesis) -> Effect:
    row = await scope.session.get(ProsthesisRow, command.prosthesis_id)
    if row is None:
        raise NotFoundError("No such prosthesis.")
    bearer = await bearer_of(scope, row.bearer_node_id)
    if command.material is not None:
        row.material = command.material
    if command.world_material_id is not None:
        world = await world_material(scope, command.world_material_id)
        row.world_material_id = world.id if world is not None else None
    if command.quality is not None:
        row.quality = command.quality
    if command.restored_pct is None and (command.quality is not None or command.world_material_id is not None or command.material is not None):
        world = await world_material(scope, row.world_material_id)
        row.restored_pct = min(PERCENT, material_workability(scope.rules.prosthetics, row.material, world) * row.quality // PERCENT)
    if command.restored_pct is not None:
        row.restored_pct = command.restored_pct
    await refresh(scope.session, scope.rules, bearer, await scope.epoch())
    return Effect(f"{bearer.name}'s {_label(row.material.value)} {_label(row.part)} was reworked.", target_node_id=bearer.id)


@player_action("body:injury_hold", ActionKind.OTHER)
async def hold_injuries(scope: PlayerScope, command: HoldInjuries) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    body = await ensure_body(scope.session, scope.rules, bearer, await scope.epoch())
    locked = set(body.locked)
    if command.hold:
        locked.add(INJURY_HOLD)
    else:
        locked.discard(INJURY_HOLD)
    body.locked = sorted(locked)
    verb = "are held as they are" if command.hold else "heal or fester again"
    return Effect(f"{bearer.name}'s wounds {verb}.", target_node_id=bearer.id)


@player_action("body:prosthesis", ActionKind.OTHER)
async def apply_prosthesis(scope: PlayerScope, command: FitProsthesis) -> Effect:
    row = await _injury(scope, command.injury_id)
    bearer = await bearer_of(scope, row.bearer_node_id)
    if not isinstance(bearer, EntityRow):
        raise ValidationFailedError("Gods regrow what they lose; they take no prosthesis.")
    body = await ensure_body(scope.session, scope.rules, bearer, await scope.epoch())
    part = anatomy_for(body).part(row.part)
    if part is None:
        raise ValidationFailedError("That part is not on this body.")
    item = await scope.session.get(EntityRow, command.item_id) if command.item_id is not None else None
    if command.item_id is not None and (item is None or item.entity_type is not EntityType.ITEM):
        raise ValidationFailedError("A prosthesis can only be an item.")
    for prosthesis in await scope.session.scalars(select(ProsthesisRow).where(ProsthesisRow.injury_id == row.id)):
        await scope.session.delete(prosthesis)
    await scope.session.flush()
    ctx = await scope.context("body_prosthesis")
    world = await world_material(scope, command.world_material_id)
    fitted = await fit_prosthesis(ctx, bearer, row, part, command.material, maker=None, quality=command.quality, item=item, world_material=world)
    await refresh(scope.session, scope.rules, bearer, ctx.epoch)
    return Effect(
        f"{bearer.name} now wears {an(_label(command.material.value))} {part.label.lower()}.",
        target_node_id=bearer.id,
        values={"prosthesis_id": fitted.id},
    )


@player_action("body:prosthesis_remove", ActionKind.OTHER)
async def remove_prosthesis(scope: PlayerScope, command: ProsthesisTarget) -> Effect:
    row = await scope.session.get(ProsthesisRow, command.prosthesis_id)
    if row is None:
        raise NotFoundError("No such prosthesis.")
    bearer = await bearer_of(scope, row.bearer_node_id)
    await scope.session.delete(row)
    await scope.session.flush()
    await refresh(scope.session, scope.rules, bearer, await scope.epoch())
    return Effect(f"{bearer.name}'s {_label(row.material.value)} {_label(row.part)} was taken away.", target_node_id=bearer.id)


@player_action("body:condition", ActionKind.OTHER)
async def add_condition(scope: PlayerScope, command: AddCondition) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    ctx = await scope.context("body_condition")
    row = await gain_condition(ctx, bearer, command.kind, HarmCause.PLAYER, severity=command.severity, part=command.part, announce=False)
    if row is None:
        raise ValidationFailedError("The condition did not take hold.")
    if command.variant_id is not None:
        variant = await scope.session.get(KindVariantRow, command.variant_id)
        if variant is None or variant.family is not KindFamily.CONDITION or variant.base != command.kind.value:
            raise ValidationFailedError(f"That is not a kind of {_label(command.kind.value)}.")
        row.variant_id = variant.id
    return Effect(f"{bearer.name} now lives with {_label(command.kind.value)}.", target_node_id=bearer.id, values={"condition_id": row.id})


@player_action("body:condition_end", ActionKind.OTHER)
async def end_condition_action(scope: PlayerScope, command: ConditionTarget) -> Effect:
    row = await scope.session.get(ConditionRow, command.condition_id)
    if row is None or row.ended_epoch is not None:
        raise NotFoundError("No such lasting condition.")
    bearer = await bearer_of(scope, row.bearer_node_id)
    ctx = await scope.context("body_condition_end")
    await end_condition(ctx, bearer, row.kind, announce=False)
    return Effect(f"{bearer.name} is free of {_label(row.kind.value)}.", target_node_id=bearer.id)


@player_action("body:plan", ActionKind.OTHER)
async def set_plan(scope: PlayerScope, command: SetBodyPlan) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    epoch = await scope.epoch()
    body = await ensure_body(scope.session, scope.rules, bearer, epoch)
    replan(body, command.plan, sorted({trait.value for trait in command.traits}))
    if not isinstance(bearer, EntityRow) or bearer.entity_type is EntityType.MORTAL:
        await refresh(scope.session, scope.rules, bearer, epoch)
    return Effect(f"{bearer.name} now has {an(_label(command.plan.value))} body.", target_node_id=bearer.id)


@player_action("body:frame", ActionKind.OTHER)
async def set_frame(scope: PlayerScope, command: SetFrame) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    body = await ensure_body(scope.session, scope.rules, bearer, await scope.epoch())
    body.height_class, body.build = command.height_class, command.build
    return Effect(f"{bearer.name} is now {spoken(command.height_class)} and {spoken(command.build)} of build.", target_node_id=bearer.id)


@player_action("body:set", ActionKind.OTHER)
async def set_body_value(scope: PlayerScope, command: SetBodyValue) -> Effect:
    if command.field not in EDITABLE:
        raise ValidationFailedError(f"{_label(command.field)} cannot be set by hand.")
    bearer = await bearer_of(scope, command.bearer_id)
    epoch = await scope.epoch()
    body = await ensure_body(scope.session, scope.rules, bearer, epoch)
    ceiling = full_counts(body)[command.field] if command.field in COUNTS else (PERCENT if command.field in (*ARMOUR_COLUMNS, PAIN, *VITALS) else None)
    value = min(command.value, ceiling) if ceiling is not None else command.value
    setattr(body, command.field, value)
    locked = set(body.locked)
    if command.lock and command.field not in (*COUNTS, "hp_max"):
        locked.add(command.field)
    body.locked = sorted(locked)
    held = " and held there" if command.field in locked else ""
    return Effect(f"{bearer.name}'s {_label(command.field)} is now {value}{held}.", target_node_id=bearer.id)


@player_action("body:unlock", ActionKind.OTHER)
async def unlock_body_value(scope: PlayerScope, command: UnlockBodyValue) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    epoch = await scope.epoch()
    body = await ensure_body(scope.session, scope.rules, bearer, epoch)
    if command.field not in body.locked:
        raise ValidationFailedError(f"{bearer.name}'s {_label(command.field)} is not held.")
    body.locked = [field for field in body.locked if field != command.field]
    await refresh(scope.session, scope.rules, bearer, epoch)
    return Effect(f"{bearer.name}'s {_label(command.field)} follows their body again.", target_node_id=bearer.id)


async def _people(scope: PlayerScope, people_id: int) -> EntityRow:
    people = await scope.session.get(EntityRow, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE:
        raise NotFoundError("No such people.")
    return people


@player_action("body:customs", ActionKind.OTHER)
async def set_customs(scope: PlayerScope, command: SetCustoms) -> Effect:
    people = await _people(scope, command.people_id)
    if command.field not in CUSTOM_FIELDS:
        raise ValidationFailedError(f"{_label(command.field)} is not a custom of the body.")
    custom: BodyCustomRow = await ensure_customs(scope.session, scope.rules, people)
    if command.field == "reading":
        custom.reading = BodyReading(str(command.value))
    elif isinstance(command.value, bool):
        setattr(custom, command.field, command.value)
    else:
        raise ValidationFailedError(f"{_label(command.field)} is either kept or not.")
    locked = set(custom.locked)
    if command.lock:
        locked.add(command.field)
    custom.locked = sorted(locked)
    return Effect(f"{people.name}'s {_label(command.field)} is now {_label(str(getattr(custom, command.field)).lower())}.", target_node_id=people.id)


@player_action("body:customs_unlock", ActionKind.OTHER)
async def unlock_customs(scope: PlayerScope, command: UnlockCustoms) -> Effect:
    people = await _people(scope, command.people_id)
    custom = await ensure_customs(scope.session, scope.rules, people)
    if command.field not in custom.locked:
        raise ValidationFailedError(f"{people.name}'s {_label(command.field)} is not held.")
    custom.locked = [field for field in custom.locked if field != command.field]
    return Effect(f"{people.name}'s {_label(command.field)} may change on its own again.", target_node_id=people.id)


@player_action("body:cohort", ActionKind.OTHER)
async def set_cohort(scope: PlayerScope, command: SetCohort) -> Effect:
    community = await scope.session.get(EntityRow, command.community_id)
    if community is None or community.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
        raise NotFoundError("No such community.")
    epoch = await scope.epoch()
    row = await scope.session.get(MaimedCohortRow, (community.id, command.kind))
    if row is None:
        row = MaimedCohortRow(community_entity_id=community.id, kind=command.kind, count=0, veterans=0, updated_epoch=epoch)
        scope.session.add(row)
    row.count = command.count
    row.veterans = min(command.count, command.veterans if command.veterans is not None else row.veterans)
    row.updated_epoch = epoch
    return Effect(f"The {_label(command.kind.value)} of {community.name} now number {command.count}.", target_node_id=community.id)
