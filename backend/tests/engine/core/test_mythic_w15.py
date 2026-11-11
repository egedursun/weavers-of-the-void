import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mythic import SKILL_DOMAINS
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.arcana import RiteGrammarRow, VisStockRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import LegendProfileRow, RiteEffectRow
from aerona.db.tables.discovery import EpithetRow
from aerona.db.tables.divine import DivineStandingRow, GodGoalRow
from aerona.db.tables.dominion import DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, SpiritProfileRow
from aerona.db.tables.mythic import CosmicOfficeRow, GeasRow, HeroquestRow, MantlingRow, ServitorRow
from aerona.db.tables.renown import ReputationRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.arcana import SpellForm, SpellRange
from aerona.domain.enums.body import Consciousness
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import LegendArchetype, MagicSchool, RiteEffectKind
from aerona.domain.enums.divine import GodGoalKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import StratumKind
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.mythic import (
    CosmicOffice,
    GeasLayer,
    GeasMode,
    GeasState,
    HeroquestBoon,
    HeroquestState,
    MantlingState,
    MythicRealm,
    OfficeChoice,
    QuestTrial,
    ServitorRank,
    ServitorRole,
)
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.entity_stats import LegendStats, OuterBeingStats, SpiritStats
from aerona.engine.arcana.grammar import ensure_grammar, reaches
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.lore.rites import Working, beyond_reach, bind_by_geas, devise
from aerona.engine.mythic.control import set_party
from aerona.engine.mythic.geas_acts import geas_acted
from aerona.engine.mythic.geasa import GeasTally, birth_geas, lay_geas, tend_geasa
from aerona.engine.mythic.heroquests import QuestTally, advance, begin_quest, fellows, realm_of, trial_of
from aerona.engine.mythic.mantling import MantleTally, gather_cult, replace, replacement_for, weigh
from aerona.engine.mythic.offices import OfficeTally, appoint, conquer_offices, tend_offices, vacant_office
from aerona.engine.mythic.servitors import ServitorTally, fall, host_of, make_servitor, raise_saints, shake_host, turned_back, wear
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.integrity.mythic_links import mend_mythic_links
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def tuned(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "mythic", rules=tuned_rules(**namespaces))


async def myth(session: AsyncSession, world: CoreWorld, credence: int = 60) -> LegendProfileRow:
    legend = await entity(session, "The First Return", EntityType.LEGEND, LegendStats(), world_id=world.world.id)
    profile = LegendProfileRow(legend_entity_id=legend.id, archetype=LegendArchetype.CREATION, credence=credence, subject_node_id=world.son.id, locked=[])
    session.add(profile)
    await session.flush()
    return profile


async def quest(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, LegendProfileRow, QuestTally]:
    town = await settlement(session, "Hollin", world, world.regions[0])
    quester = await mortal(session, "Aster", world, town.id)
    legend = await myth(session, world)
    return quester, legend, QuestTally()


async def run(ctx: TickContext, quester: EntityRow, legend: LegendProfileRow, tally: QuestTally) -> HeroquestRow:
    row = await begin_quest(ctx, quester, legend, [])
    for _ in range(row.steps + 1):
        if row.state is not HeroquestState.QUESTING:
            break
        await advance(ctx, row, tally)
    return row


def test_every_domain_has_a_path_a_mortal_can_walk() -> None:
    reached = set().union(*SKILL_DOMAINS.values())
    assert reached == set(Domain)
    assert set(SKILL_DOMAINS) == set(SkillKind)


async def test_a_heroquest_that_passes_every_step_returns_with_a_boon_and_rewrites_its_myth(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, heroquests={"step_pass": 0})
    quester, legend, tally = await quest(ctx, session, world)
    row = await run(ctx, quester, legend, tally)
    assert row.state is HeroquestState.SUCCEEDED
    assert row.boon is HeroquestBoon.FAVOUR
    assert tally.succeeded == 1
    assert legend.updated_epoch == ctx.epoch


