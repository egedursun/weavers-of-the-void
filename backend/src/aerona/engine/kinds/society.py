from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.kind_concepts.society import (
    BUILT_IN_JOBS,
    BUILT_IN_ORGANISATIONS,
    BUILT_IN_PROFESSIONS,
    BUILT_IN_RANKS,
    CLASS_LABELS,
    JOB_LABELS,
    ORGANISATION_BASE_LABELS,
    PROFESSION_BASE_LABELS,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_kinds import OrganisationKindRow, ProfessionKindRow, RankKindRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.society_kinds import OrganisationLegalForm
from aerona.engine.body.customs import people_id_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.kinds.professions import held_kinds
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.folk import present_among, towns_of_people
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat


@dataclass
class SocietyKindTally:
    built_in: int = 0
    ranks: int = 0
    earnings: int = 0
    mishaps: int = 0
    organisations: int = 0


async def ensure_built_ins(session: AsyncSession) -> int:
    added = 0
    if not await session.scalar(
        select(func.count()).select_from(ProfessionKindRow).where(ProfessionKindRow.base.is_not(None), ProfessionKindRow.built_in.is_(True))
    ):
        for profession, spec in BUILT_IN_PROFESSIONS.items():
            session.add(
                ProfessionKindRow(
                    name=PROFESSION_BASE_LABELS[profession.value],
                    built_in=True,
                    category=spec.category,
                    base=profession,
                    prestige=spec.prestige,
                    income=spec.income,
                    purity=spec.purity,
                    mishap_exposure=spec.mishap_exposure,
                    skill_need=spec.skill_need,
                    locked=[],
                )
            )
            added += 1
    if not await session.scalar(select(func.count()).select_from(ProfessionKindRow).where(ProfessionKindRow.job.is_not(None))):
        for job, spec in BUILT_IN_JOBS.items():
            session.add(
                ProfessionKindRow(
                    name=JOB_LABELS[job.value],
                    built_in=True,
                    category=spec.category,
                    job=job,
                    prestige=spec.prestige,
                    income=spec.income,
                    purity=spec.purity,
                    mishap_exposure=spec.mishap_exposure,
                    skill_need=spec.skill_need,
                    locked=[],
                )
            )
            added += 1
    if not await session.scalar(select(func.count()).select_from(RankKindRow).where(RankKindRow.built_in.is_(True))):
        for social_class, rank in BUILT_IN_RANKS.items():
            session.add(
                RankKindRow(
                    name=CLASS_LABELS[social_class.value],
                    built_in=True,
                    category=social_class,
                    standing=rank.standing,
                    privilege=rank.privilege,
                    duty=rank.duty,
                    mobility=rank.mobility,
                    purity=rank.purity,
                    locked=[],
                )
            )
            added += 1
    if not await session.scalar(select(func.count()).select_from(OrganisationKindRow).where(OrganisationKindRow.built_in.is_(True))):
        for kind, body in BUILT_IN_ORGANISATIONS.items():
            session.add(
                OrganisationKindRow(
                    name=ORGANISATION_BASE_LABELS[kind.value],
                    built_in=True,
                    category=body.category,
                    base=kind,
                    ownership=body.ownership,
                    membership=body.membership,
                    scale=body.scale,
                    legal_form=body.legal_form,
                    governance=body.governance,
                    prestige=body.prestige,
                    cohesion=body.cohesion,
                    secrecy=body.secrecy,
                    foundable=body.foundable,
                    locked=[],
                )
            )
            added += 1
    if added:
        await session.flush()
    return added


async def rank_effects(ctx: TickContext, people: EntityRow, tally: SocietyKindTally) -> None:
    pull = ctx.rules.society_kinds.rank_pull_pct
    holdings = await held_kinds(ctx.session, people.id, KindConcept.RANK, RankKindRow)
    if not holdings:
        return
    towns = [town for town in await towns_of_people(ctx.session, people.id) if not held(town)]
    for town_id in towns:
        society = await ctx.session.get(CommunitySocietyRow, town_id)
        if society is None:
            continue
        for holding, rank in holdings:
            key = f"satisfaction_{rank.category.value}"
            shift = round_half_up((rank.privilege - rank.duty) * holding.strength / PERCENT * pull / PERCENT)
            if shift:
                setattr(society, key, clamp_int(getattr(society, key) + shift, 0, PERCENT))
                tally.ranks += 1


async def earnings(ctx: TickContext, people: EntityRow, tally: SocietyKindTally) -> None:
    share = ctx.rules.society_kinds.income_pct
    holdings = await held_kinds(ctx.session, people.id, KindConcept.PROFESSION, ProfessionKindRow)
    gain = sum(kind.income * holding.strength for holding, kind in holdings) / PERCENT / max(1, len(holdings)) * share / PERCENT
    if not holdings or gain <= 0:
        return
    for town_id in await towns_of_people(ctx.session, people.id):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or held(town.id):
            continue
        shift_stat(town, "prosperity", gain, low=0, high=PERCENT)
        tally.earnings += 1


async def work_mishaps(ctx: TickContext, people: EntityRow, tally: SocietyKindTally) -> None:
    table = ctx.rules.society_kinds
    holdings = await held_kinds(ctx.session, people.id, KindConcept.PROFESSION, ProfessionKindRow)
    towns = await towns_of_people(ctx.session, people.id)
    if not towns:
        return
    for holding, kind in holdings:
        if kind.base is None:
            continue
        rng = ctx.rng(seed_of("society_kinds.mishap", people.id, kind.id, ctx.epoch))
        if not rng.chance(clamp_int(kind.mishap_exposure * holding.strength * table.mishap_pct // (PERCENT * PERCENT), 0, PERCENT)):
            continue
        workers = list(
            await ctx.session.scalars(
                select(EntityRow)
                .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
                .where(
                    EntityRow.entity_type == EntityType.MORTAL,
                    EntityRow.status == EntityStatus.CANON,
                    MortalProfileRow.profession == kind.base,
                    await present_among(ctx.session, towns),
                )
                .order_by(EntityRow.id)
            )
        )
        workers = [worker for worker in workers if not held(worker.id)]
        if not workers:
            continue
        worker = rng.pick(workers)
        await apply_hits(ctx, worker, Harm(table.mishap_harm, HarmCause.ACCIDENT, f"hurt at work as {kind.name.lower()}"), lethal=False)
        tally.mishaps += 1


async def organisation_of(session: AsyncSession, faction: FactionProfileRow) -> OrganisationKindRow | None:
    if faction.home_entity_id is not None:
        home = await session.get(EntityRow, faction.home_entity_id)
        people_id = await people_id_of(session, home) if home is not None else None
        if people_id is not None:
            for _, kind in await held_kinds(session, people_id, KindConcept.ORGANISATION, OrganisationKindRow):
                if kind.base is faction.kind:
                    return kind
    found: OrganisationKindRow | None = await session.scalar(
        select(OrganisationKindRow).where(OrganisationKindRow.built_in.is_(True), OrganisationKindRow.base == faction.kind).limit(1)
    )
    return found


def drift(current: int, target: int, pct: int) -> int:
    return clamp_int(current + round_half_up((target - current) * pct / PERCENT), 0, PERCENT)


async def organisation_kind_for(session: AsyncSession, community: EntityRow, kind: FactionKind) -> OrganisationKindRow | None:
    people_id = await people_id_of(session, community)
    if people_id is not None:
        for _, found in await held_kinds(session, people_id, KindConcept.ORGANISATION, OrganisationKindRow):
            if found.base is kind:
                return found
    built: OrganisationKindRow | None = await session.scalar(
        select(OrganisationKindRow).where(OrganisationKindRow.built_in.is_(True), OrganisationKindRow.base == kind).limit(1)
    )
    return built


async def mortals_may_found(session: AsyncSession, community: EntityRow, kind: FactionKind) -> bool:
    await ensure_built_ins(session)
    found = await organisation_kind_for(session, community, kind)
    return found is not None and found.foundable


async def shape_factions(ctx: TickContext, tally: SocietyKindTally) -> None:
    pct = ctx.rules.society_kinds.drift_pct
    for faction in list(await ctx.session.scalars(select(FactionProfileRow).order_by(FactionProfileRow.faction_entity_id))):
        if held(faction.faction_entity_id):
            continue
        kind = await organisation_of(ctx.session, faction)
        if kind is None:
            continue
        locked = set(faction.locked or [])
        if "cohesion" not in locked:
            faction.cohesion = drift(faction.cohesion, kind.cohesion, pct)
        if "secrecy" not in locked:
            faction.secrecy = drift(faction.secrecy, kind.secrecy, pct)
        if "reputation" not in locked:
            faction.reputation = drift(faction.reputation, kind.prestige, pct)
        if "outlawed" not in locked and kind.legal_form is OrganisationLegalForm.OUTLAWED:
            faction.outlawed = True
        tally.organisations += 1


async def keep_society_kinds(ctx: TickContext) -> SocietyKindTally:
    tally = SocietyKindTally(built_in=await ensure_built_ins(ctx.session))
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for people in peoples:
        if held(people.id):
            continue
        await rank_effects(ctx, people, tally)
        await earnings(ctx, people, tally)
        await work_mishaps(ctx, people, tally)
    await shape_factions(ctx, tally)
    await ctx.session.flush()
    return tally
