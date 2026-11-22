from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.services import VENUE_STRUCTURES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.childhood import STANDING_AGES, TECHNIQUE_WEIGHTS, ChildStandingRow, SocializationRow
from aerona.db.tables.commerce import LeaseRow
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.customs import TIME_FIELDS, TimeBudgetRow
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.intimacy import IntimacyNormRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.works import PublicWorksRow, PublicWorkStageRow
from aerona.db.tables.youth import YouthGroupMemberRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.endowments import EndowmentState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folk_knowledge import NumberReading
from aerona.domain.enums.intimacy import RelationContext
from aerona.domain.enums.kin import KinMembership
from aerona.domain.enums.media import MediaItemKind
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.population import PopulationInstrument
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.speech import SpeechVenue
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.lineage import sexes_fixed
from aerona.engine.death_work.handling import allowed_remains
from aerona.engine.endowments.trust import CAPTORS
from aerona.engine.folk_knowledge.truth import fits
from aerona.engine.numbers.book import towns_in
from aerona.engine.works.building import towns_of_place
from aerona.engine.youth.groups import is_youth

STAGE_KEY = 10
CLASS_KEY = 100


def budget_key(people_id: int, social_class: SocialClass, stage: LifeStage) -> int:
    return (people_id * CLASS_KEY + list(SocialClass).index(social_class)) * STAGE_KEY + list(LifeStage).index(stage)


def budget_of_key(key: int) -> tuple[int, SocialClass, LifeStage]:
    rest, stage = divmod(key, STAGE_KEY)
    people_id, social_class = divmod(rest, CLASS_KEY)
    return people_id, list(SocialClass)[social_class], list(LifeStage)[stage]


async def uneven_budgets(session: AsyncSession) -> list[int]:
    return [
        budget_key(row.people_entity_id, row.social_class, row.life_stage)
        for row in await session.scalars(select(TimeBudgetRow).order_by(TimeBudgetRow.people_entity_id, TimeBudgetRow.social_class, TimeBudgetRow.life_stage))
        if sum(getattr(row, name) for name in TIME_FIELDS) != PERCENT
    ]


