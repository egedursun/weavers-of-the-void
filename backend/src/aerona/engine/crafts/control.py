from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.crafts import (
    AFFINITY_FIELDS,
    AID_FIELDS,
    CLOCK_FIELDS,
    GROUND_FIELDS,
    INSURER_FIELDS,
    LINK_FIELDS,
    NUMBER_FIELDS,
    POLICY_FIELDS,
    RIGHT_FIELDS,
    SPIRIT_FIELDS,
    WORKS_FIELDS,
    AssistiveAidRow,
    CatchGroundRow,
    ChemicalWorksRow,
    EmotionSpiritRow,
    IncorporealRightRow,
    InsurancePolicyRow,
    InsurerRow,
    MaterialAffinityRow,
    NumberSystemRow,
    PublicClockRow,
    SympatheticLinkRow,
)
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.relations import ContestRow
from aerona.domain.enums.crafts import RightAcquired, RightKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.folk_knowledge import NumberReading
from aerona.domain.enums.relations import ContestEnd
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.crafts.aids import AidTally, keep_aids
from aerona.engine.crafts.chemistry import ChemistryTally, keep_chemistry
from aerona.engine.crafts.clocks import ClockTally, keep_clocks
from aerona.engine.crafts.games import GameTally, keep_games
from aerona.engine.crafts.grounds import GroundTally, keep_grounds
from aerona.engine.crafts.insurance import InsuranceTally, keep_insurance
from aerona.engine.crafts.numbers import NumberTally, keep_numbers
from aerona.engine.crafts.rights import RightsTally, house_of, keep_rights, made, wed_portion, win_right
from aerona.engine.crafts.spirits import SpiritTally, keep_spirits
from aerona.engine.crafts.sympathy import SympathyTally, keep_sympathy
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str
    keys: tuple[str, ...]


KINDS: Mapping[str, Kind] = {
    "catch_ground": Kind(CatchGroundRow, GROUND_FIELDS, "fishing or hunting ground", ("source_entity_id", "region_entity_id")),
    "chemical_works": Kind(ChemicalWorksRow, WORKS_FIELDS, "chemical works", ("settlement_entity_id", "product")),
    "insurer": Kind(InsurerRow, INSURER_FIELDS, "insurer", ("insurer_entity_id",)),
    "insurance_policy": Kind(InsurancePolicyRow, POLICY_FIELDS, "insurance policy", ("id",)),
    "incorporeal_right": Kind(IncorporealRightRow, RIGHT_FIELDS, "held right", ("id",)),
    "assistive_aid": Kind(AssistiveAidRow, AID_FIELDS, "aid", ("holder_node_id", "kind")),
    "public_clock": Kind(PublicClockRow, CLOCK_FIELDS, "public clock", ("settlement_entity_id",)),
    "number_system": Kind(NumberSystemRow, NUMBER_FIELDS, "number system", ("people_entity_id",)),
    "material_affinity": Kind(MaterialAffinityRow, AFFINITY_FIELDS, "magical affinity", ("material_id", "school")),
    "sympathetic_link": Kind(SympatheticLinkRow, LINK_FIELDS, "sympathetic link", ("id",)),
    "emotion_spirit": Kind(EmotionSpiritRow, SPIRIT_FIELDS, "emotion spirit", ("id",)),
}
NODE_KEYS = frozenset({"source_entity_id", "region_entity_id", "settlement_entity_id", "insurer_entity_id", "people_entity_id"})


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if value is not None and (name in NODE_KEYS or name.endswith(("_node_id", "_entity_id"))) and isinstance(value, int):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
    material = values.get("material_id")
    if isinstance(material, int) and await ctx.session.get(WorldMaterialRow, material) is None:
        raise ValidationFailedError("No such material.")


def key_of(kind: Kind, keys: Values) -> object:
    picked = tuple(keys[name] for name in kind.keys)
    return picked[0] if len(picked) == 1 else picked


