from sqlalchemy import select

from aerona.catalog.life.demography import GROWN_BANDS
from aerona.catalog.mobility import MOBILITY_EVENTS
from aerona.constants.units import PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import CohortRow, PeopleCultureRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import OutlawRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cycles import ManumissionPath
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import DebtRemedy, LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import MobilityEvent
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.collective.demography import diaspora_pull
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import at_war
from aerona.engine.cycles.indenture import freed_class, indentured_in, manumission_path, record_manumission
from aerona.engine.demography.bound import BOUND, bound_share, move_people, sync_bound_share
from aerona.engine.demography.cohorts import CohortKey, cohorts_of, row_for
from aerona.engine.demography.events import ennobled, enslaved, freed, moved_class, ruined
from aerona.engine.faith.book import faith_tenets
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.law.prisons import imprison
from aerona.engine.military.units import resize
from aerona.engine.mind.book import values_for
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.levies import demobilise
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import held_captive, take_captive
from aerona.rules.registry import Rules

LEAN = 25


def inequality(society: CommunitySocietyRow) -> int:
    return society.gini


def inequality_pressure(rules: Rules, society: CommunitySocietyRow | None, hierarchy: int) -> int:
    if society is None:
        return 0
    table = rules.mobility
    tolerance = max(0.0, hierarchy / PERCENT) * table.hierarchy_tolerance_pct / PERCENT
    return clamp_int(inequality(society) * table.inequality_crime_pct / PERCENT * (1 - tolerance), 0, PERCENT)


async def settle_captives(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow], lawful: bool) -> int:
    table = ctx.rules.mobility
    bound = 0
    for key in sorted(rows, key=lambda item: tuple(part.value for part in item)):
        band, sex, _social, condition = key
        if condition is not CohortCondition.CAPTIVE or rows[key].count <= 0:
            continue
        count = rows[key].count
        freed_captives = round_half_up(count * table.enslave_captives_pct / PERCENT) if lawful else 0
        rows[key].count = 0
        if freed_captives:
            row_for(ctx.session, rows, community.id, (band, sex, BOUND, CohortCondition.ENSLAVED), ctx.epoch).count += freed_captives
        if count - freed_captives:
            row_for(ctx.session, rows, community.id, (band, sex, SocialClass.FARMER, CohortCondition.NONE), ctx.epoch).count += count - freed_captives
        bound += freed_captives
    return bound


async def manumit(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow], lawful: bool) -> tuple[int, ManumissionPath | None]:
    table = ctx.rules.mobility
    if lawful and not ctx.rng(f"manumission.{community.id}").chance(table.manumission_chance):
        return 0, None
    share = table.manumission_pct / PERCENT if lawful else 1.0
    path = await manumission_path(ctx, community, lawful, await at_war(ctx, {community.id}))
    loosed = await move_people(ctx, community, rows, source=BOUND, target=freed_class(path), share=share)
    await record_manumission(ctx, community, loosed, path)
    return loosed, path


async def slavery_costs(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow], culture: PeopleCultureRow | None) -> None:
    table = ctx.rules.mobility
    if bound_share(rows) <= 0:
        return
    if culture is not None and "cohesion" not in culture.locked:
        culture.cohesion = max(0, culture.cohesion - table.slavery_cohesion_loss)
    holder = await people_of(ctx.session, community)
    if holder is None:
        return
    for bond in await active_bonds(ctx.session, [BondKind.ALLY, BondKind.ENEMY, BondKind.PAYS_TRIBUTE], sources=[holder.id]):
        other = await living_entity(ctx.session, bond.target_node_id)
        if other is None or other.entity_type is not EntityType.PEOPLE:
            continue
        if (await culture_of(ctx.session, other.id)).get(ValueAxis.XENOPHILIA, 0) >= LEAN:
            await change_relation(ctx, other.id, holder.id, -table.slavery_opinion_loss, MemoryKind.ILL_WILL, note="keeps slaves")


