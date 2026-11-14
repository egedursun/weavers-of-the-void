from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.arts_lines import mortal_arts_lines, son_arts_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.arts import ArtMovementRow, ArtPriceRow, BetRow, CanonWorkRow, CollectorRow, ForgeryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import MovementRow
from aerona.db.tables.constructs import InstructionOrderRow, InstructionSetRow, RemadeRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.mind import SkillRow, TraitRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import ClaimRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.sacred import BirthSignRow, DivinationSystemRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.arts import CanonPath, ClubKind, FandomLine, ForgeryKind, ForgeryStatus
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import CollectiveActKind
from aerona.domain.enums.constructs import CommandToken, ContractStatus, MindWill, OrderCondition, OrderKind
from aerona.domain.enums.culture import ArtMedium, MagicSource
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import SkillKind, SkillSource, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.sacred import DivinationKind, DivinationValidity, SignInfluence
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.models.entity_stats import ArmyStats, ArtworkStats, BeastStats, CelestialStats, PeopleStats, PolityStats, SpiritStats, TitleStats
from aerona.engine.arts import control as arts
from aerona.engine.arts.forgery import ForgeryTally, examine, forge, forge_works
from aerona.engine.arts.movements import MovementTally, form_canon, found_movements, teach_canon, tend_movements
from aerona.engine.arts.sport import SportTally, buy_favour, play, prowess, read_line
from aerona.engine.constructs.making import Design, make_construct
from aerona.engine.constructs.orders import OrderTally, keep_constructs
from aerona.engine.constructs.remaking import RemadeTally, keep_remade, may_remake, remake
from aerona.engine.constructs.wards import SealTally, keep_seals, unbind
from aerona.engine.context import TickContext
from aerona.engine.ecology.contracts import ContractTally, keep_contracts
from aerona.engine.intrigue.schemes import choose_kind, forge_work
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import close, connect
from aerona.engine.primitives.stats import stat_or
from aerona.engine.sacred.astrology import SignTally, sign_birth
from aerona.engine.sacred.foresight import validity_of
from aerona.services.integrity.arts_links import mend_arts_links
from tests.engine.core.factories import CoreWorld, bond, entity, knowledge, mortal, settlement, tuned_rules


def society(town_id: int, lead: SocialClass) -> CommunitySocietyRow:
    shares = {f"share_{item.value}": (60.0 if item is lead else 5.0) for item in SocialClass}
    satisfaction = {f"satisfaction_{item.value}": 50 for item in SocialClass}
    return CommunitySocietyRow(
        entity_id=town_id, **shares, **satisfaction, stock_food=500, stock_ore=500, stock_goods=500, price_food=300, price_ore=100, price_goods=100
    )


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "arts", rules=tuned_rules(**rules))


async def ruled_realm(session: AsyncSession, world: CoreWorld, town: EntityRow, ruler: EntityRow, treasury: int = 0) -> EntityRow:
    realm = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, treasury=treasury, locked=[], emblem={}
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id))
    await session.flush()
    return realm


async def work(session: AsyncSession, world: CoreWorld, name: str, author: EntityRow, town: EntityRow, *, quality: int = 60) -> EntityRow:
    piece = await entity(session, name, EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=town.id)
    session.add(ArtworkProfileRow(artwork_entity_id=piece.id, medium=ArtMedium.FRESCO, author_entity_id=author.id, quality=quality, locked=[]))
    await session.flush()
    return piece


async def people_of(session: AsyncSession, world: CoreWorld, *towns: EntityRow) -> EntityRow:
    folk = await entity(session, f"Folk of {towns[0].name}", EntityType.PEOPLE, PeopleStats(population=900), world_id=world.world.id)
    for town in towns:
        town.affiliated_entity_id = folk.id
    await session.flush()
    return folk


