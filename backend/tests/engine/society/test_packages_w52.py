from sqlalchemy import select

from aerona.catalog.effect_packages import CURSE_PACKAGES, PACKAGES
from aerona.db.tables.fortune import FortuneSourceRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.affliction import ChangeSign, CharmKind, CureKind, PackageKind, Transmission
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CurseKind
from aerona.engine.body.afflictions import afflict, cure, vengeance_package
from aerona.engine.body.book import ensure_body
from aerona.engine.body.packages_w52 import Shape, pull_charm
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, bonded, context, mortal, son

RULES = Rules()


def test_seventeen_packages_and_every_curse_kind_installs_one() -> None:
    assert len(PACKAGES) == len(PackageKind) == 20
    assert set(CURSE_PACKAGES) == set(CurseKind)
    assert CURSE_PACKAGES[CurseKind.TRANSFORMATION] is PackageKind.TRANSFORMATION
    assert CURSE_PACKAGES[CurseKind.COMPULSION] is PackageKind.CHARM
    assert PACKAGES[PackageKind.FORTUNE].hereditary and PACKAGES[PackageKind.FORTUNE].line is not None


async def test_two_fortunes_of_opposite_sign_meet_in_one_holder_and_shift_their_rolls(realm: Realm) -> None:
    heir = await mortal(realm, "Heir")
    ctx = context(realm.session)
    row = await afflict(ctx, heir, PackageKind.FORTUNE, Transmission.RITE, shape=Shape(fortune_sign=1, fortune_strength=60))
    assert row is not None and row.fortune_sign == 1 and row.fortune_strength == 60
    sources = await realm.session.scalars(select(FortuneSourceRow).where(FortuneSourceRow.holder_node_id == heir.id))
    assert any(source.strength > 0 for source in sources)
    await afflict(ctx, heir, PackageKind.FORTUNE, Transmission.CURSE, shape=Shape(fortune_sign=-1, fortune_strength=80))
    assert row.fortune_sign == -1 and row.fortune_strength == 20
    assert "affliction.fortune_turned" in set(await realm.session.scalars(select(IncidentRow.kind)))


async def test_a_transformation_changes_the_body_and_a_cure_gives_it_back(realm: Realm) -> None:
    bearer = await mortal(realm, "Changed")
    ctx = context(realm.session)
    body = await ensure_body(realm.session, RULES, bearer, 3)
    before = body.plan
    row = await afflict(
        ctx, bearer, PackageKind.TRANSFORMATION, Transmission.CURSE, shape=Shape(transform_plan=BodyPlan.AVIAN, transform_trigger=ChangeSign.SEASON)
    )
    assert row is not None
    assert body.plan is BodyPlan.AVIAN
    await cure(ctx, bearer, row, None)
    assert body.plan is before


async def test_a_charm_binds_toward_its_maker_and_breaks_when_found(realm: Realm) -> None:
    maker, charmed = await mortal(realm, "Courtier"), await mortal(realm, "Ruler")
    ctx = context(realm.session)
    row = await afflict(
        ctx, charmed, PackageKind.CHARM, Transmission.INGESTION, source_node_id=maker.id, shape=Shape(charm_target_node_id=maker.id, charm_kind=CharmKind.LOVE)
    )
    assert row is not None and row.charm_strength == RULES.packages.charm_strength
    assert await bonded(realm.session, charmed.id, maker.id, BondKind.LOVES)
    await cure(ctx, charmed, row, CureKind.MEDICINE)
    assert "affliction.charm_broken" in set(await realm.session.scalars(select(IncidentRow.kind)))


async def test_sacred_vengeance_is_chosen_by_the_god_not_fixed_to_a_domain(realm: Realm) -> None:
    god = await son(realm.session, "Keeper", realm.world.id)
    chosen = vengeance_package(context(realm.session), god)
    assert chosen in set(PackageKind)


async def test_a_fading_charm_is_renewed_by_a_charmer_who_pays_and_fades_for_one_who_cannot(realm: Realm) -> None:
    rich, poor = await mortal(realm, "Patron"), await mortal(realm, "Pauper")
    realm.session.add(MortalProfileRow(entity_id=rich.id, wealth=50, locked=[]))
    realm.session.add(MortalProfileRow(entity_id=poor.id, wealth=0, locked=[]))
    await realm.session.flush()
    ctx = context(realm.session)
    fading = PACKAGES[PackageKind.CHARM].stages[-1]
    assert fading.fades
    kept, lost = await mortal(realm, "Kept"), await mortal(realm, "Lost")
    renewed = await afflict(ctx, kept, PackageKind.CHARM, Transmission.RITE, source_node_id=rich.id, shape=Shape(charm_target_node_id=rich.id))
    faded = await afflict(ctx, lost, PackageKind.CHARM, Transmission.RITE, source_node_id=poor.id, shape=Shape(charm_target_node_id=poor.id))
    assert renewed is not None and faded is not None
    renewed.charm_strength = faded.charm_strength = 30
    await pull_charm(ctx, kept, renewed, fading)
    await pull_charm(ctx, lost, faded, fading)
    assert renewed.charm_strength == RULES.packages.charm_strength
    assert faded.charm_strength == 30 - RULES.packages.charm_fade
    wealth = await realm.session.get(MortalProfileRow, rich.id)
    assert wealth is not None and wealth.wealth < 50
    assert "affliction.charm_renewed" in set(await realm.session.scalars(select(IncidentRow.kind)))
