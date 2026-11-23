from typing import Literal

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import KIN_BOND_KINDS, BondKind, BondState
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import MemoryKind, Profession
from aerona.domain.enums.mortal import CareerPath, CrimeKind, DeathCause, EquipmentSlot, LifeStage, MarriageEnd, PunishmentKind
from aerona.domain.enums.unions import UnionForm, UnionPurpose
from aerona.domain.models.entity_stats import MortalStats, revised
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.equipment import SLOT_CLASSES, SLOT_COLUMNS, fits_slot
from aerona.engine.mortal.justice import sentence
from aerona.engine.mortal.kinship import betroth, end_marriage, marriage_between, marry
from aerona.engine.mortal.profile import ensure_equipment, ensure_profile
from aerona.engine.primitives.queries import connect, remove_flag
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PERCENT_FIELDS = ("fertility", "health", "stress", "wealth", "renown", "honour", "infamy", "education", "loyalty_liege", "loyalty_community", "loyalty_god")
NULLABLE_PERCENT = ("legitimacy",)
CHOICE_FIELDS: dict[str, type[LifeStage] | type[CareerPath] | type[DeathCause] | type[Profession]] = {
    "life_stage": LifeStage,
    "career": CareerPath,
    "cause_of_death": DeathCause,
    "profession": Profession,
}
NODE_FIELDS = ("polity_id", "death_place_id")
FORCED_NOTE = "a marriage forced upon them"
Value = int | str | None


class MortalTarget(Command):
    mortal_id: int


class SetMortal(MortalTarget):
    field: str = Field(pattern=r"^[a-z_]+$")
    value: Value = None
    hold: bool = True


class ReleaseMortal(MortalTarget):
    field: str = Field(pattern=r"^[a-z_]+$")


class SetSex(MortalTarget):
    sex: SexKind


class PairCommand(Command):
    first_id: int
    second_id: int


class ForceMarriage(PairCommand):
    form: UnionForm = UnionForm.PAIR
    purpose: UnionPurpose = UnionPurpose.KINSHIP
    forced: bool = True


class MarriageTarget(Command):
    marriage_id: int


class EndMarriage(MarriageTarget):
    cause: MarriageEnd = MarriageEnd.DIVORCE


class EditMarriage(MarriageTarget):
    form: UnionForm | None = None
    purpose: UnionPurpose | None = None
    treaty_id: int | None = None
    start_epoch: int | None = Field(default=None, ge=0)


class KinBond(Command):
    source_id: int
    target_id: int
    kind: Literal["parent_of", "spouse_of", "betrothed_to", "concubine_of", "fostered_by", "sworn_kin"]


class KinBondTarget(Command):
    bond_id: int


class Equip(MortalTarget):
    slot: EquipmentSlot
    item_id: int | None = None
    hold: bool = True


class ReleaseSlot(MortalTarget):
    slot: EquipmentSlot


class Sentence(MortalTarget):
    crime: CrimeKind
    punishment: PunishmentKind
    judge_id: int | None = None


class Pardon(MortalTarget):
    return_to_id: int | None = None


def label(text: str) -> str:
    return text.replace("_", " ")


async def mortal_of(scope: PlayerScope, mortal_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, mortal_id)
    if found is None or found.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such mortal.")
    return found


def coerce(field: str, value: Value) -> object:
    if field in PERCENT_FIELDS:
        if not isinstance(value, int) or not 0 <= value <= PERCENT:
            raise ValidationFailedError(f"{label(field)} must be between 0 and {PERCENT}.")
        return value
    if field in NULLABLE_PERCENT:
        if value is not None and (not isinstance(value, int) or not 0 <= value <= PERCENT):
            raise ValidationFailedError(f"{label(field)} must be between 0 and {PERCENT}.")
        return value
    if field in CHOICE_FIELDS:
        if value is None:
            return None
        try:
            return CHOICE_FIELDS[field](str(value))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a known {label(field)}.") from error
    if field in NODE_FIELDS:
        if value is not None and not isinstance(value, int):
            raise ValidationFailedError(f"{label(field)} must name a record.")
        return value
    raise ValidationFailedError(f"{label(field)} cannot be set by hand.")


def hold(row_locked: list[str] | None, field: str, held: bool) -> list[str]:
    locked = set(row_locked or [])
    if held:
        locked.add(field)
    else:
        locked.discard(field)
    return sorted(locked)


