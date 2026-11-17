import re
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import endpoints_valid
from aerona.catalog.entity_types import can_contain
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.transformations import ENGINE_KINDS, TRANSFORMS, WARNED_KINDS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import PhenomenonProfileRow
from aerona.db.tables.culture import IdeologyProfileRow
from aerona.db.tables.discovery import TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.physics import StarPhysicsRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.tables.transform import StarModifierRow, TransformationRow, TransformProspectRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import PhenomenonCause, PhenomenonKind
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.domain.enums.titles import TitleTier
from aerona.domain.enums.transform import ProspectStance, TransformKind, TransformState, TransformTrigger
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import (
    BeastStats,
    CultStats,
    EntityStats,
    HouseStats,
    IdeologyStats,
    MortalStats,
    OuterBeingStats,
    PhenomenonStats,
    PolityStats,
    SpiritStats,
    TheoryStats,
    TitleStats,
    TraditionStats,
)
from aerona.engine.context import TickContext
from aerona.engine.cosmos.stellar import luminosity_of, refresh
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect
from aerona.engine.transform import realms
from aerona.engine.transform.anchors import star_god_died
from aerona.engine.transform.kinds import KINDS
from aerona.engine.transform.run import force, order, set_stance, watch
from aerona.rules.registry import Rules
from aerona.services.player.transform_undo import revert
from tests.engine.core.factories import entity
from tests.engine.integration.factories import RichCosmos, seed_rich_cosmos

K = TransformKind
SOURCE = Path(__file__).resolve().parents[3] / "src" / "aerona"
HOOKS = {K.ARTWORK_REMEMBERED: "remember_artwork", K.COLOSSAL_CORPSE: "colossal_remains"}
HOOKED = frozenset(HOOKS)
Builder = Callable[[TickContext, RichCosmos], Awaitable[int]]


def test_every_transformation_has_its_registry_entry_its_line_and_its_engine() -> None:
    assert set(TRANSFORMS) == set(TransformKind)
    assert all(f"transform.{kind.value}" in INCIDENT_KINDS and not INCIDENT_KINDS[f"transform.{kind.value}"].draft for kind in TransformKind)
    assert set(KINDS) == set(ENGINE_KINDS)
    assert {K.FALL, K.CORRUPTION} == WARNED_KINDS
    assert all(not TRANSFORMS[kind].existing for kind in ENGINE_KINDS | HOOKED)


def test_every_transformation_outside_the_watched_ones_is_recorded_where_it_happens() -> None:
    texts = [path.read_text(encoding="utf-8") for path in (SOURCE / "engine").rglob("*.py") if "transform" not in path.parts]
    outside = [kind for kind in TransformKind if kind not in ENGINE_KINDS and kind not in HOOKED]
    missing = [kind for kind in outside if not any(re.search(rf"TransformKind\.{kind.name}\b", text) for text in texts)]
    unhooked = [kind for kind, hook in HOOKS.items() if not any(f"await {hook}(" in text for text in texts)]
    assert missing == [] and unhooked == []


async def world_of_kind(session: AsyncSession, name: str, world_type: WorldType) -> WorldRow:
    home = await session.get(WorldRow, (await CosmosRepository(session).require_cosmos()).primary_world_id)
    assert home is not None
    return await WorldRepository(session).create_world(
        WorldDraft(
            name=name,
            world_type=world_type,
            orbit=home.orbit + 3,
            terrain_seed=name.lower(),
            terrain_sea=0.4,
            terrain_mountains=0.3,
            terrain_humidity=0.5,
            danger=10,
            created_epoch=1,
            star_id=home.star_id,
        )
    )


async def made(ctx: TickContext, cosmos: RichCosmos, name: str, entity_type: EntityType, stats: EntityStats) -> EntityRow:
    region = cosmos.home.regions[0]
    inside = can_contain(region.entity_type, entity_type)
    return await entity(ctx.session, name, entity_type, stats, world_id=cosmos.home.world.id, location_id=region.id if inside else None)


async def a_son(ctx: TickContext, cosmos: RichCosmos) -> int:
    return cosmos.home.son.id


