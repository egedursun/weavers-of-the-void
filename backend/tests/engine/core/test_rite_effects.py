from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import RiteEffectRow, RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import ForcedWeatherRow
from aerona.db.tables.faith import PossessionRow, SpiritProfileRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CalendarSlot, MagicSchool, MagicSource, RiteEffectKind, SummonForm
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.faith import AfterlifeState, BindingKind, SpiritAlignment
from aerona.domain.enums.military import CaptiveFate
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.lore.rites import (
    EFFECTS,
    Working,
    at_war,
    gathering,
    pay_blood,
    pay_divine,
    pay_sanity,
    pay_souls,
    phenomenon,
    possessed_near,
    sky_shows,
    slot_closed,
    victim_in,
    wandering_near,
)
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement

E = RiteEffectKind


async def scene(session: AsyncSession, world: CoreWorld) -> tuple[TickContext, EntityRow, EntityRow]:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    caster = await mortal(session, "Ilsa", world, town.id)
    return ctx, town, caster


def work(caster: EntityRow, effect: RiteEffectKind, *, target: EntityRow | None = None, power: int = 5, form: SummonForm | None = None) -> Working:
    row = RiteProfileRow(school=MagicSchool.DEATH, source=MagicSource.SOUL, power=power, locked=[], forbidden_by=[], requirements={}, cost={})
    return Working(caster, target, RiteEffectRow(effect=effect, magnitude=5, summon_form=form), 5, row)


async def soul(session: AsyncSession, world: CoreWorld, origin: EntityRow, **values: object) -> SpiritProfileRow:
    spirit = await entity(session, f"Shade of {origin.name}", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=origin.location_id)
    profile = SpiritProfileRow(spirit_entity_id=spirit.id, origin_mortal_id=origin.id, locked=[], **values)
    session.add(profile)
    await session.flush()
    return profile


async def test_a_divine_price_is_paid_from_the_patrons_essence(session: AsyncSession, world: CoreWorld) -> None:
    ctx, _, caster = await scene(session, world)
    assert not await pay_divine(ctx, caster, 1)
    await bond(session, caster.id, world.son.id, BondKind.WORSHIPS)
    world.son.essence = 10
    assert await pay_divine(ctx, caster, 4) and world.son.essence == 6
    assert not await pay_divine(ctx, caster, 100)


async def test_blood_is_taken_from_captives_before_the_caster(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, caster = await scene(session, world)
    hp = stat(caster, "hp") or 0
    assert await pay_blood(ctx, caster, 10)
    assert (stat(caster, "hp") or 0) < hp
    cohort = CaptiveCohortRow(
        captor_entity_id=town.id, origin_entity_id=world.people.id, count=5, social_class=SocialClass.FARMER, fate=CaptiveFate.HELD, since_epoch=1
    )
    session.add(cohort)
    await session.flush()
    wounded = stat(caster, "hp")
    assert await pay_blood(ctx, caster, ctx.rules.rites.hp_per_captive * 2)
    assert cohort.count == 3 and stat(caster, "hp") == wounded


async def test_souls_and_sanity_pay_their_own_price(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, caster = await scene(session, world)
    dead = await mortal(session, "Oren", world, town.id)
    assert not await pay_souls(ctx, caster, 1)
    profile = await soul(session, world, dead)
    assert await pay_souls(ctx, caster, 1)
    assert profile.state is AfterlifeState.CONSUMED
    spirit = await session.get(EntityRow, profile.spirit_entity_id)
    assert spirit is not None and spirit.status is EntityStatus.DESTROYED
    before = caster.sanity
    assert await pay_sanity(ctx, caster, 10)
    assert caster.sanity is not None and (before is None or caster.sanity < before)


async def test_a_gathering_counts_the_folk_and_a_quiet_sky_shows_nothing(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, caster = await scene(session, world)
    assert await gathering(ctx, caster) == 1
    assert await gathering(ctx, town) == stat(town, "population")
    assert not await sky_shows(ctx, "eclipse")
    assert await slot_closed(ctx, caster, CalendarSlot.HOLY_DAY) is not None
    assert not await at_war(ctx, caster)


async def test_binding_and_raising_take_the_wandering_dead_of_the_place(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, caster = await scene(session, world)
    assert await EFFECTS[E.BIND](ctx, work(caster, E.BIND)) is None
    dead = await mortal(session, "Oren", world, town.id)
    assert await victim_in(ctx, town.id) is not None
    first = await soul(session, world, dead)
    assert await wandering_near(ctx, town.id) is first
    assert await EFFECTS[E.BIND](ctx, work(caster, E.BIND)) is not None
    assert first.binding is BindingKind.PLACE and first.alignment is SpiritAlignment.GUARDIAN
    other = await mortal(session, "Pell", world, town.id)
    second = await soul(session, world, other)
    assert await EFFECTS[E.RAISE_DEAD](ctx, work(caster, E.RAISE_DEAD)) is not None
    assert second.binding is BindingKind.PERSON and second.bound_entity_id == caster.id


async def test_a_summons_calls_a_servant_spirit(session: AsyncSession, world: CoreWorld) -> None:
    ctx, _, caster = await scene(session, world)
    text = await EFFECTS[E.SUMMON](ctx, work(caster, E.SUMMON))
    assert text is not None and "summoned" in text
    commanded = await session.scalar(select(BondRow).where(BondRow.source_node_id == caster.id, BondRow.kind == BondKind.COMMANDS))
    assert commanded is not None
    assert await EFFECTS[E.SUMMON](ctx, work(caster, E.SUMMON, form=SummonForm.UNDEAD)) is None


async def test_seals_hold_a_soul_and_exorcism_finds_the_possessed(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, caster = await scene(session, world)
    assert await EFFECTS[E.SEAL_SOUL](ctx, work(caster, E.SEAL_SOUL)) is None
    dead = await mortal(session, "Oren", world, town.id)
    profile = await soul(session, world, dead)
    assert await EFFECTS[E.SEAL_SOUL](ctx, work(caster, E.SEAL_SOUL, power=10)) is not None and profile.sealed
    assert await EFFECTS[E.UNSEAL_SOUL](ctx, work(caster, E.UNSEAL_SOUL, power=1)) == "the seal on the soul held"
    assert await EFFECTS[E.EXORCISE](ctx, work(caster, E.EXORCISE)) is None
    host = await mortal(session, "Pell", world, town.id)
    session.add(PossessionRow(host_entity_id=host.id, spirit_entity_id=profile.spirit_entity_id, since_epoch=1, locked=[]))
    await session.flush()
    assert await possessed_near(ctx, town.id) is host
    assert await EFFECTS[E.EXORCISE](ctx, work(caster, E.EXORCISE, power=100)) is not None


async def test_scrying_needs_a_target_and_a_harvest_blesses_the_fields(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, caster = await scene(session, world)
    assert await EFFECTS[E.SCRY](ctx, work(caster, E.SCRY)) is None
    assert await EFFECTS[E.SCRY](ctx, work(caster, E.SCRY, target=world.people)) is not None
    assert await EFFECTS[E.HARVEST_BLESSING](ctx, work(caster, E.HARVEST_BLESSING)) == f"blessed the fields of {town.name}"


async def test_a_rite_gone_wrong_leaves_an_undying_storm(session: AsyncSession, world: CoreWorld) -> None:
    ctx, _, _ = await scene(session, world)
    await phenomenon(ctx, world.regions[0])
    storm = await session.scalar(select(ForcedWeatherRow).where(ForcedWeatherRow.region_entity_id == world.regions[0].id))
    assert storm is not None and storm.kind is WeatherKind.MAGIC_STORM