async def desertion(ctx: TickContext) -> int:
    table = ctx.rules.mobility
    deserted = 0
    for row in await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)):
        army = await living_entity(ctx.session, row.entity_id)
        owner = await living_entity(ctx.session, row.owner_entity_id)
        society = await ctx.session.get(CommunitySocietyRow, row.owner_entity_id)
        if army is None or owner is None or society is None or society.satisfaction(SocialClass.WARRIOR) >= table.bitter_satisfaction:
            continue
        size = stat(army, "size") or 0
        leaving = round_half_up(size * table.desertion_pct / PERCENT)
        if leaving <= 0:
            continue
        returned = demobilise(ctx.rules, owner, leaving)
        with flowing(FlowCategory.LEVY):
            set_stats(army, size=size - returned)
        with flowing(FlowCategory.DEATH):
            await resize(ctx.session, ctx.rules, army, size - leaving)
        deserted += leaving
        await record_incident(
            ctx,
            "society.desertion",
            roles={IncidentRole.SUBJECT: army.id, IncidentRole.OWNER: owner.id},
            facts={"deserters": leaving, "returned": returned},
            terms=[Term("rules.mobility.desertion_pct", table.desertion_pct)],
        )
    return deserted


async def bitter_emigration(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow], society: CommunitySocietyRow | None) -> int:
    table = ctx.rules.mobility
    if society is None:
        return 0
    bitter = [
        social_class for social_class in SocialClass if society.share(social_class) > 0 and society.satisfaction(social_class) < table.bitter_satisfaction
    ]
    if not bitter:
        return 0
    people = await people_of(ctx.session, community)
    if people is None:
        return 0
    homes = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[people.id])]
    best: EntityRow | None = None
    best_mood = -1.0
    for home_id in homes:
        home = await living_entity(ctx.session, home_id)
        other = await ctx.session.get(CommunitySocietyRow, home_id)
        if home is None or other is None or home.id == community.id or home.entity_type is not EntityType.SETTLEMENT:
            continue
        mood = sum(other.satisfaction(social_class) for social_class in bitter) / len(bitter)
        mood *= await diaspora_pull(ctx.session, ctx.rules.diaspora.pull_pct, people.id, home.id)
        if mood > best_mood:
            best, best_mood = home, mood
    if best is None or best_mood < table.bitter_satisfaction:
        return 0
    leaving = sum(
        round_half_up(row.count * table.desertion_pct / PERCENT)
        for key, row in rows.items()
        if key[2] in bitter and key[0] in GROWN_BANDS and key[3] is CohortCondition.NONE
    )
    population = stat(community, "population") or 0
    leaving = min(max(0, leaving - await indentured_in(ctx.session, community.id)), population // 10)
    if leaving <= 0:
        return 0
    with flowing(FlowCategory.MIGRATION):
        set_stats(community, population=population - leaving)
        set_stats(best, population=(stat(best, "population") or 0) + leaving)
    return leaving


async def ennoble_heroes(ctx: TickContext) -> int:
    table = ctx.rules.mobility
    raised = 0
    battles = await ctx.session.scalars(select(BattleRow).where(BattleRow.epoch == ctx.epoch).order_by(BattleRow.id))
    winners = {battle.winner_entity_id for battle in battles}
    if not winners:
        return 0
    armies = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.owner_entity_id.in_(winners), ArmyRow.commander_entity_id.is_not(None)))
    for army in armies:
        hero = await living_entity(ctx.session, army.commander_entity_id) if army.commander_entity_id is not None else None
        if hero is None or hero.social_class is SocialClass.NOBLE or not ctx.rng(f"ennoble.{hero.id}").chance(table.ennoble_chance):
            continue
        hero.social_class = SocialClass.NOBLE
        raised += 1
        await ennobled(ctx, hero, await living_entity(ctx.session, army.owner_entity_id))
    return raised


