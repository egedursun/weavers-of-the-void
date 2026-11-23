from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.customs import EVIDENCE, EXPERT_SKILLS, PATH_WAIT, RIGHT_GRIEVANCE, RIGHTS
from aerona.catalog.relief import RELIEF_KINDS
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.customs import BorderControlRow, EvidenceRow, MeasureStandardRow, MembershipCategoryRow, MembershipRow, PoorReliefRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society_depth import PolityLoyaltyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import EvidenceKind, MemberRight, Membership, Naturalisation, ReliefKind
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.justice import CaseStage, Deposition
from aerona.domain.enums.mind import PressureKind, Profession
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import OathBreach, OathKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.customs.relief import realm_people
from aerona.engine.demography.cohorts import cohorts_of, row_for
from aerona.engine.faith.book import patron_node
from aerona.engine.law.systems import written_code
from aerona.engine.media.press import recorded_evidence
from aerona.engine.mind.book import pressures_of
from aerona.engine.mortal.kin import spouses_of
from aerona.engine.polity.oaths import break_oath, swear
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import members_of, ruler_of_realm
from aerona.engine.services.war import ongoing_wars, realms_of_side


@dataclass
class CivicsTally:
    evidence: int = 0
    members: int = 0
    naturalised: int = 0
    relieved: int = 0
    frauds: int = 0
    borders: int = 0


async def read_and_confess(ctx: TickContext, case: CrimeCaseRow) -> list[EvidenceRow]:
    table = ctx.rules.evidence
    found: list[EvidenceRow] = []
    rng = ctx.rng(seed_of("evidence.read", case.id, ctx.epoch))
    if case.culprit_entity_id is not None and case.culprit_entity_id == case.accused_entity_id and rng.chance(table.confession_chance):
        found.append(
            EvidenceRow(
                case_id=case.id,
                kind=EvidenceKind.CONFESSION,
                points_to_node_id=case.culprit_entity_id,
                reliability=table.confession_reliability,
                found_epoch=ctx.epoch,
                locked=[],
            )
        )
    if case.settlement_entity_id is not None:
        here = await present_among(ctx.session, [case.settlement_entity_id])
        seer = await ctx.session.scalar(
            select(EntityRow.id).where(here, EntityRow.mortal_role == MortalRole.SEER, EntityRow.status == EntityStatus.CANON).limit(1)
        )
        if seer is not None:
            named = case.culprit_entity_id if case.culprit_entity_id is not None and rng.chance(table.divination_reliability) else case.accused_entity_id
            found.append(
                EvidenceRow(
                    case_id=case.id,
                    kind=EvidenceKind.DIVINATION,
                    points_to_node_id=named,
                    reliability=table.divination_reliability,
                    found_epoch=ctx.epoch,
                    locked=[],
                )
            )
    found.extend(await recorded_evidence(ctx, case))
    return found


SKILL_SCALE = 10


async def expert_evidence(ctx: TickContext, case: CrimeCaseRow) -> EvidenceRow | None:
    if case.culprit_entity_id is None or case.settlement_entity_id is None:
        return None
    found = await ctx.session.execute(
        select(SkillRow.level)
        .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
        .where(
            SkillRow.skill.in_(list(EXPERT_SKILLS)),
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, [case.settlement_entity_id]),
        )
        .order_by(SkillRow.level.desc())
        .limit(1)
    )
    level = next(iter(found.scalars()), None)
    if level is None:
        return None
    reliability = clamp_int(round_half_up(level * SKILL_SCALE * ctx.rules.evidence.expert_skill_pct / PERCENT), 0, PERCENT)
    return EvidenceRow(
        case_id=case.id, kind=EvidenceKind.EXPERT, points_to_node_id=case.culprit_entity_id, reliability=reliability, found_epoch=ctx.epoch, locked=[]
    )


def hearsay(ctx: TickContext, case: CrimeCaseRow) -> EvidenceRow | None:
    if case.accused_entity_id is None:
        return None
    return EvidenceRow(
        case_id=case.id,
        kind=EvidenceKind.HEARSAY,
        points_to_node_id=case.accused_entity_id,
        reliability=ctx.rules.evidence.hearsay_weight // 2,
        found_epoch=ctx.epoch,
        locked=[],
    )


