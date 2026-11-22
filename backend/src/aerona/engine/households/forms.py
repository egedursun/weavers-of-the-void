from collections.abc import Mapping, Sequence

from sqlalchemy import func, select

from aerona.catalog.life.households import FORM_CARE, YOUNG
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import InheritanceCustom
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.genetics import DwellingTenure, HouseholdForm, HouseholdRole
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mortal.kin import children_of, parents_of, siblings_of, spouses_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.engine.technology.profiles import family_level

CLASS_TENURE: Mapping[SocialClass, DwellingTenure] = {
    SocialClass.SERF_OR_SLAVE: DwellingTenure.GRANTED,
    SocialClass.OUTCAST: DwellingTenure.SQUATTED,
    SocialClass.UNEMPLOYED: DwellingTenure.SQUATTED,
    SocialClass.WORKER: DwellingTenure.RENTED,
    SocialClass.CITIZEN: DwellingTenure.RENTED,
}
ENERGY_BY_LEVEL: tuple[tuple[int, EnergyKind], ...] = ((8, EnergyKind.FUSION), (6, EnergyKind.ELECTRIC), (3, EnergyKind.FUEL), (0, EnergyKind.HEAT))
OPEN_FIRE = frozenset({EnergyKind.HEAT, EnergyKind.MUSCLE})


async def made_member(ctx: TickContext, node_id: int) -> bool:
    mind = await ctx.session.get(MindProfileRow, node_id)
    return mind is not None and mind.origin is not MindOrigin.BORN


async def kin_of(ctx: TickContext, head_id: int) -> set[int]:
    found = {
        *await spouses_of(ctx.session, head_id),
        *await children_of(ctx.session, head_id),
        *await parents_of(ctx.session, head_id),
        *await siblings_of(ctx.session, head_id),
    }
    for child in list(found):
        found |= set(await children_of(ctx.session, child))
    return found


async def form_of(ctx: TickContext, household: HouseholdRow, member_ids: Sequence[int]) -> HouseholdForm:
    if len(member_ids) <= 1:
        return HouseholdForm.SINGLE
    head = household.head_node_id or member_ids[0]
    if any([await made_member(ctx, node_id) for node_id in member_ids]):
        return HouseholdForm.MIXED
    kin = await kin_of(ctx, head)
    strangers = [node_id for node_id in member_ids if node_id != head and node_id not in kin]
    if len(strangers) >= ctx.rules.households.institution_size:
        return HouseholdForm.INSTITUTIONAL
    if len(strangers) * 2 > len(member_ids):
        return HouseholdForm.COMMUNAL if len(member_ids) > ctx.rules.households.mean_size else HouseholdForm.CHOSEN
    return await kin_form(ctx, head, set(member_ids))


async def kin_form(ctx: TickContext, head: int, present: set[int]) -> HouseholdForm:
    if len(await spouses_of(ctx.session, head)) > 1:
        return HouseholdForm.POLYGAMOUS
    elders = present & set(await parents_of(ctx.session, head))
    wedded_siblings = [
        sibling for sibling in await siblings_of(ctx.session, head) if sibling in present and set(await spouses_of(ctx.session, sibling)) & present
    ]
    if wedded_siblings:
        return HouseholdForm.JOINT
    wedded_children = [child for child in await children_of(ctx.session, head) if child in present and set(await spouses_of(ctx.session, child)) & present]
    if len(wedded_children) == 1:
        return HouseholdForm.STEM
    return HouseholdForm.EXTENDED if elders or wedded_children else HouseholdForm.NUCLEAR


def tenure_for(social_class: SocialClass | None) -> DwellingTenure:
    return CLASS_TENURE.get(social_class, DwellingTenure.OWNED) if social_class is not None else DwellingTenure.OWNED


async def energy_for(ctx: TickContext, settlement_id: int | None) -> EnergyKind:
    level = await family_level(ctx.session, settlement_id, TechFamily.ENERGY)
    return next(kind for floor, kind in ENERGY_BY_LEVEL if level >= floor)


