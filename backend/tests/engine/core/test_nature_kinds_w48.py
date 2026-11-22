from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_tables import ORIGIN_SOURCE
from aerona.catalog.methods import METHODS
from aerona.db.kind_concepts.nature import CREATURE_TRAITS, HOUSE_TRAITS, NATURAL_TRAITS, OFFICE_DUTY, PRODUCT_PARTS, REALM_FUNCTION
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.mythic import CosmicOfficeRow
from aerona.db.tables.nature_kinds import DivineOfficeKindRow, ProductionMethodKindRow, RealmKindRow, TraitKindRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mythic import CosmicOffice, MythicRealm, OfficeChoice
from aerona.domain.enums.nature_kinds import MaterialSource, OfficeDuty, ProductPart, RealmFunction, TraitFunction
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.context import TickContext
from aerona.engine.industry.chosen import method_of
from aerona.engine.kinds.nature import build_of, ensure_built_ins, keep_traits, office_duty, realm_kind_for, realm_kind_of, sturdiness
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, settlement


async def test_every_legacy_value_becomes_a_built_in_row(session: AsyncSession, world: CoreWorld) -> None:
    await ensure_built_ins(session)
    methods = list(await session.scalars(select(ProductionMethodKindRow).where(ProductionMethodKindRow.built_in.is_(True))))
    assert {row.base for row in methods} == set(METHODS)
    offices = list(await session.scalars(select(DivineOfficeKindRow)))
    assert {row.built_in_key for row in offices} == {office.value for office in CosmicOffice}
    realms = list(await session.scalars(select(RealmKindRow)))
    assert {row.built_in_key for row in realms} == {realm.value for realm in MythicRealm}
    traits = list(await session.scalars(select(TraitKindRow)))
    assert len(traits) == len(NATURAL_TRAITS) + len(HOUSE_TRAITS) + len(CREATURE_TRAITS)
    assert await ensure_built_ins(session) == 0


async def test_an_authored_method_drives_what_a_community_makes(ctx: TickContext, world: CoreWorld) -> None:
    town = await settlement(ctx.session, "Mill", world, world.regions[0])
    base = METHODS[MethodKind.HAND_SICKLE]
    kind = ProductionMethodKindRow(name="Wide reaping", category=base.process, base=base.kind, output_pct=250, quality_bonus=10, labour_pct=40, locked=[])
    ctx.session.add(kind)
    await ctx.session.flush()
    ctx.session.add(CommunityMethodRow(community_node_id=town.id, process=base.process, method=base.kind, method_kind_id=kind.id, adopted_epoch=0, locked=[]))
    await ctx.session.flush()
    spec = await method_of(ctx.session, town.id, base.process)
    assert spec.output_pct == 250 and spec.labour_pct == 40 and spec.label == "Wide reaping"


async def test_an_office_takes_its_duty_from_its_authored_kind(ctx: TickContext, world: CoreWorld) -> None:
    row = CosmicOfficeRow(office=CosmicOffice.HUNT, holder_node_id=None, chosen_by=OfficeChoice.CREATOR, neglect=0, duty=0, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    assert (await office_duty(ctx.session, row))[0] is OFFICE_DUTY[CosmicOffice.HUNT]
    kind = DivineOfficeKindRow(name="Keeper of the healed", category=OfficeDuty.HEALING, income_pct=150, locked=[])
    ctx.session.add(kind)
    await ctx.session.flush()
    row.office_kind_id = kind.id
    assert await office_duty(ctx.session, row) == (OfficeDuty.HEALING, 150)


async def test_a_heroquest_enters_an_authored_realm_of_its_function(ctx: TickContext, world: CoreWorld) -> None:
    await ensure_built_ins(ctx.session)
    kind = RealmKindRow(name="The low halls", category=REALM_FUNCTION[MythicRealm.DEAD], steps=5, danger=60, world_id=world.world.id, locked=[])
    ctx.session.add(kind)
    await ctx.session.flush()
    chosen = await realm_kind_for(ctx, MythicRealm.DEAD, world.world.id)
    assert chosen == kind.id
    assert await realm_kind_of(ctx.session, chosen, MythicRealm.DEAD) == (RealmFunction.ABODE_OF_DEAD, 5, "The low halls")


async def test_a_held_trait_pulls_its_holder_capacity(ctx: TickContext, world: CoreWorld) -> None:
    kind = TraitKindRow(name="Keen", category=TraitFunction.MAGIC, strength=100, locked=[])
    ctx.session.add(kind)
    await ctx.session.flush()
    ctx.session.add(KindHoldingRow(concept=KindConcept.TRAIT, kind_id=kind.id, holder_node_id=world.people.id, stance=KindStance.USES, strength=100, locked=[]))
    await ctx.session.flush()
    before = stat(world.people, "magic") or 0
    await keep_traits(ctx)
    assert (stat(world.people, "magic") or 0) > before


async def test_a_world_material_sets_how_a_district_burns_and_stands(ctx: TickContext, world: CoreWorld) -> None:
    town = await settlement(ctx.session, "Stonehold", world, world.regions[0])
    stuff = WorldMaterialRow(
        world_id=world.world.id,
        origin=MaterialOrigin.CATALOG,
        family=MaterialFamily.STONE,
        hardness=90,
        toughness=90,
        weight=60,
        edge=10,
        conductivity=10,
        sanctity=0,
        corruption=0,
        rarity=20,
        base_value=5,
        decay=0,
        created_epoch=0,
        ignition_point=100,
        impact_fracture=100,
        shear_fracture=100,
    )
    ctx.session.add(stuff)
    await ctx.session.flush()
    district = DistrictRow(
        settlement_entity_id=town.id, kind=DistrictKind.MARKET, material=BuildMaterial.TIMBER, world_material_id=stuff.id, built_epoch=0, locked=[]
    )
    ctx.session.add(district)
    await ctx.session.flush()
    assert build_of(ctx.rules, BuildMaterial.TIMBER, stuff).fireproof > build_of(ctx.rules, BuildMaterial.TIMBER, None).fireproof
    assert await sturdiness(ctx.session, ctx.rules, BuildMaterial.TIMBER, stuff.id) > 1.0
    assert await sturdiness(ctx.session, ctx.rules, BuildMaterial.TIMBER, None) == 1.0


def test_every_origin_names_a_source_and_every_product_key_a_part() -> None:
    assert set(ORIGIN_SOURCE) == set(MaterialOrigin)
    assert ORIGIN_SOURCE[MaterialOrigin.DEAD_GOD] is MaterialSource.GOD
    assert PRODUCT_PARTS["milk"] is ProductPart.MILK and PRODUCT_PARTS["timber"] is ProductPart.WOOD