@player_action("mortal:set", ActionKind.OTHER)
async def set_mortal(scope: PlayerScope, command: SetMortal) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    value = coerce(command.field, command.value)
    if command.field in NODE_FIELDS and isinstance(value, int) and await scope.session.get(EntityRow, value) is None:
        raise ValidationFailedError("That record does not exist.")
    profile, _ = await ensure_profile(scope.session, mortal.id, await scope.epoch())
    setattr(profile, command.field, value)
    profile.locked = hold(profile.locked, command.field, command.hold)
    shown = label(str(getattr(value, "value", value))) if value is not None else "nothing"
    held = " and held there" if command.hold else ""
    return Effect(f"{mortal.name}'s {label(command.field)} is now {shown}{held}.", target_node_id=mortal.id)


@player_action("mortal:release", ActionKind.OTHER)
async def release_mortal(scope: PlayerScope, command: ReleaseMortal) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    profile, _ = await ensure_profile(scope.session, mortal.id, await scope.epoch())
    if command.field not in (profile.locked or []):
        raise ValidationFailedError(f"{mortal.name}'s {label(command.field)} is not held.")
    profile.locked = hold(profile.locked, command.field, False)
    return Effect(f"{mortal.name}'s {label(command.field)} follows their life again.", target_node_id=mortal.id)


@player_action("mortal:sex", ActionKind.OTHER)
async def set_sex(scope: PlayerScope, command: SetSex) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    if not isinstance(mortal.stats, MortalStats):
        raise ValidationFailedError("Only mortals have a sex.")
    mortal.stats = revised(mortal.stats, {"sex": command.sex.value})
    return Effect(f"{mortal.name} is now {spoken(command.sex)}.", target_node_id=mortal.id)


async def pair(scope: PlayerScope, command: PairCommand) -> tuple[EntityRow, EntityRow]:
    if command.first_id == command.second_id:
        raise ValidationFailedError("A bond needs two different mortals.")
    return await mortal_of(scope, command.first_id), await mortal_of(scope, command.second_id)


@player_action("kin:betroth", ActionKind.OTHER)
async def set_betrothal(scope: PlayerScope, command: PairCommand) -> Effect:
    first, second = await pair(scope, command)
    await betroth(scope.session, first, second, await scope.epoch(), description="promised by the gods")
    return Effect(f"{first.name} is now promised to {second.name}.", target_node_id=first.id)


@player_action("kin:marry", ActionKind.OTHER)
async def force_marriage(scope: PlayerScope, command: ForceMarriage) -> Effect:
    first, second = await pair(scope, command)
    if await marriage_between(scope.session, first.id, second.id) is not None:
        raise ValidationFailedError(f"{first.name} and {second.name} are already wed.")
    epoch = await scope.epoch()
    row = await marry(
        scope.session,
        first,
        second,
        epoch,
        form=command.form,
        purpose=command.purpose,
        forced=command.forced,
        description=FORCED_NOTE if command.forced else None,
    )
    if command.forced:
        bitterness = -scope.rules.kinship.forced_marriage_magnitude
        for holder, subject in ((first.id, second.id), (second.id, first.id)):
            await remember(
                scope.session, scope.rules, holder_id=holder, subject_id=subject, kind=MemoryKind.ILL_WILL, magnitude=bitterness, epoch=epoch, note=FORCED_NOTE
            )
    verb = "were forced to wed" if command.forced else "were wed"
    return Effect(f"{first.name} and {second.name} {verb}.", target_node_id=first.id, values={"marriage_id": row.id})


async def marriage_row(scope: PlayerScope, marriage_id: int) -> MarriageRow:
    row = await scope.session.get(MarriageRow, marriage_id)
    if row is None:
        raise NotFoundError("No such marriage.")
    return row


@player_action("kin:end_marriage", ActionKind.OTHER)
async def end_marriage_action(scope: PlayerScope, command: EndMarriage) -> Effect:
    row = await marriage_row(scope, command.marriage_id)
    if row.end_epoch is not None:
        raise ValidationFailedError("That marriage has already ended.")
    await end_marriage(scope.session, row, await scope.epoch(), command.cause)
    return Effect(f"The marriage ended by {spoken(command.cause)}.", target_node_id=row.first_id)


@player_action("kin:edit_marriage", ActionKind.OTHER)
async def edit_marriage(scope: PlayerScope, command: EditMarriage) -> Effect:
    row = await marriage_row(scope, command.marriage_id)
    if command.form is not None:
        row.form = command.form
    if command.purpose is not None:
        row.purpose = command.purpose
    if command.treaty_id is not None:
        row.treaty_id = command.treaty_id or None
    if command.start_epoch is not None:
        row.start_epoch = command.start_epoch
    return Effect("The marriage was changed.", target_node_id=row.first_id)