async def keep_dwelling(ctx: TickContext, household: HouseholdRow, dwelling: DwellingRow, members: int) -> None:
    table = ctx.rules.households
    locked = dwelling.locked or []
    if "tenure" not in locked and dwelling.built_epoch == ctx.epoch:
        dwelling.tenure = tenure_for(household.social_class)
    if "heating" not in locked:
        dwelling.heating = await energy_for(ctx, dwelling.settlement_node_id)
    if "light" not in locked:
        dwelling.light = dwelling.heating
    if "crowding" not in locked:
        dwelling.crowding = members * PERCENT // max(1, dwelling.rooms)
    if dwelling.tenure is DwellingTenure.RENTED and "wealth" not in (household.locked or []):
        household.wealth = max(0, household.wealth - household.income * table.rent_pct // PERCENT)
    elif dwelling.tenure is DwellingTenure.SQUATTED and ctx.rng(f"evict.{household.id}.{ctx.epoch}").chance(table.eviction_pct) and "quality" not in locked:
        dwelling.quality = clamp_int(dwelling.quality - table.eviction_quality, 0, PERCENT)
    elif dwelling.tenure is DwellingTenure.GRANTED and household.head_node_id is not None and not held(household.head_node_id):
        profile = await ctx.session.get(MortalProfileRow, household.head_node_id)
        if profile is not None and "stress" not in (profile.locked or []):
            profile.stress = clamp_int(profile.stress + table.granted_stress, 0, PERCENT)


def home_comfort(rules_heated: int, rules_lit: int, dwelling: DwellingRow) -> tuple[int, int]:
    heated = rules_heated if dwelling.heating is not None and dwelling.heating not in OPEN_FIRE else 0
    lit = rules_lit if dwelling.light is not None and dwelling.light not in OPEN_FIRE else 0
    return heated, lit


async def custom_of(ctx: TickContext, head: EntityRow | None) -> InheritanceCustom | None:
    people = await people_of(ctx.session, head) if head is not None else None
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.inheritance if culture is not None else None


def heir_by_custom(custom: InheritanceCustom | None, grown: Sequence[EntityRow], skills: Mapping[int, int], renown: Mapping[int, int]) -> EntityRow | None:
    if not grown:
        return None
    by_age = sorted(grown, key=lambda row: (row.birth_epoch, row.id))
    if custom is InheritanceCustom.ULTIMOGENITURE:
        return by_age[-1]
    if custom is InheritanceCustom.BY_MERIT:
        return max(grown, key=lambda row: (skills.get(row.id, 0), -row.id))
    if custom is InheritanceCustom.ELECTIVE:
        return max(grown, key=lambda row: (renown.get(row.id, 0), -row.id))
    return by_age[0]


async def keep_form(ctx: TickContext, household: HouseholdRow, rows: Sequence[HouseholdMemberRow], dwelling: DwellingRow | None) -> None:
    member_ids = [row.member_node_id for row in rows]
    if "form" not in (household.locked or []):
        household.form = await form_of(ctx, household, member_ids)
    if "burden" not in (household.locked or []):
        relief = household.burden * FORM_CARE[household.form] * ctx.rules.households.care_relief_pct // (PERCENT * PERCENT)
        household.burden = clamp_int(household.burden - relief, 0, PERCENT)
    if dwelling is not None:
        await keep_dwelling(ctx, household, dwelling, len(member_ids))


async def inherit(ctx: TickContext, household: HouseholdRow, rows: Sequence[HouseholdMemberRow], dead_head: EntityRow) -> int | None:
    custom = await custom_of(ctx, dead_head)
    grown: list[EntityRow] = []
    for row in rows:
        member = await ctx.session.get(EntityRow, row.member_node_id)
        profile = await ctx.session.get(MortalProfileRow, row.member_node_id)
        if member is None or row.role in (HouseholdRole.SERVANT, HouseholdRole.LODGER) or profile is None or profile.life_stage in YOUNG:
            continue
        grown.append(member)
    ids = [member.id for member in grown]
    levels = await ctx.session.execute(
        select(SkillRow.holder_node_id, func.max(SkillRow.level)).where(SkillRow.holder_node_id.in_(ids)).group_by(SkillRow.holder_node_id)
    )
    skills = {holder: int(level or 0) for holder, level in levels}
    renown = {member.id: stat_or(member, "renown", 0) for member in grown}
    heir = heir_by_custom(custom, grown, skills, renown)
    if heir is None:
        return None
    return heir.id
