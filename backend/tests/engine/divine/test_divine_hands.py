from sqlalchemy import select

from aerona.agents.context.divine_lines import goal_lines
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.mortal import candidates
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.divine import DivineWoundKind, GodGoalKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import ArmourType, ShieldType, Stance, UnitKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.son import ExistenceMode
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.entity_stats import SpiritStats
from aerona.domain.models.profiles import ExistenceProfile
from aerona.engine.divine import control
from aerona.engine.divine.battles import intervene
from aerona.engine.divine.wounds import heal_wounds, inflict
from aerona.engine.military.battle import Side, divine_hand, make_stacks
from aerona.rules.registry import Rules
from aerona.tools.mortal.registry import SPIRIT_TOOLS
from tests.engine.divine.pantheon import foreign, god, worship
from tests.engine.society.factories import Realm, context, make, natural_law, settlement, tuned


async def scoped(realm: Realm) -> Scope:
    repository = CosmosRepository(realm.session)
    if await repository.get() is None:
        await repository.create(CosmosDraft(name="Aerona", rng_seed=7, lore_language=LoreLanguage.ENGLISH, seed_idea="", cosmology="", tone="", rules=Rules()))
        await repository.create_creator(CreatorDraft(name="Aeron", essence=500, mood_contentment=50, mood_anger=20, mood_interest=60, mood_loneliness=30))
    return await load_scope(realm.session, Rules())


CERTAIN = {"battle_intervene_chance": 100, "battle_contest_spread_pct": 0}


def soldiers(army: int, count: int) -> ArmyUnitRow:
    return ArmyUnitRow(
        id=army,
        army_entity_id=army,
        kind=UnitKind.LEVY,
        count=count,
        quality=50,
        armour=ArmourType.NONE,
        shield=ShieldType.NONE,
        helmet=False,
        weapons=[],
        experience=10,
        morale=60,
        fatigue=0,
        wounded=0,
        condition=100,
        locked=[],
    )


def side_for(entity: EntityRow, count: int = 400) -> Side:
    profile = ArmyProfileRow(army_entity_id=entity.id, stance=Stance.MARCH, doctrine=MartialStyle.SHIELDWALL, entrenchment=0, baggage=100, loot=50, locked=[])
    return Side(entity=entity, army=entity, profile=profile, stacks=make_stacks([soldiers(entity.id, count)]), edge=1.0, defending=False, skill=0, traits=set())


async def test_a_patron_god_strikes_for_its_faithful_and_pays_essence(realm: Realm) -> None:
    war = await god(realm, "Kerr", Domain.WAR, Domain.BLOOD)
    war.essence, war.wrath, war.mercy = 50, 80, 10
    town = await settlement(realm, "Embercourt")
    foe = await settlement(realm, "Timberfold")
    await worship(realm, town, war.id)
    ctx = context(realm.session, tuned(domains=CERTAIN))
    first, second = side_for(town), side_for(foe)
    assert await intervene(ctx, 1, 1, first, second) == 1
    assert first.divine_strike_pct == ctx.rules.domains.battle_strike_pct and war.essence == 50 - ctx.rules.domains.battle_essence
    standing = await realm.session.get(DivineStandingRow, (town.id, war.id))
    assert standing is not None and standing.awe > 0
    before = second.standing
    assert divine_hand(ctx.rules, first, second) > 0 and second.standing < before


async def test_a_merciful_god_steadies_its_faithful_instead(realm: Realm) -> None:
    kind = await god(realm, "Pell", Domain.LIFE, Domain.LOVE)
    kind.essence, kind.wrath, kind.mercy = 50, 10, 90
    town = await settlement(realm, "Saltmouth")
    await worship(realm, town, kind.id)
    ctx = context(realm.session, tuned(domains=CERTAIN))
    first, second = side_for(town), side_for(await settlement(realm, "Dryhollow"))
    await intervene(ctx, 1, 2, first, second)
    assert first.divine_strike_pct == 0 and first.divine_shield == ctx.rules.domains.battle_shield_morale
    assert first.morale_parts["god_shield"] == ctx.rules.domains.battle_shield_morale


