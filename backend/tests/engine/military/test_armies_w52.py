from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.war_w52 import ARMY_ROLES, STANCES, UNIT_HONOURS, VETERAN_GRANTS
from aerona.db.tables.honours import UnitHonourRow, VeteranPolicyRow
from aerona.db.tables.military import ArmyOfficerRow
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.honours import UnitHonourKind, VeteranGrant
from aerona.domain.enums.military import ArmyRole, Stance
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.honours.units import HonourTally, esprit_shift
from aerona.engine.honours.veterans import policy_grant, set_policy
from aerona.engine.military.raids import escorted_take
from aerona.engine.military.w52_war import honour_army, keep_paymaster, role_effect, staff_army, winter_cut
from tests.engine.military.w52_war_setup import army_of
from tests.engine.warfare.factories import make, make_ctx
from tests.tools.factories import make_entity


def test_every_stance_role_honour_and_grant_has_its_catalogue_entry() -> None:
    assert set(STANCES) == set(Stance) and set(ARMY_ROLES) == set(ArmyRole)
    assert set(UNIT_HONOURS) == set(UnitHonourKind) and set(VETERAN_GRANTS) == set(VeteranGrant)
    assert STANCES[Stance.WINTER_QUARTERS].resting and STANCES[Stance.WINTER_QUARTERS].feeds and not STANCES[Stance.WINTER_QUARTERS].plunders


async def test_winter_quarters_spare_attrition_and_an_escort_turns_raids_away(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    owner = await make(session, "Vale Folk", EntityType.PEOPLE, world_id, population=4000)
    _, profile = await army_of(ctx, owner.id, world_id)
    assert winter_cut(ctx, profile, 100) == 100
    profile.stance = Stance.WINTER_QUARTERS
    assert winter_cut(ctx, profile, 100) == 100 - ctx.rules.campaign.winter_quarters_attrition_cut_pct
    profile.stance = Stance.ESCORT
    assert escorted_take(ctx.rules, profile, 40) == 40 * (100 - ctx.rules.campaign.escort_raid_cut_pct) // 100


async def test_new_staff_roles_are_filled_and_an_honest_paymaster_eases_mutiny(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    owner = await make(session, "Valeford", EntityType.SETTLEMENT, world_id, population=4000)
    priest = await make(session, "Odo", EntityType.MORTAL, world_id, location_id=owner.id)
    priest.mortal_role = MortalRole.PRIEST
    trader = await make(session, "Mira", EntityType.MORTAL, world_id, location_id=owner.id)
    trader.mortal_role = MortalRole.MERCHANT
    army_id, profile = await army_of(ctx, owner.id, world_id)
    army = await session.get(type(owner), army_id)
    assert army is not None
    assert await staff_army(ctx, army, owner) == 2
    roles = set(await session.scalars(select(ArmyOfficerRow.role).where(ArmyOfficerRow.army_entity_id == army_id)))
    assert {ArmyRole.CHAPLAIN, ArmyRole.PAYMASTER} <= roles
    profile.mutiny = 50
    assert await keep_paymaster(ctx, army_id, profile)
    assert profile.mutiny == 50 - role_effect(ctx, ArmyRole.PAYMASTER) // 2


async def test_relief_and_crossing_honours_raise_esprit_and_a_policy_sets_the_grant(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    owner = await make(session, "Vale Folk", EntityType.PEOPLE, world_id, population=4000)
    army_id, _ = await army_of(ctx, owner.id, world_id)
    assert esprit_shift(ctx, UnitHonourKind.RELIEF) == ctx.rules.unit_honours.relief_esprit
    assert await honour_army(ctx, army_id, UnitHonourKind.CROSSING, "the Grey Ford", HonourTally()) == 1
    kinds = set(await session.scalars(select(UnitHonourRow.kind)))
    assert kinds == {UnitHonourKind.CROSSING}
    realm = await make_entity(session, "Vale Crown", EntityType.POLITY, world_id=world_id, stats=PolityStats())
    await set_policy(ctx, realm.id, VeteranGrant.TAX_EXEMPTION)
    assert (await session.get(VeteranPolicyRow, realm.id)) is not None
    assert await policy_grant(ctx, realm, colony=False, afford=True) is VeteranGrant.TAX_EXEMPTION
    await set_policy(ctx, realm.id, VeteranGrant.LAND)
    assert await policy_grant(ctx, realm, colony=False, afford=True) is None
