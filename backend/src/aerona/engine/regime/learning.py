from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.mind import CAREER_SKILLS
from aerona.catalog.structures import RESEARCH_HOUSES
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import IdeologyAdherentRow
from aerona.db.tables.cycles import PolityStressRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.regime import (
    AcademicFreedomRow,
    CredentialRow,
    ExaminationRow,
    ExamSittingRow,
    SchoolLineageRow,
    SchoolMemberRow,
)
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.gathering import AttendanceReason, GatheringKind, GuestRole
from aerona.domain.enums.mind import MemoryKind, SkillKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.regime import CredentialKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.faith.book import faith_tenets
from aerona.engine.gatherings.hold import GatheringTally, hold, plan
from aerona.engine.gatherings.occasions import Guest, Occasion
from aerona.engine.lore.civics import realm_allows
from aerona.engine.lore.research import SCHOLARLY, techniques_of
from aerona.engine.lore.research_depth import add_progress
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.skills import practise
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.offices import adult, subjects
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import definite
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat_or
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.readers import Working, working

EXAMINED = (SkillKind.LAW, SkillKind.WRITING, SkillKind.LORE)
CARRIED = 3
LICENSED_ROLES = frozenset({MortalRole.PHYSICIAN, MortalRole.ENGINEER, MortalRole.PILOT, MortalRole.OFFICER})


@dataclass
class LearningTally:
    sittings: int = 0
    graduates: int = 0
    credentials: int = 0
    suppressed: int = 0
    migrated: int = 0
    schools: int = 0
    taught: int = 0
    rivalries: int = 0


async def best_skill(ctx: TickContext, mortal_id: int, skills: tuple[SkillKind, ...]) -> tuple[SkillKind, int] | None:
    rows = list(await ctx.session.scalars(select(SkillRow).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill.in_(list(skills)))))
    if not rows:
        return None
    best = max(rows, key=lambda row: (row.level, -list(skills).index(row.skill)))
    return best.skill, best.level


async def holds(ctx: TickContext, mortal_id: int, kind: CredentialKind) -> bool:
    found = await ctx.session.scalar(select(CredentialRow.id).where(CredentialRow.mortal_entity_id == mortal_id, CredentialRow.kind == kind).limit(1))
    return found is not None


