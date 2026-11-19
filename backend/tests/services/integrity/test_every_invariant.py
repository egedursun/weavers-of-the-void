from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.invariants import TYPED, GenericCheck, InvariantSpec, Remedy
from aerona.db.record_context import RecordScope, scoped
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow, StateCheckpointRow
from aerona.db.tables.childhood import ChildStandingRow, SocializationRow
from aerona.db.tables.commerce import LeaseRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.council_order import DivineSeatRow
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import CurrencyRow, WorldMaterialRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.intimacy import IntimacyNormRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow
from aerona.db.tables.pantheon import PantheonTieRow, SyncretismRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.tables.works import PublicWorksRow, PublicWorkStageRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import OrderKind
from aerona.domain.enums.creator import CovenantDuty, CreatorPromise
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import FuneralCustom, InheritanceCustom, MartialStyle
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin, MoneyForm
from aerona.domain.enums.endowments import EndowmentState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.intimacy import RelationContext
from aerona.domain.enums.kinds import GoodCategory, KindConcept
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.population import PopulationInstrument
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.enums.records import FactUnit, StepAction, WitnessMode
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.speech import SpeechVenue
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import PeopleStats, PolityStats, SpeciesStats
from aerona.engine.recording.checkpoints import take_checkpoint
from aerona.services.integrity.invariants import CHECKS, findings, resolve, sweep
from aerona.services.integrity.record_links import absent_witnesses
from tests.conftest import OpenDatabase
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, seed_core_world, settlement
from tests.engine.core.test_arcana_w15 import foreign_caster

Breaker = Callable[[AsyncSession, CoreWorld], Awaitable[None]]
PHASE_KIND = "phase.statecraft"


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "integrity.db")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
async def world(session: AsyncSession) -> CoreWorld:
    return await seed_core_world(session)


async def captor_dies(session: AsyncSession, world: CoreWorld) -> None:
    captor = await mortal(session, "Holder", world, world.regions[0].id)
    held = await mortal(session, "Held", world, world.regions[0].id)
    session.add(CaptiveRow(captive_entity_id=held.id, captor_entity_id=captor.id, status=CaptiveStatus.HELD, taken_epoch=1))
    captor.status, captor.end_epoch = EntityStatus.DEAD, 1


