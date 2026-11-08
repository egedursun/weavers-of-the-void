from pathlib import Path

from aerona.catalog.laws import LAW_PARAMS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import TraitKind, TraitSource
from aerona.domain.enums.polity import ClaimBasis, GenderRule, LawKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import FactionStats, HouseStats
from aerona.engine.context import TickContext
from aerona.engine.mind.book import add_trait
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.formation import found_polity, set_ruler, sync_members
from aerona.engine.polity.offices import backing, divine_favour, gender_rank, house_of, living_mortal, regency, support
from aerona.engine.primitives.queries import add_flag, connect
from tests.engine.society.factories import Realm as World
from tests.engine.society.factories import context, make, mortal, settlement, son, tuned

SOURCE = Path(__file__).resolve().parents[3] / "src" / "aerona"


async def kingdom(world: World, ruler_age: int = 40) -> tuple[TickContext, Realm, EntityRow, EntityRow]:
    ctx = context(world.session)
    capital = await settlement(world, "Crownhold")
    world.session.add(SettlementProfileRow(settlement_entity_id=capital.id, size_tier=SizeTier.TOWN, treasury=100, unrest=10, locked=[], foreigners={}))
    ruler = await mortal(world, "Ysolde", location_id=capital.id, age=ruler_age)
    book = await RealmBook.load(world.session)
    state = await found_polity(ctx, book, capital)
    await sync_members(ctx, book, state, {capital.id})
    set_ruler(ctx, state, ruler.id, "crowned")
    await world.session.flush()
    return ctx, state, capital, ruler


async def test_no_law_prefers_a_sex_and_each_gender_rule_ranks_as_written(realm: World) -> None:
    assert LAW_PARAMS[LawKind.SUCCESSION_RULE]["gender"].default == GenderRule.ANY.value
    for path in SOURCE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "or GenderRule.MALE" not in text and "or GenderRule.FEMALE" not in text, path
        assert "default=GenderRule.MALE" not in text and "default=GenderRule.FEMALE" not in text, path
    first = await mortal(realm, "Ana")
    second = await mortal(realm, "Bo")
    first.stats = first.stats.model_copy(update={"sex": "female"})
    second.stats = second.stats.model_copy(update={"sex": "male"})
    assert gender_rank(GenderRule.ANY, first) == gender_rank(GenderRule.ANY, second) == 0
    assert gender_rank(GenderRule.MALE_ONLY, first) is None and gender_rank(GenderRule.MALE_ONLY, second) == 0
    assert gender_rank(GenderRule.FEMALE_ONLY, first) == 0 and gender_rank(GenderRule.FEMALE_ONLY, second) is None
    assert gender_rank(GenderRule.MALE_PREFERENCE, first) == 1 and gender_rank(GenderRule.FEMALE_PREFERENCE, first) == 0
    ctx = context(realm.session)
    assert await living_mortal(ctx, first.id) is first
    assert await living_mortal(ctx, realm.region.id) is None


async def test_a_child_ruler_gets_a_regent_who_may_seize_the_crown(realm: World) -> None:
    ctx, state, capital, child = await kingdom(realm, ruler_age=6)
    elder = await mortal(realm, "Orrin", location_id=capital.id, age=50)
    assert await regency(ctx, state, set()) == "appointed"
    regent = state.office(OfficeKind.REGENT)
    assert regent is not None and regent.holder_entity_id == elder.id
    assert await regency(ctx, state, set()) is None
    await add_trait(realm.session, elder.id, TraitKind.AMBITIOUS, TraitSource.BIRTH, 1)
    grasping = context(realm.session, tuned(succession={"usurp_chance": 100}))
    assert await regency(grasping, state, set()) == "usurped"
    assert state.ruler_id == elder.id and regent.holder_entity_id is None
    child.stats = child.stats.model_copy(update={"age": 40})
    assert await regency(ctx, state, set()) is None


async def test_a_grown_ruler_ends_the_regency(realm: World) -> None:
    ctx, state, capital, ruler = await kingdom(realm, ruler_age=6)
    await mortal(realm, "Orrin", location_id=capital.id, age=50)
    assert await regency(ctx, state, set()) == "appointed"
    ruler.stats = ruler.stats.model_copy(update={"age": 40})
    assert await regency(ctx, state, set()) == "ended"


async def test_the_patron_favours_its_worshippers_its_children_and_the_chosen(realm: World) -> None:
    ctx, state, capital, _ = await kingdom(realm)
    patron = await son(realm.session, "Vael", realm.world.id)
    state.profile.patron_son_id = patron.id
    devout = await mortal(realm, "Ana", location_id=capital.id)
    chosen = await mortal(realm, "Bo", location_id=capital.id)
    plain = await mortal(realm, "Cy", location_id=capital.id)
    await connect(realm.session, devout.id, patron.id, BondKind.WORSHIPS, 1)
    await add_flag(realm.session, chosen.id, EntityFlag.CHOSEN, 1)
    favour = await divine_favour(ctx, state, [devout, chosen, plain])
    weight = ctx.rules.succession.patron_favour
    assert favour == {devout.id: weight, chosen.id: weight, plain.id: 0}


async def test_a_claimant_weighs_house_factions_and_discontent_against_the_throne(realm: World) -> None:
    ctx, state, capital, ruler = await kingdom(realm)
    claimant = await mortal(realm, "Rask", location_id=capital.id)
    assert await house_of(ctx, None) is None and await house_of(ctx, claimant.id) is None
    house = await make(realm.session, "House Rask", EntityType.HOUSE, HouseStats(), world_id=realm.world.id)
    realm.session.add_all(
        [
            HouseProfileRow(house_entity_id=house.id, prestige=80, traits=[], seats=[], locked=[]),
            HouseMemberRow(house_entity_id=house.id, mortal_entity_id=claimant.id, joined_epoch=1, by_marriage=False),
        ]
    )
    band = await make(realm.session, "The Unbowed", EntityType.FACTION, FactionStats(strength=60), world_id=realm.world.id, location_id=capital.id)
    await connect(realm.session, claimant.id, band.id, BondKind.MEMBER_OF, 1)
    claim = ClaimRow(claimant_entity_id=claimant.id, house_entity_id=house.id, polity_entity_id=state.entity.id, basis=ClaimBasis.INHERITANCE, strength=40)
    realm.session.add(claim)
    await realm.session.flush()
    assert await house_of(ctx, claimant.id) is not None
    assert await backing(ctx, claimant.id) == 60
    backers, throne = await support(ctx, state, claim)
    assert backers > claim.strength and throne >= state.profile.legitimacy
    assert ruler.id == state.ruler_id
