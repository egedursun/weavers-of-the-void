from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.domain import REVOLT_CAUSES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import OutlawRow, PardonRow, PrisonerRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.mind.ethics import ethic_reading
from aerona.engine.mortal.standing import add_renown
from aerona.engine.polity.repute import shift_infamy
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.relations.book import relation
from aerona.engine.renown.axes import honour_axis

CORRUPTION = "corruption"


@dataclass
class PardonTally:
    pardoned: int = 0
    corrupt: int = 0
    amnesties: int = 0


async def ruler_office(ctx: TickContext, polity_id: int) -> OfficeRow | None:
    rows = await ctx.session.scalars(
        select(OfficeRow).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None)).limit(1)
    )
    return rows.first()


async def held_in_realm(ctx: TickContext, polity_id: int) -> list[PrisonerRow]:
    towns = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)
    prisons = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.host_entity_id.in_(towns))
    return list(await ctx.session.scalars(select(PrisonerRow).where(PrisonerRow.prison_entity_id.in_(prisons)).order_by(PrisonerRow.mortal_entity_id)))


async def wrongful(ctx: TickContext, case_id: int | None) -> bool:
    case = await ctx.session.get(CrimeCaseRow, case_id) if case_id is not None else None
    return case is not None and case.wrongful


async def read_mercy(ctx: TickContext, granter: EntityRow, polity_id: int | None) -> int:
    table = ctx.rules.pardons
    profile = await ctx.session.get(PolityProfileRow, polity_id) if polity_id is not None else None
    judge = profile.capital_entity_id if profile is not None and profile.capital_entity_id is not None else granter.location_id or granter.id
    reading = await ethic_reading(ctx.session, ctx.rules, judge, ActKind.MERCY_TO_ENEMY, await values_for(ctx.session, judge))
    if reading > 0:
        await add_renown(ctx.session, granter.id, table.mercy_renown, ctx.epoch, rules=ctx.rules)
    elif reading < 0:
        await shift_infamy(ctx, granter.id, table.tyranny_infamy)
    return reading


async def civil_war_ended(ctx: TickContext, polity_id: int, since: int) -> bool:
    found = await ctx.session.scalar(
        select(WarRow.id)
        .join(WarSideRow, WarSideRow.war_id == WarRow.id)
        .where(
            WarSideRow.entity_id == polity_id,
            WarRow.cause.in_(list(REVOLT_CAUSES)),
            WarRow.ended_epoch >= ctx.epoch - ctx.rules.pardons.amnesty_epochs,
            WarRow.ended_epoch > since,
        )
        .limit(1)
    )
    return found is not None


async def grant_pardon(ctx: TickContext, granter: EntityRow, mortal: EntityRow, *, polity_id: int | None, case_id: int | None) -> PardonRow:
    table = ctx.rules.pardons
    view = await relation(ctx.session, granter.id, mortal.id)
    unjust = await wrongful(ctx, case_id)
    corrupt = not unjust and view is not None and view.friendship >= table.friend_at
    for row in (await ctx.session.get(PrisonerRow, mortal.id), await ctx.session.get(OutlawRow, mortal.id)):
        if row is not None:
            await ctx.session.delete(row)
    pardon = PardonRow(granter_entity_id=granter.id, pardoned_entity_id=mortal.id, case_id=case_id, amnesty=False, corrupt=corrupt, epoch=ctx.epoch)
    ctx.session.add(pardon)
    if corrupt:
        await shift_infamy(ctx, granter.id, table.corruption_infamy)
        profile = await ctx.session.get(PolityProfileRow, polity_id) if polity_id is not None else None
        if profile is not None and CORRUPTION not in profile.locked:
            profile.corruption = clamp_int(profile.corruption + table.corruption_infamy, 0, PERCENT)
    if unjust:
        await add_renown(ctx.session, granter.id, table.mercy_renown, ctx.epoch, rules=ctx.rules)
    await read_mercy(ctx, granter, polity_id)
    if not corrupt:
        await honour_axis(ctx, granter.id, ReputationAxis.MERCY, ctx.rules.renown.mercy_gain, granter.location_id)
    await ctx.session.flush()
    await record(
        ctx,
        "law.pardon_corrupt" if corrupt else "law.pardon_wrongful" if unjust else "law.pardon",
        roles={IncidentRole.AUTHORITY: granter.id, IncidentRole.SUBJECT: mortal.id},
        facts={"realm": polity_id},
        place=granter.location_id,
    )
    return pardon


async def pardon_friends(ctx: TickContext, polity_id: int, ruler: EntityRow, tally: PardonTally) -> None:
    table = ctx.rules.pardons
    for row in await held_in_realm(ctx, polity_id):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        view = await relation(ctx.session, ruler.id, row.mortal_entity_id)
        if mortal is None or held(mortal.id) or view is None or view.friendship < table.friend_at:
            continue
        if ctx.rng(f"law.pardon.{ruler.id}.{mortal.id}").chance(table.friend_pct):
            pardon = await grant_pardon(ctx, ruler, mortal, polity_id=polity_id, case_id=row.case_id)
            tally.pardoned += 1
            tally.corrupt += int(pardon.corrupt)


async def declare_amnesty(ctx: TickContext, polity_id: int, ruler: EntityRow) -> int:
    freed = 0
    outlaws = list(await ctx.session.scalars(select(OutlawRow).where(OutlawRow.polity_entity_id == polity_id)))
    rows: list[PrisonerRow | OutlawRow] = [*await held_in_realm(ctx, polity_id), *outlaws]
    for row in rows:
        if held(row.mortal_entity_id):
            continue
        await ctx.session.delete(row)
        freed += 1
    ctx.session.add(PardonRow(granter_entity_id=ruler.id, pardoned_entity_id=None, case_id=None, amnesty=True, corrupt=False, epoch=ctx.epoch))
    await ctx.session.flush()
    await record(
        ctx,
        "law.amnesty",
        roles={IncidentRole.AUTHORITY: ruler.id, IncidentRole.SUBJECT: polity_id},
        facts={"freed": freed},
        place=ruler.location_id,
    )
    return freed


async def amnesty_due(ctx: TickContext, office: OfficeRow) -> bool:
    if office.holder_entity_id is None:
        return False
    last = await ctx.session.scalar(
        select(PardonRow.epoch)
        .where(PardonRow.granter_entity_id == office.holder_entity_id, PardonRow.amnesty.is_(True))
        .order_by(PardonRow.epoch.desc())
        .limit(1)
    )
    crowned = ctx.epoch - office.since_epoch <= ctx.rules.pardons.amnesty_epochs and last is None
    return crowned or await civil_war_ended(ctx, office.polity_entity_id, last if last is not None else -1)


async def grant_pardons(ctx: TickContext, tally: PardonTally) -> None:
    realms = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for polity_id in list(realms):
        office = await ruler_office(ctx, polity_id)
        ruler = await living_entity(ctx.session, office.holder_entity_id) if office is not None and office.holder_entity_id is not None else None
        if office is None or ruler is None or held(polity_id, ruler.id):
            continue
        if await amnesty_due(ctx, office) and ctx.rng(f"law.amnesty.{polity_id}.{ruler.id}").chance(ctx.rules.pardons.amnesty_pct):
            await declare_amnesty(ctx, polity_id, ruler)
            tally.amnesties += 1
            continue
        await pardon_friends(ctx, polity_id, ruler, tally)
