from aerona.catalog.arcs import ARCS, CONFRONTING, ENDS_IN_DEATH
from aerona.db.tables.ages import ArcRow
from aerona.domain.enums.ages import ArcTemplate
from aerona.domain.enums.bond import BondKind
from aerona.engine.storyteller.arcs import GOALS, estrangements, open_arc, outlived, stages_of
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, mortal

RULES = Rules()


def test_nineteen_arcs_with_their_kinds_read_from_the_catalogue() -> None:
    assert len(ARCS) == len(ArcTemplate) == 22
    assert ArcTemplate.OVERCOMING in CONFRONTING and ArcTemplate.SACRIFICE in ENDS_IN_DEATH
    assert len(stages_of(ArcTemplate.QUEST)) > len(stages_of(ArcTemplate.DISCOVERY))
    assert {ArcTemplate.RECONCILIATION, ArcTemplate.DISCOVERY, ArcTemplate.OVERCOMING} <= set(GOALS)
    assert GOALS[ArcTemplate.RIVALRY] is outlived and GOALS[ArcTemplate.RECONCILIATION] is not outlived


async def test_an_estrangement_becomes_a_tale_of_reconciliation_that_ends_in_peace(realm: Realm) -> None:
    first, second = await mortal(realm, "First"), await mortal(realm, "Second")
    feud = await link(realm.session, first.id, second.id, BondKind.ENEMY)
    ctx = context(realm.session)
    found = [candidate for candidate in await estrangements(ctx) if candidate.subject_id == first.id]
    assert found and found[0].template is ArcTemplate.RECONCILIATION
    arc: ArcRow = await open_arc(ctx, first.id, ArcTemplate.RECONCILIATION, found[0].figures)
    judge = GOALS[ArcTemplate.RECONCILIATION]
    assert not await judge(ctx, arc, [second.id])
    await realm.session.delete(feud)
    await realm.session.flush()
    assert await judge(ctx, arc, [second.id])
