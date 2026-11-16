from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.concealment import BreachRow, HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow
from aerona.db.tables.environment import LeyLineRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.powers import MagicSystemRow, PowerRegistryRow, PowerRow, PowerSourceRow, SourceDensityRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperRole
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import PowerCost, PowerOrigin, PowerState, PowerVisibility, SourceAccess, SourceLocus, SourceRenewal
from aerona.domain.models.entity_stats import ArmyStats, PolityStats
from aerona.engine.concealment.truths import breach, reveal_or_fade
from aerona.engine.polity.laws import enact
from aerona.engine.powers import control
from aerona.engine.powers.backfill import built_in_source, legacy_backfill
from aerona.engine.powers.phase import keep_powers
from aerona.engine.powers.society import keep_registries
from aerona.engine.powers.sources import density_row, keep_density
from aerona.engine.powers.use import use
from aerona.engine.powers.war import power_edge
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at


def power_for(holder_id: int, technique: SpellTechnique = SpellTechnique.DESTROY, form: SpellForm = SpellForm.FORCE, **values: object) -> PowerRow:
    return PowerRow(
        holder_node_id=holder_id,
        technique=technique,
        form=form,
        strength=values.get("strength", 5),
        control=values.get("control", 80),
        origin=PowerOrigin.BORN,
        state=values.get("state", PowerState.ACTIVE),
        visibility=values.get("visibility", PowerVisibility.SUBTLE),
        strain=0,
        strain_cap=values.get("strain_cap", 30),
        uses=0,
        gained_epoch=1,
        source_id=values.get("source_id"),
        locked=[],
    )


