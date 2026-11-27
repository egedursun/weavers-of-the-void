from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.death_shapes import (
    DEATH_SKILLS,
    GROUND_REMAINS,
    REACHABLE_REMAINS,
    RITE_TREATMENTS,
    TREATMENT_COST_PCT,
    TREATMENT_SANITATION,
    TREATMENT_SPIRIT_PCT,
)
from aerona.catalog.entity_types import LEAVES_REMAINS
from aerona.catalog.life_traits import DEATH_ROLE_TRAITS, having
from aerona.catalog.peoples import FUNERALS
from aerona.constants.units import PERCENT
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.death_work import DeathRole, DeathStanding, RemainsTreatment
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import DeathRoleTrait
from aerona.domain.enums.mind import Profession
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.death_work.seed import needed_workers
from aerona.engine.economy.purse import shift_points, take_coin
from aerona.engine.folkways.purity import barred_professions
from aerona.engine.primitives.folk import folk_among, towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.rules.registry import Rules

TENDING = having(DEATH_ROLE_TRAITS, DeathRoleTrait.TENDING)
TEN = 10


@dataclass
class DeathTally:
    seeded: int = 0
    treated: int = 0
    exceptions: int = 0
    untended: int = 0
    shunned: int = 0
    called: int = 0
    left: int = 0


async def remains_of(session: AsyncSession, being: EntityRow) -> RemainsTreatment | None:
    people = await people_of(session, being)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.remains_treatment if culture is not None else None


def spirit_share(treatment: RemainsTreatment | None) -> float:
    return TREATMENT_SPIRIT_PCT[treatment] / PERCENT if treatment is not None else 1.0


def uses_grounds(treatment: RemainsTreatment | None) -> bool:
    return treatment is None or treatment in GROUND_REMAINS


def reachable(treatment: RemainsTreatment | None) -> bool:
    return treatment is None or treatment in REACHABLE_REMAINS


async def own_treatment(session: AsyncSession, being: EntityRow) -> RemainsTreatment | None:
    if being.entity_type is EntityType.SPIRIT:
        return RemainsTreatment.RELEASE
    mind = await session.get(MindProfileRow, being.id)
    return RemainsTreatment.RETURN_TO_MAKER if mind is not None and mind.origin is MindOrigin.MADE else None


async def treat(ctx: TickContext, people: EntityRow, culture: PeopleCultureRow, dead: EntityRow, tally: DeathTally) -> RemainsTreatment:
    custom = culture.remains_treatment
    own = await own_treatment(ctx.session, dead)
    treatment = own or custom
    cost = round_half_up(ctx.rules.death_work.treatment_cost * TREATMENT_COST_PCT[treatment] / PERCENT)
    if cost:
        await shift_points(ctx.session, dead, -cost)
    roles = {IncidentRole.SUBJECT: dead.id, IncidentRole.MEMBER: people.id}
    if own is not None and own is not custom:
        await record(ctx, "death_work.exception", roles=roles, facts={"treatment": treatment, "custom": custom}, place=dead.location_id)
        tally.exceptions += 1
    else:
        await record(ctx, "death_work.remains_treated", roles=roles, facts={"treatment": treatment, "cost": cost}, place=dead.location_id)
        tally.treated += 1
    return treatment


async def clean_or_foul(ctx: TickContext, town_id: int, treated: list[RemainsTreatment], people_id: int) -> None:
    profile = await ctx.session.get(SettlementProfileRow, town_id)
    if profile is None or held(town_id) or "sanitation" in (profile.locked or []):
        return
    shift = round_half_up(sum(TREATMENT_SANITATION[item] for item in treated) * ctx.rules.death_work.sanitation_per_ten_dead / TEN)
    if not shift:
        return
    with explaining():
        term("death_work.sanitation_per_ten_dead", shift, source_node_id=people_id)
        profile.sanitation = clamp_int(profile.sanitation + shift, 0, PERCENT)


async def treat_the_dead(ctx: TickContext, people: EntityRow, towns: list[int], tally: DeathTally) -> None:
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    if culture is None or not towns:
        return
    by_town: dict[int, list[RemainsTreatment]] = defaultdict(list)
    for dead in list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(
                EntityRow.status == EntityStatus.DEAD,
                EntityRow.end_epoch == ctx.epoch,
                EntityRow.entity_type.in_(sorted(LEAVES_REMAINS)),
                await folk_among(ctx.session, towns),
            )
            .order_by(EntityRow.id)
        )
    ):
        if held(dead.id):
            continue
        treatment = await treat(ctx, people, culture, dead, tally)
        home = dead.location_id if dead.location_id in towns else towns[0]
        by_town[home].append(treatment)
    for town_id, treated in sorted(by_town.items()):
        await clean_or_foul(ctx, town_id, treated, people.id)
    await keep_custom(ctx, people, culture, towns, sum(1 for treated in by_town.values() for item in treated if item is culture.remains_treatment))