async def shift_classes(ctx: TickContext) -> int:
    table = ctx.rules.mobility
    moved = 0
    mortals = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    outlaws = set(await ctx.session.scalars(select(OutlawRow.mortal_entity_id)))
    enriching = MOBILITY_EVENTS[MobilityEvent.ENRICHED].from_classes
    for mortal in list(mortals):
        if held(mortal.id):
            continue
        if mortal.id in outlaws and mortal.social_class is not SocialClass.OUTCAST:
            moved += await moved_class(ctx, mortal, MobilityEvent.OUTCAST, cause="declared an outlaw")
        elif mortal.mortal_role is MortalRole.PRIEST and mortal.social_class not in (SocialClass.PRIEST, SocialClass.MONASTIC):
            moved += await moved_class(ctx, mortal, MobilityEvent.ORDAINED, cause="took up the service of a faith")
        elif mortal.social_class in enriching and stat_or(mortal, "wealth", 0) >= table.enrich_threshold:
            hierarchy = (await values_for(ctx.session, mortal.location_id or mortal.id)).get(ValueAxis.HIERARCHY, 0)
            if hierarchy <= table.enrich_hierarchy_max:
                moved += await moved_class(ctx, mortal, MobilityEvent.ENRICHED, cause="grew rich")
    return moved


async def debtors_prison(ctx: TickContext, lender: EntityRow, member: EntityRow) -> None:
    if await imprison(ctx, member) is None:
        await take_captive(ctx, lender, member, None, description="held in debtors' prison", home_id=member.location_id)


async def ruin_merchants(ctx: TickContext) -> int:
    table = ctx.rules.mobility
    fallen = 0
    loans = await ctx.session.scalars(select(LoanRow).where(LoanRow.status == LoanStatus.DEFAULTED, LoanRow.due_epoch >= ctx.epoch - 1))
    for loan in loans:
        borrower = await living_entity(ctx.session, loan.borrower_entity_id)
        if borrower is None or borrower.entity_type is not EntityType.FACTION or borrower.social_class is not SocialClass.MERCHANT:
            continue
        members = await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == borrower.id)
        )
        for member_id in members:
            member = await living_entity(ctx.session, member_id)
            if member is None or member.entity_type is not EntityType.MORTAL or member.status is not EntityStatus.CANON:
                continue
            if member.social_class is SocialClass.OUTCAST or not ctx.rng(f"ruin.{member.id}.{loan.id}").chance(table.ruin_chance):
                continue
            remedy = await law_param(ctx.session, member.location_id or 0, LawKind.DEBT_LAW, "remedy")
            if remedy == DebtRemedy.JUBILEE.value:
                continue
            member.social_class = SocialClass.SERF_OR_SLAVE if remedy == DebtRemedy.BONDAGE.value else SocialClass.OUTCAST
            lender = await living_entity(ctx.session, loan.lender_entity_id)
            if remedy == DebtRemedy.PRISON.value and lender is not None and await held_captive(ctx.session, member.id) is None:
                await debtors_prison(ctx, lender, member)
            fallen += 1
            await ruined(ctx, member, borrower)
    return fallen


async def lay_down_arms(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow]) -> int:
    if TenetKind.PACIFISM not in await faith_tenets(ctx.session, community.id):
        return 0
    table = ctx.rules.doctrine
    share = (1 - table.pacifist_warrior_pct / PERCENT) * table.pacifist_drift_pct / PERCENT
    return await move_people(ctx, community, rows, source=SocialClass.WARRIOR, target=SocialClass.FARMER, share=share)


async def class_mobility(ctx: TickContext, community: EntityRow) -> dict[str, int]:
    rows = await cohorts_of(ctx.session, community.id)
    if not rows:
        return {}
    people = await people_of(ctx.session, community)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    lawful = culture.slavery_lawful if culture is not None else False
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    bound = await settle_captives(ctx, community, rows, lawful)
    loosed, path = await manumit(ctx, community, rows, lawful)
    await enslaved(ctx, community, bound)
    await freed(ctx, community, loosed, path=path)
    counts = {
        "enslaved": bound,
        "freed": loosed,
        "emigrated": await bitter_emigration(ctx, community, rows, society),
        "laid_down_arms": await lay_down_arms(ctx, community, rows),
    }
    await slavery_costs(ctx, community, rows, culture)
    sync_bound_share(society, rows)
    return counts


def bound_revolt(rules: Rules, rows: dict[CohortKey, CohortRow]) -> int:
    return clamp_int(bound_share(rows) * PERCENT * rules.mobility.slavery_revolt_pct / PERCENT, 0, PERCENT)
