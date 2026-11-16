from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.mind import PersonalityValueRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import FeudAction, FeudParty, FeudStatus
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.military.feuds import common_enemy, intermarried, members, realm_party, temper
from aerona.engine.mind.memories import remember
from aerona.engine.phases.vendettas import act, choose, feuds, grief, honour_duels, target_of
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import feud_between, open_feud, start_blood_feud
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx, tune

NEVER = {
    "mediation_chance": 0,
    "wergild_chance": 0,
    "escalate_chance": 0,
    "assassinate_chance": 0,
    "raid_chance": 0,
    "seek_mediation_chance": 0,
    "allies_chance": 0,
    "abduct_chance": 0,
    "ambush_chance": 0,
    "property_chance": 0,
}


def only(action: str) -> Rules:
    return tune(Rules(), vendetta=NEVER | {action: 100})


async def peoples(session: AsyncSession, world_id: int) -> tuple[EntityRow, EntityRow]:
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, prosperity=60, wealth=60)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000, prosperity=60, wealth=60)
    return first, second


async def ruler(session: AsyncSession, world_id: int, realm: EntityRow, name: str) -> EntityRow:
    mortal = await make(session, name, EntityType.MORTAL, world_id, age=30, hp=90)
    await bond(session, mortal.id, realm.id, BondKind.RULES)
    return mortal


async def burning(ctx: TickContext, first: EntityRow, second: EntityRow) -> FeudRow:
    await start_blood_feud(ctx, first.id, second.id, "a killing")
    await remember(ctx.session, ctx.rules, holder_id=first.id, subject_id=second.id, kind=MemoryKind.KILLED_KIN, magnitude=-90, epoch=ctx.epoch)
    feud = await feud_between(ctx.session, first.id, second.id)
    assert feud is not None
    feud.grievance = feud.intensity = 90
    await ctx.session.flush()
    return feud


async def house(session: AsyncSession, world_id: int, name: str, head: EntityRow | None = None) -> EntityRow:
    row = await make(session, name, EntityType.HOUSE, world_id)
    session.add(HouseProfileRow(house_entity_id=row.id, head_entity_id=head.id if head else None, traits=[], seats=[], locked=[]))
    if head is not None:
        session.add(HouseMemberRow(house_entity_id=row.id, mortal_entity_id=head.id, joined_epoch=1, by_marriage=False))
    await session.flush()
    return row