async def grant(
    ctx: TickContext, mortal: EntityRow, kind: CredentialKind, *, granter_id: int | None, skill: SkillKind | None, tally: LearningTally
) -> CredentialRow:
    row = CredentialRow(mortal_entity_id=mortal.id, kind=kind, granter_node_id=granter_id, skill=skill, epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    mortal.importance = clamp_int((mortal.importance or 0) + ctx.rules.credentials.renown, 0, PERCENT)
    tally.credentials += 1
    await ctx.session.flush()
    return row


async def exam_row(ctx: TickContext, realm: Realm) -> ExaminationRow | None:
    row = await ctx.session.get(ExaminationRow, realm.entity.id)
    if row is None and await realm_allows(ctx.session, realm, Technique.EXAMINATIONS):
        row = ExaminationRow(polity_entity_id=realm.entity.id, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def candidates_of(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    found = 0.0
    for member in book.members(realm):
        shares = await class_shares(ctx.session, ctx.rules, member.id)
        found += stat_or(member, "population", 0) * (shares.get(SocialClass.SCRIBE, 0.0) + shares.get(SocialClass.NOBLE, 0.0)) / PERCENT
    return round_half_up(found * ctx.rules.examinations.candidate_pct / PERCENT)


async def sit(ctx: TickContext, book: RealmBook, realm: Realm, row: ExaminationRow, tally: LearningTally) -> ExamSittingRow | None:
    stress = await ctx.session.get(PolityStressRow, realm.entity.id)
    if stress is not None and "demand" not in row.locked:
        row.demand = stress.elite_overproduction
    if row.last_epoch is not None and ctx.epoch - row.last_epoch < row.interval:
        return None
    return await hold_sitting(ctx, book, realm, row, tally)


async def hold_sitting(ctx: TickContext, book: RealmBook, realm: Realm, row: ExaminationRow, tally: LearningTally) -> ExamSittingRow:
    table = ctx.rules.examinations
    quota = round_half_up(row.quota * (1 + row.demand * table.quota_growth / PERCENT / PERCENT))
    candidates = await candidates_of(ctx, book, realm)
    passed = min(quota, round_half_up(candidates * table.pass_rate / PERCENT))
    sitting = ExamSittingRow(polity_entity_id=realm.entity.id, candidates=candidates, passed=passed, mark=row.pass_mark, epoch=ctx.epoch, locked=[])
    ctx.session.add(sitting)
    if "last_epoch" not in row.locked:
        row.last_epoch = ctx.epoch
    if "quota" not in row.locked:
        row.quota = max(row.quota, quota)
    scored: list[tuple[int, EntityRow, SkillKind]] = []
    for mortal in await subjects(ctx, realm):
        if held(mortal.id) or not adult(ctx, mortal) or await holds(ctx, mortal.id, CredentialKind.EXAMINATION):
            continue
        best = await best_skill(ctx, mortal.id, EXAMINED)
        if best is not None and best[1] >= table.skill_mark:
            scored.append((best[1], mortal, best[0]))
    await gather(ctx, realm, [mortal.id for _, mortal, _ in scored])
    for _, mortal, skill in sorted(scored, key=lambda item: (-item[0], item[1].id))[: table.notable_passes]:
        await grant(ctx, mortal, CredentialKind.EXAMINATION, granter_id=realm.entity.id, skill=skill, tally=tally)
    tally.sittings += 1
    tally.graduates += passed
    await note(ctx, f"{realm.entity.name} held its examinations: {passed} of {candidates} candidates passed.", key="examinations.held", ids=[realm.entity.id])
    await ctx.session.flush()
    return sitting


async def gather(ctx: TickContext, realm: Realm, candidates: list[int]) -> None:
    seat = realm.profile.capital_entity_id
    occasion = Occasion(
        GatheringKind.EXAMINATION,
        realm.entity.id,
        realm.entity.world_id,
        seat,
        None,
        None,
        guests=[Guest(candidate, GuestRole.GUEST, AttendanceReason.SUMMONED) for candidate in candidates],
    )
    row = await plan(ctx, occasion, by_player=False)
    if row is not None:
        await hold(ctx, row, await RegionAtlas.load(ctx.session), GatheringTally())


async def scholars_at(ctx: TickContext, host_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [host_id]))
        .order_by(EntityRow.id)
    )
    return [mortal for mortal in rows if not held(mortal.id)]


async def confer(ctx: TickContext, house: Working, tally: LearningTally) -> None:
    table = ctx.rules.credentials
    host = house.profile.host_entity_id
    if host is None:
        return
    for mortal in await scholars_at(ctx, host):
        best = await best_skill(ctx, mortal.id, SCHOLARLY)
        if best is None:
            continue
        skill, level = best
        if level >= table.master_at and not await holds(ctx, mortal.id, CredentialKind.MASTER):
            await grant(ctx, mortal, CredentialKind.MASTER, granter_id=house.structure.id, skill=skill, tally=tally)
        if house.profile.kind is StructureKind.ACADEMY and level >= table.doctor_at and not await holds(ctx, mortal.id, CredentialKind.DOCTOR):
            await grant(ctx, mortal, CredentialKind.DOCTOR, granter_id=house.structure.id, skill=skill, tally=tally)
        if house.profile.kind is StructureKind.UNIVERSITY and level >= table.degree_at and not await holds(ctx, mortal.id, CredentialKind.DEGREE):
            await grant(ctx, mortal, CredentialKind.DEGREE, granter_id=house.structure.id, skill=skill, tally=tally)


async def license_holders(ctx: TickContext, realm: Realm, tally: LearningTally) -> None:
    table = ctx.rules.credentials
    if not await realm_allows(ctx.session, realm, Technique.WRITTEN_LAW):
        return
    for mortal in await subjects(ctx, realm):
        kind = CredentialKind.COMMISSION if mortal.mortal_role is MortalRole.OFFICER else CredentialKind.LICENCE
        skills = CAREER_SKILLS.get(mortal.mortal_role) if mortal.mortal_role in LICENSED_ROLES else None
        if skills is None or held(mortal.id) or not adult(ctx, mortal) or await holds(ctx, mortal.id, kind):
            continue
        best = await best_skill(ctx, mortal.id, skills)
        mark = table.commission_at if kind is CredentialKind.COMMISSION else table.licence_at
        if best is not None and best[1] >= mark:
            await grant(ctx, mortal, kind, granter_id=realm.entity.id, skill=best[0], tally=tally)


async def ordain(ctx: TickContext, book: RealmBook, temple: Working, tally: LearningTally) -> None:
    host = temple.profile.host_entity_id
    realm = book.realm_of(host)
    if host is None or realm is None or not await realm_allows(ctx.session, realm, Technique.ORGANISED_CLERGY):
        return
    for mortal in await scholars_at(ctx, host):
        if mortal.social_class is not SocialClass.PRIEST or await holds(ctx, mortal.id, CredentialKind.ORDINATION):
            continue
        best = await best_skill(ctx, mortal.id, (SkillKind.THEOLOGY,))
        if best is not None and best[1] >= ctx.rules.credentials.ordain_at:
            await grant(ctx, mortal, CredentialKind.ORDINATION, granter_id=temple.structure.id, skill=best[0], tally=tally)


async def freedom_target(ctx: TickContext, book: RealmBook, host_id: int) -> tuple[int, int | None]:
    table = ctx.rules.academic_freedom
    strictness = await law_param(ctx.session, host_id, LawKind.CENSORSHIP, "strictness")
    level = table.base - (table.censorship_cut * int(strictness) / PERCENT if isinstance(strictness, int) else 0)
    realm = book.realm_of(host_id)
    orthodoxy = None
    if realm is not None:
        church = realm.profile.state_religion_id
        if church is not None and TenetKind.EXCLUSIVITY in await faith_tenets(ctx.session, host_id):
            level -= table.orthodoxy_cut
            orthodoxy = church
        ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
        if ruler is not None:
            level += (await stored_values(ctx.session, ValueHolder.PERSONAL, ruler.id)).get(ValueAxis.KNOWLEDGE, 0) * table.mandate_weight / PERCENT
    return clamp_int(level, 0, PERCENT), orthodoxy


async def weigh_freedom(ctx: TickContext, book: RealmBook, house: Working, tally: LearningTally) -> AcademicFreedomRow | None:
    table = ctx.rules.academic_freedom
    host = house.profile.host_entity_id
    if host is None or held(house.structure.id, host):
        return None
    row = await ctx.session.get(AcademicFreedomRow, house.structure.id)
    if row is None:
        row = AcademicFreedomRow(structure_entity_id=house.structure.id, level=table.base, locked=[])
        ctx.session.add(row)
    target, orthodoxy = await freedom_target(ctx, book, host)
    shift(row, "level", (target - row.level) * table.drift_pct / PERCENT)
    if "orthodoxy_node_id" not in row.locked:
        row.orthodoxy_node_id = orthodoxy
    if "suppressed" not in row.locked:
        row.suppressed = row.level < table.suppress_at
    row.updated_epoch = ctx.epoch
    if row.suppressed:
        tally.suppressed += 1
    return row


async def freest_house(ctx: TickContext, rows: dict[int, tuple[Working, AcademicFreedomRow]], world_id: int | None) -> Working | None:
    found = [
        (row.level, house)
        for house, row in rows.values()
        if not row.suppressed and house.structure.world_id == world_id and house.profile.host_entity_id is not None and not held(house.profile.host_entity_id)
    ]
    return max(found, key=lambda item: (item[0], -item[1].structure.id))[1] if found else None


async def migrate(ctx: TickContext, rows: dict[int, tuple[Working, AcademicFreedomRow]], tally: LearningTally) -> None:
    table = ctx.rules.academic_freedom
    for house, row in sorted(rows.values(), key=lambda item: item[0].structure.id):
        origin = house.profile.host_entity_id
        if not row.suppressed or origin is None:
            continue
        refuge = await freest_house(ctx, rows, house.structure.world_id)
        destination = refuge.profile.host_entity_id if refuge is not None else None
        if destination is None or destination == origin:
            continue
        for mortal in await scholars_at(ctx, origin):
            if await best_skill(ctx, mortal.id, SCHOLARLY) is None or not ctx.rng(f"learning.migrate.{mortal.id}.{ctx.epoch}").chance(table.migrate_pct):
                continue
            mortal.location_id = destination
            lacking = sorted(await techniques_of(ctx.session, origin) - await techniques_of(ctx.session, destination), key=lambda item: item.value)
            for technique in lacking[:CARRIED]:
                await add_progress(ctx, destination, technique, table.carried_progress)
            tally.migrated += 1
            await note(
                ctx, f"{mortal.name} left the stifled learning of their home for a freer house.", key="learning.migrated", ids=[mortal.id, origin, destination]
            )


async def doctrine_of(ctx: TickContext, mortal_id: int) -> int | None:
    found: int | None = await ctx.session.scalar(
        select(IdeologyAdherentRow.ideology_entity_id)
        .where(IdeologyAdherentRow.adherent_entity_id == mortal_id)
        .order_by(IdeologyAdherentRow.strength.desc(), IdeologyAdherentRow.ideology_entity_id)
        .limit(1)
    )
    return found


async def schooled_ids(ctx: TickContext) -> set[int]:
    return set(await ctx.session.scalars(select(SchoolMemberRow.mortal_entity_id)))


async def found_school(ctx: TickContext, host_id: int, members: set[int], tally: LearningTally) -> SchoolLineageRow | None:
    table = ctx.rules.school_lineages
    ranked: list[tuple[int, EntityRow]] = []
    for mortal in await scholars_at(ctx, host_id):
        best = await best_skill(ctx, mortal.id, SCHOLARLY)
        if best is not None and mortal.id not in members:
            ranked.append((best[1], mortal))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    if not ranked or ranked[0][0] < table.found_at or len(ranked) - 1 < table.disciples:
        return None
    master = ranked[0][1]
    school = SchoolLineageRow(
        name=f"School of {master.name}", doctrine_entity_id=await doctrine_of(ctx, master.id), founder_entity_id=master.id, since_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(school)
    await ctx.session.flush()
    ctx.session.add(SchoolMemberRow(school_id=school.id, mortal_entity_id=master.id, generation=0, since_epoch=ctx.epoch, locked=[]))
    for _, disciple in ranked[1 : table.disciples + 1]:
        ctx.session.add(
            SchoolMemberRow(school_id=school.id, mortal_entity_id=disciple.id, master_entity_id=master.id, generation=1, since_epoch=ctx.epoch, locked=[])
        )
        members.add(disciple.id)
    members.add(master.id)
    tally.schools += 1
    await note(ctx, f"{master.name} gathered disciples into {definite(school.name)}.", key="schools.founded", ids=[master.id, host_id])
    await ctx.session.flush()
    return school


async def teach(ctx: TickContext, school: SchoolLineageRow, tally: LearningTally) -> None:
    table = ctx.rules.school_lineages
    rows = list(await ctx.session.scalars(select(SchoolMemberRow).where(SchoolMemberRow.school_id == school.id).order_by(SchoolMemberRow.mortal_entity_id)))
    living = {row.mortal_entity_id: await living_entity(ctx.session, row.mortal_entity_id) for row in rows}
    for row in rows:
        if living[row.mortal_entity_id] is None and not row.locked:
            await ctx.session.delete(row)
    alive = [row for row in rows if living[row.mortal_entity_id] is not None]
    if not alive:
        return
    heir = min(alive, key=lambda row: (row.generation, row.mortal_entity_id))
    if heir.master_entity_id is not None and living.get(heir.master_entity_id) is None and "master_entity_id" not in heir.locked:
        heir.master_entity_id = None
    for row in alive:
        if held(row.mortal_entity_id) or row is heir:
            continue
        if (row.master_entity_id is None or living.get(row.master_entity_id) is None) and "master_entity_id" not in row.locked:
            row.master_entity_id = heir.mortal_entity_id
            if "generation" not in row.locked:
                row.generation = heir.generation + 1
        master = row.master_entity_id
        best = await best_skill(ctx, master, SCHOLARLY) if master is not None else None
        if best is not None:
            await practise(ctx.session, ctx.rules, row.mortal_entity_id, best[0], table.teach_xp, epoch=ctx.epoch)
            tally.taught += 1


async def rival_of(ctx: TickContext, school: SchoolLineageRow, founder: EntityRow, schools: list[SchoolLineageRow]) -> SchoolLineageRow | None:
    for other in schools:
        if other.id == school.id or other.doctrine_entity_id in {None, school.doctrine_entity_id} or other.founder_entity_id is None:
            continue
        other_founder = await living_entity(ctx.session, other.founder_entity_id)
        if other_founder is not None and other_founder.location_id == founder.location_id:
            return other
    return None


async def contend(ctx: TickContext, schools: list[SchoolLineageRow], tally: LearningTally) -> None:
    table = ctx.rules.school_lineages
    for school in schools:
        founder = await living_entity(ctx.session, school.founder_entity_id) if school.founder_entity_id is not None else None
        if founder is None or school.doctrine_entity_id is None:
            continue
        rival = await rival_of(ctx, school, founder, schools)
        if rival is None:
            continue
        if "rival_id" not in school.locked and school.rival_id != rival.id:
            school.rival_id = rival.id
            tally.rivalries += 1
        if rival.founder_entity_id is not None:
            await change_relation(ctx, founder.id, rival.founder_entity_id, -table.rival_regard, MemoryKind.ILL_WILL, note="a rival school")


async def persecuted(ctx: TickContext, school: SchoolLineageRow, rows: dict[int, tuple[Working, AcademicFreedomRow]]) -> bool:
    founder = await living_entity(ctx.session, school.founder_entity_id) if school.founder_entity_id is not None else None
    if founder is None:
        return school.persecuted
    return any(row.suppressed and house.profile.host_entity_id == founder.location_id for house, row in rows.values())


async def keep_learning(ctx: TickContext, tally: LearningTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        row = await exam_row(ctx, realm)
        if row is not None:
            await sit(ctx, book, realm, row, tally)
        await license_holders(ctx, realm, tally)
    houses = await working(ctx.session, RESEARCH_HOUSES)
    rows: dict[int, tuple[Working, AcademicFreedomRow]] = {}
    for house in houses:
        found = await weigh_freedom(ctx, book, house, tally)
        if found is not None:
            rows[house.structure.id] = (house, found)
        await confer(ctx, house, tally)
    for temple in await working(ctx.session, (StructureKind.TEMPLE,)):
        await ordain(ctx, book, temple, tally)
    await migrate(ctx, rows, tally)
    members = await schooled_ids(ctx)
    for host in sorted({house.profile.host_entity_id for house in houses if house.profile.host_entity_id is not None}):
        if not held(host):
            await found_school(ctx, host, members, tally)
    schools = list(await ctx.session.scalars(select(SchoolLineageRow).order_by(SchoolLineageRow.id)))
    for school in schools:
        await teach(ctx, school, tally)
        if "persecuted" not in school.locked:
            school.persecuted = await persecuted(ctx, school, rows)
    await contend(ctx, schools, tally)
    await ctx.session.flush()
