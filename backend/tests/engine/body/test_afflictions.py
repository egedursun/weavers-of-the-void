from sqlalchemy import select

from aerona.catalog.effect_packages import PACKAGES
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission, Visibility
from aerona.domain.enums.body import BodyFunction, ConditionKind, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.mind import MemoryKind, NeedKind
from aerona.engine.body.afflictions import active, afflict, ageless, cure, inherit, progress, spread_by_bite, traumatise, visible
from aerona.engine.mind.book import needs_of
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, son, tuned

RULES = Rules()


async def conditions(realm: Realm, bearer_id: int) -> set[ConditionKind]:
    rows = await realm.session.scalars(select(ConditionRow.kind).where(ConditionRow.bearer_node_id == bearer_id, ConditionRow.ended_epoch.is_(None)))
    return set(rows)


def test_every_package_has_stages_cures_and_a_transmission() -> None:
    for kind, spec in PACKAGES.items():
        assert spec.kind is kind and spec.stages and spec.cures and spec.transmissions
        assert spec.stages[-1].epochs is None or len(spec.stages) == 1


async def test_a_package_holds_its_condition_and_stats_and_a_cure_gives_them_back(realm: Realm) -> None:
    ctx = context(realm.session)
    bearer = await mortal(realm, "Ivra")
    before = stat(bearer, "strength")
    giver = await son(realm.session, "Oruth", realm.world.id)
    row = await afflict(ctx, bearer, PackageKind.DIVINE_BLESSING, Transmission.RITE, source_node_id=giver.id)
    assert row is not None and row.stage == 1
    assert ConditionKind.CHOSEN_MARK in await conditions(realm, bearer.id)
    assert stat(bearer, "strength") == (before or 0) + 10
    fear = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == bearer.id, MemoryRow.kind == MemoryKind.DREADS))
    assert fear is not None
    assert await afflict(ctx, bearer, PackageKind.DIVINE_BLESSING, Transmission.RITE) is row
    await cure(ctx, bearer, row, CureKind.RITE)
    assert stat(bearer, "strength") == before
    assert ConditionKind.CHOSEN_MARK not in await conditions(realm, bearer.id)
    assert await active(realm.session, bearer.id) == []


async def test_stages_advance_with_time_and_a_hold_stops_them(realm: Realm) -> None:
    bearer = await mortal(realm, "Seln")
    row = await afflict(context(realm.session, epoch=3), bearer, PackageKind.VOID_TAINT, Transmission.CONTACT)
    assert row is not None and row.stage == 1 and visible(row)
    await progress(context(realm.session, epoch=5))
    assert row.stage == 2
    assert ConditionKind.VISIONS in await conditions(realm, bearer.id)
    row.locked = ["stage"]
    await progress(context(realm.session, epoch=9))
    assert row.stage == 2


async def test_a_bite_from_a_moon_changed_bearer_can_pass_the_curse(realm: Realm) -> None:
    ctx = context(realm.session, tuned(effect_packages={"bite_pct": 100}))
    wolf = await mortal(realm, "Garr")
    victim = await mortal(realm, "Pell")
    await afflict(ctx, wolf, PackageKind.LYCANTHROPY, Transmission.CURSE)
    realm.session.add(
        InjuryRow(
            bearer_node_id=victim.id,
            part="left_arm",
            kind=InjuryKind.BITE,
            damage_type=DamageType.PIERCE,
            severity=2,
            state=InjuryState.FRESH,
            function_loss=10,
            cause_kind=HarmCause.MONSTER,
            cause_node_id=wolf.id,
            epoch=ctx.epoch,
        )
    )
    await realm.session.flush()
    assert await spread_by_bite(ctx) == 1
    carried = await active(realm.session, victim.id)
    assert [row.package for row in carried] == [PackageKind.LYCANTHROPY]
    assert PACKAGES[PackageKind.LYCANTHROPY].visibility is Visibility.HIDDEN


async def test_blessings_pass_to_children_and_the_blood_curse_stops_ageing(realm: Realm) -> None:
    ctx = context(realm.session, tuned(effect_packages={"birth_pct": 100}))
    parent = await mortal(realm, "Aud")
    child = await mortal(realm, "Ree")
    await afflict(ctx, parent, PackageKind.DIVINE_BLESSING, Transmission.RITE)
    assert await inherit(ctx, child, [parent.id]) == 1
    cursed = await mortal(realm, "Voss")
    await afflict(ctx, cursed, PackageKind.VAMPIRISM, Transmission.CURSE)
    assert not await ageless(realm.session, cursed.id)
    await progress(context(realm.session, epoch=ctx.epoch + 1))
    assert await ageless(realm.session, cursed.id)
    assert not await ageless(realm.session, parent.id)


async def test_a_heavy_memory_on_a_weak_will_leaves_a_trauma(realm: Realm) -> None:
    ctx = context(realm.session)
    weak = await mortal(realm, "Tam")
    strong = await mortal(realm, "Brec")
    set_stats(weak, willpower=10)
    set_stats(strong, willpower=90)
    foe = await mortal(realm, "Kel")
    for holder in (weak, strong):
        await remember(realm.session, RULES, holder_id=holder.id, subject_id=foe.id, kind=MemoryKind.KILLED_KIN, magnitude=-90, epoch=ctx.epoch)
    assert await traumatise(ctx) == 1
    assert [row.package for row in await active(realm.session, weak.id)] == [PackageKind.TRAUMA]
    assert await active(realm.session, strong.id) == []
    assert (await realm.session.scalars(select(AfflictionRow))).first() is not None


async def test_a_stage_grants_body_traits_and_quenches_needs_until_cured(realm: Realm) -> None:
    ctx = context(realm.session)
    bearer = await mortal(realm, "Iska")
    row = await afflict(ctx, bearer, PackageKind.VAMPIRISM, Transmission.CURSE)
    assert row is not None
    await progress(context(realm.session, epoch=ctx.epoch + 1))
    body = await realm.session.get(BodyRow, bearer.id)
    assert body is not None and BodyFunction.VENOM.value in body.traits
    assert (await needs_of(realm.session, bearer.id)).get(NeedKind.SUSTENANCE) == 100
    await cure(ctx, bearer, row, CureKind.RITE)
    assert BodyFunction.VENOM.value not in body.traits