async def test_a_match_moves_ratings_fandom_and_the_wagers_of_the_towns(session: AsyncSession, world: CoreWorld) -> None:
    north = await settlement(session, "Northwick", world, world.regions[0], wealth=50)
    south = await settlement(session, "Southwick", world, world.regions[1], wealth=50)
    runner = await mortal(session, "Fenna", world, north.id, strength=90, agility=90)
    await mortal(session, "Dorrin", world, north.id, strength=10, agility=10)
    ctx = await at(session, 2, sports={"athletes": 1})
    home = await arts.start_club(ctx, north.id, ClubKind.TEAM_GAME)
    squad = list(await session.scalars(select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id == home.faction_entity_id)))
    assert squad == [runner.id] and await prowess(ctx, home) == 90
    away = await arts.start_club(ctx, south.id, ClubKind.TEAM_GAME)
    home.fandom = away.fandom = 100
    match = await play(ctx, None, home, away, SportTally(), fixed=home.faction_entity_id)
    assert match.winner_entity_id == home.faction_entity_id and match.stake > 0
    assert (home.wins, home.losses, away.wins, away.losses) == (1, 0, 0, 1)
    assert home.rating > away.rating and home.fandom == 100 and away.fandom < 100
    bets = {row.club_entity_id: row for row in await session.scalars(select(BetRow).where(BetRow.match_id == match.id))}
    assert bets[home.faction_entity_id].won is True and bets[away.faction_entity_id].won is False
    assert stat_or(north, "wealth", 0) > 50 > stat_or(south, "wealth", 0)


