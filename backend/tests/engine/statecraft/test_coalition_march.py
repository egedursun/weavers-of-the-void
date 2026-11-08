from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.coalitions import AGAINST, CoalitionTally, coalitions_against, members_of, tend_coalitions
from aerona.engine.primitives.stats import set_stats
from tests.engine.society.factories import Realm, bonded, context, tuned
from tests.engine.statecraft.crowns import crown

MARCHING = tuned(statecraft={"coalition_war_pct": 100})


async def coalition(realm: Realm, target_core: int, cores: list[int]) -> int:
    ctx = context(realm.session)
    treaty = await sign(
        ctx,
        TreatyKind.COALITION,
        [(core, PartyRole.SIGNATORY) for core in cores],
        clauses=[Clause(ClauseKind.CALL_TO_ARMS, core, None, {AGAINST: target_core}) for core in cores],
    )
    return treaty.id


async def test_a_stronger_coalition_marches_on_the_realm_it_fears(realm: Realm) -> None:
    _, target_core = await crown(realm, "Iron Crown")
    _, first = await crown(realm, "Reed Throne")
    _, second = await crown(realm, "Brook Throne")
    treaty_id = await coalition(realm, target_core.id, [second.id, first.id])
    assert await members_of(context(realm.session), treaty_id) == sorted([first.id, second.id])
    assert await coalitions_against(context(realm.session), target_core.id) == [treaty_id]
    tally = CoalitionTally()
    await tend_coalitions(context(realm.session, MARCHING), tally)
    assert tally.wars == 1 and tally.formed == 0
    assert await bonded(realm.session, min(first.id, second.id), target_core.id, BondKind.ENEMY)


async def test_a_coalition_weaker_than_its_foe_stays_home(realm: Realm) -> None:
    _, target_core = await crown(realm, "Iron Crown")
    _, lone = await crown(realm, "Reed Throne")
    set_stats(target_core, population=500000)
    set_stats(lone, population=10)
    await realm.session.flush()
    await coalition(realm, target_core.id, [lone.id])
    tally = CoalitionTally()
    await tend_coalitions(context(realm.session, MARCHING), tally)
    assert tally.wars == 0
    assert not await bonded(realm.session, lone.id, target_core.id, BondKind.ENEMY)
