from sqlalchemy import select

from aerona.db.tables.ecology import HerdRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import AnimalRole, Diet, DomesticationStage, SizeClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.domestication import advance, draught, ensure_herds, keeper_of, promote
from aerona.engine.ecology.profiles import SpeciesSpec
from aerona.engine.mind.skills import set_skill
from aerona.engine.primitives.queries import connect, living_entity
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, tick, tuned
from tests.engine.cosmos.test_husbandry_rp2 import herd, kind, town

S = DomesticationStage


async def test_a_tamed_kind_opens_a_herd_in_its_tamers_town(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Pasture Downs", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    grazer = await kind(ctx, cosmos, region.id, "Grazer", SpeciesSpec(size_class=SizeClass.LARGE, diet=Diet.HERBIVORE))
    tamer = await make_entity(ctx.session, "Ilsa", EntityType.MORTAL, MortalStats(hp=30, age=30), world_id=cosmos.home.id, location_id=hold)
    town_row = await living_entity(ctx.session, hold)
    assert town_row is not None and await keeper_of(ctx, town_row) is town_row and await keeper_of(ctx, tamer) is town_row
    await connect(ctx.session, tamer.id, grazer, BondKind.TAMED, ctx.epoch)
    assert await ensure_herds(ctx) == 1
    row = await ctx.session.scalar(select(HerdRow).where(HerdRow.community_entity_id == hold))
    assert row is not None and row.species_entity_id == grazer


async def test_a_kept_herd_is_herded_then_domesticated_then_bred(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Pasture Downs", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    grazer = await kind(ctx, cosmos, region.id, "Grazer", SpeciesSpec(size_class=SizeClass.LARGE, diet=Diet.HERBIVORE))
    tamed = herd(hold, grazer, stage=S.TAMED, fed_epochs=rules.domestication.herd_epochs)
    ctx.session.add(tamed)
    await ctx.session.flush()
    assert "keeps herds" in (await advance(ctx, tamed, 0) or "")
    assert tamed.stage is S.HERDED
    tamed.since_epoch = ctx.epoch - rules.domestication.domesticate_epochs
    keeper = await living_entity(ctx.session, hold)
    species = await living_entity(ctx.session, grazer)
    assert keeper is not None and species is not None
    told = await promote(ctx, tamed, species, keeper, tamed=True, bred=False)
    assert told is not None and "tamed" in told
    kept = await ctx.session.scalar(select(HerdRow).where(HerdRow.community_entity_id == hold))
    assert kept is not None and kept.stage is S.DOMESTICATED and kept.species_entity_id != grazer
    assert await promote(ctx, kept, species, keeper, tamed=False, bred=True) is None
    herder = await make_entity(ctx.session, "Bram", EntityType.MORTAL, MortalStats(hp=30, age=30), world_id=cosmos.home.id, location_id=hold)
    await set_skill(ctx.session, herder.id, SkillKind.BEAST_HANDLING, 100, epoch=ctx.epoch, source=SkillSource.PRACTICE)
    told = await promote(ctx, kept, species, keeper, tamed=False, bred=True)
    assert told is not None and "breed" in told
    bred = await ctx.session.scalar(select(HerdRow).where(HerdRow.community_entity_id == hold))
    assert bred is not None and bred.stage is S.BREED


async def test_a_capped_epoch_advances_no_herd_and_draught_beasts_lift_the_fields(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Pasture Downs", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    ox = await kind(ctx, cosmos, region.id, "Ox", SpeciesSpec(size_class=SizeClass.LARGE, diet=Diet.HERBIVORE), AnimalRole.DRAFT)
    row = herd(hold, ox, head=rules.domestication.labour_head, stage=S.DOMESTICATED)
    ctx.session.add(row)
    await ctx.session.flush()
    assert await advance(tick(ctx.session, tuned(rules, "domestication", cap=0)), row, 0) is None
    assert await draught(ctx, hold) == 1 + rules.domestication.labour_pct / 100
    row.locked = ["stage"]
    assert await advance(ctx, row, 0) is None
