from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.polity import PolityProfileRow, VassalageRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState, SubjectKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.services.player import realms, statecraft
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def realm(session: AsyncSession, world: PlayerWorld, name: str, treasury: int = 100) -> int:
    found = await make_entity(session, name, EntityType.POLITY, world_id=world.world.id, stats=PolityStats())
    session.add(
        PolityProfileRow(
            polity_entity_id=found.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            treasury=treasury,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    await session.flush()
    return found.id


async def test_the_god_sets_regard_capacity_spheres_and_subject_terms(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await realm(session, world, "Ash Crown"), await realm(session, world, "Oak Crown")
    await statecraft.set_regard(scope, statecraft.SetRegard(holder_id=first, subject_id=second, threat=70, trust=20))
    regard = await session.get(PolityRegardRow, (first, second))
    assert regard is not None and regard.threat == 70 and {"threat", "trust"} <= set(regard.locked)
    await statecraft.remove_regard(scope, statecraft.RegardTarget(holder_id=first, subject_id=second))
    await statecraft.edit_diplomacy(scope, statecraft.EditDiplomacy(polity_id=first, capacity=5))
    diplomacy = await session.get(DiplomacyProfileRow, first)
    assert diplomacy is not None and diplomacy.capacity == 5
    await statecraft.set_sphere(scope, statecraft.SetSphere(power_id=first, client_id=second, strength=40))
    assert await session.get(SphereRow, (first, second)) is not None
    await statecraft.remove_sphere(scope, statecraft.SphereTarget(power_id=first, client_id=second))
    session.add(VassalageRow(vassal_entity_id=second, overlord_entity_id=first, locked=[]))
    await session.flush()
    await realms.edit_vassalage(scope, realms.EditVassalage(vassal_id=second, kind=SubjectKind.MARCH, liberty=55, coinage=True))
    row = await session.get(VassalageRow, second)
    assert row is not None and row.kind is SubjectKind.MARCH and row.liberty == 55 and row.coinage


async def test_the_god_opens_backs_and_ends_a_crisis(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    demander, target, backer = (
        await realm(session, world, "Elk Crown", 0),
        await realm(session, world, "Fox Crown", 100),
        await realm(session, world, "Jay Crown"),
    )
    opened = await statecraft.open_crisis(scope, statecraft.OpenCrisis(demander_id=demander, target_id=target, demand=CrisisDemand.PAY, amount=30))
    crisis_id = int(opened.values["crisis_id"])
    await statecraft.edit_crisis(scope, statecraft.EditCrisis(crisis_id=crisis_id, escalation=2))
    await statecraft.set_backer(scope, statecraft.SetBacker(crisis_id=crisis_id, backer_id=backer, side=CrisisSide.TARGET, promised=10))
    assert await session.get(CrisisBackerRow, (crisis_id, backer)) is not None
    await statecraft.remove_backer(scope, statecraft.BackerTarget(crisis_id=crisis_id, backer_id=backer))
    await statecraft.hold_crisis(scope, statecraft.HoldCrisis(crisis_id=crisis_id, hold=False))
    await statecraft.resolve_crisis(scope, statecraft.ResolveCrisis(crisis_id=crisis_id, state=CrisisState.CONCEDED))
    row = await session.get(CrisisRow, crisis_id)
    assert row is not None and row.state is CrisisState.CONCEDED
    payer = await session.get(PolityProfileRow, target)
    assert payer is not None and payer.treasury == 70
    await statecraft.delete_crisis(scope, statecraft.CrisisTarget(crisis_id=crisis_id))
    assert await session.get(CrisisRow, crisis_id) is None
