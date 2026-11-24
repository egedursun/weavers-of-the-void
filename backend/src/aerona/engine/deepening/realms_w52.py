from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.deepened import CLOSED_CASES, KIN_GOALS, MARKED_PRIVILEGES, OPEN_CASES, PERSECUTED, SEEN_FROM_FOREST
from aerona.catalog.life.customs import RIGHTS
from aerona.constants.units import PERCENT
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.collective import MovementRow
from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.customs import EvidenceRow, MembershipRow
from aerona.db.tables.cycles import ConfederationRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.intrigue import IdentityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import AppealRow
from aerona.db.tables.polity import ClaimRow, OathRow, OfficeRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.communication import SignalKind, SignalState
from aerona.domain.enums.customs import EvidenceKind, MemberRight, Membership, Naturalisation
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.faction import EstatePrivilege, FactionGoalKind
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.law_depth import CourtLevel
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis, OathKind, OathStatus
from aerona.domain.enums.titles import TitleTenure, TitleTier
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.intrigue.identities import assume
from aerona.engine.kin_dynamics.book import parents_of
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.oaths import swear
from aerona.engine.polity.titles import found_title
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.engine.services.war import ongoing_wars


@dataclass
class RealmTally:
    rights: int = 0
    adopted: int = 0
    stateless: int = 0
    conquests: int = 0
    leagues: int = 0
    prophecies: int = 0
    appeals: int = 0
    evidence: int = 0
    oaths: int = 0
    goals: int = 0
    privileges: int = 0
    signals: int = 0
    relays: int = 0
    identities: int = 0


async def capital_profile(ctx: TickContext, profile: PolityProfileRow) -> tuple[EntityRow, SettlementProfileRow] | None:
    seat = await living_entity(ctx.session, profile.capital_entity_id) if profile.capital_entity_id is not None else None
    town = await ctx.session.get(SettlementProfileRow, seat.id) if seat is not None else None
    if seat is None or town is None or held(seat.id):
        return None
    return seat, town


def nudge(row: object, field: str, amount: int, key: str, low: int = 0) -> None:
    if not amount or field in getattr(row, "locked", []):
        return
    term(key, amount)
    setattr(row, field, clamp_int(getattr(row, field) + amount, low, PERCENT))