async def set_record(ctx: TickContext, name: str, keys: Values, values: Values) -> Base:
    kind = KINDS[name]
    await checked(ctx, {**keys, **values})
    row = await ctx.session.get(kind.table, key_of(kind, keys)) if "id" not in kind.keys else None
    if row is None:
        row = await saved(ctx, kind.table(**keys, **values, locked=[]))
    else:
        apply(row, allowed(values, kind.fields, kind.label), [])
        await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def claim_right(
    ctx: TickContext,
    holder_id: int,
    kind: RightKind,
    name: str,
    *,
    subject_id: int | None = None,
    dish_id: int | None = None,
    technique: Technique | None = None,
    contest_id: int | None = None,
    marriage_id: int | None = None,
) -> IncorporealRightRow:
    await node_exists(ctx, holder_id, "holder")
    if contest_id is not None:
        contest = await found(ctx, ContestRow, contest_id, "contest")
        loser = contest.defender_node_id if contest.challenger_node_id == holder_id else contest.challenger_node_id
        won = await win_right(ctx, contest.id, contest.stake_node_id, holder_id, loser) if contest.outcome is not ContestEnd.DRAWN else None
        if won is None:
            raise ValidationFailedError("No right was staked in that contest, or you did not win it.")
        return won
    if marriage_id is not None:
        union = await found(ctx, MarriageRow, marriage_id, "union")
        if holder_id not in {union.first_id, union.second_id}:
            raise ValidationFailedError("That union is not yours.")
        partner = union.second_id if union.first_id == holder_id else union.first_id
        portion = await wed_portion(ctx, await house_of(ctx, partner), holder_id, union.id)
        if portion is None:
            raise ValidationFailedError("Your partner's line has no right to pass with the union.")
        return portion
    if kind is RightKind.RECIPE and (dish_id is None or await ctx.session.get(DishRow, dish_id) is None):
        raise ValidationFailedError("A right to a recipe names a dish.")
    if kind is RightKind.TECHNIQUE:
        known = await ctx.session.get(HolderTechniqueRow, (holder_id, technique)) if technique is not None else None
        if known is None:
            raise ValidationFailedError("A right to a technique names a technique you hold.")
    return await made(
        ctx,
        IncorporealRightRow(
            holder_node_id=holder_id,
            kind=kind,
            subject_node_id=subject_id,
            name=name,
            dish_id=dish_id,
            technique=technique,
            acquired=RightAcquired.CREATED,
            since_epoch=ctx.epoch,
            locked=[],
        ),
    )


async def read_number(ctx: TickContext, people_id: int, number: int, reading: NumberReading | None) -> NumberSystemRow:
    system = await ctx.session.get(NumberSystemRow, people_id)
    if system is None:
        raise ValidationFailedError("That people has no number system to read yet.")
    if not 0 <= number < system.base:
        raise ValidationFailedError(f"In base {system.base} a number to read lies from 0 to {system.base - 1}.")
    readings = dict(system.numerology or {})
    if reading is None:
        readings.pop(str(number), None)
    else:
        readings[str(number)] = reading.value
    system.numerology = readings
    await ctx.session.flush()
    return system


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()


@dataclass
class TradesRun:
    grounds: GroundTally
    chemistry: ChemistryTally
    insurance: InsuranceTally
    rights: RightsTally
    clocks: ClockTally


@dataclass
class LearningRun:
    aids: AidTally
    games: GameTally
    numbers: NumberTally


@dataclass
class SympathiesRun:
    sympathy: SympathyTally
    spirits: SpiritTally


async def run_trades(ctx: TickContext) -> TradesRun:
    tally = TradesRun(GroundTally(), ChemistryTally(), InsuranceTally(), RightsTally(), ClockTally())
    await keep_grounds(ctx, tally.grounds)
    await keep_chemistry(ctx, tally.chemistry)
    await keep_insurance(ctx, tally.insurance)
    await keep_rights(ctx, tally.rights)
    await keep_clocks(ctx, tally.clocks)
    return tally


async def run_learning(ctx: TickContext) -> LearningRun:
    tally = LearningRun(AidTally(), GameTally(), NumberTally())
    await keep_aids(ctx, tally.aids)
    await keep_games(ctx, tally.games)
    await keep_numbers(ctx, tally.numbers)
    return tally


async def run_sympathies(ctx: TickContext) -> SympathiesRun:
    tally = SympathiesRun(SympathyTally(), SpiritTally())
    await keep_sympathy(ctx, tally.sympathy)
    await keep_spirits(ctx, tally.spirits)
    return tally