async def a_fallen_body(ctx: TickContext, cosmos: RichCosmos) -> int:
    row = await force(ctx, K.FALL, cosmos.home.son.id)
    son = await ctx.session.get_one(SonRow, cosmos.home.son.id)
    son.existence = 100
    assert row.result_node_id is not None
    return row.result_node_id


async def the_people(ctx: TickContext, cosmos: RichCosmos) -> int:
    return cosmos.home.people.id


async def a_cult(ctx: TickContext, cosmos: RichCosmos) -> int:
    cult = await made(ctx, cosmos, "Keepers of the Count", EntityType.CULT, CultStats(followers=100, zeal=90, influence=40))
    await connect(ctx.session, cult.id, cosmos.home.son.id, BondKind.WORSHIPS, ctx.epoch)
    return cult.id


async def a_realm(ctx: TickContext, cosmos: RichCosmos) -> int:
    polity = await made(ctx, cosmos, "Realm of the Count", EntityType.POLITY, PolityStats(legitimacy=50, stability=50, subjects=1, territory=1))
    ctx.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=cosmos.home.people.id, joined_epoch=1, autonomy=0, locked=[]))
    await ctx.session.flush()
    return polity.id


async def a_house(ctx: TickContext, cosmos: RichCosmos) -> int:
    return (await made(ctx, cosmos, "House Arvel", EntityType.HOUSE, HouseStats(prestige=40, members=20))).id


async def a_phenomenon(ctx: TickContext, cosmos: RichCosmos) -> int:
    phenomenon = await made(ctx, cosmos, "The Open Seam", EntityType.PHENOMENON, PhenomenonStats())
    ctx.session.add(
        PhenomenonProfileRow(
            entity_id=phenomenon.id, kind=PhenomenonKind.OUTSIDE_OPENING, intensity=99, cause=PhenomenonCause.DIVINE, formed_epoch=1, locked=[]
        )
    )
    await ctx.session.flush()
    return phenomenon.id


async def a_living_world(ctx: TickContext, cosmos: RichCosmos) -> int:
    return (await world_of_kind(ctx.session, "Breathing One", WorldType.LIVING)).id


async def a_star(ctx: TickContext, cosmos: RichCosmos) -> int:
    assert cosmos.home.world.star_id is not None
    return cosmos.home.world.star_id


async def a_teaching(ctx: TickContext, cosmos: RichCosmos) -> int:
    ideology = await made(ctx, cosmos, "The Even Hand", EntityType.IDEOLOGY, IdeologyStats(adherents=3, appeal=60))
    ctx.session.add(
        IdeologyProfileRow(ideology_entity_id=ideology.id, value_delta={}, tenets=[], founder_entity_id=None, appeal={}, texts=[], updated_epoch=1, locked=[])
    )
    await ctx.session.flush()
    return ideology.id


async def a_beast(ctx: TickContext, cosmos: RichCosmos) -> int:
    return (await made(ctx, cosmos, "The Long Coil", EntityType.BEAST, BeastStats(hp=200, strength=80, danger=70))).id


async def an_outer_being(ctx: TickContext, cosmos: RichCosmos) -> int:
    return (await made(ctx, cosmos, "The Unlit", EntityType.OUTER_BEING, OuterBeingStats(size=50, interest=60, influence=30))).id


async def a_theory(ctx: TickContext, cosmos: RichCosmos) -> int:
    theory = await made(ctx, cosmos, "The Turning Spheres", EntityType.THEORY, TheoryStats(adherents=3, explanatory=60))
    ctx.session.add(TheoryProfileRow(theory_entity_id=theory.id, domain=TheoryDomain.COSMOLOGY, claim="The spheres turn.", correctness=95, endorsed_by=[]))
    await ctx.session.flush()
    return theory.id


async def a_spirit(ctx: TickContext, cosmos: RichCosmos) -> int:
    return (await made(ctx, cosmos, "Spirit of the Ford", EntityType.SPIRIT, SpiritStats(strength=40, unrest=10))).id


