from sqlalchemy import select

from aerona.catalog.intrigue import SCHEMES
from aerona.db.tables.intrigue import IdentityRow, SchemeRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import FavourOrigin, HookSource, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.intrigue.favours import owe
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.names import confide_names, name_bearer
from aerona.engine.intrigue.schemes import begin_scheme, recruit, unmask
from aerona.engine.intrigue.secrets import grant_hook, keep_secret
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.polity.treaties import answer_call
from aerona.engine.polity.trials import report_crime, uncover
from aerona.engine.relations.book import ensure_relation
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned


async def test_a_schemer_recruits_friends_then_hooks_and_debtors_then_paid_hands(realm: Realm) -> None:
    ctx = context(realm.session, tuned(intrigue={"agent_wage": 10}))
    town = await settlement(realm, "Gullhaven")
    plotter = await mortal(realm, "Rhea", location_id=town.id)
    rival = await mortal(realm, "Sorrel", location_id=town.id)
    hooked = await mortal(realm, "Tibb", location_id=town.id)
    debtor = await mortal(realm, "Una", location_id=town.id)
    hired = await mortal(realm, "Vasco", location_id=town.id)
    await grant_hook(ctx, plotter.id, hooked.id, HookSource.DEBT, strong=True)
    await owe(ctx, debtor.id, plotter.id, FavourOrigin.GIFT, 20)
    friendship = await ensure_relation(realm.session, debtor.id, plotter.id, ctx.epoch)
    assert friendship is not None
    friendship.friendship = 50
    purse, _ = await ensure_profile(realm.session, plotter.id, ctx.epoch)
    purse.wealth = 100
    await ensure_profile(realm.session, hired.id, ctx.epoch)
    scheme = await begin_scheme(ctx, plotter, PlotKind.COUP, rival)
    assert scheme is not None and SCHEMES[PlotKind.COUP].agents == 3
    await recruit(ctx, scheme)
    assert scheme.agents[:2] == [hooked.id, debtor.id] and len(scheme.agents) == 3
    assert hired.id in scheme.agents and purse.wealth == 90


async def test_an_uncovered_scheme_exposes_its_agents(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Wexmoor")
    plotter = await mortal(realm, "Xan", location_id=town.id)
    agent = await mortal(realm, "Yew", location_id=town.id)
    target = await mortal(realm, "Zil", location_id=town.id)
    scheme = await begin_scheme(ctx, plotter, PlotKind.SWAY, target)
    assert scheme is not None
    scheme.agents = [agent.id]
    await unmask(ctx, scheme, target)
    assert scheme.phase is SchemePhase.EXPOSED
    grudge = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == target.id, MemoryRow.subject_node_id == agent.id))
    assert grudge is not None and grudge.kind is MemoryKind.BETRAYED_ME


async def test_an_investigation_uncovers_the_culprit_s_secrets_and_traces_a_false_name(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Ashcombe")
    culprit = await mortal(realm, "Abel", location_id=town.id)
    sleuth = await mortal(realm, "Brisk", location_id=town.id)
    secret = await keep_secret(ctx, culprit.id, IntrigueSecret.CRIME)
    assert secret is not None
    await assume(ctx, culprit, IdentityReason.EXILE, "Adler", cover_role="tinker", community_id=town.id)
    case = await report_crime(ctx, town.id, culprit.id, CrimeKind.THEFT)
    assert case is not None and case.stage is CaseStage.INVESTIGATION and case.culprit_entity_id == culprit.id
    assert await uncover(ctx, case, culprit.id, sleuth.id) == 1
    assert sleuth.id in secret.known_by
    mask = await realm.session.get(IdentityRow, culprit.id)
    assert mask is not None and mask.exposure == ctx.rules.intrigue.identity_investigation
    assert await realm.session.get(CrimeCaseRow, case.id) is case


async def test_a_mortal_confides_a_true_name_to_an_intimate_friend(realm: Realm) -> None:
    ctx = context(realm.session, tuned(intrigue={"confide_name_pct": 100}))
    town = await settlement(realm, "Cindral")
    bearer = await mortal(realm, "Dov", location_id=town.id)
    friend = await mortal(realm, "Esme", location_id=town.id)
    row = await name_bearer(ctx, bearer.id, "Dov-Atharen")
    assert row is not None
    close = await ensure_relation(realm.session, bearer.id, friend.id, ctx.epoch)
    assert close is not None
    close.friendship = 90
    await realm.session.flush()
    assert await confide_names(ctx) == 1
    assert friend.id in row.known_by


async def test_a_debt_brings_an_ally_who_would_not_have_answered_the_call(realm: Realm) -> None:
    ctx = context(realm.session, tuned(treaties={"call_to_arms_chance": 0}))
    caller_town = await settlement(realm, "Fennick")
    ally_town = await settlement(realm, "Gorse")
    caller_realm = await make(realm.session, "Realm of Fennick", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    ally_realm = await make(realm.session, "Realm of Gorse", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    caller = await mortal(realm, "Hale", location_id=caller_town.id)
    answerer = await mortal(realm, "Iver", location_id=ally_town.id)
    for polity, town, ruler in ((caller_realm, caller_town, caller), (ally_realm, ally_town, answerer)):
        realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
        realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    await realm.session.flush()
    assert not await answer_call(ctx, ally_town.id, caller_town.id)
    await grant_hook(ctx, caller.id, answerer.id, HookSource.FAVOUR, strong=True)
    assert await answer_call(ctx, ally_town.id, caller_town.id)


async def test_sabotage_of_the_land_is_judged_as_desecration() -> None:
    assert SCHEMES[PlotKind.ECOSABOTAGE].act is ActKind.DESECRATION
    assert SCHEMES[PlotKind.ECOSABOTAGE].secret is IntrigueSecret.ECOSABOTAGE
    assert SchemeRow.__tablename__ == "schemes"
