from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.customs import BorderControlRow, EvidenceRow, MeasureStandardRow, MembershipCategoryRow, MembershipRow, PoorReliefRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import EvidenceKind, MemberRight, Membership, Naturalisation, ReliefKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.justice import CaseStage, Deposition
from aerona.domain.enums.mind import PressureKind, Profession
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.faith.book import patron_node
from aerona.engine.mind.book import pressures_of
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.renown.currencies import members_of, ruler_of_realm
from aerona.engine.services.war import ongoing_wars, realms_of_side

RIGHTS: Mapping[Membership, tuple[MemberRight, ...]] = {
    Membership.CITIZEN: tuple(MemberRight),
    Membership.SUBJECT: (MemberRight.MARRIAGE, MemberRight.COURTS, MemberRight.ARMS),
    Membership.RESIDENT_FOREIGNER: (MemberRight.MARRIAGE, MemberRight.COURTS),
    Membership.PROTECTED_MINORITY: (MemberRight.MARRIAGE, MemberRight.COURTS),
    Membership.BOUND: (),
}


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
    return found


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
            for witness in await ctx.session.scalars(
                select(CaseWitnessRow).where(CaseWitnessRow.case_id == case.id, CaseWitnessRow.testimony == Deposition.ACCUSES)
            ):
                rows.append(
                    EvidenceRow(
                        case_id=case.id,
                        kind=EvidenceKind.WITNESS,
                        points_to_node_id=case.accused_entity_id,
                        reliability=witness.reliability,
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
            ctx.session.add_all(rows)
            tally.evidence += len(rows)
        else:
            for row in rows:
                if "reliability" not in row.locked and row.found_epoch < ctx.epoch:
                    row.reliability = clamp_int(row.reliability - table.decay, 0, PERCENT)
        if "evidence" not in case.locked and rows:
            against = sum(row.reliability for row in rows if row.points_to_node_id == case.accused_entity_id)
            case.evidence = clamp_int(round_half_up(against / len(rows) * table.witness_weight_pct / PERCENT), 0, PERCENT)


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
PATH_WAIT: Mapping[Naturalisation, int] = total(
    Naturalisation,
    {
        Naturalisation.DESCENT: 0,
        Naturalisation.BIRTHPLACE: 0,
        Naturalisation.RESIDENCE: 100,
        Naturalisation.CONVERSION: 50,
        Naturalisation.SERVICE: 50,
        Naturalisation.PURCHASE: 0,
        Naturalisation.GRANT: 0,
    },
)


async def path_for(ctx: TickContext, mortal: EntityRow, realm: EntityRow) -> Naturalisation:
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
                tally.naturalised += 1


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
        if poverty and sum(poverty) / len(poverty) >= table.adopt_from and profile is not None and profile.treasury >= table.adopt_budget:
            kind = ctx.rng(seed_of("relief", realm.id)).pick(list(ReliefKind))
            ctx.session.add(PoorReliefRow(polity_entity_id=realm.id, kind=kind, budget=table.adopt_budget, reach=table.adopt_reach, locked=[]))


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
            if len(members) < table.adopt_members:
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


async def keep_civics(ctx: TickContext, tally: CivicsTally) -> None:
    await gather_evidence(ctx, tally)
    await adopt_borders(ctx, tally)
    await keep_memberships(ctx, tally)
    await adopt_relief(ctx)
    await spend_relief(ctx, tally)
    await keep_measures(ctx, tally)
    await ctx.session.flush()