async def keep_custom(ctx: TickContext, people: EntityRow, culture: PeopleCultureRow, towns: list[int], dead: int) -> None:
    spec = FUNERALS[culture.funeral_rite]
    table = ctx.rules.funerals
    cost = table.mummification_cost * dead if spec.preserves else 0
    paid = 0
    if cost:
        payer = await ctx.session.get(EntityRow, towns[0])
        if payer is not None and await take_coin(ctx.session, ctx.rules, payer, cost):
            paid = cost
    if dead and paid:
        await record(ctx, "death.funeral", roles={IncidentRole.SUBJECT: people.id}, facts={"custom": culture.funeral_rite, "dead": dead, "cost": paid})
    elif dead:
        await record(ctx, "death.funeral_unpaid", roles={IncidentRole.SUBJECT: people.id}, facts={"custom": culture.funeral_rite, "dead": dead})
    if not spec.second_rite or table.epochs(table.secondary_rite_years) <= 0:
        return
    gathered = await ctx.session.scalar(
        select(func.count(EntityRow.id)).where(
            EntityRow.status == EntityStatus.DEAD,
            EntityRow.end_epoch == ctx.epoch - table.epochs(table.secondary_rite_years),
            EntityRow.entity_type.in_(sorted(LEAVES_REMAINS)),
            await folk_among(ctx.session, towns),
        )
    )
    if gathered and "cohesion" not in culture.locked:
        culture.cohesion = clamp_int(culture.cohesion + table.second_rite_cohesion, 0, PERCENT)
        await record(ctx, "death.second_rite", roles={IncidentRole.SUBJECT: people.id}, facts={"dead": int(gathered), "cohesion": culture.cohesion})


def standing_of(purity: int, line: int) -> DeathStanding:
    if purity < line // 2:
        return DeathStanding.AVOIDED
    return DeathStanding.HONOURED if purity > line else DeathStanding.PLAIN


def recruited(ctx: TickContext, row: DeathWorkRow, population: int) -> int:
    table = ctx.rules.death_work
    need = needed_workers(ctx.rules.scale.death_workers_per_mille, population)
    share = ctx.rules.scale.over_epoch(ctx.rules.scale.death_recruit_gap_pct) / PERCENT
    if row.standing is DeathStanding.HONOURED:
        return max(table.recruit_step, round_half_up((need - row.workers) * share)) if row.workers < need else 0
    if row.standing is DeathStanding.AVOIDED:
        return -max(table.recruit_step, round_half_up(row.workers * share)) if row.workers > 0 else 0
    return round_half_up((need - row.workers) * share)


async def recruit(ctx: TickContext, row: DeathWorkRow, tally: DeathTally, population: int) -> None:
    table = ctx.rules.death_work
    if "standing" not in (row.locked or []):
        row.standing = (
            DeathStanding.AVOIDED
            if row.purity < table.role_standing // 2
            else DeathStanding.HONOURED
            if row.purity > table.role_standing
            else DeathStanding.PLAIN
        )
    if "workers" in (row.locked or []):
        return
    step = recruited(ctx, row, population)
    before = row.workers
    with explaining():
        term("scale.death_recruit_gap_pct", step, source_node_id=row.people_entity_id)
        row.workers = max(0, row.workers + step)
    if before > 0 and row.workers == 0:
        await record(ctx, "death_work.role_shunned", roles={IncidentRole.SUBJECT: row.people_entity_id}, facts={"role": row.role, "standing": row.standing})
        tally.shunned += 1


async def untended(ctx: TickContext, people: EntityRow, roles: dict[DeathRole, DeathWorkRow], towns: list[int], tally: DeathTally) -> None:
    if any(roles[role].workers > 0 for role in TENDING if role in roles):
        return
    table = ctx.rules.death_work
    for town_id in towns:
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.location_id is None or held(town_id):
            continue
        outbreak = await ctx.session.scalar(
            select(OutbreakRow)
            .where(OutbreakRow.region_entity_id == town.location_id, OutbreakRow.status != OutbreakStatus.ENDED)
            .order_by(OutbreakRow.id)
            .limit(1)
        )
        if outbreak is None:
            continue
        worse = max(1, round_half_up(outbreak.severity * table.untended_disease_pct / PERCENT / TEN))
        with explaining():
            term("death_work.untended_disease_pct", worse, source_node_id=people.id)
            outbreak.severity = clamp_int(outbreak.severity + worse, 0, PERCENT)
        profile = await ctx.session.get(SettlementProfileRow, town_id)
        if profile is not None and "unrest" not in (profile.locked or []):
            profile.unrest = clamp_int(profile.unrest + worse, 0, PERCENT)
        await record(ctx, "death_work.untended", roles={IncidentRole.SUBJECT: people.id, IncidentRole.PLACE: town_id}, facts={"severity": outbreak.severity})
        tally.untended += 1