async def keep_rights(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    for profile in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        cats = set(await ctx.session.scalars(select(MembershipRow.category).where(MembershipRow.polity_entity_id == profile.polity_entity_id)))
        rights = {right for category in cats for right in RIGHTS[category]}
        seat = await capital_profile(ctx, profile)
        if seat is None or held(profile.polity_entity_id):
            continue
        town, town_profile = seat
        with explaining():
            if MemberRight.ASSEMBLY in rights:
                nudge(town_profile, "unrest", -table.assembly_calm, "deepened.assembly_calm")
                for movement in await ctx.session.scalars(
                    select(MovementRow).where(MovementRow.settlement_entity_id == town.id, MovementRow.ended_epoch.is_(None))
                ):
                    nudge(movement, "strength", table.assembly_movement, "deepened.assembly_movement")
            if MemberRight.EDUCATION in rights:
                people = await people_of(ctx.session, town)
                culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
                if culture is not None and not held(culture.people_entity_id):
                    nudge(culture, "literacy", table.education_literacy, "deepened.education_literacy")
        tally.rights += 1


async def naturalise_wards(ctx: TickContext, tally: RealmTally) -> None:
    rows = await ctx.session.execute(
        select(HouseholdMemberRow.member_node_id, HouseholdRow.head_node_id)
        .join(HouseholdRow, HouseholdRow.id == HouseholdMemberRow.household_id)
        .where(HouseholdMemberRow.role == HouseholdRole.WARD, HouseholdRow.head_node_id.is_not(None))
        .order_by(HouseholdMemberRow.member_node_id)
    )
    for ward_id, head_id in rows.all():
        head = await ctx.session.scalar(select(MembershipRow).where(MembershipRow.mortal_entity_id == head_id).limit(1))
        if head is None or held(ward_id) or await ctx.session.get(MembershipRow, ward_id) is not None:
            continue
        ctx.session.add(
            MembershipRow(
                mortal_entity_id=ward_id,
                polity_entity_id=head.polity_entity_id,
                category=head.category,
                path=Naturalisation.ADOPTION,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.adopted += 1
        await record(ctx, "deepened.ward_naturalised", roles={IncidentRole.SUBJECT: ward_id, IncidentRole.AUTHORITY: head.polity_entity_id})
    await ctx.session.flush()


async def name_stateless(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(select(FugitiveRow).where(FugitiveRow.caught_epoch.is_(None), FugitiveRow.freed_epoch.is_(None)).order_by(FugitiveRow.id))
    for row in list(rows):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is None or held(mortal.id) or row.pursuer_entity_id is None:
            continue
        known = await ctx.session.scalar(
            select(MembershipRow).where(MembershipRow.mortal_entity_id == mortal.id, MembershipRow.polity_entity_id == row.pursuer_entity_id)
        )
        if known is not None and known.category is not Membership.STATELESS and "category" not in known.locked:
            known.category = Membership.STATELESS
            tally.stateless += 1
            await record(ctx, "deepened.made_stateless", roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.AUTHORITY: row.pursuer_entity_id})
    stateless = await ctx.session.scalars(select(MembershipRow).where(MembershipRow.category == Membership.STATELESS))
    for member in list(stateless):
        mortal = await living_entity(ctx.session, member.mortal_entity_id)
        if mortal is not None and not held(mortal.id) and stat_or(mortal, "wealth", 0) > 0:
            with explaining():
                term("deepened.stateless_loss", -table.stateless_loss)
                shift_stat(mortal, "wealth", -table.stateless_loss)
    await ctx.session.flush()


async def fade_conquests(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    for profile in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        if held(profile.polity_entity_id) or "legitimacy_parts" in profile.locked or profile.core_entity_id is None:
            continue
        parts = dict(profile.legitimacy_parts)
        won = await ongoing_wars(ctx.session, profile.core_entity_id)
        conquest = int(parts.get("conquest", 0))
        if won and not conquest:
            conquest = table.conquest_seed
        if not conquest:
            continue
        joined = profile.legitimacy >= table.conquest_join_at
        faded = conquest * table.conquest_fade_pct // PERCENT
        with explaining():
            term("deepened.conquest_fade", -faded)
            if joined:
                nudge(profile, "legitimacy", faded // 2, "deepened.conquest_joined")
            else:
                nudge(profile, "legitimacy", -faded // 2, "deepened.conquest_faded")
        parts["conquest"] = max(0, conquest - faded)
        profile.legitimacy_parts = parts
        tally.conquests += 1


async def seat_league_heads(ctx: TickContext, tally: RealmTally) -> None:
    book = await RealmBook.load(ctx.session)
    for league in list(await ctx.session.scalars(select(ConfederationRow).where(ConfederationRow.dissolved_epoch.is_(None)).order_by(ConfederationRow.id))):
        realm = book.realm_for(league.leader_entity_id) if league.leader_entity_id is not None else None
        if realm is None or held(realm.entity.id):
            continue
        has = await ctx.session.scalar(
            select(TitleProfileRow.title_entity_id)
            .where(TitleProfileRow.polity_entity_id == realm.entity.id, TitleProfileRow.rank == TitleTier.LEAGUE, TitleProfileRow.destroyed_epoch.is_(None))
            .limit(1)
        )
        if has is not None:
            continue
        title = await found_title(ctx, realm, TitleTier.LEAGUE, TitleTenure.FOUNDED, set(league.members))
        tally.leagues += 1
        await record(
            ctx,
            "deepened.league_seated",
            roles={IncidentRole.SUBJECT: title.title_entity_id, IncidentRole.AUTHORITY: realm.entity.id},
            facts={"members": len(league.members)},
        )


async def weigh_prophecies(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    for claim in list(
        await ctx.session.scalars(select(ClaimRow).where(ClaimRow.basis == ClaimBasis.PROPHECY, ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.id))
    ):
        realm = await living_entity(ctx.session, claim.polity_entity_id)
        if realm is None or held(claim.claimant_entity_id) or "strength" in claim.locked:
            continue
        belief = stat_or(realm, "piety", PERCENT // 2)
        step = round_half_up((belief - claim.strength) * table.prophecy_pull_pct / PERCENT)
        with explaining():
            nudge(claim, "strength", step, "deepened.prophecy_belief")
        tally.prophecies += 1


async def hear_appeals(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    cases = await ctx.session.scalars(
        select(CrimeCaseRow)
        .where(CrimeCaseRow.verdict == Verdict.GUILTY, CrimeCaseRow.wrongful.is_(True), CrimeCaseRow.stage.in_(sorted(CLOSED_CASES)))
        .order_by(CrimeCaseRow.id)
    )
    for case in list(cases):
        if (
            await ctx.session.get(AppealRow, case.id) is not None
            or held(case.polity_entity_id)
            or case.accused_entity_id is None
            or held(case.accused_entity_id)
        ):
            continue
        reversed_ = ctx.rng(f"appeal.{case.id}").chance(table.appeal_reverse_pct)
        ctx.session.add(
            AppealRow(
                case_id=case.id,
                from_court=case.court,
                to_court=CourtLevel.APPELLATE,
                fee=table.appeal_fee,
                filed_epoch=ctx.epoch,
                decided_epoch=ctx.epoch + 1,
                reversed=reversed_,
                locked=[],
            )
        )
        if reversed_ and "wrongful" not in case.locked:
            case.wrongful, case.verdict = False, Verdict.ACQUITTED
            await record(ctx, "deepened.appeal_reversed", roles={IncidentRole.SUBJECT: case.accused_entity_id, IncidentRole.AUTHORITY: case.polity_entity_id})
        tally.appeals += 1
    await ctx.session.flush()


async def gather_evidence(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    for case in list(await ctx.session.scalars(select(CrimeCaseRow).where(CrimeCaseRow.stage.in_(sorted(OPEN_CASES))).order_by(CrimeCaseRow.id))):
        if case.culprit_entity_id is None or held(case.polity_entity_id):
            continue
        kinds = set(await ctx.session.scalars(select(EvidenceRow.kind).where(EvidenceRow.case_id == case.id)))
        town = await living_entity(ctx.session, case.settlement_entity_id)
        people = await people_of(ctx.session, town) if town is not None else None
        culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
        healer = await ctx.session.scalar(
            select(EntityRow.id)
            .where(
                await present_among(ctx.session, [case.settlement_entity_id]),
                EntityRow.mortal_role == MortalRole.HEALER,
                EntityRow.entity_type == EntityType.MORTAL,
            )
            .order_by(EntityRow.id)
            .limit(1)
        )
        found: list[EvidenceKind] = []
        if EvidenceKind.RECORD not in kinds and culture is not None and culture.literacy >= table.record_literacy:
            found.append(EvidenceKind.RECORD)
        if EvidenceKind.BODY not in kinds and healer is not None:
            found.append(EvidenceKind.BODY)
        for kind in found:
            ctx.session.add(
                EvidenceRow(
                    case_id=case.id,
                    kind=kind,
                    points_to_node_id=case.culprit_entity_id,
                    reliability=table.found_reliability,
                    forged=False,
                    sworn=False,
                    found_epoch=ctx.epoch,
                    locked=[],
                )
            )
            tally.evidence += 1
            await record(ctx, "deepened.evidence_found", roles={IncidentRole.SUBJECT: case.culprit_entity_id}, facts={"kind": kind})
    await ctx.session.flush()


async def swear_officers(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    for office in list(await ctx.session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id))):
        holder = await living_entity(ctx.session, office.holder_entity_id)
        if holder is None or held(holder.id):
            continue
        sworn = await ctx.session.scalar(
            select(OathRow.id)
            .where(
                OathRow.swearer_entity_id == holder.id,
                OathRow.kind == OathKind.OFFICE,
                OathRow.recipient_node_id == office.polity_entity_id,
                OathRow.status == OathStatus.SWORN,
            )
            .limit(1)
        )
        if sworn is None and office.since_epoch == ctx.epoch:
            await swear(ctx, holder, OathKind.OFFICE, recipient_id=office.polity_entity_id, note_text="to serve the office faithfully")
            tally.oaths += 1
            continue
        if sworn is not None and "diligence" not in office.locked:
            with explaining():
                nudge(office, "diligence", table.oath_diligence, "deepened.oath_diligence")


async def pursue_goals(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(
        select(FactionGoalRow).where(FactionGoalRow.achieved_epoch.is_(None), FactionGoalRow.kind.in_(sorted(KIN_GOALS))).order_by(FactionGoalRow.id)
    )
    for goal in list(rows):
        faction = await ctx.session.get(FactionProfileRow, goal.faction_entity_id)
        if faction is None or held(goal.faction_entity_id) or faction.home_entity_id is None:
            continue
        if goal.kind is FactionGoalKind.PROTECT_MEMBERS:
            cases = await ctx.session.scalars(
                select(CrimeCaseRow)
                .where(CrimeCaseRow.settlement_entity_id == faction.home_entity_id, CrimeCaseRow.stage.in_(sorted(OPEN_CASES)))
                .order_by(CrimeCaseRow.id)
            )
            for case in list(cases):
                member = await living_entity(ctx.session, case.accused_entity_id) if case.accused_entity_id is not None else None
                if member is not None and member.affiliated_entity_id == faction.faction_entity_id and ctx.rng(f"shield.{case.id}").chance(table.protect_pct):
                    case.evidence = max(0, case.evidence - table.protect_evidence)
                    await record(ctx, "deepened.member_shielded", roles={IncidentRole.ACTOR: faction.faction_entity_id, IncidentRole.SUBJECT: member.id})
            tally.goals += 1
            continue
        spend = min(faction.treasury, table.settle_spend)
        if "treasury" in faction.locked or spend <= 0:
            continue
        with explaining():
            term("deepened.settle_spend", -spend)
            faction.treasury -= spend
            goal.progress = clamp_int(goal.progress + spend * PERCENT // max(1, table.settle_cost), 0, PERCENT)
        if goal.progress >= PERCENT:
            home = await living_entity(ctx.session, faction.home_entity_id)
            if home is not None and not held(home.id):
                settlers = round_half_up(stat_or(home, "population", 0) * table.settle_share_pct / PERCENT)
                shift_stat(home, "population", -settlers)
                goal.achieved_epoch = ctx.epoch
                await record(
                    ctx,
                    "deepened.faction_settled",
                    roles={IncidentRole.ACTOR: faction.faction_entity_id, IncidentRole.ORIGIN: home.id},
                    facts={"settlers": settlers},
                )
        tally.goals += 1


async def keep_privileges(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(
        select(EstatePrivilegeRow).where(EstatePrivilegeRow.privilege.in_(sorted(MARKED_PRIVILEGES))).order_by(EstatePrivilegeRow.estate_entity_id)
    )
    for row in list(rows):
        estate = await ctx.session.get(EstateProfileRow, row.estate_entity_id)
        realm = await ctx.session.get(PolityProfileRow, estate.polity_entity_id) if estate is not None else None
        if estate is None or realm is None or held(row.estate_entity_id):
            continue
        seat = await capital_profile(ctx, realm)
        with explaining():
            if row.privilege is EstatePrivilege.SERVICE_EXEMPTION:
                nudge(estate, "loyalty", table.exempt_loyalty, "deepened.exempt_loyalty")
                if seat is not None and "militia" not in seat[1].locked:
                    cut = seat[1].militia * table.exempt_levy_pct // PERCENT
                    term("deepened.exempt_levy", -cut)
                    seat[1].militia -= cut
            else:
                nudge(estate, "loyalty", table.dress_loyalty, "deepened.dress_loyalty")
                if seat is not None:
                    nudge(seat[1], "unrest", table.dress_resentment, "deepened.dress_resentment")
        tally.privileges += 1


async def restore_signals(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(select(SignalLinkRow).where(SignalLinkRow.state == SignalState.BURNED).order_by(SignalLinkRow.id))
    for row in list(rows):
        if held(row.owner_node_id) or "state" in row.locked or await ongoing_wars(ctx.session, row.owner_node_id):
            continue
        row.state, row.condition = SignalState.RESTORED, table.restored_condition
        tally.signals += 1
        await record(ctx, "deepened.signal_restored", roles={IncidentRole.OWNER: row.owner_node_id}, facts={"kind": row.kind})


async def build_drum_relays(ctx: TickContext, tally: RealmTally) -> None:
    table = ctx.rules.deepened
    beacons = await ctx.session.scalars(
        select(SignalLinkRow).where(SignalLinkRow.kind.in_(sorted(SEEN_FROM_FOREST)), SignalLinkRow.state == SignalState.ACTIVE).order_by(SignalLinkRow.id)
    )
    for row in list(beacons):
        ground = await ctx.session.get(RegionEnvironmentRow, row.from_region_id)
        if ground is None or ground.forest_cover < table.drum_forest_at or held(row.owner_node_id):
            continue
        known = await ctx.session.scalar(
            select(SignalLinkRow.id)
            .where(
                SignalLinkRow.owner_node_id == row.owner_node_id,
                SignalLinkRow.kind == SignalKind.DRUM_RELAY,
                SignalLinkRow.from_region_id == row.from_region_id,
            )
            .limit(1)
        )
        if known is not None:
            continue
        ctx.session.add(
            SignalLinkRow(
                owner_node_id=row.owner_node_id,
                kind=SignalKind.DRUM_RELAY,
                from_region_id=row.from_region_id,
                to_region_id=row.to_region_id,
                state=SignalState.ACTIVE,
                condition=PERCENT,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.relays += 1
        await record(ctx, "deepened.drum_relay_built", roles={IncidentRole.OWNER: row.owner_node_id})
    await ctx.session.flush()


async def protect_kin(ctx: TickContext, tally: RealmTally) -> None:
    hunted = await ctx.session.scalars(
        select(FugitiveRow).where(FugitiveRow.kind.in_(sorted(PERSECUTED)), FugitiveRow.caught_epoch.is_(None)).order_by(FugitiveRow.id)
    )
    for row in list(hunted):
        for kin_id in await parents_of(ctx.session, row.mortal_entity_id):
            kin = await living_entity(ctx.session, kin_id)
            if kin is None or held(kin.id) or await ctx.session.get(IdentityRow, kin.id) is not None:
                continue
            made = await assume(ctx, kin, IdentityReason.PROTECTION, f"{kin.name} of no house", community_id=kin.location_id)
            if made is not None:
                tally.identities += 1
                await record(ctx, "deepened.kin_hidden", roles={IncidentRole.SUBJECT: kin.id, IncidentRole.TARGET: row.mortal_entity_id})


async def deepen_realms(ctx: TickContext, tally: RealmTally) -> None:
    await keep_rights(ctx, tally)
    await naturalise_wards(ctx, tally)
    await name_stateless(ctx, tally)
    await fade_conquests(ctx, tally)
    await seat_league_heads(ctx, tally)
    await weigh_prophecies(ctx, tally)
    await hear_appeals(ctx, tally)
    await gather_evidence(ctx, tally)
    await swear_officers(ctx, tally)
    await pursue_goals(ctx, tally)
    await keep_privileges(ctx, tally)
    await restore_signals(ctx, tally)
    await build_drum_relays(ctx, tally)
    await protect_kin(ctx, tally)
    await ctx.session.flush()