async def test_a_source_drawn_past_its_floor_runs_thin_and_withers_its_towns(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashwell", world, world.regions[0], prosperity=60)
    ctx = await at(session, 2)
    draft = control.SourceDraft("The Ember Seam", world.regions[0].id, SourceLocus.PLACE, SourceRenewal.NONE, SourceAccess.ANYONE, PowerVisibility.SUBTLE, 50)
    source = await control.create_source(ctx, draft)
    await control.add_part(ctx, control.SOURCE_PARTS, "cost", source.id, {"cost": PowerCost.SURROUNDINGS, "weight": 50})
    density = await density_row(ctx, source, world.regions[0].id)
    density.density = 5
    await session.flush()
    await keep_density(await at(session, 3))
    assert density.depleted
    assert stat_or(town, "prosperity", 0) < 60


async def test_a_power_pushed_past_its_strain_scars_its_user_and_gives_out(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stormhold", world, world.regions[0])
    user = await mortal(session, "Caer", world, town.id)
    foe = await mortal(session, "Mott", world, town.id)
    ctx = await at(session, 2, powers={"strain_per_use": 50, "burnout_at_pct": 150})
    power = power_for(user.id, strain_cap=10)
    session.add(power)
    await session.flush()
    outcome = await use(ctx, power, user, foe)
    assert outcome.done is not None and outcome.strained
    assert power.state is PowerState.BURNED_OUT


async def test_a_latent_power_wakes_under_stress(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Quietford", world, world.regions[0])
    child = await mortal(session, "Ila", world, town.id)
    session.add(MortalProfileRow(entity_id=child.id, stress=80, locked=[]))
    power = power_for(child.id, SpellTechnique.PERCEIVE, SpellForm.MIND, state=PowerState.LATENT)
    session.add(power)
    await session.flush()
    await keep_powers(await at(session, 2, powers={"emerge_chance": 100, "use_chance": 0}))
    assert power.state in {PowerState.EMERGING, PowerState.ACTIVE}


async def test_a_registering_realm_lists_its_gifted_and_a_hunting_realm_brings_them_to_court(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lawmarch", world, world.regions[0])
    realm = await entity(session, "The Ward Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    gifted = await mortal(session, "Sef", world, town.id)
    session.add(power_for(gifted.id))
    await session.flush()
    ctx = await at(session, 2)
    await enact(ctx, realm, LawKind.POWER_LAW, {"level": "registered", "mind_powers": "licensed"})
    await keep_registries(ctx)
    assert await session.scalar(select(PowerRegistryRow).where(PowerRegistryRow.holder_node_id == gifted.id)) is not None
    await enact(ctx, realm, LawKind.POWER_LAW, {"level": "hunted", "mind_powers": "banned"})
    await keep_registries(await at(session, 3))
    case = await session.scalar(select(CrimeCaseRow).where(CrimeCaseRow.culprit_entity_id == gifted.id, CrimeCaseRow.crime == CrimeKind.WITCHCRAFT))
    assert case is not None


async def test_a_breach_spreads_belief_by_trust_reveals_at_the_bar_and_fades_unspoken(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Whisperdale", world, world.regions[0])
    hidden = await mortal(session, "Nyx", world, town.id)
    ctx = await at(session, 2, concealment={"spread_pct": 100, "belief_pct": 100})
    truth = HiddenTruthRow(
        title="one who walks unseen", subject_node_id=hidden.id, kind=HiddenTruthKind.PRESENCE, hidden_from=ConcealScope.EVERYONE, strength=0, locked=[]
    )
    session.add(truth)
    await session.flush()
    row = await breach(ctx, truth, BreachCause.WITNESS, place_id=town.id)
    assert row is not None
    known = await session.scalar(select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id == truth.id))
    assert known is not None and known.know_pct > 0 and known.believe_pct > 0
    known.know_pct, known.believe_pct = 90, 90
    await reveal_or_fade(ctx, truth, known)
    assert known.revealed_epoch == 2
    other = await mortal(session, "Lorn", world, town.id)
    quiet = HiddenTruthRow(title="an old grief", subject_node_id=other.id, kind=HiddenTruthKind.EVENT, strength=50, locked=[])
    session.add(quiet)
    await session.flush()
    fading = PublicKnowledgeRow(truth_id=quiet.id, population_node_id=town.id, know_pct=20, believe_pct=10, locked=[])
    session.add(fading)
    await session.flush()
    await reveal_or_fade(await at(session, 40), quiet, fading)
    assert fading.know_pct < 20


async def test_a_mind_bent_by_a_power_remembers_and_the_law_hears_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Bendmere", world, world.regions[0])
    user = await mortal(session, "Vey", world, town.id)
    target = await mortal(session, "Orr", world, town.id)
    power = power_for(user.id, SpellTechnique.CONTROL, SpellForm.EMOTION, strength=9, control=100)
    session.add(power)
    await session.flush()
    await use(await at(session, 2), power, user, target)
    memory = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == target.id, MemoryRow.kind == MemoryKind.COMPELLED_ME))
    assert memory is not None


async def test_units_of_the_gifted_lift_an_army_and_dampeners_take_it_away(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fieldgate", world, world.regions[0])
    realm = await entity(session, "The First Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    host = await entity(session, "The Bright Host", EntityType.ARMY, ArmyStats(), world_id=world.world.id, location_id=town.id)
    foe = await entity(session, "The Dull Host", EntityType.ARMY, ArmyStats(), world_id=world.world.id, location_id=town.id)
    session.add(ArmyRow(entity_id=host.id, owner_entity_id=realm.id, raised_epoch=1))
    session.add(ArmyUnitRow(army_entity_id=host.id, kind=UnitKind.GIFTED, count=50))
    session.add(ArmyUnitRow(army_entity_id=host.id, kind=UnitKind.LEVY, count=50))
    await session.flush()
    ctx = await at(session, 2)
    lifted = await power_edge(session, ctx.rules, realm.id, [host.id], [])
    session.add(ArmyUnitRow(army_entity_id=foe.id, kind=UnitKind.DAMPENERS, count=100))
    await session.flush()
    damped = await power_edge(session, ctx.rules, realm.id, [host.id], [foe.id])
    assert lifted > damped > 1


async def test_the_legacy_backfill_makes_the_old_sources_ley_density_systems_and_keeps_buried_histories(session: AsyncSession, world: CoreWorld) -> None:
    session.add(LeyLineRow(world_id=world.world.id, region_a_id=world.regions[0].id, region_b_id=world.regions[1].id, strength=50, formed_epoch=1))
    await session.flush()
    ctx = await at(session, 2)
    assert await legacy_backfill(ctx) > 0
    ley = await built_in_source(session, MagicSource.LEY)
    assert await session.scalar(select(SourceDensityRow).where(SourceDensityRow.source_id == ley.id)) is not None
    assert await session.scalar(select(MagicSystemRow).where(MagicSystemRow.scope_node_id == world.world.id)) is not None
    assert len(list(await session.scalars(select(PowerSourceRow).where(PowerSourceRow.built_in.is_not(None))))) == len(MagicSource)
    assert await legacy_backfill(await at(session, 3)) == 0


async def test_a_breach_answered_by_a_keeper_takes_back_belief(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Coverley", world, world.regions[0])
    keeper = await mortal(session, "Hask", world, town.id)
    hidden = await mortal(session, "Shade", world, town.id)
    ctx = await at(session, 2, concealment={"spread_pct": 100, "belief_pct": 100, "cover_cut_pct": 100, "keeper_cost": 0})
    truth = HiddenTruthRow(title="the shade among us", subject_node_id=hidden.id, kind=HiddenTruthKind.PRESENCE, strength=0, by_cover_story=True, locked=[])
    session.add(truth)
    await session.flush()
    session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=keeper.id, role=KeeperRole.ENFORCER, locked=[]))
    await session.flush()
    row = await breach(ctx, truth, BreachCause.WITNESS, place_id=town.id)
    assert row is not None and row.response.value == "cover_story"
    stored = await session.scalar(select(BreachRow).where(BreachRow.truth_id == truth.id))
    assert stored is not None