async def a_mortal(ctx: TickContext, cosmos: RichCosmos) -> int:
    return (await made(ctx, cosmos, "Teodor", EntityType.MORTAL, MortalStats(strength=60, agility=50))).id


async def a_cursed_beast(ctx: TickContext, cosmos: RichCosmos) -> int:
    mortal = await a_mortal(ctx, cosmos)
    await force(ctx, K.BEAST_CURSE, mortal)
    return mortal


async def a_held_title(ctx: TickContext, cosmos: RichCosmos) -> int:
    title = await made(ctx, cosmos, "Crown of the Ford", EntityType.TITLE, TitleStats())
    ctx.session.add(TitleProfileRow(title_entity_id=title.id, rank=TitleTier.DISTRICT, holder_node_id=cosmos.home.people.id, locked=[]))
    await ctx.session.flush()
    return title.id


async def a_kept_custom(ctx: TickContext, cosmos: RichCosmos) -> int:
    realm = await a_realm(ctx, cosmos)
    tradition = await made(ctx, cosmos, "The Long Fast", EntityType.TRADITION, TraditionStats())
    second = cosmos.frontiers[0].settlements[0]
    ctx.session.add(PolityMemberRow(polity_entity_id=realm, member_entity_id=second.id, joined_epoch=1, autonomy=0, locked=[]))
    for keeper in (cosmos.home.people.id, second.id):
        await connect(ctx.session, keeper, tradition.id, BondKind.CELEBRATES, ctx.epoch)
    await ctx.session.flush()
    return tradition.id


BUILDERS: dict[TransformKind, Builder] = {
    K.FALL: a_son,
    K.RESTORATION: a_fallen_body,
    K.CORRUPTION: a_son,
    K.LOSS_OF_SAPIENCE: the_people,
    K.ETHNORELIGIOUS: a_cult,
    K.NATION_BUILDING: a_realm,
    K.HOUSE_PEOPLE: a_house,
    K.POCKET_WORLD: a_phenomenon,
    K.WORLD_SOUL: a_living_world,
    K.STAR_GOD: a_star,
    K.SACRALISATION: a_teaching,
    K.SECULARISATION: a_cult,
    K.PROGENITOR: a_beast,
    K.OUTER_ENTRY: an_outer_being,
    K.THEORY_SETTLED: a_theory,
    K.LOCAL_GOD: a_spirit,
    K.BEAST_CURSE: a_mortal,
    K.CURSE_LIFTED: a_cursed_beast,
    K.REALM_FROM_TITLE: a_held_title,
    K.TRADITION_CODIFIED: a_kept_custom,
}


def test_every_watched_kind_has_a_case() -> None:
    assert set(BUILDERS) == set(ENGINE_KINDS)


async def status_of(session: AsyncSession, son_id: int) -> SonStatus:
    return (await session.get_one(SonRow, son_id)).status


async def written(session: AsyncSession, holder_ids: list[int]) -> bool:
    return True


@pytest.mark.parametrize("kind", sorted(BUILDERS))
async def test_every_watched_transformation_can_be_forced_recorded_and_undone(database: Database, monkeypatch: pytest.MonkeyPatch, kind: TransformKind) -> None:
    monkeypatch.setattr(realms, "written_code", written)
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "test_transform", Rules())
        subject = await BUILDERS[kind](ctx, cosmos)
        witness = cosmos.frontiers[0].settlements[0]
        before = await session.get(EntityRow, subject)
        if before is not None:
            await connect(session, witness.id, subject, BondKind.RELATED, ctx.epoch, description="an old tie")
        row = await force(ctx, kind, subject)
        after = await session.get(EntityRow, row.result_node_id)
        if before is not None and after is not None and after.id != subject and endpoints_valid(BondKind.RELATED, witness.entity_type, after.entity_type):
            assert (
                await session.scalar(
                    select(BondRow.id).where(BondRow.source_node_id == witness.id, BondRow.target_node_id == after.id, BondRow.kind == BondKind.RELATED)
                )
                is not None
            )
        assert row.kind is kind and row.state is TransformState.DONE and row.epoch == ctx.epoch
        assert row.result_node_id is not None and await session.get(NodeRow, row.result_node_id) is not None
        assert row.trigger is KINDS[kind].forced_trigger and row.undo
        assert row.incident_id is not None
        assert (await revert(ctx, row.id)).state is TransformState.REVERTED
        subject_row = await session.get(EntityRow, subject)
        if subject_row is not None and subject_row.entity_type is not EntityType.MORTAL:
            assert subject_row.status is EntityStatus.CANON


