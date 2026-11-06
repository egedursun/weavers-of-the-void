from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.reputation_line import reputation_line
from aerona.catalog import god_lines
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.tables.foreign_gods import ForeignGodPowerRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.son import ReputationLabel, SonStatus
from aerona.domain.models.stats import StatBlock
from aerona.engine.gods.acts import foreign_kill_cost, foreign_kill_cost_for
from aerona.engine.gods.signs import grace_sign, silence
from aerona.engine.gods.stats import Trait, trait_or
from aerona.prompts import SonToolId
from aerona.rules.registry import Rules
from aerona.tools.son.availability import SonWorldState, condition_holds
from tests.engine.gods.factories import GodsWorld, bond, chronicle_keys, make_context, make_entity, make_son


async def test_grace_sign_blesses_a_creator_worshipper_first(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    devout = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    other = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, devout.id, world.creator.id, BondKind.WORSHIPS)
    before = (trait_or(devout, Trait.PROSPERITY, 0), trait_or(other, Trait.PROSPERITY, 0))
    target = await grace_sign(make_context(session, rules, 3, "grace"), world.creator)
    assert target is not None and target.id == devout.id
    assert trait_or(devout, Trait.PROSPERITY, 0) > before[0]
    assert trait_or(other, Trait.PROSPERITY, 0) == before[1]
    assert any(key.startswith("creator.grace") or "grace" in key for key in await chronicle_keys(session))


async def test_grace_sign_falls_back_to_the_most_pious_community(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    assert await grace_sign(make_context(session, rules, 3, "grace"), world.creator) is not None


async def test_silence_costs_loyalty_and_feeds_ambition(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    active = await make_son(session, "Velkar", world.world.id)
    asleep = await make_son(session, "Iolen", world.world.id)
    asleep.status = SonStatus.ASLEEP
    loyalty, ambition = active.loyalty, active.ambition
    affected = await silence(make_context(session, rules, 3, "silence"), world.creator, announce=True)
    assert [son.id for son in affected] == [active.id]
    assert active.loyalty == loyalty - rules.creator.indifferent_loyalty_loss
    assert active.ambition == ambition + rules.creator.indifferent_ambition_gain
    assert any(key in {line.key for line in god_lines.SILENCE_SIGNS} for key in await chronicle_keys(session))
    quiet = await silence(make_context(session, rules, 4, "silence"), world.creator, announce=False)
    assert quiet


async def test_foreign_kill_cost_grows_with_power_and_deathless(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    god = await ForeignGodRepository(session).create(
        ForeignGodDraft(name="Ur", world_id=world.world.id, domain_primary=Domain.SEA, power=60, stats=StatBlock.uniform(50), created_epoch=1)
    )
    ctx = make_context(session, rules, 3)
    table = rules.god_power
    plain = round(table.kill_foreign_base_cost + 60 * table.kill_foreign_strength_pct / 100)
    assert await foreign_kill_cost(ctx, god) == plain == foreign_kill_cost_for(rules, 60, False)
    session.add(ForeignGodPowerRow(god_id=god.id, slot=0, name="Endless", description="never dies", effect=ForeignGodPowerEffect.DEATHLESS))
    await session.flush()
    assert await foreign_kill_cost(ctx, god) == round(plain * table.kill_immortal_foreign_mult)


async def test_reputation_line_renders_stance_numbers_and_passions(session: AsyncSession, world: GodsWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    assert reputation_line(son, []) == ""
    son.reputation_label = ReputationLabel.FEARED
    son.reputation_love, son.reputation_fear, son.reputation_forgotten, son.reputation_unanswered = 10, 70, 5, 2
    text = reputation_line(son, ["order", "war"])
    assert "HOW YOU SEE THE CREATOR: feared (love 10, fear 70, oblivion 5, you have 2 unanswered prayers)" in text
    assert "You fear the Creator." in text and "order, war" in text


def test_world_state_gates_son_tools(rules: Rules) -> None:
    empty = SonWorldState(1, False, False, False, False, False, False)
    full = SonWorldState(2, True, True, True, True, True, True)
    gated = {
        SonToolId.MOVE_TO_WORLD: "automatic_distribution",
        SonToolId.RESURRECT_SIBLING: "dead_sibling",
        SonToolId.SCATTER_BONES: "dead_sibling",
        SonToolId.REKINDLE_STAR: "dead_star",
        SonToolId.BIND_SPIRIT: "free_spirit",
        SonToolId.TALK_TO_FOREIGN_GOD: "contacted_foreign_god",
        SonToolId.WAR_ON_FOREIGN_GOD: "contacted_foreign_god",
        SonToolId.BARGAIN_WITH_OUTSIDER: "outer_being",
        SonToolId.MAKE_INTERWORLD_TREATY: "world_count",
        SonToolId.DECLARE_HOLY_WORLD: "world_count",
    }
    for tool in gated:
        assert not condition_holds(tool, rules, empty), tool
        assert condition_holds(tool, rules, full), tool
    only_distribution = replace(empty, world_count=2)
    assert not condition_holds(SonToolId.MOVE_TO_WORLD, rules, only_distribution)
    assert condition_holds(SonToolId.WRITE_PLAN, rules, empty)