async def test_rival_patrons_contest_the_battle_and_the_loser_turns_on_its_own(realm: Realm) -> None:
    strong = await god(realm, "Kerr", Domain.WAR, Domain.BLOOD)
    strong.essence, strong.strength, strong.will, strong.level, strong.wrath, strong.mercy = 50, 90, 90, 20, 80, 10
    weak = await foreign(realm.session, realm, "Ussamar", Domain.DEATH, power=10)
    town, foe = await settlement(realm, "Embercourt"), await settlement(realm, "Timberfold")
    await worship(realm, town, strong.id)
    await worship(realm, foe, weak.id)
    ctx = context(realm.session, tuned(domains=CERTAIN))
    first, second = side_for(town), side_for(foe)
    assert await intervene(ctx, 1, 3, first, second) == 2
    assert first.divine_strike_pct > 0 and second.divine_spurned == ctx.rules.domains.battle_spurned_morale and second.divine_strike_pct == 0
    assert weak.power == 10 - ctx.rules.domains.battle_foreign_power
    grudge = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == weak.id, MemoryRow.subject_node_id == strong.id))
    assert grudge is not None and grudge.kind is MemoryKind.HUMILIATED_ME


async def test_a_held_or_poor_god_and_a_shared_patron_stay_out(realm: Realm) -> None:
    war = await god(realm, "Kerr", Domain.WAR, Domain.BLOOD)
    war.essence = 0
    town, foe = await settlement(realm, "Embercourt"), await settlement(realm, "Timberfold")
    await worship(realm, town, war.id)
    ctx = context(realm.session, tuned(domains=CERTAIN))
    assert await intervene(ctx, 1, 4, side_for(town), side_for(foe)) == 0
    war.essence = 50
    token = HELD_SCOPE.set(HeldScope(None, frozenset({war.id})))
    try:
        assert await intervene(ctx, 1, 5, side_for(town), side_for(foe)) == 0
    finally:
        HELD_SCOPE.reset(token)
    await worship(realm, foe, war.id)
    assert await intervene(ctx, 1, 6, side_for(town), side_for(foe)) == 0 and war.essence == 50


async def test_a_shattered_manifestation_scatters_the_form_until_it_heals(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    sea.existence_profile = ExistenceProfile(mode=ExistenceMode.CONCRETE)
    ctx = context(realm.session)
    first = await inflict(ctx, sea, DivineWoundKind.SHATTERED_MANIFESTATION, WoundCause.CREATOR, severity=10)
    second = await inflict(ctx, sea, DivineWoundKind.SHATTERED_MANIFESTATION, WoundCause.CREATOR, severity=90)
    assert first is not None and second is not None
    assert sea.existence_profile.mode is ExistenceMode.SCATTERED and first.prior_mode is second.prior_mode is ExistenceMode.CONCRETE
    await heal_wounds(context(realm.session, tuned(divine_wounds={"base_heal": 20})))
    assert first.healed == 100 and second.healed < 100 and sea.existence_profile.mode is ExistenceMode.SCATTERED
    await control.edit_wound(ctx, second.id, {"prior_mode": ExistenceMode.CONCEPTUAL.value}, [])
    await control.remove_wound(ctx, second.id)
    assert sea.existence_profile.mode is ExistenceMode.CONCEPTUAL


async def test_a_son_s_plan_is_written_about_its_aim(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    scope = await scoped(realm)
    assert (await goal_lines(scope, sea))[-1] == "You hold no aim yet; take one, then write your plan about it"
    await control.set_goal(context(realm.session), sea.id, GodGoalKind.BE_WORSHIPPED, amount=2)
    lines = await goal_lines(scope, sea)
    assert lines[0].startswith("Your aim: to be worshipped") and lines[-1] == "Your plan is written about one of your aims"


async def test_where_the_dead_speak_spirits_take_turns_with_a_spirit_s_tools(realm: Realm) -> None:
    spirit = await make(realm.session, "Old Voice", EntityType.SPIRIT, SpiritStats(), world_id=realm.world.id, location_id=realm.region.id)
    scope = await scoped(realm)
    assert spirit.id not in {candidate.entity.id for candidate in await candidates(scope)}
    await natural_law(realm, "The Speaking Dead", NaturalLaw.THE_DEAD_SPEAK)
    await realm.session.flush()
    assert spirit.id in {candidate.entity.id for candidate in await candidates(await scoped(realm))}
    assert {tool.value for tool in SPIRIT_TOOLS} == {"look_at_world", "inspect_entity", "search_entities", "prophesy", "send_dispatch", "pray_to_creator"}
