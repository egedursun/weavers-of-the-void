from aerona.catalog.life.demography import BEARING_BANDS
from aerona.catalog.reproduction import SEX_SYSTEMS
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.collective import RoleNormRow
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.collective import RoleEligibility, RoleKind
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.engine.demography.cohorts import apply_flow, cohorts_of, pyramid, seed, total
from aerona.engine.demography.vital import Pressures, give_births, one_year
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.society import class_shares
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import tick
from tests.engine.society.factories import Realm, people, settlement

RULES = Rules()
CALM = Pressures(fertility=1.0, hunger=0.0, crowding=0.0, disease=0.0, stress=0.0, mortality=1.0)


async def town_of(realm: Realm, system: ReproductiveSystem, name: str) -> tuple[int, object]:
    folk = await people(realm, f"{name} folk")
    town = await settlement(realm, name, population=12000)
    await BondRepository(realm.session).connect(BondDraft(folk.id, town.id, BondKind.LIVES_IN, 1, role=BondRole.HOMELAND))
    realm.session.add(PeopleReproductionRow(people_entity_id=folk.id, system=system, locked=[]))
    await realm.session.flush()
    return folk.id, town


async def test_a_two_sex_people_keeps_its_cohorts_and_births(realm: Realm) -> None:
    _, town = await town_of(realm, ReproductiveSystem.TWO_SEX, "Steadfield")
    rows = await seed(realm.session, RULES, town, 1)
    assert total(rows) == 12000
    assert {key[1] for key in rows} == {SexKind.BEARER, SexKind.BEGETTER}
    shares = await class_shares(realm.session, RULES, town.id)
    weight = sum(max(0.0, value) for value in shares.values())
    female = RULES.cohorts.bearer_pct / PERCENT
    adult = pyramid(RULES)[AgeBand.ADULT]
    expected = sum(round_half_up(12000 * adult * female * max(0.0, share) / weight) for share in shares.values())
    adult_women = sum(row.count for key, row in rows.items() if key[0] is AgeBand.ADULT and key[1] is SexKind.BEARER)
    assert abs(adult_women - expected) <= len(rows)
    year = one_year(RULES, rows, None, CALM, SEX_SYSTEMS[ReproductiveSystem.TWO_SEX])
    bearers = sum(row.count for key, row in rows.items() if key[0] in BEARING_BANDS and key[1] is SexKind.BEARER)
    assert year.births == round_half_up(bearers * RULES.demography.birth_pct_per_year / PERCENT)
    placed = await give_births(tick(realm.session, RULES), town, rows, year.births, SEX_SYSTEMS[ReproductiveSystem.TWO_SEX])
    assert placed == year.births
    born = {key[1] for key, row in rows.items() if key[0] is AgeBand.INFANT and row.count > 0}
    assert born == {SexKind.BEARER, SexKind.BEGETTER}


async def test_a_people_of_one_sex_seeds_and_bears_through_it(realm: Realm) -> None:
    _, town = await town_of(realm, ReproductiveSystem.ASEXUAL, "Budmere")
    rows = await seed(realm.session, RULES, town, 1)
    assert total(rows) == 12000
    assert {key[1] for key in rows} == {SexKind.NONE}
    spec = SEX_SYSTEMS[ReproductiveSystem.ASEXUAL]
    year = one_year(RULES, rows, None, CALM, spec)
    assert year.births > 0
    await give_births(tick(realm.session, RULES), town, rows, year.births, spec)
    assert {key[1] for key in rows} == {SexKind.NONE}


async def test_war_losses_fall_on_the_sexes_the_culture_sends_to_fight(realm: Realm) -> None:
    folk_id, town = await town_of(realm, ReproductiveSystem.TWO_SEX, "Evenfold")
    await seed(realm.session, RULES, town, 1)
    await apply_flow(realm.session, RULES, town, -2000, category=FlowCategory.CASUALTY, epoch=1)
    rows = await cohorts_of(realm.session, town.id)
    lost = {sex: sum(row.count for key, row in rows.items() if key[1] is sex and key[0] is AgeBand.ADULT) for sex in (SexKind.BEARER, SexKind.BEGETTER)}
    assert abs(lost[SexKind.BEARER] - lost[SexKind.BEGETTER]) < 200
    _, other = await town_of(realm, ReproductiveSystem.TWO_SEX, "Shieldmoor")
    realm.session.add(RoleNormRow(holder_entity_id=other.id, role=RoleKind.COMBAT, eligibility=RoleEligibility.BEARERS_ONLY, classes=[], locked=[]))
    await seed(realm.session, RULES, other, 1)
    before = {
        sex: sum(row.count for key, row in (await cohorts_of(realm.session, other.id)).items() if key[1] is sex) for sex in (SexKind.BEARER, SexKind.BEGETTER)
    }
    await apply_flow(realm.session, RULES, other, -2000, category=FlowCategory.CASUALTY, epoch=1)
    after = await cohorts_of(realm.session, other.id)
    drop = {sex: before[sex] - sum(row.count for key, row in after.items() if key[1] is sex) for sex in (SexKind.BEARER, SexKind.BEGETTER)}
    assert drop[SexKind.BEARER] > drop[SexKind.BEGETTER] * 5
    assert folk_id
    assert {key[3] for key in after} <= {CohortCondition.NONE, CohortCondition.ORPHANED}
