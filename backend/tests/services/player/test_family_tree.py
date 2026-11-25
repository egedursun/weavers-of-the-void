import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.mortal import MarriageEnd
from aerona.domain.models.entity_stats import MortalStats
from aerona.services.books.familysvg import family_plan
from aerona.services.kinship.layout import CARD_WIDTH, lay_out
from aerona.services.kinship.naming import relations_of
from aerona.services.kinship.tree import trace_family
from aerona.services.player import mortals
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity

KIN = "gp1 gp2 gp3 p1 p2 ex root sib half spouse stepex step kid sibspouse nib gk godparent fosterer conc cc"


async def _family(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> dict[str, int]:
    ids: dict[str, int] = {}
    for key in KIN.split():
        row = await make_entity(
            session,
            key.capitalize(),
            EntityType.MORTAL,
            world_id=world.world.id,
            location_id=world.region.id,
            stats=MortalStats(hp=80, strength=50, agility=50, intellect=50, charisma=50, age=30, lifespan=70),
            mortal_role=MortalRole.COMMONER,
        )
        ids[key] = row.id

    async def bond(source: str, target: str, kind: BondKind) -> None:
        await mortals.add_kin_bond(scope, mortals.KinBond(source_id=ids[source], target_id=ids[target], kind=kind.value))

    async def wed(first: str, second: str, end: MarriageEnd | None = None) -> None:
        made = await mortals.force_marriage(scope, mortals.ForceMarriage(first_id=ids[first], second_id=ids[second], forced=False))
        if end is not None:
            await mortals.end_marriage_action(scope, mortals.EndMarriage(marriage_id=made.values["marriage_id"], cause=end))

    await wed("gp1", "gp2", MarriageEnd.DEATH)
    for parent, child in (("gp1", "p1"), ("gp2", "p1"), ("gp3", "p2"), ("p1", "root"), ("p2", "root"), ("p1", "sib"), ("p2", "sib"), ("p1", "half")):
        await bond(parent, child, BondKind.PARENT_OF)
    await wed("p1", "ex", MarriageEnd.DIVORCE)
    await bond("ex", "half", BondKind.PARENT_OF)
    await wed("p1", "p2")
    await wed("spouse", "stepex", MarriageEnd.DIVORCE)
    await wed("root", "spouse")
    await wed("sib", "sibspouse")
    for parent, child in (("spouse", "step"), ("stepex", "step"), ("root", "kid"), ("spouse", "kid"), ("sib", "nib"), ("sibspouse", "nib")):
        await bond(parent, child, BondKind.PARENT_OF)
    await wed("kid", "nib")
    await bond("kid", "gk", BondKind.PARENT_OF)
    await bond("nib", "gk", BondKind.PARENT_OF)
    await bond("godparent", "root", BondKind.GODPARENT_OF)
    await bond("root", "fosterer", BondKind.FOSTERED_BY)
    await bond("conc", "root", BondKind.CONCUBINE_OF)
    await bond("root", "cc", BondKind.PARENT_OF)
    await bond("conc", "cc", BondKind.PARENT_OF)
    return ids


async def test_a_tangled_family_is_traced_named_and_laid_out(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ids = await _family(scope, session, world)
    family = await trace_family(session, ids["root"], 3, 3)
    named = {key: relations_of(family)[ids[key]] for key in ids}
    assert named == {
        "gp1": "Grandparent",
        "gp2": "Grandparent",
        "gp3": "Grandparent",
        "p1": "Parent",
        "p2": "Parent",
        "ex": "Parent's former spouse",
        "root": "This mortal",
        "sib": "Sibling",
        "half": "Half-sibling",
        "spouse": "Spouse",
        "stepex": "Spouse's former spouse",
        "step": "Stepchild",
        "kid": "Child",
        "sibspouse": "Sibling's spouse",
        "nib": "Sibling's child",
        "gk": "Grandchild",
        "godparent": "Godparent",
        "fosterer": "Fosterer",
        "conc": "Concubine",
        "cc": "Child",
    }
    generation = {person.id: person.generation for person in family.people}
    assert generation[ids["gk"]] == 2
    assert generation[ids["gp1"]] == -2
    assert not next(person for person in family.people if person.id == ids["spouse"]).blood
    layout = lay_out(family)
    rows: dict[float, list[float]] = {}
    for card in layout.cards.values():
        rows.setdefault(card.y, []).append(card.x)
    for xs in rows.values():
        ordered = sorted(xs)
        assert all(right - left >= CARD_WIDTH for left, right in itertools.pairwise(ordered))
    for line in layout.families:
        assert all(layout.cards[child].y > layout.cards[parent].y for child in line.children for parent in line.parents)
    marriage = next(mark for mark in layout.partners if {mark.first, mark.second} == {ids["root"], ids["spouse"]})
    assert " H " in marriage.path and not marriage.ended
    widowed = next(mark for mark in layout.partners if {mark.first, mark.second} == {ids["gp1"], ids["gp2"]})
    assert widowed.widowed and not widowed.ended
    divorced = next(mark for mark in layout.partners if {mark.first, mark.second} == {ids["p1"], ids["ex"]})
    assert divorced.ended


async def test_the_reach_and_the_bonds_of_care_bound_the_tree(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ids = await _family(scope, session, world)
    near = await trace_family(session, ids["root"], 1, 0, frozenset())
    present = {person.id for person in near.people}
    assert near.deeper_up and near.deeper_down
    assert ids["p1"] in present and ids["gp1"] not in present and ids["kid"] not in present
    assert ids["godparent"] not in present and ids["fosterer"] not in present
    assert all(tie.kind not in {BondKind.GODPARENT_OF, BondKind.FOSTERED_BY} for tie in near.ties)
    full = await trace_family(session, ids["root"], 3, 3)
    assert not full.deeper_up and not full.deeper_down


async def test_the_book_draws_the_family_and_lists_every_kin(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ids = await _family(scope, session, world)
    plan = await family_plan(session, ids["root"], "Root")
    assert plan is not None
    assert len(plan.rows) == len(ids)
    assert "Root" in plan.figure and plan.figure.startswith("<svg")
    assert {row.relation for row in plan.rows} >= {"Grandchild", "Stepchild", "Godparent"}
    lonely = await make_entity(session, "Alone", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    assert await family_plan(session, lonely.id, "Alone") is None