async def test_fans_split_by_class_give_a_club_leverage_and_a_weak_ruler_buys_its_favour(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brightmoor", world, world.regions[0])
    session.add(society(town.id, SocialClass.ARTISAN))
    ruler = await mortal(session, "Aldric", world, town.id)
    session.add(MortalProfileRow(entity_id=ruler.id, legitimacy=10, locked=[]))
    await ruled_realm(session, world, town, ruler, treasury=1000)
    ctx = await at(session, 2)
    club = await arts.start_club(ctx, town.id, ClubKind.COMBAT)
    club.fandom = 100
    await read_line(ctx, club, town)
    assert club.line is FandomLine.CLASS and club.leverage > 0
    tally = SportTally()
    await buy_favour(ctx, tally)
    profile = await session.get(MortalProfileRow, ruler.id)
    assert tally.bought == 1 and club.bought_by_entity_id is not None
    assert profile is not None and (profile.legitimacy or 0) > 10


async def test_makers_band_into_a_movement_that_becomes_orthodox_and_their_works_enter_the_canon(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Inkwell", world, world.regions[0])
    folk = await people_of(session, world, town)
    first = await mortal(session, "Sera", world, town.id)
    second = await mortal(session, "Tamsin", world, town.id)
    await write_values(session, ValueHolder.PERSONAL, first.id, {ValueAxis.KNOWLEDGE: 90, ValueAxis.HONOUR: 60})
    piece = await work(session, world, "The Quiet Hours", first, town)
    await work(session, world, "Lantern Song", second, town)
    ctx = await at(session, 3, art_movements={"found_chance": 100, "found_artists": 2, "orthodoxy_patrons": 0, "scandal_chance": 0})
    tally = MovementTally()
    await found_movements(ctx, tally)
    movement = await session.scalar(select(ArtMovementRow))
    assert tally.founded == 1 and movement is not None and movement.manifesto.get("knowledge") == 90
    profile = await session.get(FactionProfileRow, movement.faction_entity_id)
    assert profile is not None and profile.kind is FactionKind.ART_MOVEMENT
    await tend_movements(ctx, tally)
    assert movement.orthodoxy
    await form_canon(await at(session, 3, canon={"renown_quality": 100, "copies": 100}), tally)
    canon = await session.get(CanonWorkRow, (folk.id, piece.id))
    assert canon is not None and canon.path is CanonPath.MOVEMENT


async def test_a_priced_work_is_forged_and_a_keen_eyed_collector_exposes_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Gildmark", world, world.regions[0])
    master = await mortal(session, "Velma", world, town.id)
    forger = await mortal(session, "Quill", world, town.id, creativity=80)
    session.add(MortalProfileRow(entity_id=forger.id, locked=[]))
    piece = await work(session, world, "The Golden Field", master, town, quality=90)
    session.add(ArtPriceRow(artwork_entity_id=piece.id, price=500, locked=[]))
    critic = await mortal(session, "Orrin", world, town.id)
    session.add(CollectorRow(holder_entity_id=critic.id, connoisseurship=100, locked=[]))
    await session.flush()
    ctx = await at(session, 3, forgery={"forge_chance": 100, "skill_floor": 50, "price_floor": 100, "expose_chance": 100})
    tally = ForgeryTally()
    await forge_works(ctx, tally)
    row = await session.scalar(select(ForgeryRow).where(ForgeryRow.forger_entity_id == forger.id))
    assert tally.forged == 1 and row is not None and row.kind is ForgeryKind.ARTWORK and row.original_entity_id == piece.id
    session.add(ArtPriceRow(artwork_entity_id=row.item_entity_id, price=300, locked=[]))
    await session.flush()
    await examine(ctx, tally)
    profile = await session.get(MortalProfileRow, forger.id)
    copy = await session.get(ArtPriceRow, row.item_entity_id)
    assert row.status is ForgeryStatus.EXPOSED and row.exposed_by_entity_id == critic.id
    assert copy is not None and copy.price == 0 and profile is not None and profile.infamy > 0


async def test_a_forged_charter_gives_a_fabricated_claim_that_dies_with_its_exposure(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stonereach", world, world.regions[0])
    ruler = await mortal(session, "Hadrik", world, town.id)
    realm = await ruled_realm(session, world, town, ruler)
    forger = await mortal(session, "Lisle", world, town.id, creativity=70)
    title = await entity(session, "Crown of the Reach", EntityType.TITLE, TitleStats(), world_id=world.world.id)
    title.affiliated_entity_id = realm.id
    await session.flush()
    ctx = await at(session, 3)
    row = await forge(ctx, title, forger)
    claim = await session.get(ClaimRow, row.claim_id) if row.claim_id is not None else None
    assert row.kind is ForgeryKind.DOCUMENT and claim is not None and claim.polity_entity_id == realm.id and claim.ended_epoch is None
    await arts.expose_forgery(ctx, row.id, None)
    assert claim.ended_epoch == 3


async def test_a_construct_guards_its_charge_answers_a_thief_of_its_token_and_runs_down_without_its_maker(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Forgeholm", world, world.regions[0], defense=30)
    maker = await mortal(session, "Brask", world, town.id)
    thief = await mortal(session, "Nim", world, town.id)
    ctx = await at(session, 2)
    row = await make_construct(ctx, maker, Design(material=MaterialKind.STONE, source=MagicSource.LEY, token=CommandToken.ITEM))
    rules = await session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == row.entity_id))
    assert rules is not None and rules.holder_node_id == maker.id and rules.token_entity_id is not None
    tally = OrderTally()
    await keep_constructs(await at(session, 3), tally)
    assert stat_or(town, "defense", 0) > 30 and tally.acted >= 1
    for owned in await session.scalars(
        select(BondRow).where(BondRow.target_node_id == rules.token_entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    ):
        await close(session, owned, 3, "stolen")
    await connect(session, thief.id, rules.token_entity_id, BondKind.OWNS, 3)
    await keep_constructs(await at(session, 4), tally)
    beast = await session.get(BeastProfileRow, row.entity_id)
    assert rules.holder_node_id == thief.id and tally.seized == 1 and beast is not None and beast.bound_to_node_id == thief.id
    maker.status, maker.end_epoch = EntityStatus.DEAD, 2
    row.power = row.upkeep
    await session.flush()
    await keep_constructs(await at(session, 5), tally)
    body = await session.get(EntityRow, row.entity_id)
    assert body is not None and body.status is not EntityStatus.CANON and tally.ran_down == 1


async def test_a_bound_soul_grows_a_will_past_every_order_and_a_kill_switch_stills_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hollowgate", world, world.regions[0])
    maker = await mortal(session, "Iska", world, town.id)
    ctx = await at(session, 2)
    row = await make_construct(ctx, maker, Design(material=MaterialKind.BRONZE, source=MagicSource.LEY, token=CommandToken.WORD))
    spirit = await entity(session, "Restless One", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=world.regions[0].id)
    row.soul_entity_id = spirit.id
    rules = await session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == row.entity_id))
    assert rules is not None
    await session.flush()
    tally = OrderTally()
    for epoch in (3, 4):
        await keep_constructs(await at(session, epoch, constructs={"will_chance": 100}), tally)
    assert row.will is MindWill.FULL and tally.woke == 2
    rules.kill_switch = True
    await session.flush()
    await keep_constructs(await at(session, 5, constructs={"will_chance": 100}), tally)
    body = await session.get(EntityRow, row.entity_id)
    assert row.will is MindWill.EXCEEDING and tally.freed == 1 and tally.killed == 1 and tally.risen == 1
    enemy = await session.scalar(
        select(BondRow).where(BondRow.source_node_id == row.entity_id, BondRow.target_node_id == maker.id, BondRow.kind == BondKind.ENEMY)
    )
    assert enemy is not None
    assert body is not None and body.status is not EntityStatus.CANON


async def test_an_order_kept_while_its_maker_lives_lapses_at_the_makers_death(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Wardholm", world, world.regions[0])
    maker = await mortal(session, "Oddo", world, town.id)
    ctx = await at(session, 2)
    row = await make_construct(
        ctx, maker, Design(material=MaterialKind.IRON, source=MagicSource.DIVINE, token=CommandToken.WORD, orders=[(OrderKind.SERVE, 1)])
    )
    order = await session.scalar(
        select(InstructionOrderRow)
        .join(InstructionSetRow, InstructionSetRow.id == InstructionOrderRow.set_id)
        .where(InstructionSetRow.owner_entity_id == row.entity_id)
    )
    assert order is not None
    order.condition = OrderCondition.WHILE_MAKER_LIVES
    maker.status, maker.end_epoch = EntityStatus.DEAD, 2
    await session.flush()
    tally = OrderTally()
    await keep_constructs(await at(session, 3), tally)
    assert order.lapsed and tally.lapsed == 1


async def test_construct_stacks_stand_still_without_their_seal_and_a_dispel_drains_a_construct(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Bastion", world, world.regions[0])
    ruler = await mortal(session, "Merrow", world, town.id)
    usurper = await mortal(session, "Cade", world, town.id)
    realm = await ruled_realm(session, world, town, ruler)
    army = await entity(session, "Host of Bastion", EntityType.ARMY, ArmyStats(size=20), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=realm.id, raised_epoch=1))
    unit = ArmyUnitRow(army_entity_id=army.id, kind=UnitKind.CONSTRUCTS, count=20, locked=[])
    session.add(unit)
    await session.flush()
    tally = SealTally()
    await keep_seals(await at(session, 2), tally)
    rules = await session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == army.id))
    assert tally.sealed == 1 and rules is not None and rules.holder_node_id == ruler.id and unit.organisation == 100
    for owned in await session.scalars(
        select(BondRow).where(BondRow.target_node_id == rules.token_entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    ):
        await close(session, owned, 2, "stolen")
    await connect(session, usurper.id, rules.token_entity_id, BondKind.OWNS, 2)
    await keep_seals(await at(session, 3), tally)
    assert unit.organisation == 0 and tally.stilled == 1
    ctx = await at(session, 3)
    body = await make_construct(ctx, ruler, Design(material=MaterialKind.CLAY, source=MagicSource.LEY, token=CommandToken.WORD))
    before = body.power
    construct = await session.get(EntityRow, body.entity_id)
    assert construct is not None
    told = await unbind(ctx, construct, 40)
    assert told is not None and body.power == before - 20


async def test_a_raided_town_posts_a_bounty_and_a_studied_hunt_slays_the_beast(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fellmoor", world, world.regions[0])
    hunter = await mortal(session, "Rook", world, town.id, strength=80)
    session.add(MortalProfileRow(entity_id=hunter.id, locked=[]))
    session.add(SkillRow(holder_node_id=hunter.id, skill=SkillKind.HUNTING, level=6, peak=6, last_used_epoch=1, source=SkillSource.PRACTICE))
    beast = await entity(session, "The Ashen Maw", EntityType.BEAST, BeastStats(hp=80, danger=20), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(BeastProfileRow(beast_entity_id=beast.id, temper=BeastTemper.HUNGRY, raids=3, lair_place_id=world.regions[0].id, hoard={}, locked=[]))
    await session.flush()
    tally = ContractTally()
    rules = {"take_chance": 100, "hunt_base": 100}
    await keep_contracts(await at(session, 3, monster_contracts=rules), tally)
    row = await session.scalar(select(MonsterContractRow).where(MonsterContractRow.beast_entity_id == beast.id))
    assert row is not None and row.community_entity_id == town.id and tally.posted == 1 and tally.taken == 1
    assert row.status is ContractStatus.SLAIN and row.hunter_entity_id == hunter.id and tally.slain == 1
    profile = await session.get(MortalProfileRow, hunter.id)
    assert beast.status is not EntityStatus.CANON and profile is not None and profile.renown > 0


async def test_a_dreaded_birth_under_a_ruling_sky_is_shaped_by_it_and_sent_away_by_star_readers(session: AsyncSession, world: CoreWorld) -> None:
    home = await settlement(session, "Starfall", world, world.regions[0])
    other = await settlement(session, "Dimmere", world, world.regions[1])
    folk = await people_of(session, world, home, other)
    sky = await entity(
        session, "The Pale Wanderer", EntityType.CELESTIAL, CelestialStats(brightness=10, influence=95, cycle=1, visibility=100), world_id=world.world.id
    )
    system = DivinationSystemRow(people_entity_id=folk.id, kind=DivinationKind.ASTROLOGY, locked=[])
    session.add(system)
    child = await mortal(session, "Wren", world, home.id, willpower=50)
    session.add(MortalProfileRow(entity_id=child.id, locked=[]))
    await session.flush()
    ctx = await at(session, 4, astrology={"dread_chance": 100, "foster_chance": 100})
    row = await sign_birth(ctx, child, SignTally())
    assert row.ruling_celestial_entity_id == sky.id and row.dreaded and row.influence is SignInfluence.REAL
    assert row.fortune < 0 and stat_or(child, "willpower", 0) < 50
    assert row.exposed and child.location_id == other.id
    profile = await session.get(MortalProfileRow, child.id)
    assert profile is not None and profile.infamy > 0
    assert await validity_of(ctx, system) is DivinationValidity.NATURAL_LAW
    stored = await session.get(BirthSignRow, child.id)
    assert stored is row


async def test_a_court_deep_in_magic_remakes_the_condemned_who_labour_and_rise(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Grimhold", world, world.regions[0])
    folk = await people_of(session, world, town)
    lore = await knowledge(session, world, "Deep Workings", KnowledgeBranch.MAGIC)
    await bond(session, folk.id, lore.id, BondKind.KNOWS)
    session.add(society(town.id, SocialClass.FARMER))
    convict = await mortal(session, "Tobin", world, town.id, charisma=60, agility=60, strength=40)
    await session.flush()
    ctx = await at(session, 3, punitive_remaking={"magic_floor": 1, "revolt_count": 1, "revolt_grievance": 10})
    assert await may_remake(ctx, town.id)
    row = await remake(ctx, convict, None)
    assert row.lost_function in {None, BodyFunction.SPEECH, BodyFunction.LOCOMOTION}
    tally = RemadeTally()
    await keep_remade(ctx, tally)
    revolt = await session.scalar(select(MovementRow).where(MovementRow.settlement_entity_id == town.id, MovementRow.act == CollectiveActKind.REVOLT))
    assert revolt is not None and tally.revolts == 1
    stored = await session.get(RemadeRow, convict.id)
    assert stored is row


async def test_a_deceitful_creative_rival_plots_a_forged_work(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Quillmere", world, world.regions[0])
    plotter = await mortal(session, "Mirelle", world, town.id, creativity=90)
    rival = await mortal(session, "Osric", world, town.id)
    session.add(TraitRow(node_id=plotter.id, trait=TraitKind.DECEITFUL, source=TraitSource.BIRTH, epoch=1))
    piece = await work(session, world, "Osric's Garden", rival, town)
    await session.flush()
    ctx = await at(session, 3)
    assert await choose_kind(ctx, plotter, rival) is PlotKind.FORGE_WORK
    told = await forge_work(ctx, SchemeRow(owner_node_id=plotter.id, kind=PlotKind.FORGE_WORK, target_node_id=rival.id), plotter, rival)
    row = await session.scalar(select(ForgeryRow).where(ForgeryRow.forger_entity_id == plotter.id))
    assert row is not None and row.original_entity_id == piece.id and "forgery" in told


async def test_integrity_withdraws_bounties_on_vanished_beasts_and_frees_their_hunters(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Marrow", world, world.regions[0])
    hunter = await mortal(session, "Pell", world, town.id)
    beast = await entity(session, "The Old Tusk", EntityType.BEAST, BeastStats(hp=40), world_id=world.world.id, location_id=world.regions[0].id)
    gone = MonsterContractRow(community_entity_id=town.id, beast_entity_id=beast.id, hunter_entity_id=hunter.id, status=ContractStatus.TAKEN, locked=[])
    session.add(gone)
    beast.status, beast.end_epoch = EntityStatus.DEAD, 3
    await session.flush()
    assert await mend_arts_links(session, 4) >= 1
    await session.refresh(gone)
    assert gone.status is ContractStatus.WITHDRAWN and gone.closed_epoch == 4


async def test_mortals_and_gods_read_their_works_constructs_bounties_and_signs_in_context(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Readwell", world, world.regions[0])
    maker = await mortal(session, "Ilsa", world, town.id)
    ctx = await at(session, 2)
    await make_construct(ctx, maker, Design(material=MaterialKind.STONE, source=MagicSource.LEY, token=CommandToken.WORD))
    session.add(BirthSignRow(mortal_entity_id=maker.id, dreaded=True, influence=SignInfluence.BELIEVED, locked=[]))
    await session.flush()
    scope = await load_scope(session, tuned_rules())
    lines = await mortal_arts_lines(scope, maker)
    assert any("answers you" in line for line in lines) and any("dreaded sign" in line for line in lines)
    world.son.current_world_id = world.world.id
    assert any("construct" in line for line in await son_arts_lines(scope, world.son))


async def test_the_values_a_canon_carries_pull_its_people_across_generations(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Loremere", world, world.regions[0])
    folk = await people_of(session, world, town)
    poet = await mortal(session, "Ysolde", world, town.id)
    piece = await work(session, world, "The Oathkeeper's Lay", poet, town)
    profile = await session.get(ArtworkProfileRow, piece.id)
    assert profile is not None
    profile.message = {"honour": 90}
    session.add(CanonWorkRow(people_entity_id=folk.id, artwork_entity_id=piece.id, path=CanonPath.RENOWN, weight=60, locked=[]))
    await write_values(session, ValueHolder.CULTURE, folk.id, {ValueAxis.HONOUR: 10})
    await session.flush()
    tally = MovementTally()
    await teach_canon(await at(session, 4, canon={"value_pull": 50}), tally)
    values = await stored_values(session, ValueHolder.CULTURE, folk.id)
    assert tally.taught == 1 and values[ValueAxis.HONOUR] == 50