async def even_budget(session: AsyncSession, key: int) -> None:
    row = await session.get(TimeBudgetRow, budget_of_key(key))
    if row is None:
        return
    total = sum(getattr(row, name) for name in TIME_FIELDS)
    if total <= 0:
        row.work = PERCENT
        return
    shares = {name: getattr(row, name) * PERCENT // total for name in TIME_FIELDS}
    shares["work"] += PERCENT - sum(shares.values())
    for name, value in shares.items():
        setattr(row, name, value)


async def headless_heads(session: AsyncSession) -> list[int]:
    members = select(KinGroupMemberRow.member_node_id).where(KinGroupMemberRow.group_id == KinGroupRow.id)
    statement = select(KinGroupRow.id).where(KinGroupRow.head_node_id.is_not(None), KinGroupRow.head_node_id.not_in(members.scalar_subquery()))
    return list(await session.scalars(statement.order_by(KinGroupRow.id)))


async def clear_head(session: AsyncSession, group_id: int) -> None:
    group = await session.get(KinGroupRow, group_id)
    if group is not None:
        group.head_node_id = None


MEMBER_KEY = 10_000_000


async def strangers_in_kin(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(KinGroupMemberRow.group_id, KinGroupMemberRow.member_node_id, KinGroupRow.people_entity_id)
        .join(KinGroupRow, KinGroupRow.id == KinGroupMemberRow.group_id)
        .where(KinGroupRow.membership == KinMembership.DESCENT, KinGroupMemberRow.adopted.is_(False))
        .order_by(KinGroupMemberRow.group_id, KinGroupMemberRow.member_node_id)
    )
    found: list[int] = []
    for group_id, member_id, people_id in rows:
        member = await session.get(EntityRow, member_id)
        folk = await people_of(session, member) if member is not None else None
        if folk is not None and folk.id != people_id:
            found.append(group_id * MEMBER_KEY + member_id)
    return found


async def adopt_stranger(session: AsyncSession, key: int) -> None:
    group_id, member_id = divmod(key, MEMBER_KEY)
    member = await session.get(KinGroupMemberRow, (group_id, member_id))
    if member is not None:
        member.adopted = True


async def unordered_ages(session: AsyncSession) -> list[int]:
    return [
        row.people_entity_id
        for row in await session.scalars(select(ChildStandingRow).order_by(ChildStandingRow.people_entity_id))
        if [getattr(row, age) for age in STANDING_AGES] != sorted(getattr(row, age) for age in STANDING_AGES)
    ]


async def order_ages(session: AsyncSession, key: int) -> None:
    row = await session.get(ChildStandingRow, key)
    if row is None:
        return
    for age, value in zip(STANDING_AGES, sorted(getattr(row, age) for age in STANDING_AGES), strict=True):
        setattr(row, age, value)


async def uneven_upbringing(session: AsyncSession) -> list[int]:
    return [
        row.people_entity_id
        for row in await session.scalars(select(SocializationRow).order_by(SocializationRow.people_entity_id))
        if sum(getattr(row, name) for name in TECHNIQUE_WEIGHTS) != PERCENT
    ]


async def even_upbringing(session: AsyncSession, key: int) -> None:
    row = await session.get(SocializationRow, key)
    if row is None:
        return
    total = sum(getattr(row, name) for name in TECHNIQUE_WEIGHTS)
    if total <= 0:
        row.example = PERCENT
        return
    shares = {name: getattr(row, name) * PERCENT // total for name in TECHNIQUE_WEIGHTS}
    shares["example"] += PERCENT - sum(shares.values())
    for name, value in shares.items():
        setattr(row, name, value)


async def sexless_norms(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(
        select(IntimacyNormRow).where(IntimacyNormRow.context == RelationContext.BETWEEN_ANY_SEXES).order_by(IntimacyNormRow.people_entity_id)
    ):
        reproduction = await session.get(PeopleReproductionRow, row.people_entity_id)
        if not sexes_fixed(reproduction.system if reproduction is not None else ReproductiveSystem.TWO_SEX):
            found.append(row.people_entity_id)
    return found


async def drop_sexless_norm(session: AsyncSession, key: int) -> None:
    row = await session.get(IntimacyNormRow, (key, RelationContext.BETWEEN_ANY_SEXES))
    if row is not None:
        await session.delete(row)


YOUTH_KEY = 10_000_000


async def grown_members(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for member in await session.scalars(select(YouthGroupMemberRow).order_by(YouthGroupMemberRow.group_id, YouthGroupMemberRow.member_node_id)):
        being = await session.get(EntityRow, member.member_node_id)
        if being is not None and being.status is EntityStatus.CANON and not await is_youth(session, being):
            found.append(member.group_id * YOUTH_KEY + member.member_node_id)
    return found


async def release_grown(session: AsyncSession, key: int) -> None:
    row = await session.get(YouthGroupMemberRow, divmod(key, YOUTH_KEY))
    if row is not None:
        await session.delete(row)


POLICY_HOLDERS = frozenset({EntityType.POLITY, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT, EntityType.SETTLEMENT})


async def stray_policies(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for policy in await session.scalars(select(PopulationPolicyRow).order_by(PopulationPolicyRow.id)):
        holder = await session.get(NodeRow, policy.holder_node_id)
        if isinstance(holder, EntityRow) and holder.entity_type not in POLICY_HOLDERS:
            found.append(policy.id)
    return found


async def drop_policy(session: AsyncSession, key: int) -> None:
    row = await session.get(PopulationPolicyRow, key)
    if row is not None:
        await session.delete(row)


INSTRUMENT_KEY = 100


async def strayed_instruments(session: AsyncSession) -> list[int]:
    statement = (
        select(PopulationInstrumentRow)
        .join(PopulationPolicyRow, PopulationPolicyRow.id == PopulationInstrumentRow.policy_id)
        .where(PopulationInstrumentRow.holder_node_id != PopulationPolicyRow.holder_node_id)
        .order_by(PopulationInstrumentRow.policy_id, PopulationInstrumentRow.instrument)
    )
    return [row.policy_id * INSTRUMENT_KEY + list(PopulationInstrument).index(row.instrument) for row in await session.scalars(statement)]


async def return_instrument(session: AsyncSession, key: int) -> None:
    policy_id, index = divmod(key, INSTRUMENT_KEY)
    row = await session.get(PopulationInstrumentRow, (policy_id, list(PopulationInstrument)[index]))
    policy = await session.get(PopulationPolicyRow, policy_id)
    if row is not None and policy is not None:
        row.holder_node_id = policy.holder_node_id


async def unowned_leases(session: AsyncSession) -> list[int]:
    owned = (
        select(BondRow.id)
        .where(
            BondRow.kind == BondKind.OWNS,
            BondRow.state == BondState.ACTIVE,
            BondRow.source_node_id == LeaseRow.owner_node_id,
            BondRow.target_node_id == LeaseRow.thing_node_id,
        )
        .exists()
    )
    return list(await session.scalars(select(LeaseRow.id).where(~owned).order_by(LeaseRow.id)))


async def void_lease(session: AsyncSession, key: int) -> None:
    row = await session.get(LeaseRow, key)
    if row is not None:
        await session.delete(row)


async def foreign_works(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for works in await session.scalars(select(PublicWorksRow).order_by(PublicWorksRow.id)):
        mine = set(await towns_in(session, works.polity_entity_id))
        route = await session.get(TradeRouteProfileRow, works.place_node_id)
        there = {route.first_market_id, route.second_market_id} if route is not None else set(await towns_of_place(session, works.place_node_id))
        if mine and there and not mine & there:
            found.append(works.id)
    return found


async def drop_works(session: AsyncSession, key: int) -> None:
    row = await session.get(PublicWorksRow, key)
    if row is not None:
        await session.delete(row)


async def overreaching_items(session: AsyncSession) -> list[int]:
    statement = (
        select(MediaItemRow.id)
        .join(MediaOutletRow, MediaOutletRow.id == MediaItemRow.outlet_id)
        .where(
            (MediaItemRow.reach > MediaOutletRow.reach)
            | (MediaItemRow.subject_incident_id.is_(None) & MediaItemRow.subject_node_id.is_(None) & (MediaItemRow.kind == MediaItemKind.RECORD_OF_EVENT))
        )
        .order_by(MediaItemRow.id)
    )
    return list(await session.scalars(statement))


async def fit_item(session: AsyncSession, key: int) -> None:
    item = await session.get(MediaItemRow, key)
    outlet = await session.get(MediaOutletRow, item.outlet_id) if item is not None else None
    if item is None or outlet is None:
        return
    if item.kind is MediaItemKind.RECORD_OF_EVENT and item.subject_incident_id is None and item.subject_node_id is None:
        await session.delete(item)
        return
    item.reach = min(item.reach, outlet.reach)


async def venue_missing(session: AsyncSession, speech: SpeechRow) -> bool:
    if speech.venue is SpeechVenue.OUTLET:
        return await session.scalar(select(MediaOutletRow.id).where(MediaOutletRow.seat_entity_id == speech.place_entity_id).limit(1)) is None
    kinds = VENUE_STRUCTURES.get(speech.venue)
    if kinds is None:
        return False
    found = await session.scalar(
        select(StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.host_entity_id == speech.place_entity_id, StructureProfileRow.kind.in_(sorted(kinds)))
        .limit(1)
    )
    return found is None


async def venueless_speeches(session: AsyncSession) -> list[int]:
    return [speech.id for speech in await session.scalars(select(SpeechRow).order_by(SpeechRow.id)) if await venue_missing(session, speech)]


async def move_to_square(session: AsyncSession, key: int) -> None:
    speech = await session.get(SpeechRow, key)
    if speech is not None:
        speech.venue = SpeechVenue.SQUARE


async def misfit_classes(session: AsyncSession) -> list[int]:
    return [row.id for row in await session.scalars(select(FolkClassRow).order_by(FolkClassRow.id)) if not await fits(session, row)]


async def strike_class(session: AsyncSession, key: int) -> None:
    row = await session.get(FolkClassRow, key)
    if row is not None:
        await session.delete(row)


def read_well(system: NumberSystemRow) -> dict[str, str]:
    known = {reading.value for reading in NumberReading}
    return {number: reading for number, reading in system.numerology.items() if number.isdigit() and int(number) < system.base and reading in known}


async def misread_numbers(session: AsyncSession) -> list[int]:
    return [
        system.people_entity_id
        for system in await session.scalars(select(NumberSystemRow).order_by(NumberSystemRow.people_entity_id))
        if read_well(system) != (system.numerology or {})
    ]


async def drop_misread(session: AsyncSession, key: int) -> None:
    system = await session.get(NumberSystemRow, key)
    if system is not None:
        system.numerology = read_well(system)


async def strayed_stages(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(PublicWorkStageRow.id)
        .join(PublicWorksRow, PublicWorksRow.id == PublicWorkStageRow.works_id)
        .where(PublicWorkStageRow.polity_entity_id != PublicWorksRow.polity_entity_id)
        .order_by(PublicWorkStageRow.id)
    )
    return list(rows.scalars())


async def return_stage(session: AsyncSession, key: int) -> None:
    stage = await session.get(PublicWorkStageRow, key)
    works = await session.get(PublicWorksRow, stage.works_id) if stage is not None else None
    if stage is not None and works is not None:
        stage.polity_entity_id = works.polity_entity_id


async def strayed_practices(session: AsyncSession) -> list[int]:
    communities = select(EntityRow.id).where(EntityRow.entity_type.in_([EntityType.PEOPLE, EntityType.SETTLEMENT]))
    statement = select(FacetPracticeRow.id).where(FacetPracticeRow.community_entity_id.not_in(communities)).order_by(FacetPracticeRow.id)
    return list(await session.scalars(statement))


async def drop_practice(session: AsyncSession, key: int) -> None:
    row = await session.get(FacetPracticeRow, key)
    if row is not None:
        await session.delete(row)


async def misfit_remains(session: AsyncSession) -> list[int]:
    return [
        row.people_entity_id
        for row in await session.scalars(select(PeopleCultureRow).order_by(PeopleCultureRow.people_entity_id))
        if row.remains_treatment not in allowed_remains(row) and "remains_treatment" not in (row.locked or [])
    ]


async def fit_remains_to_rite(session: AsyncSession, key: int) -> None:
    row = await session.get(PeopleCultureRow, key)
    if row is not None:
        row.remains_treatment = allowed_remains(row)[0]


async def false_captures(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(EndowmentRow).where(EndowmentRow.state == EndowmentState.CAPTURED).order_by(EndowmentRow.id)):
        trustee = await session.get(EntityRow, row.trustee_node_id) if row.trustee_node_id is not None else None
        if trustee is None or trustee.entity_type not in CAPTORS:
            found.append(row.id)
    return found


async def free_endowment(session: AsyncSession, key: int) -> None:
    row = await session.get(EndowmentRow, key)
    if row is not None:
        row.state = EndowmentState.SERVING