async def sworn_witness(ctx: TickContext, case: CrimeCaseRow, witness_id: int) -> bool:
    witness = await ctx.session.get(EntityRow, witness_id)
    if witness is None or witness.status is not EntityStatus.CANON or held(witness.id):
        return False
    oath = await swear(ctx, witness, OathKind.TESTIMONY, recipient_id=case.polity_entity_id, note_text="sworn before giving evidence")
    lied = case.culprit_entity_id is not None and case.accused_entity_id is not None and case.culprit_entity_id != case.accused_entity_id
    if lied:
        await break_oath(ctx, oath, OathBreach.FALSE_WITNESS, cause=case.id)
        await record(
            ctx,
            "oath.broken",
            roles={IncidentRole.ACTOR: witness.id, IncidentRole.AUTHORITY: case.polity_entity_id, IncidentRole.ACCUSED: case.accused_entity_id},
            facts={"oath": OathKind.TESTIMONY},
            place=case.settlement_entity_id,
        )
    return True


async def weight_of(ctx: TickContext, case: CrimeCaseRow, row: EvidenceRow) -> float:
    spec = EVIDENCE[row.kind]
    base: int = getattr(ctx.rules.evidence, spec.weight)
    weight = base / PERCENT
    if spec.hearsay and await written_code(ctx.session, [holder for holder in (case.polity_entity_id, case.settlement_entity_id) if holder is not None]):
        weight *= ctx.rules.evidence.written_hearsay_pct / PERCENT
    if row.sworn:
        weight *= 1 + ctx.rules.oaths.testimony_weight_pct / PERCENT
    return weight


async def gather_evidence(ctx: TickContext, tally: CivicsTally) -> None:
    table = ctx.rules.evidence
    open_cases = list(
        await ctx.session.scalars(select(CrimeCaseRow).where(CrimeCaseRow.stage.in_([CaseStage.INVESTIGATION, CaseStage.TRIAL])).order_by(CrimeCaseRow.id))
    )
    for case in open_cases:
        if case.settlement_entity_id is not None and held(case.settlement_entity_id):
            continue
        rows = list(await ctx.session.scalars(select(EvidenceRow).where(EvidenceRow.case_id == case.id)))
        if not rows:
            for witness in list(
                await ctx.session.scalars(select(CaseWitnessRow).where(CaseWitnessRow.case_id == case.id, CaseWitnessRow.testimony == Deposition.ACCUSES))
            ):
                rows.append(
                    EvidenceRow(
                        case_id=case.id,
                        kind=EvidenceKind.WITNESS,
                        points_to_node_id=case.accused_entity_id,
                        reliability=witness.reliability,
                        sworn=await sworn_witness(ctx, case, witness.witness_entity_id),
                        found_epoch=ctx.epoch,
                        locked=[],
                    )
                )
            if case.culprit_entity_id is not None:
                rows.append(
                    EvidenceRow(
                        case_id=case.id,
                        kind=EvidenceKind.TRACE,
                        points_to_node_id=case.culprit_entity_id,
                        reliability=table.trace_reliability,
                        found_epoch=ctx.epoch,
                        locked=[],
                    )
                )
            if case.forged:
                rows.append(
                    EvidenceRow(
                        case_id=case.id,
                        kind=EvidenceKind.DOCUMENT,
                        points_to_node_id=case.accused_entity_id,
                        reliability=table.forged_reliability,
                        forged=True,
                        found_epoch=ctx.epoch,
                        locked=[],
                    )
                )
            rows += await read_and_confess(ctx, case)
            rows += [row for row in (await expert_evidence(ctx, case), hearsay(ctx, case)) if row is not None]
            ctx.session.add_all(rows)
            tally.evidence += len(rows)
        else:
            for row in rows:
                if "reliability" not in row.locked and row.found_epoch < ctx.epoch:
                    row.reliability = clamp_int(row.reliability - table.decay - getattr(table, EVIDENCE[row.kind].decay), 0, PERCENT)
        if "evidence" not in case.locked and rows:
            weights = [await weight_of(ctx, case, row) for row in rows]
            against = sum(row.reliability * weight for row, weight in zip(rows, weights, strict=True) if row.points_to_node_id == case.accused_entity_id)
            total = sum(weights) or 1.0
            case.evidence = clamp_int(round_half_up(against / total * table.witness_weight_pct / PERCENT), 0, PERCENT)


