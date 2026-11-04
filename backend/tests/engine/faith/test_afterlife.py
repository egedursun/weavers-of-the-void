from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.faith import AfterlifeStratumRow, PossessionRow, SpiritProfileRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.body import ConditionKind, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import (
    AfterlifeState,
    FuneralRite,
    JudgementDoctrine,
    RebirthPath,
    SpiritAlignment,
    StratumKind,
    TenetKind,
)
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.models.entity_stats import HouseStats
from aerona.domain.models.faith import StratumCriteria
from aerona.engine.body.conditions import condition_of, end_condition
from aerona.engine.faith.backfill import CRITERIA_FIXUP, PROFILES_FIXUP, backfill_faith
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.judgement import default_criteria, judge, leave_realm, new_stratum, profile_for, route, score_of
from aerona.engine.faith.souls import (
    burden,
    consume,
    cradle,
    fear_of_torment,
    realm_essence,
    realm_population,
    release_host,
    seal_with,
    take_host,
    unseal_with,
)
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.phases.spirits import ghost_legend
from aerona.rules.registry import Rules
from tests.engine.faith.factories import faithful, mortal, spirit, tick
from tests.engine.gods.factories import GodsWorld, bond, make_entity, make_son


def test_criteria_match_every_typed_predicate() -> None:
    hall = StratumCriteria(violence_at_least=40, tenets_any=(TenetKind.HOLY_WAR,), needs_rite=True)
    deeds = {"violence": 50}
    assert hall.matches(score=10, deeds=deeds, has_god=True, rite=FuneralRite.BURIAL, tenets={TenetKind.HOLY_WAR})
    assert not hall.matches(score=10, deeds=deeds, has_god=True, rite=FuneralRite.NONE, tenets={TenetKind.HOLY_WAR})
    assert not hall.matches(score=10, deeds=deeds, has_god=True, rite=FuneralRite.BURIAL, tenets=set())
    assert not hall.matches(score=10, deeds={"violence": 10}, has_god=True, rite=FuneralRite.BURIAL, tenets={TenetKind.HOLY_WAR})
    assert StratumCriteria(no_god=True).matches(score=0, deeds={}, has_god=False, rite=FuneralRite.NONE, tenets=set())
    assert not StratumCriteria().matches(score=0, deeds={}, has_god=False, rite=FuneralRite.NONE, tenets=set())
    assert StratumCriteria.read({"score_between": "25-60", "score_at_least": 60}).score_at_least == 60
    assert StratumCriteria.read({"priority": "high"}) == StratumCriteria()


