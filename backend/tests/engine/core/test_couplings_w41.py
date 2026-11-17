from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.session import Database
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.couplings import CarrionPulseRow, NoveltyStockRow, SignOriginRow, SociolectRow, TeachingRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.discovery import ArtFormProfileRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.collective import AccountKind
from aerona.domain.enums.couplings import (
    CarrionRest,
    FieldAgreementKind,
    FieldAgreementState,
    RestraintKind,
    RiteComponent,
    SealKind,
    SignCause,
    SociolectKind,
    TeachingKind,
    TeachingState,
)
from aerona.domain.enums.culture import ArtMode, MagicSchool, MagicSource
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.transform import TransformKind
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import ArtFormStats, BeastStats, CultStats, MortalStats, PolityStats, RiteStats, SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.couplings import control
from aerona.engine.couplings.beast_memory import memory_dies
from aerona.engine.couplings.carrion import carrion
from aerona.engine.couplings.deep import active_seal, deep_seals
from aerona.engine.couplings.field import break_terms
from aerona.engine.couplings.novelty import novelty
from aerona.engine.couplings.offices import found_sinecure, office_count
from aerona.engine.couplings.rite_body import component_bar
from aerona.engine.couplings.teachers import lesson
from aerona.engine.demography.cohorts import rebalance_classes, seed
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.phases.society_economy import save_society, society_of
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import set_stats
from aerona.engine.transform.bodies import lift_fallen
from aerona.engine.transform.run import force
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity
from tests.engine.integration.factories import RichCosmos, seed_rich_cosmos


async def rite(ctx: TickContext, cosmos: RichCosmos, name: str) -> int:
    made = await entity(ctx.session, name, EntityType.RITE, RiteStats(), world_id=cosmos.home.world.id)
    ctx.session.add(RiteProfileRow(rite_entity_id=made.id, school=next(iter(MagicSchool)), source=MagicSource.LEY, requirements={}, cost={}, locked=[]))
    await ctx.session.flush()
    return made.id


async def caster(ctx: TickContext, cosmos: RichCosmos, name: str) -> int:
    made = await entity(
        ctx.session, name, EntityType.MORTAL, MortalStats(hp=60, age=30, lifespan=70), world_id=cosmos.home.world.id, location_id=cosmos.home.regions[0].id
    )
    return made.id