async def seed_categories(ctx: TickContext, realm_id: int) -> None:
    if await ctx.session.scalar(select(MembershipCategoryRow.category).where(MembershipCategoryRow.polity_entity_id == realm_id).limit(1)) is not None:
        return
    for category, rights in RIGHTS.items():
        ctx.session.add(MembershipCategoryRow(polity_entity_id=realm_id, category=category, rights=[right.value for right in rights], locked=[]))


async def core_people(ctx: TickContext, realm_id: int) -> int | None:
    ruler = await ruler_of_realm(ctx.session, realm_id)
    ruling = await ctx.session.get(EntityRow, ruler) if ruler is not None else None
    folk = await people_of(ctx.session, ruling) if ruling is not None else None
    return folk.id if folk is not None else None


SERVING = frozenset({MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.CAPTAIN})


async def citizen_spouse(ctx: TickContext, mortal: EntityRow, realm: EntityRow) -> int | None:
    for spouse in sorted(await spouses_of(ctx.session, mortal.id)):
        row = await ctx.session.get(MembershipRow, spouse)
        if row is not None and row.polity_entity_id == realm.id and row.category is Membership.CITIZEN:
            return spouse
    return None


async def path_for(ctx: TickContext, mortal: EntityRow, realm: EntityRow) -> Naturalisation:
    if await citizen_spouse(ctx, mortal, realm) is not None:
        return Naturalisation.UNION
    if mortal.mortal_role in SERVING:
        return Naturalisation.SERVICE
    capital = await ctx.session.get(PolityProfileRow, realm.id)
    patron = await patron_node(ctx.session, capital.capital_entity_id) if capital is not None and capital.capital_entity_id is not None else None
    if patron is not None and await BondRepository(ctx.session).exists_between(mortal.id, patron, BondKind.WORSHIPS):
        return Naturalisation.CONVERSION
    return Naturalisation.RESIDENCE


async def keep_memberships(ctx: TickContext, tally: CivicsTally) -> None:
    table = ctx.rules.citizenship
    realms = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for realm in realms:
        if held(realm.id):
            continue
        await seed_categories(ctx, realm.id)
        core = await core_people(ctx, realm.id)
        rows = await ctx.session.execute(
            select(EntityRow, MortalProfileRow)
            .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
            .where(MortalProfileRow.polity_id == realm.id, EntityRow.status == EntityStatus.CANON)
        )
        for mortal, _ in rows.all():
            if held(mortal.id):
                continue
            row = await ctx.session.get(MembershipRow, mortal.id)
            folk = await people_of(ctx.session, mortal)
            if row is None or row.polity_entity_id != realm.id:
                category = (
                    Membership.BOUND
                    if mortal.social_class is SocialClass.SERF_OR_SLAVE
                    else Membership.CITIZEN
                    if folk is not None and folk.id == core
                    else Membership.RESIDENT_FOREIGNER
                )
                path = Naturalisation.DESCENT if category is Membership.CITIZEN else Naturalisation.BIRTHPLACE
                if row is None:
                    ctx.session.add(
                        MembershipRow(mortal_entity_id=mortal.id, polity_entity_id=realm.id, category=category, path=path, since_epoch=ctx.epoch, locked=[])
                    )
                elif not row.locked:
                    row.polity_entity_id, row.category, row.path, row.since_epoch = realm.id, category, path, ctx.epoch
                tally.members += 1
                continue
            foreign = row.category is Membership.RESIDENT_FOREIGNER and "category" not in row.locked
            path = await path_for(ctx, mortal, realm)
            if (
                foreign
                and ctx.epoch - row.since_epoch >= table.residence_epochs * PATH_WAIT[path] // PERCENT
                and ctx.rng(seed_of("naturalise", mortal.id, ctx.epoch)).chance(table.naturalise_chance)
            ):
                row.category, row.path, row.since_epoch = Membership.CITIZEN, path, ctx.epoch
                row.spouse_entity_id = await citizen_spouse(ctx, mortal, realm) if path is Naturalisation.UNION else None
                tally.naturalised += 1
                await record(
                    ctx,
                    "membership.gained",
                    roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.AUTHORITY: realm.id, IncidentRole.SPOUSE: row.spouse_entity_id},
                    facts={"way": path},
                )