async def test_a_fall_is_warned_an_epoch_ahead_and_a_block_holds_it(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "test_fall", Rules())
        son = cosmos.home.son
        prospect = await order(ctx, K.FALL, son.id, TransformTrigger.COUNCIL)
        assert prospect.warned_epoch == ctx.epoch and prospect.due_epoch == ctx.epoch + 1
        assert await watch(ctx, K.FALL) == 0
        assert await status_of(session, son.id) is not SonStatus.FALLEN
        prospect.due_epoch = ctx.epoch
        await set_stance(ctx, K.FALL, son.id, ProspectStance.BLOCKED)
        assert await watch(ctx, K.FALL) == 0
        await set_stance(ctx, K.FALL, son.id, ProspectStance.FORCED)
        assert await watch(ctx, K.FALL) == 1
        assert await status_of(session, son.id) is SonStatus.FALLEN and son.essence == 0 and son.body_entity_id is not None
        recorded = await session.scalar(select(TransformationRow).where(TransformationRow.kind == K.FALL))
        assert recorded is not None and recorded.trigger is TransformTrigger.COUNCIL
        assert await session.scalar(select(TransformProspectRow).where(TransformProspectRow.subject_node_id == son.id)) is None


async def test_a_corrupted_son_leaves_no_corpse_and_its_worshippers_follow_what_it_became(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "test_corruption", Rules())
        son = cosmos.home.son
        await connect(session, cosmos.home.people.id, son.id, BondKind.WORSHIPS, ctx.epoch)
        row = await force(ctx, K.CORRUPTION, son.id)
        assert son.status is SonStatus.DEAD and son.death_cause is SonDeathCause.COSMIC_HORROR and son.corpse_entity_id is None
        being = await session.get_one(EntityRow, row.result_node_id)
        assert being.entity_type is EntityType.OUTER_BEING
        assert cosmos.home.people.id in [entity.id for entity in await worshippers_of(session, being.id)]


async def test_a_dead_star_god_dims_its_star_by_a_modifier_on_its_derived_light(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        rules = Rules()
        ctx = await manual_context(session, "test_star_god", rules)
        star_id = await a_star(ctx, cosmos)
        row = await force(ctx, K.STAR_GOD, star_id)
        god = await session.get_one(ForeignGodRow, row.result_node_id)
        assert god.anchor_star_id == star_id
        modifier = await star_god_died(ctx, god)
        assert modifier is not None and modifier.luminosity_pct == -rules.transform.star_god_dim_pct
        star = await session.get_one(StarRow, star_id)
        physics = StarPhysicsRow(
            star_id=star_id, mass=1.0, metallicity=50, age_epochs=10, luminosity=1.0, lifetime_epochs=100, band_inner=0.9, band_outer=1.4, upkeep=0, locked=[]
        )
        refresh(rules, star, physics, modifier.luminosity_pct)
        base = luminosity_of(rules, 1.0, star.age_stage, star.star_type)
        assert physics.luminosity == pytest.approx(base * (100 - rules.transform.star_god_dim_pct) / 100)
        assert physics.mass == 1.0
        assert await session.scalar(select(StarModifierRow.id).where(StarModifierRow.star_id == star_id)) is not None


async def test_a_people_that_loses_its_sapience_ends_and_its_towns_feed_the_kind_it_became(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "test_sapience", Rules())
        people = cosmos.home.people
        row = await force(ctx, K.LOSS_OF_SAPIENCE, people.id)
        assert people.status is EntityStatus.DESTROYED
        species = await session.get_one(EntityRow, row.result_node_id)
        assert species.entity_type is EntityType.SPECIES and row.trigger is TransformTrigger.PUNISHMENT