def people_standing(rules: Rules, rows: list[DeathWorkRow]) -> DeathStanding | None:
    if not rows:
        return None
    return standing_of(round_half_up(sum(row.purity for row in rows) / len(rows)), rules.death_work.role_standing)


async def standing_among(session: AsyncSession, rules: Rules, being: EntityRow) -> DeathStanding | None:
    people = await people_of(session, being)
    if people is None:
        return None
    rows = list(await session.scalars(select(DeathWorkRow).where(DeathWorkRow.people_entity_id == people.id).order_by(DeathWorkRow.id)))
    return people_standing(rules, rows)


async def death_match(session: AsyncSession, rules: Rules, being: EntityRow) -> int:
    profile = await session.get(MortalProfileRow, being.id)
    if profile is None or profile.profession is not Profession.DEATH_WORKER:
        return 0
    standing = await standing_among(session, rules, being)
    weight = rules.death_work.standing_match
    return {None: 0, DeathStanding.HONOURED: weight, DeathStanding.PLAIN: 0, DeathStanding.AVOIDED: -weight}[standing]


async def answer_calling(ctx: TickContext, people: EntityRow, towns: list[int], standing: DeathStanding | None, tally: DeathTally) -> None:
    if standing is None or not towns:
        return
    workers = list(
        await ctx.session.scalars(
            select(MortalProfileRow)
            .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
            .where(EntityRow.status == EntityStatus.CANON, await folk_among(ctx.session, towns), MortalProfileRow.profession == Profession.DEATH_WORKER)
            .order_by(MortalProfileRow.entity_id)
        )
    )
    if standing is DeathStanding.AVOIDED:
        for profile in workers:
            if held(profile.entity_id) or "profession" in (profile.locked or []):
                continue
            profile.profession = None
            roles = {IncidentRole.SUBJECT: profile.entity_id, IncidentRole.MEMBER: people.id}
            await record(ctx, "death_work.calling_left", roles=roles, facts={"standing": standing})
            tally.left += 1
        return
    floor = ctx.rules.skills.profession_level // 2
    skilled = select(SkillRow.holder_node_id).where(SkillRow.skill.in_(DEATH_SKILLS), SkillRow.level >= floor)
    for profile in list(
        await ctx.session.scalars(
            select(MortalProfileRow)
            .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
            .where(
                EntityRow.status == EntityStatus.CANON,
                await folk_among(ctx.session, towns),
                MortalProfileRow.profession.is_(None),
                MortalProfileRow.entity_id.in_(skilled),
            )
            .order_by(MortalProfileRow.entity_id)
            .limit(ctx.rules.death_work.called_per_epoch)
        )
    ):
        barred = Profession.DEATH_WORKER.value in await barred_professions(ctx.session, profile.entity_id)
        if held(profile.entity_id) or "profession" in (profile.locked or []) or barred:
            continue
        profile.profession = Profession.DEATH_WORKER
        await record(ctx, "death_work.called", roles={IncidentRole.SUBJECT: profile.entity_id, IncidentRole.MEMBER: people.id}, facts={"standing": standing})
        tally.called += 1


async def keep_death_work(ctx: TickContext, tally: DeathTally) -> None:
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        towns = await towns_of_people(ctx.session, people.id)
        await treat_the_dead(ctx, people, towns, tally)
        roles = {
            row.role: row for row in await ctx.session.scalars(select(DeathWorkRow).where(DeathWorkRow.people_entity_id == people.id).order_by(DeathWorkRow.id))
        }
        for row in roles.values():
            await recruit(ctx, row, tally, stat_or(people, "population", 0))
        await untended(ctx, people, roles, towns, tally)
        await answer_calling(ctx, people, towns, people_standing(ctx.rules, list(roles.values())), tally)
    await ctx.session.flush()


def allowed_remains(culture: PeopleCultureRow) -> tuple[RemainsTreatment, ...]:
    return RITE_TREATMENTS[culture.funeral_rite]