async def spend_relief(ctx: TickContext, tally: CivicsTally) -> None:
    for row in list(await ctx.session.scalars(select(PoorReliefRow).order_by(PoorReliefRow.polity_entity_id))):
        if held(row.polity_entity_id):
            continue
        profile = await ctx.session.get(PolityProfileRow, row.polity_entity_id)
        if profile is None or "treasury" in profile.locked:
            continue
        paid = min(row.budget, max(0, profile.treasury))
        profile.treasury -= paid
        if paid < row.budget and "reach" not in row.locked:
            row.reach = clamp_int(row.reach * paid // max(1, row.budget), 0, PERCENT)
        tally.relieved += 1
        if paid > 0:
            await relieve_kind(ctx, row)


async def take_in(ctx: TickContext, town: EntityRow, condition: CohortCondition, share: int) -> int:
    rows = await cohorts_of(ctx.session, town.id)
    moved = 0
    for key in sorted((key for key in rows if key[3] is condition), key=lambda item: tuple(part.value for part in item)):
        count = round_half_up(rows[key].count * share / PERCENT)
        if count > 0 and move_amount(rows[key], row_for(ctx.session, rows, town.id, (key[0], key[1], key[2], CohortCondition.NONE), ctx.epoch), "count", count):
            moved += count
    return moved


async def relieve_kind(ctx: TickContext, row: PoorReliefRow) -> int:
    spec = RELIEF_KINDS[row.kind]
    share = int(getattr(ctx.rules.relief, spec.effect)) * row.reach // PERCENT
    helped = 0
    for member_id in await members_of(ctx.session, row.polity_entity_id):
        town = await ctx.session.get(EntityRow, member_id)
        if town is None or held(town.id):
            continue
        if spec.takes_in is not None:
            helped += await take_in(ctx, town, spec.takes_in, share)
        if spec.pays_loyalty:
            loyalty = await ctx.session.get(PolityLoyaltyRow, (row.polity_entity_id, town.id))
            if loyalty is not None and "benefits" not in loyalty.locked:
                loyalty.benefits += share
                helped += share
    if helped > 0:
        await record(ctx, "relief.given", roles={IncidentRole.AUTHORITY: row.polity_entity_id}, facts={"kind": row.kind, "helped": helped})
    return helped


async def needed_relief(ctx: TickContext, members: list[int]) -> ReliefKind | None:
    orphans = sick = 0
    for member_id in members:
        rows = await cohorts_of(ctx.session, member_id)
        orphans += sum(item.count for key, item in rows.items() if key[3] is CohortCondition.ORPHANED)
        sick += sum(item.count for key, item in rows.items() if key[3] is CohortCondition.SICK)
    if orphans > sick and orphans > 0:
        return ReliefKind.FOSTER_CARE
    if sick > 0:
        return ReliefKind.SICK_HOUSE
    return None


async def adopt_relief(ctx: TickContext) -> None:
    table = ctx.rules.poor_relief
    for realm in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(realm.id) or await ctx.session.get(PoorReliefRow, realm.id) is not None:
            continue
        members = await members_of(ctx.session, realm.id)
        poverty = [(await pressures_of(ctx.session, member)).get(PressureKind.POVERTY, 0) for member in members]
        profile = await ctx.session.get(PolityProfileRow, realm.id)
        if not poverty or sum(poverty) / len(poverty) < table.adopt_from or profile is None:
            continue
        needed = await needed_relief(ctx, members)
        kind = needed if needed is not None else ctx.rng(seed_of("relief", realm.id)).pick([item for item, spec in RELIEF_KINDS.items() if spec.eases_poverty])
        cost = max(table.adopt_budget, int(getattr(ctx.rules.relief, RELIEF_KINDS[kind].cost)))
        budget = max(1, round_half_up(cost * await realm_people(ctx.session, realm.id) / PER_MILLE))
        if profile.treasury >= budget:
            ctx.session.add(PoorReliefRow(polity_entity_id=realm.id, kind=kind, budget=budget, reach=table.adopt_reach, locked=[]))
            await record(ctx, "relief.given", roles={IncidentRole.AUTHORITY: realm.id}, facts={"kind": kind, "helped": 0})


async def keep_measures(ctx: TickContext, tally: CivicsTally) -> None:
    table = ctx.rules.measures
    for realm in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(realm.id):
            continue
        row = await ctx.session.get(MeasureStandardRow, realm.id)
        if row is None:
            members = await members_of(ctx.session, realm.id)
            if len(members) < table.adopt_members and await realm_people(ctx.session, realm.id) < table.adopt_population:
                continue
            row = MeasureStandardRow(polity_entity_id=realm.id, standard=True, adopted_epoch=ctx.epoch, fraud=table.adopt_fraud, locked=[])
            ctx.session.add(row)
        if not row.fraud or not ctx.rng(seed_of("fraud", realm.id, ctx.epoch)).chance(table.fraud_chance * row.fraud / PERCENT):
            continue
        merchants = await ctx.session.scalars(
            select(EntityRow)
            .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
            .where(MortalProfileRow.polity_id == realm.id, MortalProfileRow.profession == Profession.MERCHANT, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
            .limit(1)
        )
        cheat = merchants.first()
        if (
            cheat is not None
            and cheat.location_id is not None
            and not held(cheat.id)
            and await report_crime(ctx, cheat.location_id, cheat.id, CrimeKind.THEFT) is not None
        ):
            tally.frauds += 1


async def adopt_borders(ctx: TickContext, tally: CivicsTally) -> None:
    table = ctx.rules.borders
    for war in await ongoing_wars(ctx.session):
        for side in war.sides:
            for realm in sorted(await realms_of_side(ctx.session, side)):
                if held(realm) or await ctx.session.get(BorderControlRow, realm) is not None:
                    continue
                ctx.session.add(BorderControlRow(polity_entity_id=realm, fee=PERCENT // 2, delay=table.war_delay, enforcement=table.war_enforcement, locked=[]))
                await ctx.session.flush()
                tally.borders += 1


RIGHTS_FIXUP = "membership.w52"
TEN = 10


async def widen_rights(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, RIGHTS_FIXUP) is not None:
        return 0
    widened = 0
    for row in list(await ctx.session.scalars(select(MembershipCategoryRow).order_by(MembershipCategoryRow.polity_entity_id, MembershipCategoryRow.category))):
        if "rights" in row.locked:
            continue
        due = sorted({*row.rights, *(right.value for right in RIGHTS[row.category] if right.value not in row.rights)})
        if due != sorted(row.rights):
            row.rights = due
            widened += 1
    ctx.session.add(AppliedFixupRow(key=RIGHTS_FIXUP, result={"categories": widened}))
    await ctx.session.flush()
    return widened


async def lacking_rights(ctx: TickContext) -> None:
    table = ctx.rules.membership
    lacking: dict[tuple[int, Membership], int] = {}
    for row in await ctx.session.scalars(select(MembershipCategoryRow)):
        missing = [right for right in MemberRight if right.value not in row.rights]
        lacking[(row.polity_entity_id, row.category)] = sum(getattr(table, RIGHT_GRIEVANCE[right]) for right in missing)
    towns: dict[int, int] = {}
    members = await ctx.session.execute(
        select(MembershipRow.polity_entity_id, MembershipRow.category, EntityRow.location_id)
        .join(EntityRow, EntityRow.id == MembershipRow.mortal_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        .order_by(MembershipRow.mortal_entity_id)
    )
    for polity_id, category, town_id in members.all():
        grievance = lacking.get((polity_id, category), 0)
        if grievance and town_id is not None:
            towns[town_id] = max(towns.get(town_id, 0), grievance)
    for town_id, grievance in sorted(towns.items()):
        town = await ctx.session.get(SettlementProfileRow, town_id)
        if town is not None and not held(town_id) and "unrest" not in (town.locked or []):
            town.unrest = clamp_int(town.unrest + grievance // TEN, 0, PERCENT)


async def keep_civics(ctx: TickContext, tally: CivicsTally) -> None:
    await widen_rights(ctx)
    await gather_evidence(ctx, tally)
    await adopt_borders(ctx, tally)
    await keep_memberships(ctx, tally)
    await lacking_rights(ctx)
    await adopt_relief(ctx)
    await spend_relief(ctx, tally)
    await keep_measures(ctx, tally)
    await ctx.session.flush()
