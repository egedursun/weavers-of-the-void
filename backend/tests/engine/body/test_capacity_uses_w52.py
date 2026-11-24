from types import SimpleNamespace
from typing import cast

from aerona.db.tables.military import SpyAgentRow
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.entity import MortalRole
from aerona.engine.body.book import capacity_lean, ensure_body
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import named_labour
from aerona.engine.environment.deep import drift_shares
from aerona.engine.phases.espionage import covered_gain
from aerona.engine.recording.terms import explaining
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal

RULES = Rules()


async def test_a_quiet_body_hides_an_agent_and_a_clumsy_one_gives_the_agent_away(realm: Realm) -> None:
    ctx = context(realm.session)
    quiet, clumsy = await mortal(realm, "Quiet"), await mortal(realm, "Clumsy")
    for being, stealth in ((quiet, 150), (clumsy, 40)):
        body = await ensure_body(realm.session, ctx.rules, being, ctx.epoch)
        body.stealth = stealth
    await realm.session.flush()
    with explaining() as collector:
        hidden = await covered_gain(ctx, cast(SpyAgentRow, SimpleNamespace(mortal_entity_id=quiet.id)), 20)
        shown = await covered_gain(ctx, cast(SpyAgentRow, SimpleNamespace(mortal_entity_id=clumsy.id)), 20)
    assert hidden < 20 < shown
    assert "capacities.stealth_cover" in {term.key for term in collector.terms}
    assert await capacity_lean(realm.session, [quiet.id], "stealth", ctx.rules.capacities.stealth_theft_pct) > 0


async def test_the_labour_of_named_workers_moves_the_output_of_their_community(realm: Realm) -> None:
    ctx = context(realm.session)
    strong, weak = await mortal(realm, "Strong", role=MortalRole.COMMONER), await mortal(realm, "Weak", role=MortalRole.COMMONER)
    for being, labour in ((strong, 160), (weak, 30)):
        body = await ensure_body(realm.session, ctx.rules, being, ctx.epoch)
        body.labour = labour
    await realm.session.flush()
    for being, expect_more in ((strong, True), (weak, False)):
        book = cast(EconomyBook, SimpleNamespace(entities={being.id: being}, affiliated={being.id: 77}))
        with explaining() as collector:
            factor = await named_labour(ctx, book, 77)
        assert (factor > 1) is expect_more
        assert "capacities.labour_work" in {term.key for term in collector.terms}
    assert await named_labour(ctx, cast(EconomyBook, SimpleNamespace(entities={}, affiliated={})), 77) == 1


def test_pumice_drifts_to_near_shores_and_farther_along_a_speeding_current() -> None:
    line = {1: [2], 2: [1, 3], 3: [2, 4], 4: [3, 5], 5: [4, 6], 6: [5]}
    slack = drift_shares(RULES, 1, line.__getitem__, dict.fromkeys(range(1, 7), OceanCurrent.NONE))
    assert set(slack) < set(range(1, 7))
    assert slack[1] > slack[2] > slack[3]
    carried = drift_shares(RULES, 1, line.__getitem__, {1: OceanCurrent.NONE} | dict.fromkeys(range(2, 7), OceanCurrent.WARM))
    assert carried[4] > slack[4] == 0
    inland = drift_shares(RULES, 1, line.__getitem__, {region: OceanCurrent.NONE for region in (4, 5, 6)})
    assert inland == {}
