import pytest
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.kin import WillHeirRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import InheritanceCustom
from aerona.engine.demography.wills import allot, make_will, read_will, remove_will, senior_heirs
from aerona.engine.primitives.queries import connect
from tests.engine.society.factories import Realm, context, mortal, tuned


def test_shares_are_dealt_in_proportion() -> None:
    order = allot(10, [70, 30])
    assert order.count(0) == 7 and order.count(1) == 3


async def test_a_will_must_be_whole_and_is_read_at_death(realm: Realm) -> None:
    ctx = context(realm.session, tuned(inheritance={"will_contest_pct": 0}))
    elder = await mortal(realm, "Elder", age=70)
    first, second = await mortal(realm, "First"), await mortal(realm, "Second")
    with pytest.raises(ValidationFailedError):
        await make_will(ctx, elder, [(first.id, 60)])
    will = await make_will(ctx, elder, [(first.id, 60), (second.id, 40)])
    assert sum(row.share for row in await realm.session.scalars(select(WillHeirRow).where(WillHeirRow.will_id == will.id))) == 100
    read = await read_will(ctx, elder, [first], InheritanceCustom.DESIGNATED)
    assert read is not None and {row.id for row, _share in read} == {first.id, second.id}
    assert await remove_will(ctx, elder.id)


async def test_seniority_passes_to_the_eldest_of_the_line(realm: Realm) -> None:
    ctx = context(realm.session, tuned(inheritance={"seniority_dispute_pct": 0}))
    parent = await mortal(realm, "Parent", age=90)
    dead, brother, child = await mortal(realm, "Dead", age=60), await mortal(realm, "Sibling", age=55), await mortal(realm, "Child", age=30)
    for kid in (dead, brother):
        await connect(realm.session, parent.id, kid.id, BondKind.PARENT_OF, ctx.epoch)
    await connect(realm.session, dead.id, child.id, BondKind.PARENT_OF, ctx.epoch)
    await realm.session.flush()
    assert [row.id for row in await senior_heirs(ctx, dead, [child])] == [brother.id]