async def test_a_fallen_quester_is_trapped_until_another_quest_of_its_realm_frees_it(session: AsyncSession, world: CoreWorld) -> None:
    trap = await tuned(session, heroquests={"step_pass": 200, "deviation_pct": 0, "trap_pct": 100})
    quester, legend, tally = await quest(trap, session, world)
    lost = await run(trap, quester, legend, tally)
    assert lost.state is HeroquestState.TRAPPED
    assert await soul_trapped(session, quester.id)
    body = await refresh(session, trap.rules, quester, trap.epoch)
    assert body.consciousness is Consciousness.UNCONSCIOUS
    rescue = await tuned(session, heroquests={"step_pass": 0})
    hero = await mortal(session, "Brand", world, quester.location_id or world.regions[0].id)
    await run(rescue, hero, legend, QuestTally())
    assert {lost.state} == {HeroquestState.FAILED}
    assert not await soul_trapped(session, quester.id)


async def soul_trapped(session: AsyncSession, mortal_id: int) -> bool:
    found = await session.scalar(
        select(AfflictionRow.id).where(
            AfflictionRow.bearer_node_id == mortal_id, AfflictionRow.package == PackageKind.SOUL_TRAPPED, AfflictionRow.cured_epoch.is_(None)
        )
    )
    return found is not None


async def test_a_party_shares_the_fall_of_its_quest(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, heroquests={"step_pass": 200, "deviation_pct": 0, "trap_pct": 0, "break_pct": 0, "madness_pct": 100})
    quester, legend, tally = await quest(ctx, session, world)
    friend = await mortal(session, "Cade", world, quester.location_id or world.regions[0].id)
    row = await begin_quest(ctx, quester, legend, [friend.id])
    await advance(ctx, row, tally)
    assert row.state is HeroquestState.FAILED
    for hero in (quester, friend):
        mad = await session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == hero.id, AfflictionRow.package == PackageKind.TRAUMA))
        assert mad is not None


