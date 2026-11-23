from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.customs import (
    AGE_MEMBER_FIELDS,
    AGE_SET_FIELDS,
    BORDER_FIELDS,
    CATEGORY_FIELDS,
    COMMUTE_FIELDS,
    COOP_FIELDS,
    EVIDENCE_FIELDS,
    GRADE_DUTY_FIELDS,
    INTOXICANT_FIELDS,
    MARK_CUSTOM_FIELDS,
    MARK_FIELDS,
    MEASURE_FIELDS,
    MEMBER_FIELDS,
    NAME_FORM_FIELDS,
    NAMING_FIELDS,
    RELIEF_FIELDS,
    REVIVAL_FIELDS,
    TAVERN_FIELDS,
    TIME_FIELDS,
    WELFARE_FIELDS,
    AgeSetMemberRow,
    AgeSetRow,
    BodyMarkRow,
    BorderControlRow,
    CommuteRow,
    CooperativeRow,
    EvidenceRow,
    GradeDutyRow,
    IntoxicantCustomRow,
    MarkCustomRow,
    MeasureStandardRow,
    MembershipCategoryRow,
    MembershipRow,
    NameFormRow,
    NamingCustomRow,
    PoorReliefRow,
    RevivalRow,
    TavernRow,
    TimeBudgetRow,
    WelfareRow,
)
from aerona.db.tables.justice import CrimeCaseRow
from aerona.domain.enums.customs import MemberRight, Membership
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.customs.age_sets import AgeSetTally, keep_age_sets
from aerona.engine.customs.civics import CivicsTally, keep_civics
from aerona.engine.customs.town_life import TownLifeTally, keep_town_life
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
    "revival": Kind(RevivalRow, REVIVAL_FIELDS, "movement", ("id",)),
    "intoxicant_custom": Kind(IntoxicantCustomRow, INTOXICANT_FIELDS, "intoxicant custom", ("people_entity_id", "intoxicant")),
    "mark_custom": Kind(MarkCustomRow, MARK_CUSTOM_FIELDS, "mark custom", ("people_entity_id", "kind")),
    "body_mark": Kind(BodyMarkRow, MARK_FIELDS, "mark", ("id",)),
    "time_budget": Kind(TimeBudgetRow, TIME_FIELDS, "time budget", ("people_entity_id", "social_class", "life_stage")),
    "naming_custom": Kind(NamingCustomRow, NAMING_FIELDS, "naming custom", ("people_entity_id",)),
    "name_form": Kind(NameFormRow, NAME_FORM_FIELDS, "name", ("holder_node_id", "form")),
    "age_set": Kind(AgeSetRow, AGE_SET_FIELDS, "age-set", ("id",)),
    "grade_duty": Kind(GradeDutyRow, GRADE_DUTY_FIELDS, "grade duty", ("people_entity_id", "duty")),
    "age_set_member": Kind(AgeSetMemberRow, AGE_MEMBER_FIELDS, "age-set membership", ("mortal_entity_id",)),
    "tavern": Kind(TavernRow, TAVERN_FIELDS, "tavern", ("structure_entity_id",)),
    "welfare_house": Kind(WelfareRow, WELFARE_FIELDS, "house of welfare", ("structure_entity_id",)),
    "commute": Kind(CommuteRow, COMMUTE_FIELDS, "way to work", ("settlement_entity_id",)),
    "cooperative": Kind(CooperativeRow, COOP_FIELDS, "cooperative", ("faction_entity_id",)),
    "evidence": Kind(EvidenceRow, EVIDENCE_FIELDS, "evidence", ("id",)),
    "membership_category": Kind(MembershipCategoryRow, CATEGORY_FIELDS, "membership category", ("polity_entity_id", "category")),
    "membership": Kind(MembershipRow, MEMBER_FIELDS, "membership", ("mortal_entity_id",)),
    "border_control": Kind(BorderControlRow, BORDER_FIELDS, "border", ("polity_entity_id",)),
    "poor_relief": Kind(PoorReliefRow, RELIEF_FIELDS, "poor relief", ("polity_entity_id",)),
    "measure_standard": Kind(MeasureStandardRow, MEASURE_FIELDS, "standard of measures", ("polity_entity_id",)),
}
NODE_KEYS = frozenset(
    {"people_entity_id", "holder_node_id", "mortal_entity_id", "structure_entity_id", "settlement_entity_id", "faction_entity_id", "polity_entity_id"}
)


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if value is not None and (name in NODE_KEYS or name.endswith(("_node_id", "_entity_id"))) and isinstance(value, int):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
    case = values.get("case_id")
    if isinstance(case, int) and await ctx.session.get(CrimeCaseRow, case) is None:
        raise ValidationFailedError("No such case.")
    age_set = values.get("age_set_id")
    if isinstance(age_set, int) and await ctx.session.get(AgeSetRow, age_set) is None:
        raise ValidationFailedError("No such age-set.")


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


async def grant_right(ctx: TickContext, polity_id: int, category: Membership, right: MemberRight, *, granted: bool) -> MembershipCategoryRow:
    await node_exists(ctx, polity_id, "realm")
    row = await ctx.session.get(MembershipCategoryRow, (polity_id, category)) or await saved(
        ctx, MembershipCategoryRow(polity_entity_id=polity_id, category=category, rights=[], locked=[])
    )
    rights = [item for item in row.rights if item != right.value]
    row.rights = sorted([*rights, right.value]) if granted else rights
    row.locked = sorted({*row.locked, "rights"})
    await ctx.session.flush()
    return row


async def edit_category(ctx: TickContext, polity_id: int, category: Membership, values: Values, release: list[str]) -> MembershipCategoryRow:
    row = await found(ctx, MembershipCategoryRow, (polity_id, category), "membership category")
    named = {right.value for right in MemberRight}
    unknown = sorted(set(values) - named)
    if unknown:
        raise ValidationFailedError(f"A category holds only its rights, not {', '.join(unknown)}.")
    rights = set(row.rights)
    for name, value in values.items():
        if value is True:
            rights.add(name)
        elif value is False:
            rights.discard(name)
    if values:
        row.rights = sorted(rights)
        row.locked = sorted({*row.locked, "rights"})
    if "rights" in release or named & set(release):
        row.locked = [item for item in row.locked if item != "rights"]
    await ctx.session.flush()
    return row


async def run_town_life(ctx: TickContext) -> TownLifeTally:
    tally = TownLifeTally()
    await keep_town_life(ctx, tally)
    return tally


async def run_civics(ctx: TickContext) -> CivicsTally:
    tally = CivicsTally()
    await keep_civics(ctx, tally)
    return tally


async def run_age_sets(ctx: TickContext) -> AgeSetTally:
    tally = AgeSetTally()
    await keep_age_sets(ctx, tally)
    return tally


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()
