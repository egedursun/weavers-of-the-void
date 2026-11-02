from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.lore import MessageRow, ThreadRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.son import SonDeathCause
from aerona.engine.gods.god_death import god_death
from aerona.prompts.contexts.opportunities import (
    BreatheLife,
    DeadGod,
    DeadSibling,
    Enemies,
    Existence,
    Godless,
    LovingNeighbours,
    NoGod,
    NoKnowledge,
    OpenThreads,
    OwnWorshippers,
    RivalSiblings,
    Silence,
    StaleThreads,
    TeachableKnowledge,
    TradePartners,
    Unclaimed,
)
from aerona.rules.registry import Rules
from aerona.services.gods.opportunities import creator_context, mortal_lines, player_hints, son_lines
from tests.engine.gods.factories import GodsWorld, bond, make_context, make_entity, make_son


async def test_son_lines(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, loyalty=10)
    rival = await make_son(session, "Iolen", world.world.id)
    await SonRepository(session).change_relation(son.id, rival.id, -60)
    lost = await make_entity(session, "Lost", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    mine = await make_entity(session, "Mine", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, mine.id, son.id, BondKind.WORSHIPS)
    await EntityRepository(session).add_flag(lost.id, EntityFlag.GODLESS, 1)
    session.add(ThreadRow(epoch=1, text="An old feud waits."))
    await session.flush()
    dead = await make_son(session, "Fallen", world.world.id)
    await god_death(make_context(session, rules, 2), dead, "fell", SonDeathCause.OTHER)
    lines = await son_lines(session, rules, son.id)
    kinds = {type(line) for line in lines}
    assert {BreatheLife, Unclaimed, OwnWorshippers, RivalSiblings, Godless, DeadSibling, TeachableKnowledge, Silence, OpenThreads} <= kinds
    rivals = next(line for line in lines if isinstance(line, RivalSiblings))
    assert rivals.rivals[0].id == rival.id and rivals.rivals[0].value == -60
    assert any(isinstance(line, Existence) for line in lines) is False or son.existence <= rules.opportunities.fading_existence
    world.cosmos.epoch = 2 + rules.opportunities.stale_epochs
    later = await son_lines(session, rules, son.id)
    assert any(isinstance(line, StaleThreads) for line in later)


async def test_mortal_lines(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    home = await make_entity(session, "Home", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    friend = await make_entity(session, "Friends", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    foe = await make_entity(session, "Foes", EntityType.FACTION, world_id=world.world.id, location_id=world.region.id)
    session.add(CommunityRelationRow(entity_a_id=min(home.id, friend.id), entity_b_id=max(home.id, friend.id), value=80))
    session.add(CommunityRelationRow(entity_a_id=min(home.id, foe.id), entity_b_id=max(home.id, foe.id), value=-50))
    await bond(session, home.id, foe.id, BondKind.ENEMY)
    son = await make_son(session, "Velkar", world.world.id)
    lines = await mortal_lines(session, rules, home.id)
    kinds = {type(line) for line in lines}
    assert {TradePartners, Enemies, LovingNeighbours, NoKnowledge, NoGod} <= kinds
    enemies = next(line for line in lines if isinstance(line, Enemies))
    assert enemies.enemies[0].id == foe.id and enemies.can_declare_war
    await bond(session, home.id, son.id, BondKind.WORSHIPS)
    loyal = replace(rules, death=replace(rules.death, apostasy_chance=0))
    await god_death(make_context(session, loyal, 2), son, "fell", SonDeathCause.OTHER)
    after = await mortal_lines(session, rules, home.id)
    assert any(isinstance(line, DeadGod) for line in after)


async def test_creator_context_and_hints(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    session.add(MessageRow(epoch=2, sender_node_id=people.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="help"))
    rebel = await make_son(session, "Velkar", world.world.id)
    rebel.rebel = True
    rebel.existence = 5
    await session.flush()
    context = await creator_context(session, rules)
    assert context.unanswered_prayers == 1
    assert context.rebel_sons == ["Velkar"]
    assert context.fading_sons[0].existence == 5
    assert context.unclaimed_count == 1
    hints = await player_hints(session, rules)
    assert hints.sons_without_orders == ("Velkar",)
    assert hints.sons_without_image == 1