async def test_each_step_is_a_trial_the_legend_sets(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    quester, legend, _ = await quest(ctx, session, world)
    legend.archetype = LegendArchetype.BETRAYAL
    row = await begin_quest(ctx, quester, legend, [])
    trials = [await trial_of(ctx, row)]
    row.step = 1
    trials.append(await trial_of(ctx, row))
    assert trials == [QuestTrial.PASSION, QuestTrial.CONVICTION]
    legend.archetype = LegendArchetype.HAUNTED_PLACE
    assert realm_of(legend) is MythicRealm.DEAD


async def test_a_failed_heroquest_can_break_its_myth(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, heroquests={"step_pass": 200, "deviation_pct": 0, "trap_pct": 0, "break_pct": 100})
    quester, legend, tally = await quest(ctx, session, world)
    row = await run(ctx, quester, legend, tally)
    assert row.state is HeroquestState.BROKEN
    assert legend.credence == 60 - ctx.rules.heroquests.break_credence


async def candidate(session: AsyncSession, world: CoreWorld) -> EntityRow:
    towns = [await settlement(session, name, world, world.regions[0]) for name in ("Vell", "Oran")]
    hero = await mortal(session, "Ilse", world, towns[0].id)
    hero.power_level = 6
    session.add(
        ReputationRow(
            subject_node_id=hero.id, community_node_id=towns[0].id, axis=ReputationAxis.HEROISM, skill=SkillKind.FORAGING, value=100, heard_epoch=1, locked=[]
        )
    )
    for town in towns:
        await bond(session, town.id, hero.id, BondKind.WORSHIPS)
    await session.flush()
    return hero


async def test_a_mortal_whose_deeds_follow_a_harvest_god_walks_its_path_to_the_end(session: AsyncSession, world: CoreWorld, rules: Rules) -> None:
    hero = await candidate(session, world)
    ctx = await manual_context(session, "mantle", rules=rules)
    tally = MantleTally()
    await weigh(ctx, hero, tally)
    row = await session.get(MantlingRow, hero.id)
    assert row is not None
    assert row.god_node_id == world.son.id
    assert row.progress == 100
    assert tally.walking == 1


async def test_fate_lets_a_mortal_at_the_end_of_the_path_ascend(session: AsyncSession, world: CoreWorld) -> None:
    hero = await candidate(session, world)
    ctx = await tuned(session, mantling={"fate_pct": 100})
    tally = MantleTally()
    await weigh(ctx, hero, tally)
    row = await session.get(MantlingRow, hero.id)
    assert row is not None
    assert row.state is MantlingState.ASCENDED
    assert row.notified
    assert tally.ascended == 1


async def test_a_god_set_against_a_mantling_blocks_it(session: AsyncSession, world: CoreWorld) -> None:
    hero = await candidate(session, world)
    session.add(GodGoalRow(god_node_id=world.son.id, kind=GodGoalKind.PREVENT_MANTLING, target_node_id=hero.id, world_id=world.world.id, locked=[]))
    await session.flush()
    ctx = await tuned(session, mantling={"oppose_pct": 100})
    tally = MantleTally()
    await weigh(ctx, hero, tally)
    row = await session.get(MantlingRow, hero.id)
    assert row is not None
    assert row.state is MantlingState.BLOCKED
    assert tally.blocked == 1


async def test_a_mortal_who_slays_a_weak_god_takes_its_place_and_its_offices(session: AsyncSession, world: CoreWorld) -> None:
    hero = await candidate(session, world)
    ctx = await tuned(session, mantling={"fate_pct": 100})
    son = world.son
    son.existence, son.strength, son.will, son.level = 10, 1, 1, 1
    await session.execute(update(BondRow).where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS).values(state=BondState.PAST))
    await session.execute(update(DivineStandingRow).where(DivineStandingRow.god_node_id == son.id).values(awe=0))
    session.add(DominionRow(god_node_id=son.id, region_entity_id=world.regions[0].id, strength=40, epoch=1, locked=[]))
    await appoint(ctx, CosmicOffice.HUNT, son.id, OfficeChoice.CREATOR)
    session.add(MantlingRow(mortal_entity_id=hero.id, god_node_id=son.id, deeds=10, worship=2, progress=100, locked=[]))
    await session.flush()
    plan = await replacement_for(ctx, hero, son)
    assert plan is not None
    heir = await replace(ctx, hero, plan)
    assert heir is not None
    assert (heir.domain_primary, heir.domain_secondary) == (son.domain_primary, son.domain_secondary)
    office = await session.get(CosmicOfficeRow, CosmicOffice.HUNT)
    assert office is not None
    assert office.holder_node_id == heir.id
    assert office.chosen_by is OfficeChoice.MANTLING
    claim = await session.get(DominionRow, (heir.id, world.regions[0].id))
    assert claim is not None


async def test_a_strong_god_cannot_be_replaced(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    hero = await candidate(session, world)
    session.add(MantlingRow(mortal_entity_id=hero.id, god_node_id=world.son.id, deeds=10, worship=2, progress=100, locked=[]))
    await session.flush()
    assert await replacement_for(ctx, hero, world.son) is None


async def test_a_guarding_servitor_turns_back_a_desecrator_and_a_host_adds_to_its_god(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, servitors={"guard_pct": 100})
    shrine = await settlement(session, "Calder", world, world.regions[0])
    await make_servitor(ctx, world.son.id, name="Warden", rank=ServitorRank.ANGEL, role=ServitorRole.GUARD, post_id=shrine.id, world_id=world.world.id)
    await make_servitor(ctx, world.son.id, name="Spear", rank=ServitorRank.ANGEL, role=ServitorRole.HOST, post_id=None, world_id=world.world.id)
    assert await turned_back(ctx, [shrine.id], "test.guard")
    assert not await turned_back(ctx, [world.regions[1].id], "test.guard")
    assert await host_of(session, ctx.rules, world.son.id) == ctx.rules.servitors.host_strength


async def test_a_disloyal_servitor_falls_to_another_master(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, servitors={"fall_pct": 100})
    outer = await entity(session, "The Outside", EntityType.OUTER_BEING, OuterBeingStats(), world_id=world.world.id)
    row = await make_servitor(ctx, world.son.id, name="Herald", rank=ServitorRank.HERALD, role=ServitorRole.MESSENGER, post_id=None, world_id=world.world.id)
    row.loyalty = 0
    tally = ServitorTally()
    await fall(ctx, row, tally)
    assert row.god_node_id == outer.id
    assert row.fallen_to_node_id == outer.id
    assert tally.fallen == 1


async def test_a_broken_taboo_dooms_its_bearer(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Ferd", world, world.regions[0].id)
    row = await lay_geas(ctx, bearer, layer_node_id=world.son.id, layer=GeasLayer.GOD, mode=GeasMode.TABOO, act=ActKind.THEFT)
    assert await geas_acted(ctx, bearer.id, ActKind.THEFT) == 1
    assert row.state is GeasState.BROKEN
    tally = GeasTally()
    await tend_geasa(ctx, tally)
    doom = await session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == bearer.id, AfflictionRow.package == PackageKind.GEAS_DOOM))
    assert doom is not None
    assert tally.broken == 1