async def test_grief_sums_only_the_pain_of_slain_and_maimed_kin(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    await remember(session, ctx.rules, holder_id=first.id, subject_id=second.id, kind=MemoryKind.KILLED_KIN, magnitude=-30, epoch=1)
    await remember(session, ctx.rules, holder_id=first.id, subject_id=second.id, kind=MemoryKind.MAIMED_ME, magnitude=-20, epoch=1, merge=False)
    await remember(session, ctx.rules, holder_id=first.id, subject_id=second.id, kind=MemoryKind.HUMILIATED_ME, magnitude=-40, epoch=1)
    assert await grief(ctx, first.id, second.id) == 50
    assert await grief(ctx, second.id, first.id) == 0


async def test_a_burning_feud_raids_the_enemy_and_records_the_act(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, only("raid_chance"))
    first, second = await peoples(session, world_id)
    lord = await ruler(session, world_id, second, "Lord Tam")
    feud = await burning(ctx, first, second)
    hp = stat(lord, "hp") or 0
    assert await feuds(ctx) == 1
    assert feud.last_action == FeudAction.RAID.value and feud.last_epoch == ctx.epoch
    assert (stat(second, "prosperity") or 0) < 60 and (stat(lord, "hp") or 0) < hp


async def test_wergild_moves_wealth_and_lays_the_feud_to_rest(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    feud = await burning(ctx, first, second)
    text = await act(ctx, FeudAction.DEMAND_WERGILD, first, second)
    assert text is not None and "wergild" in text
    assert (stat(first, "wealth") or 0) > (stat(second, "wealth") or 0)
    assert feud.status is FeudStatus.SETTLED


async def test_mediation_ends_the_feud_as_mediated(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    feud = await burning(ctx, first, second)
    assert await act(ctx, None, first, second) is not None
    assert feud.status is FeudStatus.MEDIATED


async def test_an_assassin_kills_the_enemy_ruler_and_the_feud_turns_back(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    lord = await ruler(session, world_id, second, "Lord Tam")
    await burning(ctx, first, second)
    assert await target_of(ctx, second) is lord
    text = await act(ctx, FeudAction.ASSASSINATE, first, second)
    assert text is not None and lord.status is EntityStatus.DEAD


async def test_an_assassin_finds_no_one_where_the_enemy_has_no_ruler(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    assert await act(ctx, FeudAction.ASSASSINATE, first, second) is None


async def test_a_house_feud_strikes_at_the_head_and_opens_a_house_feud(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first_head = await make(session, "Ana", EntityType.MORTAL, world_id, age=40)
    second_head = await make(session, "Bel", EntityType.MORTAL, world_id, age=40)
    first, second = await house(session, world_id, "House Ana", first_head), await house(session, world_id, "House Bel", second_head)
    assert await members(session, first) == {first_head.id}
    assert await target_of(ctx, second) is second_head
    assert await act(ctx, FeudAction.ASSASSINATE, first, second) is not None
    feud = await feud_between(session, first.id, second.id)
    assert feud is not None and feud.party is FeudParty.HOUSE


async def test_escalation_opens_a_war_between_the_realms(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    await burning(ctx, first, second)
    assert await act(ctx, FeudAction.ESCALATE, first, second) is not None
    enemy = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.source_node_id == first.id))
    assert enemy is not None and enemy.target_node_id == second.id and enemy.war_cause is WarCause.VENDETTA


async def test_escalation_within_one_realm_finds_no_war(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    realm = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    first, second = await house(session, world_id, "House Ana"), await house(session, world_id, "House Bel")
    for row in (first, second):
        profile = await session.get(HouseProfileRow, row.id)
        assert profile is not None
        profile.polity_entity_id = realm.id
    assert await realm_party(session, first) == realm.id
    assert await act(ctx, FeudAction.ESCALATE, first, second) is None
    assert await act(ctx, FeudAction.REST, first, second) is None


async def test_choose_follows_the_chances_and_rests_when_none_fire(session: AsyncSession, world_id: int) -> None:
    first, second = await peoples(session, world_id)
    assert await choose(make_ctx(session, only("escalate_chance")), first, second) is FeudAction.ESCALATE
    assert await choose(make_ctx(session, only("assassinate_chance")), first, second) is FeudAction.ASSASSINATE
    assert await choose(make_ctx(session, tune(Rules(), vendetta=NEVER)), first, second) is FeudAction.REST


async def test_marriage_and_a_shared_enemy_cool_a_feud(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    foe = await make(session, "Ash Folk", EntityType.PEOPLE, world_id, population=4000)
    homes = [await make(session, f"{realm.name} Town", EntityType.SETTLEMENT, world_id, population=900) for realm in (first, second)]
    await bond(session, homes[0].id, first.id, BondKind.DESCENDS_FROM)
    await BondRepository(session).connect(BondDraft(second.id, homes[1].id, BondKind.RULES, 1, "homeland", role=BondRole.HOMELAND))
    lover = await make(session, "Ama", EntityType.MORTAL, world_id, location_id=homes[0].id, age=25)
    beloved = await make(session, "Bo", EntityType.MORTAL, world_id, location_id=homes[1].id, age=25)
    assert await members(session, first) == {lover.id} and await members(session, second) == {beloved.id}
    feud = await burning(ctx, first, second)
    hot = await temper(ctx, feud, first, second, 90)
    await bond(session, lover.id, beloved.id, BondKind.LOVES)
    assert await intermarried(session, first, second)
    await open_war(ctx, first, foe)
    await open_war(ctx, second, foe)
    assert await common_enemy(session, first, second)
    feud.intensity = 90
    assert await temper(ctx, feud, first, second, 90) < hot


async def test_a_cold_feud_fades_and_a_feud_with_a_lost_side_ends(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first, second = await peoples(session, world_id)
    cold = await open_feud(session, ctx.rules, first.id, second.id, epoch=1, cause="old", party=FeudParty.COMMUNITY)
    cold.grievance = cold.intensity = 0
    third = await make(session, "Ash Folk", EntityType.PEOPLE, world_id, population=4000)
    lost = await open_feud(session, ctx.rules, first.id, third.id, epoch=1, cause="old", party=FeudParty.COMMUNITY)
    third.status, third.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    await session.flush()
    assert await feuds(ctx) == 0
    assert cold.status is FeudStatus.FADED and lost.status is FeudStatus.EXTINGUISHED


async def test_an_insulted_mortal_of_honour_calls_a_duel(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    town = await make(session, "Brookhold", EntityType.SETTLEMENT, world_id, population=900)
    holder = await make(session, "Asa", EntityType.MORTAL, world_id, location_id=town.id, age=30, hp=60)
    subject = await make(session, "Bram", EntityType.MORTAL, world_id, location_id=town.id, age=30, hp=60)
    session.add(PersonalityValueRow(node_id=holder.id, axis=ValueAxis.HONOUR, value=60))
    await remember(session, ctx.rules, holder_id=holder.id, subject_id=subject.id, kind=MemoryKind.HUMILIATED_ME, magnitude=-80, epoch=1)
    await session.flush()
    assert await honour_duels(ctx) == 1


async def test_a_mortal_without_honour_swallows_the_insult(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    town = await make(session, "Brookhold", EntityType.SETTLEMENT, world_id, population=900)
    holder = await make(session, "Asa", EntityType.MORTAL, world_id, location_id=town.id, age=30, hp=60)
    subject = await make(session, "Bram", EntityType.MORTAL, world_id, location_id=town.id, age=30, hp=60)
    session.add(PersonalityValueRow(node_id=holder.id, axis=ValueAxis.HONOUR, value=-60))
    await remember(session, ctx.rules, holder_id=holder.id, subject_id=subject.id, kind=MemoryKind.HUMILIATED_ME, magnitude=-80, epoch=1)
    await session.flush()
    assert await honour_duels(ctx) == 0