async def test_a_mortal_with_no_body_record_casts_and_a_gag_stops_a_spoken_rite(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_rite_body", Rules())
        rite_id = await rite(ctx, cosmos, "Spoken Call")
        await control.set_component(ctx, rite_id, RiteComponent.GESTURED, True)
        await control.set_component(ctx, rite_id, RiteComponent.SPOKEN, True)
        mage_id = await caster(ctx, cosmos, "Ilse")
        mage = await ctx.session.get(type(cosmos.home.people), mage_id)
        assert mage is not None
        free = await component_bar(ctx, mage, rite_id)
        assert free.reason is None and free.factor == 1.0
        captor = cosmos.frontiers[0].settlements[0]
        held_row = CaptiveRow(captive_entity_id=mage_id, captor_entity_id=captor.id, taken_epoch=ctx.epoch)
        ctx.session.add(held_row)
        await ctx.session.flush()
        await control.set_restraint(ctx, held_row.id, RestraintKind.GAG, True)
        gagged = await component_bar(ctx, mage, rite_id)
        assert gagged.factor == 0.0 and gagged.reason is not None and "spoken" in gagged.reason
        await control.set_restraint(ctx, held_row.id, RestraintKind.GAG, False)
        assert (await component_bar(ctx, mage, rite_id)).factor == 1.0


async def test_ways_of_speaking_are_made_merged_and_signed(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_registers", Rules())
        folk = cosmos.home.people
        guild = await control.create_sociolect(ctx, folk.id, SociolectKind.GUILD)
        cant = await control.create_sociolect(ctx, folk.id, SociolectKind.CANT)
        assert cant.secret and not guild.secret and guild.language_entity_id == cant.language_entity_id
        kept = await control.merge_sociolects(ctx, guild.id, cant.id)
        assert kept.id == guild.id
        assert list(await ctx.session.scalars(select(SociolectRow.id))) == [guild.id]
        with pytest.raises(ValidationFailedError):
            await control.merge_sociolects(ctx, guild.id, guild.id)
        signed = await control.create_sign_language(ctx, folk.id, SignCause.DEAFNESS)
        origin = await ctx.session.get(SignOriginRow, signed.id)
        assert signed.entity_type is EntityType.LANGUAGE and origin is not None and origin.cause is SignCause.DEAFNESS


async def test_unburied_dead_are_buried_unless_the_god_keeps_them(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_carrion", Rules())
        region = cosmos.home.regions[0]
        row = await control.keep_dead(ctx, region.id, False)
        row.carrion = 1000
        await ctx.session.flush()
        await carrion(ctx)
        buried = await ctx.session.get(CarrionPulseRow, region.id)
        assert buried is not None and buried.carrion < 1000
        left = buried.carrion
        await control.keep_dead(ctx, region.id, True)
        await carrion(ctx)
        kept = await ctx.session.get(CarrionPulseRow, region.id)
        assert kept is not None and kept.kept and kept.carrion <= left
        assert await control.clear_dead(ctx, region.id) == kept.carrion
        assert await ctx.session.get(CarrionPulseRow, region.id) is None


async def test_a_spirit_teaches_its_living_kin_a_rite_unless_the_creator_forbids_it(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_teachers", Rules())
        folk = cosmos.home.people
        rite_id = await rite(ctx, cosmos, "Old Song of the Ford")
        elder = await entity(ctx.session, "Old Teacher", EntityType.MORTAL, MortalStats(hp=0, age=80, lifespan=70), world_id=cosmos.home.world.id)
        elder.status, elder.end_epoch = EntityStatus.DEAD, 1
        await connect(ctx.session, elder.id, rite_id, BondKind.OWNS, 1)
        shade = await entity(
            ctx.session, "Teacher's Shade", EntityType.SPIRIT, SpiritStats(), world_id=cosmos.home.world.id, location_id=cosmos.home.regions[0].id
        )
        await connect(ctx.session, shade.id, elder.id, BondKind.DESCENDS_FROM, 1)
        await control.block_teaching(ctx, shade.id, folk.id)
        assert await lesson(ctx, shade, folk, kinds=(TeachingKind.RITE,)) is None
        row = await control.grant_teaching(ctx, shade.id, folk.id, TeachingKind.RITE)
        assert row.state is TeachingState.TAUGHT and row.subject_node_id == rite_id
        owns = await ctx.session.scalar(select(TeachingRow.id).where(TeachingRow.learner_entity_id == folk.id, TeachingRow.kind == TeachingKind.RITE))
        assert owns == row.id


async def test_an_elder_beast_remembers_tells_and_takes_its_memory_when_it_dies(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_beasts", Rules())
        folk = cosmos.home.people
        beast = await entity(ctx.session, "Grey Elder", EntityType.BEAST, BeastStats(), world_id=cosmos.home.world.id, location_id=cosmos.home.regions[0].id)
        ctx.session.add(BeastProfileRow(beast_entity_id=beast.id, intelligence=80, age=400))
        happening = CollectionRow(kind=next(iter(CollectionKind)), world_id=cosmos.home.world.id, name="The Long Flood", start_epoch=1)
        ctx.session.add(happening)
        await ctx.session.flush()
        memory = await control.grant_lore(ctx, beast.id, happening.id)
        assert memory.kind is AccountKind.ELDER_MEMORY
        told = await control.reveal_lore(ctx, beast.id, folk.id)
        assert told.kind is TeachingKind.ACCOUNT
        assert await memory_dies(ctx, beast) >= 1
        assert await ctx.session.scalar(select(AccountRow.id).where(AccountRow.holder_entity_id == beast.id)) is None
        assert await ctx.session.scalar(select(AccountRow.id).where(AccountRow.holder_entity_id == folk.id)) is not None


async def test_terms_in_the_field_are_forced_voided_and_broken(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_field", Rules())
        town = cosmos.frontiers[0].settlements[0]
        truce = await control.force_agreement(ctx, FieldAgreementKind.TRUCE, None, commander_id=None, counterpart_id=None, place_id=town.id)
        assert truce.state is FieldAgreementState.KEPT
        voided = await control.void_agreement(ctx, truce.id)
        assert voided.state is FieldAgreementState.REPUDIATED and voided.ended_epoch == ctx.epoch
        with pytest.raises(ValidationFailedError):
            await control.void_agreement(ctx, truce.id)
        terms = await control.force_agreement(ctx, FieldAgreementKind.SURRENDER, None, commander_id=None, counterpart_id=None, place_id=town.id)
        await break_terms(ctx, terms, town.id)
        assert terms.state is FieldAgreementState.BROKEN


async def test_a_seal_over_the_deep_wears_and_can_be_broken(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_deep", Rules())
        town = cosmos.frontiers[0].settlements[0]
        sealed = await control.seal(ctx, town.id, SealKind.STRUCTURE, 50)
        assert await active_seal(ctx.session, town.id) is not None
        await deep_seals(ctx)
        assert sealed.strength < 50
        await control.unseal(ctx, sealed.id)
        assert sealed.broken_epoch == ctx.epoch and await active_seal(ctx.session, town.id) is None


async def test_fashion_wears_out_as_a_form_spreads_and_only_forms_and_dishes_have_it(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_fashion", Rules())
        form = await entity(ctx.session, "Reed Song", EntityType.ART_FORM, ArtFormStats(), world_id=cosmos.home.world.id)
        ctx.session.add(ArtFormProfileRow(art_form_entity_id=form.id, discipline=next(iter(ArtMode))))
        await ctx.session.flush()
        with pytest.raises(ValidationFailedError):
            await control.set_novelty(ctx, cosmos.home.people.id, {"novelty": 10}, [])
        row = await control.set_novelty(ctx, form.id, {"novelty": 90, "adoption": 100}, [])
        assert row.locked == ["novelty", "adoption"] or set(row.locked) == {"novelty", "adoption"}
        await control.set_novelty(ctx, form.id, {}, ["novelty", "adoption"])
        await novelty(ctx)
        stock = await ctx.session.get(NoveltyStockRow, form.id)
        assert stock is not None and stock.novelty != 90


async def test_a_realm_makes_an_office_for_its_aspirants_and_pays_for_it(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_offices", Rules())
        realm = await entity(ctx.session, "Vale Crown", EntityType.POLITY, PolityStats(), world_id=cosmos.home.world.id)
        rule = {"government": next(iter(GovernmentKind)), "decision_rule": next(iter(DecisionRule))}
        profile = PolityProfileRow(polity_entity_id=realm.id, treasury=ctx.rules.offices_made.cost * 2, **rule)
        town = cosmos.frontiers[0].settlements[0]
        ctx.session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
        stats = MortalStats(hp=60, age=30, lifespan=70)
        noble = await entity(ctx.session, "Lady Orrin", EntityType.MORTAL, stats, world_id=cosmos.frontiers[0].world.id, location_id=town.id)
        noble.social_class = SocialClass.NOBLE
        ctx.session.add(profile)
        await ctx.session.flush()
        made = await found_sinecure(ctx, profile, realm)
        assert made is not None and made.sinecure
        assert profile.treasury == ctx.rules.offices_made.cost
        assert await office_count(ctx, realm.id) == 1


async def homeland_of(session: AsyncSession, cosmos: RichCosmos) -> EntityRow:
    town = cosmos.frontiers[0].settlements[0]
    folk = cosmos.frontiers[0].peoples[0]
    await connect(session, folk.id, town.id, BondKind.LIVES_IN, 1)
    bond = await session.scalar(select(BondRow).where(BondRow.source_node_id == folk.id, BondRow.target_node_id == town.id, BondRow.kind == BondKind.LIVES_IN))
    assert bond is not None
    bond.role = BondRole.HOMELAND
    await session.flush()
    return folk


async def settled_mortal(session: AsyncSession, cosmos: RichCosmos, name: str) -> EntityRow:
    town = cosmos.frontiers[0].settlements[0]
    stats = MortalStats(hp=60, age=30, lifespan=70)
    return await entity(session, name, EntityType.MORTAL, stats, world_id=cosmos.frontiers[0].world.id, location_id=town.id)


@pytest.mark.parametrize(
    ("variants", "parts", "casts"),
    [
        (["construct"], [RiteComponent.SPOKEN], False),
        (["construct"], [RiteComponent.INSCRIBED, RiteComponent.MATERIAL], True),
        (["incorporeal"], [RiteComponent.GESTURED], False),
        (["incorporeal"], [RiteComponent.MENTAL, RiteComponent.SPOKEN], True),
        (["aquatic"], [RiteComponent.INSCRIBED], False),
        (["aquatic"], [RiteComponent.SUNG, RiteComponent.GESTURED], True),
        (["plant_like"], [RiteComponent.DANCED], False),
        (["gaseous"], [RiteComponent.SPOKEN], True),
    ],
)
async def test_a_casters_biology_decides_which_parts_of_a_rite_it_can_give(
    database: Database, variants: list[str], parts: list[RiteComponent], casts: bool
) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        folk = await homeland_of(session, cosmos)
        session.add(BiologyRow(holder_entity_id=folk.id, variants=variants, locked=[]))
        await session.flush()
        ctx = await manual_context(session, "w41_biology", Rules())
        rite_id = await rite(ctx, cosmos, "Bodied Call")
        for part in parts:
            await control.set_component(ctx, rite_id, part, True)
        mage = await settled_mortal(session, cosmos, "Vessa")
        bar = await component_bar(ctx, mage, rite_id)
        assert (bar.factor > 0) is casts, bar.reason


async def test_a_plant_like_caster_casts_slowly(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        folk = await homeland_of(session, cosmos)
        session.add(BiologyRow(holder_entity_id=folk.id, variants=["plant_like"], locked=[]))
        await session.flush()
        ctx = await manual_context(session, "w41_slow", Rules())
        rite_id = await rite(ctx, cosmos, "Slow Growth")
        await control.set_component(ctx, rite_id, RiteComponent.MATERIAL, True)
        mage = await settled_mortal(session, cosmos, "Oak Speaker")
        assert (await component_bar(ctx, mage, rite_id)).factor == ctx.rules.couplings.slow_casting_pct / 100


@pytest.mark.parametrize(
    ("world_type", "rest", "kept"),
    [
        (WorldType.ICE, CarrionRest.FROZEN, True),
        (WorldType.SAND, CarrionRest.MUMMIFIED, True),
        (WorldType.ASTEROID_BELT, CarrionRest.FLOATING, True),
        (WorldType.GAS, CarrionRest.DRIFTING, False),
    ],
)
async def test_where_nothing_eats_the_dead_the_land_keeps_them_its_own_way(database: Database, world_type: WorldType, rest: CarrionRest, kept: bool) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w41_rest", Rules())
        frontier = cosmos.frontiers[0]
        frontier.world.world_type = world_type
        region = frontier.regions[0]
        row = await control.keep_dead(ctx, region.id, True)
        row.carrion = 300
        await session.flush()
        await carrion(ctx)
        after = await session.get(CarrionPulseRow, region.id)
        assert after is not None and after.rest is rest and after.preserved is kept
        assert (after.carrion == 0) is (rest is CarrionRest.DRIFTING)


async def test_story_29_the_fallen_god(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        base = Rules()
        ctx = await manual_context(session, "story_29", replace(base, transform=replace(base.transform, remnant_pct=100, seek_name_chance=100)))
        son = cosmos.home.son
        faithful, doubting = cosmos.home.people, cosmos.frontiers[0].peoples[0]
        set_stats(faithful, piety=100)
        set_stats(doubting, piety=0)
        for worshipper in (faithful, doubting):
            await connect(session, worshipper.id, son.id, BondKind.WORSHIPS, ctx.epoch)
        await force(ctx, TransformKind.FALL, son.id)
        assert son.status is SonStatus.FALLEN and son.body_entity_id is not None
        body = await session.get_one(EntityRow, son.body_entity_id)
        assert body.entity_type is EntityType.MORTAL
        recognising = {entity.id for entity in await worshippers_of(session, body.id)}
        assert faithful.id in recognising and doubting.id not in recognising
        keeper = await entity(session, "Grey Elder", EntityType.BEAST, BeastStats(), world_id=cosmos.home.world.id, location_id=body.location_id)
        session.add(BeastProfileRow(beast_entity_id=keeper.id, intelligence=90, age=600))
        name = await session.get_one(TrueNameRow, body.id)
        name.known_by = sorted({*name.known_by, keeper.id, body.id})
        before = son.existence
        await lift_fallen(ctx, body.id, ctx.rules.transform.true_name_existence)
        assert son.existence > before
        await force(ctx, TransformKind.RESTORATION, body.id)
        assert son.status is SonStatus.ACTIVE and body.status is EntityStatus.DEAD


async def test_story_29_a_fallen_god_who_dies_mortal_leaves_a_cult_that_turns_to_an_ideology(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "story_29_martyr", Rules())
        son = cosmos.home.son
        cult = await entity(session, "Followers of the Fallen", EntityType.CULT, CultStats(followers=40, zeal=20), world_id=cosmos.home.world.id)
        await connect(session, cult.id, son.id, BondKind.WORSHIPS, ctx.epoch)
        await force(ctx, TransformKind.FALL, son.id)
        row = await force(ctx, TransformKind.SECULARISATION, cult.id)
        became = await session.get_one(EntityRow, row.result_node_id)
        assert became.entity_type is EntityType.IDEOLOGY


async def test_rebalancing_classes_never_puts_people_in_a_class_with_no_share(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        folk = cosmos.home.people
        society = await save_society(session, folk.id, await society_of(session, Rules(), folk.id))
        for social_class in SocialClass:
            setattr(society, f"share_{social_class.value}", 0.0)
        society.share_farmer, society.share_artisan, society.share_priest = 61.3, 25.4, 13.3
        await session.flush()
        rows = await seed(session, Rules(), folk, 1)
        assert rows
        rows[next(iter(rows))].count += 7
        await rebalance_classes(session, Rules(), folk, rows, 1)
        idle = sum(row.count for key, row in rows.items() if key[2] in {SocialClass.UNEMPLOYED, SocialClass.MONASTIC, SocialClass.WORKER})
        assert idle == 0 and sum(row.count for row in rows.values()) > 0