async def test_a_duty_left_undone_breaks_and_a_kept_geas_wins_favour(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 20
    await session.flush()
    ctx = await manual_context(session, "geas")
    idle = await mortal(session, "Gwen", world, world.regions[0].id)
    faithful = await mortal(session, "Hob", world, world.regions[0].id)
    duty = await lay_geas(ctx, idle, layer_node_id=world.son.id, layer=GeasLayer.GOD, mode=GeasMode.DUTY, act=ActKind.HOSPITALITY)
    kept = await lay_geas(ctx, faithful, layer_node_id=world.son.id, layer=GeasLayer.GOD, mode=GeasMode.TABOO, act=ActKind.THEFT)
    duty.last_kept_epoch = ctx.epoch - ctx.rules.geasa.duty_epochs - 1
    await tend_geasa(ctx, GeasTally())
    assert duty.state is GeasState.BROKEN
    assert kept.state is GeasState.KEPT
    assert kept.favour == ctx.rules.geasa.favour


async def test_a_child_of_a_faithful_people_may_be_born_under_a_geas(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, geasa={"birth_pct": 100})
    child = await mortal(session, "Ina", world, world.regions[0].id)
    row = await birth_geas(ctx, child, world.son.id)
    assert row is not None
    assert row.layer_node_id == world.son.id
    assert await birth_geas(ctx, child, None) is None


async def test_a_held_office_fulfils_its_duty_and_an_empty_one_falls_into_neglect(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await appoint(ctx, CosmicOffice.DEAD, world.son.id, OfficeChoice.CREATOR)
    tally = OfficeTally()
    await tend_offices(ctx, tally)
    dead = await session.get(CosmicOfficeRow, CosmicOffice.DEAD)
    gates = await session.get(CosmicOfficeRow, CosmicOffice.GATES)
    assert dead is not None
    assert gates is not None
    assert dead.duty == ctx.rules.cosmic_offices.duty_gain
    assert gates.neglect == ctx.rules.cosmic_offices.neglect_gain
    assert tally.active == 1
    assert tally.neglected == len(CosmicOffice) - 1
    assert await vacant_office(ctx) not in {None, CosmicOffice.DEAD}


async def test_a_god_who_wins_a_divine_battle_may_take_an_office(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, cosmic_offices={"conquest_pct": 100})
    await appoint(ctx, CosmicOffice.STARS, world.son.id, OfficeChoice.CREATOR)
    assert await conquer_offices(ctx, world.creator.id, world.son.id, "test.battle") is CosmicOffice.STARS
    row = await session.get(CosmicOfficeRow, CosmicOffice.STARS)
    assert row is not None
    assert row.holder_node_id == world.creator.id
    assert row.chosen_by is OfficeChoice.CONQUEST


async def test_a_rite_reaches_only_as_far_as_its_range(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    caster = await mortal(session, "Ysel", world, world.regions[0].id)
    near = await mortal(session, "Pell", world, world.regions[0].id)
    far = await mortal(session, "Quin", world, world.regions[1].id)
    _, profile = await devise(ctx, MagicSchool.ELEMENTAL_FIRE, caster)
    await session.flush()
    grammar: RiteGrammarRow = await ensure_grammar(session, ctx.rules, profile)
    atlas = await RegionAtlas.load(session)
    grammar.range = SpellRange.TOUCH
    assert reaches(atlas, grammar, caster, near)
    assert not reaches(atlas, grammar, caster, far)
    beyond = await mortal(session, "Rho", world, world.regions[2].id)
    grammar.range = SpellRange.SIGHT
    assert not reaches(atlas, grammar, caster, far)
    grammar.range = SpellRange.REGION
    assert reaches(atlas, grammar, caster, far)
    assert not reaches(atlas, grammar, caster, beyond)
    assert await beyond_reach(ctx, caster, profile, beyond) is not None
    grammar.range = SpellRange.WORLD
    assert reaches(atlas, grammar, caster, far)
    assert await beyond_reach(ctx, caster, profile, beyond) is None


async def test_a_title_won_on_a_heroquest_becomes_the_questers_epithet(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, heroquests={"step_pass": 0})
    quester, legend, tally = await quest(ctx, session, world)
    row = await begin_quest(ctx, quester, legend, [])
    row.boon = HeroquestBoon.TITLE
    for _ in range(row.steps):
        await advance(ctx, row, tally)
    assert row.state is HeroquestState.SUCCEEDED
    epithet = await session.get(EpithetRow, quester.id)
    assert epithet is not None
    assert epithet.deed == "creation"


async def test_a_fall_on_a_heroquest_can_kill(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, heroquests={"step_pass": 200, "deviation_pct": 0, "trap_pct": 0, "break_pct": 0, "madness_pct": 0, "death_pct": 100})
    quester, legend, tally = await quest(ctx, session, world)
    await run(ctx, quester, legend, tally)
    assert quester.status is not EntityStatus.CANON


async def test_a_mortal_on_a_gods_path_gains_cults_that_follow_it_into_godhood(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, mantling={"cult_pct": 100, "fate_pct": 100})
    towns = [await settlement(session, name, world, world.regions[0]) for name in ("Asha", "Bel")]
    hero = await mortal(session, "Dov", world, towns[0].id)
    hero.power_level = 6
    for town in towns:
        await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
        session.add(
            ReputationRow(
                subject_node_id=hero.id, community_node_id=town.id, axis=ReputationAxis.HEROISM, skill=SkillKind.FORAGING, value=100, heard_epoch=1, locked=[]
            )
        )
    await session.flush()
    assert await gather_cult(ctx, hero) is not None
    assert await gather_cult(ctx, hero) is not None
    assert await gather_cult(ctx, hero) is None
    await weigh(ctx, hero, MantleTally())
    row = await session.get(MantlingRow, hero.id)
    assert row is not None
    assert row.state is MantlingState.ASCENDED
    left = await session.scalars(select(BondRow).where(BondRow.target_node_id == hero.id, BondRow.kind == BondKind.WORSHIPS))
    assert {bond_row.state for bond_row in left} == {BondState.PAST}


async def test_a_binding_rite_cast_on_a_mortal_lays_a_geas_witnessed_by_the_casters_god(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, geasa={"bind_pct": 100})
    town = await settlement(session, "Fen", world, world.regions[0])
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    caster = await mortal(session, "Ura", world, town.id)
    target = await mortal(session, "Vex", world, town.id)
    rite, profile = await devise(ctx, MagicSchool.ELEMENTAL_FIRE, caster)
    await session.flush()
    text = await bind_by_geas(ctx, Working(caster, target, RiteEffectRow(rite_entity_id=rite.id, effect=RiteEffectKind.BIND), 10, profile))
    assert text is not None
    geas = await session.scalar(select(GeasRow).where(GeasRow.bearer_entity_id == target.id))
    assert geas is not None
    assert geas.layer is GeasLayer.RITE
    assert geas.layer_node_id == world.son.id


async def test_a_servitors_loyalty_follows_how_its_god_treats_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, servitors={})
    row = await make_servitor(ctx, world.son.id, name="Spear", rank=ServitorRank.ANGEL, role=ServitorRole.HOST, post_id=None, world_id=world.world.id)
    start = row.loyalty
    assert await shake_host(ctx, world.son.id) == 1
    assert row.loyalty == start - ctx.rules.servitors.defeat_loyalty
    wear(ctx.rules, row)
    assert row.loyalty == start - ctx.rules.servitors.defeat_loyalty - ctx.rules.servitors.command_loyalty


async def test_only_a_saint_in_a_rewarding_stratum_rises_to_serve_the_stratums_god(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, servitors={"raise_pct": 100})
    saint = await mortal(session, "Wil", world, world.regions[0].id)
    saint.mortal_role = MortalRole.SAINT
    shade = await entity(session, "Wil's shade", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id)
    stratum = AfterlifeStratumRow(realm_entity_id=world.regions[0].id, kind=StratumKind.TORMENT, name="Below", son_id=world.son.id)
    session.add(stratum)
    await session.flush()
    session.add(SpiritProfileRow(spirit_entity_id=shade.id, origin_mortal_id=saint.id, stratum_id=stratum.id, locked=[]))
    await session.flush()
    await raise_saints(ctx, ServitorTally())
    assert await session.get(ServitorRow, shade.id) is None
    stratum.kind = StratumKind.PARADISE
    await raise_saints(ctx, ServitorTally())
    risen = await session.get(ServitorRow, shade.id)
    assert risen is not None
    assert risen.god_node_id == world.son.id


async def test_the_god_chooses_a_quests_party_and_a_companion_sent_home_from_a_trapped_quest_wakes(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, heroquests={"step_pass": 200, "deviation_pct": 0, "trap_pct": 100})
    quester, legend, tally = await quest(ctx, session, world)
    friend = await mortal(session, "Cade", world, quester.location_id or world.regions[0].id)
    row = await begin_quest(ctx, quester, legend, [])
    await set_party(ctx, row.id, [friend.id])
    await advance(ctx, row, tally)
    assert row.state is HeroquestState.TRAPPED
    assert await soul_trapped(session, friend.id)
    await set_party(ctx, row.id, [])
    assert not await soul_trapped(session, friend.id)
    assert await soul_trapped(session, quester.id)
    with pytest.raises(ValidationFailedError):
        await set_party(ctx, row.id, [world.regions[0].id])


async def test_mythic_links_to_fallen_gods_and_vanished_mortals_are_mended(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    servitor = await make_servitor(ctx, world.son.id, name="Warden", rank=ServitorRank.ANGEL, role=ServitorRole.GUARD, post_id=None, world_id=world.world.id)
    await appoint(ctx, CosmicOffice.DEAD, world.son.id, OfficeChoice.CREATOR)
    quester, legend, _ = await quest(ctx, session, world)
    row = await begin_quest(ctx, quester, legend, [])
    elder = await mortal(session, "Orla", world, world.regions[0].id)
    session.add(VisStockRow(holder_node_id=elder.id, form=SpellForm.BODY, amount=3, locked=[]))
    world.son.status, world.son.death_epoch = SonStatus.DEAD, ctx.epoch
    for gone in (quester, elder):
        gone.status, gone.end_epoch = EntityStatus.DEAD, ctx.epoch
    await session.flush()
    assert await mend_mythic_links(session) >= 4
    assert await session.get(ServitorRow, servitor.spirit_entity_id) is None
    office = await session.get(CosmicOfficeRow, CosmicOffice.DEAD)
    assert office is not None
    assert office.holder_node_id is None
    assert row.state is HeroquestState.FAILED
    assert await session.get(VisStockRow, (elder.id, SpellForm.BODY)) is None


async def test_only_mortals_standing_with_the_quester_may_walk_beside_it(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    quester, _, _ = await quest(ctx, session, world)
    near = await mortal(session, "Cade", world, quester.location_id or world.regions[0].id)
    far = await mortal(session, "Dov", world, world.regions[2].id)
    assert await fellows(ctx, quester, [near.id, near.id]) == [near.id]
    assert isinstance(await fellows(ctx, quester, [far.id]), str)
    assert isinstance(await fellows(ctx, quester, [quester.id]), str)