async def species_dies_in_its_lands(session: AsyncSession, world: CoreWorld) -> None:
    kind = await entity(session, "Last Herd", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(SpeciesRangeRow(species_entity_id=kind.id, region_entity_id=world.regions[0].id, abundance=40, locked=[]))
    kind.status, kind.end_epoch = EntityStatus.DEAD, 1


async def order_loses_target(session: AsyncSession, world: CoreWorld) -> None:
    owner = await mortal(session, "Keeper", world, world.regions[0].id)
    orders = InstructionSetRow(owner_entity_id=owner.id, locked=[])
    session.add(orders)
    await session.flush()
    session.add(InstructionOrderRow(set_id=orders.id, kind=OrderKind.GUARD, target_node_id=None, locked=[]))


async def construct_makes_itself(session: AsyncSession, world: CoreWorld) -> None:
    body = await mortal(session, "Vessel", world, world.regions[0].id)
    session.add(ConstructRow(entity_id=body.id, maker_entity_id=body.id, locked=[]))


async def ruler_dies(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Seat", world, world.regions[0])
    ruler = await mortal(session, "Ruler", world, town.id)
    await bond(session, ruler.id, town.id, BondKind.RULES)
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, 1


async def covenant_without_people(session: AsyncSession, world: CoreWorld) -> None:
    keeper = await mortal(session, "Lone", world, world.regions[0].id)
    session.add(CovenantRow(people_entity_id=keeper.id, duty=CovenantDuty.WORSHIP, promise=CreatorPromise.PLENTY, locked=[]))


async def seat_without_god(session: AsyncSession, world: CoreWorld) -> None:
    session.add(DivineSeatRow(god_node_id=world.people.id, locked=[]))


async def tie_without_god(session: AsyncSession, world: CoreWorld) -> None:
    session.add(PantheonTieRow(god_node_id=world.son.id, other_node_id=world.people.id, locked=[]))


async def joining_without_people(session: AsyncSession, world: CoreWorld) -> None:
    god = await foreign_caster(session, world)
    session.add(SyncretismRow(foreign_god_id=god.id, son_id=world.son.id, people_entity_id=world.species.id, locked=[]))


async def holding_without_kind(session: AsyncSession, world: CoreWorld) -> None:
    session.add(KindHoldingRow(concept=KindConcept.GOOD, kind_id=987654, holder_node_id=world.people.id, locked=[]))


async def kind_derived_from_itself(session: AsyncSession, world: CoreWorld) -> None:
    kind = GoodKindRow(name="Loop Bread", category=GoodCategory.GRAIN, world_id=world.world.id, locked=[])
    session.add(kind)
    await session.flush()
    kind.derived_from_id = kind.id


async def kind_out_of_range(session: AsyncSession, world: CoreWorld) -> None:
    session.add(GoodKindRow(name="Dear Salt", category=GoodCategory.MINERAL_SEASONING, world_id=world.world.id, base_value=5000, locked=[]))


async def paper_made_of_metal(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Mint", world, world.regions[0])
    session.add(
        CurrencyRow(issuer_entity_id=town.id, name="Notes", metal=MaterialKind.SILVER, purity=100, supply=0, trust=50, minted_epoch=0, form=MoneyForm.PAPER)
    )


async def genome_with_unknown_allele(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Odd Blood", world, world.regions[0].id)
    session.add(GenomeRow(holder_node_id=holder.id, genes={"muscle": ["vast", "high"]}, potential={}, likeness={}, marks=[], locked=[]))


async def star_stuff_from_a_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Forge", world, world.regions[0])
    session.add(
        WorldMaterialRow(
            world_id=world.world.id,
            origin=MaterialOrigin.STAR,
            source_node_id=town.id,
            family=MaterialFamily.EXOTIC,
            hardness=50,
            toughness=50,
            weight=50,
            edge=50,
            conductivity=50,
            sanctity=0,
            corruption=0,
            rarity=50,
            base_value=10,
            decay=0,
            created_epoch=0,
        )
    )


async def happening(session: AsyncSession, *, kind: str = "uncatalogued.happening", year: int | None = None, place: int | None = None) -> IncidentRow:
    row = IncidentRow(kind=kind, epoch=1, year=year, place_entity_id=place, magnitude=0, locked=[])
    session.add(row)
    await session.flush()
    return row


async def happening_of_a_retired_kind(session: AsyncSession, world: CoreWorld) -> None:
    await happening(session, kind="retired.happening")


async def fact_of_no_kind(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session)
    session.add(IncidentFactRow(incident_id=incident.id, key="amount", number=3.0, unit=FactUnit.COUNT))


async def step_inside_itself(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND)
    step = IncidentStepRow(incident_id=incident.id, position=0, action=StepAction.BEGIN)
    session.add(step)
    await session.flush()
    step.parent_step_id = step.id


async def step_of_no_kind(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session)
    session.add(IncidentStepRow(incident_id=incident.id, position=0, action=StepAction.STRIKE))


async def effect_before_cause(session: AsyncSession, world: CoreWorld) -> None:
    cause = await happening(session, kind=PHASE_KIND, year=40)
    effect = await happening(session, kind=PHASE_KIND, year=12)
    effect.cause_incident_id = cause.id


async def world_made_late(session: AsyncSession, world: CoreWorld) -> None:
    made = await happening(session, kind="genesis.world", year=7)
    made.epoch = 1


async def people_before_its_world(session: AsyncSession, world: CoreWorld) -> None:
    made = await happening(session, kind=PHASE_KIND, year=31)
    session.add(IncidentParticipantRow(incident_id=made.id, node_id=world.regions[0].id, role=IncidentRole.PRODUCT, position=0))
    woke = await happening(session, kind=PHASE_KIND, year=0)
    session.add(IncidentParticipantRow(incident_id=woke.id, node_id=world.regions[0].id, role=IncidentRole.SUBJECT, position=0))


async def undated_birth(session: AsyncSession, world: CoreWorld) -> None:
    made = await happening(session, kind=PHASE_KIND, year=9)
    session.add(IncidentParticipantRow(incident_id=made.id, node_id=world.people.id, role=IncidentRole.PRODUCT, position=0))


async def steps_running_back(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND, year=30)
    session.add(IncidentStepRow(incident_id=incident.id, position=0, year=30, action=StepAction.BEGIN))
    session.add(IncidentStepRow(incident_id=incident.id, position=1, year=20, action=StepAction.END))


async def witness_far_away(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND, place=world.regions[0].id)
    onlooker = await mortal(session, "Far Onlooker", world, world.regions[1].id)
    session.add(
        IncidentParticipantRow(incident_id=incident.id, node_id=onlooker.id, role=IncidentRole.WITNESS, position=0, witness_mode=WitnessMode.SAW, fidelity=90)
    )


async def time_budget_over_the_year(session: AsyncSession, world: CoreWorld) -> None:
    session.add(TimeBudgetRow(people_entity_id=world.people.id, social_class=SocialClass.FARMER, life_stage=LifeStage.ADULT, work=90, rest=40, locked=[]))


async def wedding_before_naming(session: AsyncSession, world: CoreWorld) -> None:
    session.add(ChildStandingRow(people_entity_id=world.people.id, naming_age=20, marriage_age=10, locked=[]))


async def upbringing_past_the_whole(session: AsyncSession, world: CoreWorld) -> None:
    session.add(SocializationRow(people_entity_id=world.people.id, play=90, example=90, locked=[]))


async def sexed_norm_for_a_sexless_people(session: AsyncSession, world: CoreWorld) -> None:
    session.add(PeopleReproductionRow(people_entity_id=world.people.id, system=ReproductiveSystem.ASEXUAL, locked=[]))
    session.add(IntimacyNormRow(people_entity_id=world.people.id, context=RelationContext.BETWEEN_ANY_SEXES, locked=[]))


async def elder_in_a_youth_group(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Youthford", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(YouthStandingRow(people_entity_id=world.people.id, youth_from=12, youth_to=20, locked=[]))
    elder = await mortal(session, "Old Brann", world, town.id, age=60)
    group = YouthGroupRow(settlement_entity_id=town.id, name="the youth of the ford", locked=[])
    session.add(group)
    await session.flush()
    session.add(YouthGroupMemberRow(group_id=group.id, member_node_id=elder.id, locked=[]))


async def policy_held_by_a_single_being(session: AsyncSession, world: CoreWorld) -> None:
    being = await mortal(session, "Lone Planner", world, world.regions[0].id)
    session.add(PopulationPolicyRow(holder_node_id=being.id, locked=[]))


async def instrument_of_another_holder(session: AsyncSession, world: CoreWorld) -> None:
    policy = PopulationPolicyRow(holder_node_id=world.people.id, locked=[])
    session.add(policy)
    await session.flush()
    session.add(PopulationInstrumentRow(policy_id=policy.id, instrument=PopulationInstrument.BIRTH_REWARD, holder_node_id=world.regions[0].id, locked=[]))


async def lease_of_a_thing_not_owned(session: AsyncSession, world: CoreWorld) -> None:
    owner = await mortal(session, "False Landlord", world, world.regions[0].id)
    tenant = await mortal(session, "Tenant", world, world.regions[0].id)
    session.add(LeaseRow(owner_node_id=owner.id, lessee_node_id=tenant.id, thing_node_id=world.regions[1].id, locked=[]))


async def works_on_foreign_ground(session: AsyncSession, world: CoreWorld) -> None:
    home = await settlement(session, "Homeford", world, world.regions[0])
    away = await settlement(session, "Farford", world, world.regions[1])
    await bond(session, home.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(PublicWorksRow(polity_entity_id=home.id, place_node_id=away.id, locked=[]))


async def item_beyond_its_outlet(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Criers Ford", world, world.regions[0])
    owner = await mortal(session, "Crier", world, town.id)
    outlet = MediaOutletRow(owner_node_id=owner.id, seat_entity_id=town.id, name="The Ford Crier", reach=10, locked=[])
    session.add(outlet)
    await session.flush()
    session.add(MediaItemRow(outlet_id=outlet.id, owner_node_id=owner.id, reach=90, locked=[]))


async def sermon_in_a_town_without_a_temple(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Templeless", world, world.regions[0])
    speaker = await mortal(session, "Preacher", world, town.id)
    session.add(SpeechRow(speaker_node_id=speaker.id, place_entity_id=town.id, venue=SpeechVenue.TEMPLE, locked=[]))


async def class_of_animals_pointing_at_a_region(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        FolkClassRow(
            people_entity_id=world.people.id,
            domain=FolkDomain.ANIMALS,
            name="Beasts of the hills",
            grouped_node_id=world.regions[0].id,
            locked=[],
        )
    )


async def stage_set_down_by_another_realm(session: AsyncSession, world: CoreWorld) -> None:
    builder = await entity(session, "Builders", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    stranger = await entity(session, "Strangers", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    works = PublicWorksRow(polity_entity_id=builder.id, place_node_id=world.regions[0].id, locked=[])
    session.add(works)
    await session.flush()
    session.add(PublicWorkStageRow(works_id=works.id, polity_entity_id=stranger.id, stage=1, locked=[]))


async def endowment_held_captive_by_a_mortal(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Almsford", world, world.regions[0])
    keeper = await mortal(session, "Keeper", world, town.id)
    session.add(EndowmentRow(founder_node_id=keeper.id, beneficiary_node_id=town.id, trustee_node_id=keeper.id, state=EndowmentState.CAPTURED, locked=[]))


async def practice_of_a_mortal(session: AsyncSession, world: CoreWorld) -> None:
    lone = await mortal(session, "Lone", world, world.regions[0].id)
    session.add(FacetPracticeRow(community_entity_id=lone.id, facet=FacetKind.MASONRY, level=40, locked=[]))
    await session.flush()


async def remains_the_rite_forbids(session: AsyncSession, world: CoreWorld) -> None:
    culture = await session.get(PeopleCultureRow, world.people.id)
    if culture is None:
        culture = PeopleCultureRow(
            people_entity_id=world.people.id,
            cohesion=50,
            literacy=10,
            urbanisation=10,
            martial_style=MartialStyle.SHIELDWALL,
            inheritance=InheritanceCustom.PRIMOGENITURE,
            locked=[],
        )
        session.add(culture)
    culture.funeral_rite = FuneralCustom.CREMATION
    culture.remains_treatment = RemainsTreatment.EXPOSURE


async def reading_beyond_the_base(session: AsyncSession, world: CoreWorld) -> None:
    session.add(NumberSystemRow(people_entity_id=world.people.id, base=5, numerology={"7": "lucky", "2": "sacred"}, locked=[]))


async def kin_group_headed_by_a_stranger(session: AsyncSession, world: CoreWorld) -> None:
    stranger = await mortal(session, "Stray Head", world, world.regions[0].id)
    session.add(KinGroupRow(people_entity_id=world.people.id, name="Kin of the Ford", head_node_id=stranger.id, locked=[]))


async def stranger_in_a_descent_group(session: AsyncSession, world: CoreWorld) -> None:
    other = await entity(session, "Far Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    town = await settlement(session, "Farhold", world, world.regions[1])
    await bond(session, town.id, other.id, BondKind.DESCENDS_FROM)
    stranger = await mortal(session, "Far Kin", world, town.id)
    group = KinGroupRow(people_entity_id=world.people.id, name="Kin of the Ford", locked=[])
    session.add(group)
    await session.flush()
    session.add(KinGroupMemberRow(group_id=group.id, member_node_id=stranger.id, locked=[]))


async def witness_who_does_not_say_how(session: AsyncSession, world: CoreWorld) -> None:
    incident = await happening(session, kind=PHASE_KIND, place=world.regions[0].id)
    onlooker = await mortal(session, "Silent Onlooker", world, world.regions[0].id)
    session.add(IncidentParticipantRow(incident_id=incident.id, node_id=onlooker.id, role=IncidentRole.WITNESS, position=0))


async def engine_change_of_no_happening(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        StateChangeRow(
            epoch=1,
            table_name="entities",
            row_key=f'{{"id": {world.people.id}}}',
            node_id=world.people.id,
            operation=LedgerOperation.UPDATE,
            field="power_level",
            before_number=1.0,
            after_number=2.0,
            actor_kind=ActorKind.ENGINE,
            phase="statecraft",
        )
    )


async def checkpoint_that_lies(session: AsyncSession, world: CoreWorld) -> None:
    await take_checkpoint(session, 1)
    found = await session.scalar(select(StateCheckpointRow).where(StateCheckpointRow.table_name == "entities"))
    assert found is not None
    found.digest = "not the digest of anything"


async def chronicle_kept_by_a_people(session: AsyncSession, world: CoreWorld) -> None:
    session.add(RecordKeeperRow(kind=RecordKeeperKind.CHRONICLER, scope_node_id=world.creator.id, keeper_entity_id=world.people.id, since_epoch=1, locked=[]))


BREAKERS: dict[str, Breaker] = {
    "fact_schema": fact_of_no_kind,
    "kind_known": happening_of_a_retired_kind,
    "keeper_mortal": chronicle_kept_by_a_people,
    "step_nesting": step_inside_itself,
    "step_action": step_of_no_kind,
    "moment_after_cause": effect_before_cause,
    "genesis_at_start": world_made_late,
    "moment_after_births": people_before_its_world,
    "birth_dated": undated_birth,
    "step_moment_order": steps_running_back,
    "witness_present": witness_far_away,
    "witness_mode": witness_who_does_not_say_how,
    "time_shares": time_budget_over_the_year,
    "child_ages": wedding_before_naming,
    "upbringing_shares": upbringing_past_the_whole,
    "norm_sexes": sexed_norm_for_a_sexless_people,
    "youth_years": elder_in_a_youth_group,
    "policy_holder": policy_held_by_a_single_being,
    "lease_owner": lease_of_a_thing_not_owned,
    "works_place": works_on_foreign_ground,
    "media_reach": item_beyond_its_outlet,
    "speech_venue": sermon_in_a_town_without_a_temple,
    "folk_class_kind": class_of_animals_pointing_at_a_region,
    "stage_builder": stage_set_down_by_another_realm,
    "endowment_capture": endowment_held_captive_by_a_mortal,
    "remains_rite": remains_the_rite_forbids,
    "practice_holder": practice_of_a_mortal,
    "numerology_keys": reading_beyond_the_base,
    "instrument_policy": instrument_of_another_holder,
    "kin_head_member": kin_group_headed_by_a_stranger,
    "kin_member_rule": stranger_in_a_descent_group,
    "change_in_scope": engine_change_of_no_happening,
    "checkpoint_holds": checkpoint_that_lies,
    "genome_alleles": genome_with_unknown_allele,
    "money_metal": paper_made_of_metal,
    "material_source": star_stuff_from_a_town,
    "living_captor": captor_dies,
    "living_range": species_dies_in_its_lands,
    "order_target": order_loses_target,
    "maker_not_self": construct_makes_itself,
    "living_ruler": ruler_dies,
    "covenant_people": covenant_without_people,
    "seat_god": seat_without_god,
    "tie_gods": tie_without_god,
    "syncretism_kinds": joining_without_people,
    "holding_kind": holding_without_kind,
    "kind_lineage": kind_derived_from_itself,
    "kind_ranges": kind_out_of_range,
}


@pytest.mark.parametrize("spec", TYPED, ids=lambda spec: spec.key)
async def test_each_invariant_finds_what_breaks_it_and_mends_it(session: AsyncSession, world: CoreWorld, spec: InvariantSpec) -> None:
    key = spec.key
    find, _ = CHECKS[key]
    assert await find(session) == []
    await BREAKERS[key](session, world)
    await session.flush()
    broken = await find(session)
    assert broken
    if spec.remedy is Remedy.REPAIR:
        await sweep(session)
    else:
        for finding in [item for item in await findings(session) if item.invariant == key]:
            await resolve(session, finding)
    assert await find(session) == []


async def test_every_typed_invariant_has_a_breaker() -> None:
    assert {spec.key for spec in TYPED} == set(BREAKERS) == set(CHECKS)


async def test_the_generic_checks_mend_ranges_epochs_and_report_stray_holds(session: AsyncSession, world: CoreWorld) -> None:
    session.add(TechnologyProfileRow(holder_node_id=world.people.id, family=TechFamily.ENERGY, level=3, updated_epoch=500, locked=["level", "nothing_here"]))
    await session.flush()
    swept = await sweep(session)
    assert swept.repaired[GenericCheck.PAST_EPOCHS.value] >= 1
    row = await session.get(TechnologyProfileRow, (world.people.id, TechFamily.ENERGY))
    assert row is not None
    await session.refresh(row)
    assert row.updated_epoch <= world.cosmos.epoch
    stray = [item for item in await findings(session) if item.check is GenericCheck.LOCKED_NAMES and item.table == "technology_profiles"]
    assert stray
    await resolve(session, stray[0])
    await session.refresh(row)
    assert row.locked == ["level"]


async def test_one_who_heard_from_afar_or_moved_later_is_not_called_absent(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    incident = await happening(session, kind=PHASE_KIND, place=world.regions[0].id)
    heard = await mortal(session, "Far Listener", world, world.regions[1].id)
    moved = await mortal(session, "Later Traveller", world, world.regions[0].id)
    session.add_all(
        [
            IncidentParticipantRow(
                incident_id=incident.id, node_id=heard.id, role=IncidentRole.WITNESS, position=0, witness_mode=WitnessMode.HEARD, fidelity=60
            ),
            IncidentParticipantRow(incident_id=incident.id, node_id=moved.id, role=IncidentRole.WITNESS, position=1, witness_mode=WitnessMode.SAW, fidelity=90),
        ]
    )
    await session.flush()
    with scoped(RecordScope(key="test.move", epoch=incident.epoch + 1)):
        moved.location_id = world.regions[1].id
        await session.flush()
    assert await absent_witnesses(session) == []