async def test_routing_follows_priority_closure_and_ownership(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    god = await make_son(session, "Veyra", world.world.id)
    rival = await make_son(session, "Osk", world.world.id)
    strata = [new_stratum(rules, world.region, kind) for kind in StratumKind]
    for index, row in enumerate(strata):
        row.id = index + 1
    paradise = next(row for row in strata if row.kind is StratumKind.PARADISE)
    plain = next(row for row in strata if row.kind is StratumKind.PLAIN)
    common = {"deeds": {"violence": 0}, "rite": FuneralRite.BURIAL, "tenets": set[TenetKind]()}
    assert route(strata, score=90, god=god, **common) is paradise
    assert route(strata, score=50, god=god, **common) is plain
    paradise.closed = True
    assert route(strata, score=90, god=god, **common) is plain
    paradise.closed, paradise.son_id = False, rival.id
    assert route(strata, score=90, god=god, **common) is plain
    assert route(strata, score=90, god=rival, **common) is paradise
    assert route(strata, score=90, god=None, **common).kind is StratumKind.OBLIVION
    assert default_criteria(rules.afterlife, StratumKind.TORMENT).score_below == rules.afterlife.torment_score


def test_judgement_scores_come_from_rules(rules: Rules) -> None:
    table = rules.afterlife
    assert score_of(table, {}, JudgementDoctrine.RITE, rite=FuneralRite.BURIAL, favoured=False, tenets=set()) == table.rite_score
    assert score_of(table, {}, JudgementDoctrine.RITE, rite=FuneralRite.NONE, favoured=False, tenets=set()) == table.no_rite_score
    assert score_of(table, {}, JudgementDoctrine.FAVOUR, rite=FuneralRite.NONE, favoured=True, tenets=set()) == table.favoured_score
    assert score_of(table, {}, JudgementDoctrine.NONE, rite=FuneralRite.NONE, favoured=False, tenets=set()) == table.neutral_score


async def test_judged_souls_are_counted_and_leave_the_count(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    dead = await mortal(session, world, faith.town, "Ardo", dead=True)
    await bond(session, dead.id, faith.god.id, BondKind.WORSHIPS)
    soul = await spirit(session, world, world.region, "Shade of Ardo")
    for attempt in range(40):
        profile = await session.get(SpiritProfileRow, soul.id)
        if profile is not None:
            await session.delete(profile)
            await session.flush()
        verdict = await judge(tick(session, rules, attempt + 1), soul, dead, world.region)
        if verdict.stratum is not None:
            break
    assert verdict.stratum is not None
    assert verdict.stratum.population == 1
    assert await realm_population(session, faith.god.id) == 1
    profile = await session.get(SpiritProfileRow, soul.id)
    assert profile is not None
    await leave_realm(ctx, profile, AfterlifeState.REBORN)
    assert verdict.stratum.population == 0


async def test_seals_need_a_stronger_counter_rite(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    soul = await spirit(session, world, world.region, "Bound One")
    session.add(SpiritProfileRow(spirit_entity_id=soul.id, imprint={}, traits=[], deeds={}, locked=[]))
    await session.flush()
    assert await seal_with(ctx, soul.id, 5)
    profile = await session.get(SpiritProfileRow, soul.id)
    assert profile is not None and profile.seal_strength == 5 * rules.necromancy.seal_per_power
    assert not await unseal_with(ctx, soul.id, 5)
    assert await unseal_with(ctx, soul.id, 6)
    assert not profile.sealed


async def test_nameless_burial_seals_the_executed(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:

    certain = Rules().afterlife.__class__(nameless_execution_pct=100)
    ctx = tick(session, Rules(afterlife=certain))
    dead = await mortal(session, world, world.region, "Heretic", dead=True)
    session.add(
        InjuryRow(
            bearer_node_id=dead.id,
            kind=next(iter(InjuryKind)),
            part="torso",
            damage_type=next(iter(DamageType)),
            severity=1,
            state=next(iter(InjuryState)),
            function_loss=0,
            cause_kind=HarmCause.PUNISHMENT,
            epoch=1,
        )
    )
    await session.flush()
    soul = await spirit(session, world, world.region, "Shade of the Heretic")
    profile = await profile_for(ctx, soul, dead)
    assert profile.rite is FuneralRite.NAMELESS
    assert profile.sealed and profile.seal_strength == certain.nameless_seal


async def test_possession_lays_the_imprint_and_wears_the_host(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    host = await mortal(session, world, world.region, "Host")
    await write_values(session, ValueHolder.PERSONAL, host.id, {ValueAxis.MERCY: 60})
    soul = await spirit(session, world, world.region, "Wrathful Shade", unrest=90)
    profile = SpiritProfileRow(spirit_entity_id=soul.id, imprint={"mercy": -80}, traits=[], deeds={}, alignment=SpiritAlignment.VENGEFUL, locked=[])
    session.add(profile)
    await session.flush()
    row = await take_host(ctx, profile, soul, host)
    assert (await stored_values(session, ValueHolder.PERSONAL, host.id))[ValueAxis.MERCY] == -80
    assert row.host_values["mercy"] == 60
    before = host.sanity
    held = await burden(ctx)
    assert held and row.stress == rules.necromancy.possession_stress
    assert host.sanity is not None and (before is None or host.sanity <= before)
    await release_host(ctx, row)
    assert (await stored_values(session, ValueHolder.PERSONAL, host.id))[ValueAxis.MERCY] == 60
    assert await session.get(PossessionRow, host.id) is None
    assert await condition_of(ctx, host.id, ConditionKind.POSSESSION) is None


async def test_a_lost_condition_ends_the_possession(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:

    ctx = tick(session, rules)
    host = await mortal(session, world, world.region, "Freed Host")
    soul = await spirit(session, world, world.region, "Shade")
    profile = SpiritProfileRow(spirit_entity_id=soul.id, imprint={}, traits=[], deeds={}, locked=[])
    session.add(profile)
    await session.flush()
    await take_host(ctx, profile, soul, host)
    await end_condition(ctx, host, ConditionKind.POSSESSION)
    assert await burden(ctx) == []
    assert await session.get(PossessionRow, host.id) is None


async def test_eaten_souls_cost_their_god_and_feed_the_eaters_maker(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:

    ctx = tick(session, rules)
    owner = await make_son(session, "Keeper", world.world.id)
    death = await make_son(session, "Grave", world.world.id)
    death.domain_primary = Domain.DEATH
    eater = await make_entity(session, "Maw", EntityType.SPECIES, world_id=world.world.id, creator_son_id=death.id)
    soul = await spirit(session, world, world.region, "Lost Soul")
    profile = SpiritProfileRow(spirit_entity_id=soul.id, imprint={}, traits=[], deeds={}, patron_son_id=owner.id, locked=[])
    session.add(profile)
    await session.flush()
    owner_before, death_before = owner.essence, death.essence
    fed = await consume(ctx, profile, soul, eater)
    assert fed is death and death.essence == death_before + rules.necromancy.consumption_essence
    assert owner.essence == owner_before - rules.necromancy.consumption_loss
    assert profile.state is AfterlifeState.CONSUMED and soul.status is not EntityStatus.CANON


async def test_death_gods_draw_on_their_realm(session: AsyncSession, world: GodsWorld) -> None:

    rules = Rules(afterlife=Rules().afterlife.__class__(realm_essence_per_100=100))
    ctx = tick(session, rules)
    death = await make_son(session, "Grave", world.world.id)
    death.domain_primary = Domain.DEATH
    stratum = new_stratum(rules, world.region, StratumKind.PLAIN)
    session.add(stratum)
    await session.flush()
    soul = await spirit(session, world, world.region, "Resting")
    session.add(
        SpiritProfileRow(
            spirit_entity_id=soul.id, imprint={}, traits=[], deeds={}, patron_son_id=death.id, state=AfterlifeState.IN_REALM, stratum_id=stratum.id, locked=[]
        )
    )
    await session.flush()
    before = death.essence
    assert await realm_essence(ctx) == 1
    assert death.essence == before + 1


async def test_fear_of_torment_settles_at_its_target(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    torment = new_stratum(rules, world.region, StratumKind.TORMENT)
    session.add(torment)
    await session.flush()
    dead = await mortal(session, world, faith.town, "Sinner", dead=True)
    soul = await spirit(session, world, world.region, "Tormented")
    session.add(
        SpiritProfileRow(
            spirit_entity_id=soul.id,
            origin_mortal_id=dead.id,
            imprint={},
            traits=[],
            deeds={},
            patron_son_id=faith.god.id,
            state=AfterlifeState.IN_REALM,
            stratum_id=torment.id,
            locked=[],
        )
    )
    await write_values(session, ValueHolder.CULTURE, faith.people.id, {ValueAxis.HONOUR: rules.afterlife.torment_value_target - 1})
    await session.flush()
    church = (await FaithBook.load(session)).churches[faith.cult.id]
    for _ in range(5):
        await fear_of_torment(ctx, church)
    values = await stored_values(session, ValueHolder.CULTURE, faith.people.id)
    assert values[ValueAxis.HONOUR] == rules.afterlife.torment_value_target


async def test_house_doctrine_returns_a_soul_to_its_blood(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    faith = await faithful(session, world)
    faith.doctrine.rebirth_path = RebirthPath.HOUSE
    elder = await mortal(session, world, faith.town, "Elder", dead=True)
    seat = await make_entity(session, "Velhall", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    head = await mortal(session, world, seat, "Head")
    house = await make_entity(session, "House Vel", EntityType.HOUSE, world_id=world.world.id, stats=HouseStats())
    session.add(HouseProfileRow(house_entity_id=house.id, head_entity_id=head.id, seats=[], traits=[], emblem={}, locked=[]))
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=elder.id))
    soul = await spirit(session, world, world.region, "Elder's Soul")
    profile = SpiritProfileRow(spirit_entity_id=soul.id, origin_mortal_id=elder.id, imprint={}, traits=[], deeds={}, patron_son_id=faith.god.id, locked=[])
    session.add(profile)
    await session.flush()
    place = await cradle(ctx, profile, faith.town)
    assert place.path is RebirthPath.HOUSE and place.community.id == seat.id and place.house is not None


async def test_hauntings_become_believed_ghost_legends(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    town = await make_entity(session, "Hollow", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    soul = await spirit(session, world, world.region, "Lantern Ghost", unrest=90)
    legend, born = await ghost_legend(ctx, soul, town)
    assert born
    row = await session.get(LegendProfileRow, legend.id)
    assert row is not None and row.archetype is LegendArchetype.HAUNTED_PLACE and row.credence == rules.spirits.haunt_legend_credence
    again, born_again = await ghost_legend(ctx, soul, town)
    assert again.id == legend.id and not born_again
    assert row.credence == rules.spirits.haunt_legend_credence + rules.spirits.haunt_legend_gain


async def test_backfill_gives_old_spirits_profiles_and_typed_strata(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    dead = await mortal(session, world, world.region, "Ancestor", dead=True)
    old = await spirit(session, world, world.region, "Old Spirit", unrest=5)
    await bond(session, old.id, dead.id, BondKind.DESCENDS_FROM)
    orphan = await spirit(session, world, world.region, "Nameless Wisp", unrest=95)
    legacy = AfterlifeStratumRow(realm_entity_id=world.region.id, kind=StratumKind.PLAIN, name="Grey", criteria={"score_between": "25-60"}, population=7)
    session.add(legacy)
    await session.flush()
    await backfill_faith(ctx, await FaithBook.load(session))
    old_profile = await session.get(SpiritProfileRow, old.id)
    orphan_profile = await session.get(SpiritProfileRow, orphan.id)
    assert old_profile is not None and old_profile.origin_mortal_id == dead.id and old_profile.alignment is SpiritAlignment.GUARDIAN
    assert orphan_profile is not None and orphan_profile.alignment is SpiritAlignment.VENGEFUL
    assert legacy.criteria == default_criteria(rules.afterlife, StratumKind.PLAIN).stored()
    assert legacy.population == 0
    assert await session.get(AppliedFixupRow, PROFILES_FIXUP) is not None
    assert await session.get(AppliedFixupRow, CRITERIA_FIXUP) is not None
    rows = list(await session.scalars(select(SpiritProfileRow)))
    await backfill_faith(ctx, await FaithBook.load(session))
    assert len(list(await session.scalars(select(SpiritProfileRow)))) == len(rows)
