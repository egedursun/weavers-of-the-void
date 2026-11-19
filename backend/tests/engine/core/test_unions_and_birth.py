from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.intimacy import ChildRecognitionRow, IntimacyNormRow, LegitimacyRuleRow, ReproductiveCourseRow, RestraintCustomRow
from aerona.db.tables.mind import CultureEthicRow, CultureValueRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import RoleKind
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.intimacy import (
    BirthAttendant,
    ChildLegitimacy,
    NormEnforcer,
    NormSanction,
    NormStance,
    ParentUnion,
    PostnatalCustom,
    RelationContext,
    RestraintRole,
)
from aerona.domain.enums.mind import ActKind, EthicalStance, ValueAxis
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.domain.enums.relations import RelationType
from aerona.engine.collective.roles import CAREER_ROLES, career_open
from aerona.engine.context import TickContext
from aerona.engine.intimacy.course import birth_course
from aerona.engine.intimacy.legitimacy import legitimacy_of, legitimate_heirs, parent_union
from aerona.engine.intimacy.norms import NormTally, keep_norms, lover_pairs, outside_union_weight
from aerona.engine.intimacy.restraint import RestraintTally, break_vows, vow_customs
from aerona.engine.intimacy.seed import seed_intimacy
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement, tuned_rules


async def home_town(session: AsyncSession, world: CoreWorld) -> int:
    if "town" not in world.extra:
        world.extra["town"] = await settlement(session, "Ardun", world, world.regions[0])
        await bond(session, world.extra["town"].id, world.people.id, BondKind.DESCENDS_FROM)
    return world.extra["town"].id


async def folk(session: AsyncSession, world: CoreWorld, name: str, role: MortalRole | None = None, **profile: object) -> EntityRow:
    being = await mortal(session, name, world, await home_town(session, world))
    being.mortal_role = role
    session.add(MortalProfileRow(entity_id=being.id, locked=[], **profile))
    await session.flush()
    return being


async def lovers(session: AsyncSession, first: EntityRow, second: EntityRow) -> None:
    for holder, subject in ((first, second), (second, first)):
        session.add(
            RelationshipRow(holder_node_id=holder.id, subject_node_id=subject.id, romance=90, kinds=[RelationType.LOVER.value], since_epoch=0, last_epoch=0)
        )
    await session.flush()


async def kinds_of(session: AsyncSession, prefix: str) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith(prefix)).order_by(IncidentRow.id)))


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(unions_and_birth=values)))


async def test_a_relation_against_a_forbidden_norm_comes_out_and_is_sanctioned(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(
        IntimacyNormRow(
            people_entity_id=world.people.id,
            context=RelationContext.BEFORE_UNION,
            stance=NormStance.DISCOURAGED,
            enforcer=NormEnforcer.KIN,
            sanction=NormSanction.FINE,
            locked=[],
        )
    )
    first = await folk(session, world, "Ama", honour=50, wealth=50)
    second = await folk(session, world, "Kel", honour=50, wealth=50)
    await lovers(session, first, second)
    tally = NormTally()
    await keep_norms(tuned(ctx, scandal_pct=100, norm_drift_pct=0), tally)
    shamed = await session.get(MortalProfileRow, first.id)
    assert shamed is not None and shamed.honour < 50 and shamed.wealth < 50
    assert tally.scandals == 1 and tally.sanctions == 1
    assert await kinds_of(session, "unions.") == ["unions.scandal", "unions.sanction"]


async def test_norms_move_toward_the_values_of_their_people(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add_all(CultureValueRow(entity_id=world.people.id, axis=axis, value=90) for axis in (ValueAxis.TRADITION, ValueAxis.PIETY, ValueAxis.HONOUR))
    norm = IntimacyNormRow(people_entity_id=world.people.id, context=RelationContext.WITH_OTHER_KINDS, stance=NormStance.ACCEPTED, locked=[])
    session.add(norm)
    await session.flush()
    await keep_norms(tuned(ctx, norm_drift_pct=100), NormTally())
    assert norm.stance is NormStance.TOLERATED
    assert "unions.norm_changed" in await kinds_of(session, "unions.")


async def test_a_child_without_standing_neither_inherits_nor_holds_office_until_recognised(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(LegitimacyRuleRow(people_entity_id=world.people.id, parent_union=ParentUnion.UNWED, standing=ChildLegitimacy.NONE, locked=[]))
    first, second = await folk(session, world, "Dun"), await folk(session, world, "Iro")
    child = await folk(session, world, "Pell")
    for parent in (first, second):
        await bond(session, parent.id, child.id, BondKind.PARENT_OF)
    assert await parent_union(session, child.id) is ParentUnion.UNWED
    assert await legitimacy_of(session, child) is ChildLegitimacy.NONE
    assert await legitimate_heirs(session, [child]) == []
    office = next(path for path, role in CAREER_ROLES.items() if role is RoleKind.OFFICE)
    assert not await career_open(session, ctx.rules, child, office)
    session.add(ChildRecognitionRow(child_node_id=child.id, locked=[]))
    await session.flush()
    assert await legitimate_heirs(session, [child]) == [child]


async def test_a_birth_may_go_wrong_and_the_care_after_it_restores(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(
        ReproductiveCourseRow(people_entity_id=world.people.id, attendant=BirthAttendant.NONE, postnatal=PostnatalCustom.KIN_CARE, rest_months=12, locked=[])
    )
    bearer = await folk(session, world, "Sora", health=80)
    child = await folk(session, world, "Nim")
    await birth_course(tuned(ctx, complication_base_pct=100, complication_harm=30, recovery_health=10), bearer, [child], None)
    profile = await session.get(MortalProfileRow, bearer.id)
    assert profile is not None and profile.health == 61
    assert await kinds_of(session, "birth.") == ["birth.complication", "birth.recovered"]


async def test_customs_of_restraint_bring_vows_and_a_lover_breaks_them(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(RestraintCustomRow(people_entity_id=world.people.id, role=RestraintRole.CLERGY, strength=100, locked=[]))
    priest = await folk(session, world, "Vael", role=MortalRole.PRIEST)
    await session.flush()
    tally = RestraintTally()
    tight = tuned(ctx, restraint_vow_pct=100)
    await vow_customs(tight, tally)
    assert tally.vowed == 1
    await lovers(session, priest, await folk(session, world, "Orin"))
    await break_vows(tight, await lover_pairs(tight), tally)
    oath = await session.scalar(select(OathRow).where(OathRow.swearer_entity_id == priest.id, OathRow.kind == OathKind.CELIBACY))
    assert oath is not None and oath.status is OathStatus.BROKEN and tally.broken == 1
    assert await kinds_of(session, "unions.vow") == ["unions.vow_taken", "unions.vow_broken"]


async def test_seeding_reads_the_ethics_of_a_people_and_weighs_affairs(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(CultureEthicRow(holder_entity_id=world.people.id, act=ActKind.ADULTERY, stance=EthicalStance.UNTHINKABLE, locked=[]))
    await session.flush()
    await seed_intimacy(ctx)
    outside = await session.get(IntimacyNormRow, (world.people.id, RelationContext.OUTSIDE_UNION))
    before = await session.get(IntimacyNormRow, (world.people.id, RelationContext.BEFORE_UNION))
    assert outside is not None and outside.stance is NormStance.FORBIDDEN
    assert before is not None and before.stance is NormStance.TOLERATED
    spouse = await folk(session, world, "Lir")
    assert await outside_union_weight(session, spouse) == 2.0
