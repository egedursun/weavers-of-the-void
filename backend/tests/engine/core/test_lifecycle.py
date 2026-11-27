from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import ItemStats, RegionStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.gods.mortality import ProtectorKind, kill_chance
from aerona.engine.lifecycle.aging import effective_lifespan, is_notable, life_info
from aerona.engine.lifecycle.mortal_death import die, force_death
from aerona.engine.lifecycle.succession import designate_heir, dynasty_root
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits
from aerona.engine.phases.mortals import mortal_aging, mortal_wounds
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, add_flag, bond, entity, knowledge, mortal, natural_law, settlement, son_draft, tuned_rules


async def test_single_death_path_records_fate_killer_and_heir(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[1])
    king = await mortal(session, "Hadric", world, town.id, age=60)
    await bond(session, king.id, town.id, BondKind.RULES)
    await bond(session, king.id, world.language.id, BondKind.SPEAKS)
    await bond(session, king.id, world.son.id, BondKind.WORSHIPS)
    result = await die(ctx, king, cause="was slain by a rival", killer_id=world.species.id)
    assert result is not None and result.heir is not None
    assert king.status is EntityStatus.DEAD
    assert king.end_epoch == ctx.epoch
    assert "was slain by a rival" in (king.fate_note or "")
    assert stat(king, "death_year") is not None
    heir = result.heir
    assert heir.mortal_role is MortalRole.RULER
    bonds = BondRepository(session)
    assert await bonds.exists_between(heir.id, town.id, BondKind.RULES)
    assert await bonds.exists_between(king.id, heir.id, BondKind.PARENT_OF)
    assert await bonds.exists_between(heir.id, world.son.id, BondKind.WORSHIPS)
    killed = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.KILLED, BondRow.target_node_id == king.id))
    assert killed is not None and killed.source_node_id == world.species.id
    assert await die(ctx, king) is None


async def test_shared_throne_passes_without_an_heir(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[1])
    first = await mortal(session, "Ilsa", world, town.id)
    second = await mortal(session, "Oren", world, town.id)
    await bond(session, first.id, town.id, BondKind.RULES)
    session.add(BondRow(source_node_id=second.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1))
    await session.flush()
    result = await die(ctx, first, natural=True)
    assert result is not None and result.heir is None


async def test_designated_heir_takes_the_throne(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[1])
    queen = await mortal(session, "Maelis", world, town.id)
    chosen = await mortal(session, "Tobin", world, town.id)
    await bond(session, queen.id, town.id, BondKind.RULES)
    await designate_heir(ctx, queen.id, chosen.id)
    result = await die(ctx, queen, natural=True)
    assert result is not None and result.heir == chosen
    assert await BondRepository(session).exists_between(chosen.id, town.id, BondKind.RULES)


def test_dynasty_root_strips_regnal_numbers() -> None:
    assert dynasty_root("Hadric III") == "Hadric"
    assert dynasty_root("Hadric") == "Hadric"