@player_action("kin:delete_marriage", ActionKind.OTHER)
async def delete_marriage(scope: PlayerScope, command: MarriageTarget) -> Effect:
    row = await marriage_row(scope, command.marriage_id)
    first = row.first_id
    for bond in await BondRepository(scope.session).active_between(row.first_id, row.second_id, [BondKind.SPOUSE_OF]):
        await scope.session.delete(bond)
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The marriage was struck from the record.", target_node_id=first)


@player_action("kin:bond", ActionKind.OTHER)
async def add_kin_bond(scope: PlayerScope, command: KinBond) -> Effect:
    source = await mortal_of(scope, command.source_id)
    target = await mortal_of(scope, command.target_id)
    kind = BondKind(command.kind)
    made = await connect(scope.session, source.id, target.id, kind, await scope.epoch(), description="by the gods' hand")
    if made is None:
        raise ValidationFailedError("A mortal cannot be bound to themself.")
    return Effect(f"{source.name} is now {spoken(kind)} {target.name}.", target_node_id=source.id, values={"bond_id": made.id})


@player_action("kin:unbond", ActionKind.OTHER)
async def remove_kin_bond(scope: PlayerScope, command: KinBondTarget) -> Effect:
    bond = await scope.session.get(BondRow, command.bond_id)
    if bond is None or bond.kind not in KIN_BOND_KINDS:
        raise NotFoundError("No such kin bond.")
    bond.state = BondState.HIDDEN_REJECTED
    bond.closed_epoch = await scope.epoch()
    return Effect("The kin bond was undone.", target_node_id=bond.source_node_id)


@player_action("mortal:equip", ActionKind.OTHER)
async def equip(scope: PlayerScope, command: Equip) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    row = await ensure_equipment(scope.session, mortal.id)
    column = SLOT_COLUMNS[command.slot]
    if command.item_id is not None:
        target = await scope.session.get(EntityRow, command.item_id)
        if target is None:
            raise NotFoundError("No such thing to equip.")
        if command.slot is EquipmentSlot.MOUNT:
            if target.entity_type not in (EntityType.BEAST, EntityType.SPECIES):
                raise ValidationFailedError("Only a beast or a tamed kind can be ridden.")
        else:
            profile = await scope.session.get(ItemProfileRow, target.id)
            if target.entity_type is not EntityType.ITEM or profile is None or profile.item_class not in SLOT_CLASSES[command.slot]:
                raise ValidationFailedError(f"That cannot be carried as {an(spoken(command.slot))}.")
            if not fits_slot(command.slot, profile):
                raise ValidationFailedError(f"Only one rigid layer is worn per covering; {an(spoken(command.slot))} must be soft.")
    setattr(row, column, command.item_id)
    row.locked = hold(row.locked, column, command.hold)
    action = "now carries something new as" if command.item_id is not None else "has nothing as"
    return Effect(f"{mortal.name} {action} their {spoken(command.slot)}.", target_node_id=mortal.id)


@player_action("mortal:equip_release", ActionKind.OTHER)
async def release_slot(scope: PlayerScope, command: ReleaseSlot) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    row = await ensure_equipment(scope.session, mortal.id)
    column = SLOT_COLUMNS[command.slot]
    if column not in (row.locked or []):
        raise ValidationFailedError(f"{mortal.name}'s {spoken(command.slot)} is not held.")
    row.locked = hold(row.locked, column, False)
    return Effect(f"{mortal.name} chooses their own {spoken(command.slot)} again.", target_node_id=mortal.id)


@player_action("mortal:sentence", ActionKind.OTHER)
async def sentence_mortal(scope: PlayerScope, command: Sentence) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    judge = await mortal_of(scope, command.judge_id) if command.judge_id is not None else None
    ctx = await scope.context("mortal_sentence")
    await sentence(ctx, mortal, command.crime, command.punishment, judge=judge)
    return Effect(f"{mortal.name} was sentenced to {spoken(command.punishment)} for {spoken(command.crime)}.", target_node_id=mortal.id)


@player_action("mortal:pardon", ActionKind.OTHER)
async def pardon(scope: PlayerScope, command: Pardon) -> Effect:
    mortal = await mortal_of(scope, command.mortal_id)
    removed = await remove_flag(scope.session, mortal.id, EntityFlag.EXILE)
    if command.return_to_id is not None:
        mortal.location_id = command.return_to_id
    if not removed and command.return_to_id is None:
        raise ValidationFailedError(f"{mortal.name} bears no sentence to pardon.")
    return Effect(f"{mortal.name} was pardoned.", target_node_id=mortal.id)