async def test_after_death_soul_items_and_death_gods(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(world_engine={"famous_spirit_chance": 100, "mourning_tradition_chance": 100})
    ctx = await manual_context(session, "after_death", rules)
    underworld = await entity(session, "Deepdark", EntityType.REGION, RegionStats(), world_id=world.world.id)
    underworld.is_underworld = True
    reaper = await SonRepository(session).create(son_draft("Morrow", world.world.id, (Domain.DEATH, Domain.ASH)))
    town = await settlement(session, "Brookhold", world, world.regions[1])
    hero = await mortal(session, "Selda", world, town.id, charisma=90)
    child = await mortal(session, "Pell", world, town.id)
    await bond(session, hero.id, child.id, BondKind.PARENT_OF)
    cup = await entity(session, "Silver Cup", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    await bond(session, hero.id, cup.id, BondKind.OWNS)
    essence_before = reaper.essence
    await die(ctx, hero, natural=True)
    bonds = BondRepository(session)
    assert await bonds.exists_between(hero.id, underworld.id, BondKind.SOUL_DESCENDED_TO)
    assert await bonds.exists_between(child.id, cup.id, BondKind.OWNS)
    assert reaper.essence == essence_before + rules.world_effects.death_domain_essence
    spirits = [item for item in await session.scalars(select(BondRow).where(BondRow.target_node_id == hero.id, BondRow.kind == BondKind.DESCENDS_FROM))]
    assert len(spirits) >= 1
    texts = list(await session.scalars(select(ChronicleRow.template_key).where(ChronicleRow.epoch == ctx.epoch)))
    assert {"mortal.spirit", "mortal.spirit_restless"} & set(texts)
    assert "mortal.mourning" in texts


async def test_wounds_respect_immortality(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    sage = await mortal(session, "Ivo", world, world.regions[0].id, hp=10)
    assert (await apply_hits(ctx, sage, Harm(4, HarmCause.ACCIDENT, "was hurt"))).outcome is WoundOutcome.WOUNDED
    assert stat(sage, "hp") == 6
    await add_flag(session, sage.id, EntityFlag.IMMORTAL)
    assert (await apply_hits(ctx, sage, Harm(50, HarmCause.ACCIDENT, "was hurt"))).outcome is WoundOutcome.IMMORTAL
    mortal_one = await mortal(session, "Rhea", world, world.regions[0].id, hp=5)
    assert (await apply_hits(ctx, mortal_one, Harm(9, HarmCause.MONSTER, "bled out", killer_id=world.species.id))).outcome is WoundOutcome.DIED
    assert mortal_one.status is EntityStatus.DEAD
    assert (await apply_hits(ctx, world.species, Harm(5, HarmCause.ACCIDENT, "nothing"))).outcome is None


async def test_effective_lifespan_and_life_info(ctx: TickContext, world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    sage = await mortal(session, "Ivo", world, world.regions[0].id, charisma=90, lifespan=80)
    assert is_notable(rules, sage, set())
    healing = await knowledge(session, world, "Herb Lore", KnowledgeBranch.MEDICINE)
    await bond(session, world.people.id, healing.id, BondKind.KNOWS)
    span = await effective_lifespan(session, rules, sage)
    assert span.effective == 80 + rules.world_engine.medicine_lifespan_bonus + rules.world_engine.notable_lifespan_bonus
    info = await life_info(session, rules, sage)
    assert info.years_per_epoch == rules.time.years_per_epoch and not info.immortal


async def test_mortal_phase_kills_wounded_and_ages(world: CoreWorld, session: AsyncSession) -> None:
    world.cosmos.epoch = 3
    ctx = await manual_context(session, "aging")
    broken = await mortal(session, "Cass", world, world.regions[0].id, hp=0)
    old = await mortal(session, "Wren", world, world.regions[0].id, age=65, lifespan=70)
    young = await mortal(session, "Lio", world, world.regions[0].id, age=10, lifespan=300)
    await mortal_wounds(ctx)
    assert broken.status is EntityStatus.DEAD
    await mortal_aging(ctx)
    assert old.status is EntityStatus.DEAD
    start = world.cosmos.epoch_start_year
    assert stat(old, "age") == 65 + (stat(old, "death_year") or 0) - start
    assert stat(young, "age") == 10 + ctx.rules.time.years_per_epoch


async def test_laws_freeze_or_haunt_the_old(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(world_engine={"ghost_chance": 100})
    world.cosmos.epoch = 3
    ctx = await manual_context(session, "laws", rules)
    await natural_law(session, world, "The Returning", NaturalLaw.DEAD_RETURN)
    old = await mortal(session, "Wren", world, world.regions[0].id, age=65, lifespan=70)
    await mortal_aging(ctx)
    assert old.status is EntityStatus.CANON
    assert await has_flag(session, old.id, EntityFlag.GHOST)
    await natural_law(session, world, "Endless Days", NaturalLaw.IMMORTALITY)
    other = await mortal(session, "Ama", world, world.regions[0].id, age=65, lifespan=70)
    await mortal_aging(await manual_context(session, "laws", rules))
    assert stat(other, "age") == 65


async def test_newborn_too_old_is_rejuvenated(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "young")
    newborn = await mortal(session, "Faye", world, world.regions[0].id, age=69, lifespan=70)
    newborn.birth_epoch = ctx.epoch
    await mortal_aging(ctx)
    assert newborn.status is EntityStatus.CANON
    assert (stat(newborn, "age") or 0) < 69


async def test_death_options_and_forced_death(ctx: TickContext, world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    victim = await mortal(session, "Nell", world, world.regions[0].id)
    await bond(session, victim.id, world.son.id, BondKind.WORSHIPS)
    shield = await entity(session, "Tower Shield", EntityType.ITEM, ItemStats(protection=90), world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, victim.id, shield.id, BondKind.OWNS)
    chance = await kill_chance(session, rules, victim)
    assert {ProtectorKind.PATRON, ProtectorKind.ITEM} <= {protector.kind for protector in chance.protectors}
    assert rules.death.take_life_min_chance <= chance.percent <= rules.death.take_life_max_chance
    await add_flag(session, victim.id, EntityFlag.IMMORTAL)
    result = await force_death(ctx, victim.id, "was unmade by the Creator")
    assert result.entity.status is EntityStatus.DEAD


async def test_death_raises_a_lifespan_the_mortal_outlived(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    elder = await mortal(session, "Methuselah", world, world.regions[0].id, age=400)
    base = stat(elder, "lifespan") or ctx.rules.world_effects.default_lifespan
    assert base < 400
    await die(ctx, elder, cause="was struck down", forced=True)
    assert (stat(elder, "lifespan") or 0) >= 400 - ctx.rules.world_engine.notable_lifespan_bonus - ctx.rules.world_engine.medicine_lifespan_bonus
    assert ctx.environment.stats.counters[f"{ctx.phase}.lifespans_raised"] == 1


async def test_an_heir_raised_for_a_young_ruler_is_never_older_than_the_ruler_could_have_borne(
    ctx: TickContext, world: CoreWorld, session: AsyncSession
) -> None:
    town = await settlement(session, "Youngmoor", world, world.regions[1])
    king = await mortal(session, "Etsal", world, town.id, age=20)
    await bond(session, king.id, town.id, BondKind.RULES)
    result = await die(ctx, king, cause="was slain by a rival", killer_id=world.species.id)
    assert result is not None and result.heir is not None
    youngest_parent = (stat(king, "lifespan") or ctx.rules.world_effects.default_lifespan) * ctx.rules.fertility.window_start_pct // 100
    assert (stat(result.heir, "age") or 0) <= max(0, 20 - youngest_parent)
