from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.collective import ArmsRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.crafts import GameRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kind_crafts import (
    ColourMeaningRow,
    ColourTermRow,
    EmblemSystemRow,
    FurnishingKindRow,
    GarmentKindRow,
    InstrumentKindRow,
    MusicTraditionRow,
    ScentKindRow,
    SubstanceKindRow,
    ToolKindRow,
)
from aerona.db.tables.kinds import KindHoldingRow, KindRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import HeraldryHolderKind, Tincture
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import MishapKind
from aerona.domain.enums.kind_crafts import (
    ColourFocus,
    ColourMeaning,
    EmblemSystem,
    FurnishingCategory,
    GameCategory,
    GarmentCategory,
    InstrumentCategory,
    MusicForm,
    ScentUse,
    SubstanceCategory,
    ToolCategory,
)
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.crafts.games import GameTally, keep_games, made_by, shaped
from aerona.engine.fortune.everyday import kinds_for, rate_of
from aerona.engine.kinds.crafts_life import HERALDRY_FIXUP, exposure_of, furnishing_worth, keep_crafts_of_life
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "kind_crafts", rules=tuned_rules(**rules))


async def town_of(session: AsyncSession, world: CoreWorld, name: str) -> tuple[EntityRow, SettlementProfileRow]:
    town = await settlement(session, name, world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=40, crime=10, sanitation=30, fire_risk=20, prestige=10)
    session.add(profile)
    await session.flush()
    return town, profile


async def hold(session: AsyncSession, concept: KindConcept, kind: KindRow, holder: int, stance: KindStance = KindStance.USES) -> None:
    kind.locked = []
    session.add(kind)
    await session.flush()
    session.add(KindHoldingRow(concept=concept, kind_id=kind.id, holder_node_id=holder, stance=stance, strength=100, locked=[]))
    await session.flush()


async def realm_over(session: AsyncSession, world: CoreWorld, town: EntityRow) -> EntityRow:
    realm = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    await session.flush()
    return realm


async def test_household_goods_and_substances_shape_the_towns_of_their_holders(session: AsyncSession, world: CoreWorld) -> None:
    _, profile = await town_of(session, world, "Brightwell")
    people = world.people.id
    await hold(session, KindConcept.FURNISHING, FurnishingKindRow(name="Washstand", category=FurnishingCategory.SANITATION, comfort=80), people)
    await hold(
        session, KindConcept.SUBSTANCE, SubstanceKindRow(name="Leafchew", category=SubstanceCategory.STIMULANT, potency=80, dependence=80, harm=0), people
    )
    await hold(session, KindConcept.SCENT, ScentKindRow(name="Hearthsmoke", category=ScentUse.BURNED, trade_value=500, rite_weight=0), people, KindStance.MAKES)
    unrest, crime, sanitation, treasury = profile.unrest, profile.crime, profile.sanitation, profile.treasury
    tally = await keep_crafts_of_life(await at(session, 2))
    assert tally.towns == 1
    assert profile.sanitation > sanitation and profile.unrest < unrest and profile.crime > crime and profile.treasury > treasury


async def test_tools_music_instruments_and_emblems_each_reach_the_town(session: AsyncSession, world: CoreWorld) -> None:
    town, profile = await town_of(session, world, "Toolmere")
    people = world.people.id
    prosperity = stat(town, "prosperity")
    await hold(session, KindConcept.TOOL, ToolKindRow(name="Fine adze", category=ToolCategory.CRAFTING, craft_bonus=100, quality=100, wear=0), people)
    await hold(session, KindConcept.TOOL, ToolKindRow(name="Firebow", category=ToolCategory.FIRE_MAKING, craft_bonus=0, quality=100, wear=0), people)
    await hold(session, KindConcept.EMBLEM_SYSTEM, EmblemSystemRow(name="House marks", category=EmblemSystem.MARK, legibility=100), people)
    await hold(
        session, KindConcept.MUSIC_TRADITION, MusicTraditionRow(name="Round chant", category=MusicForm.CHORUS, rite_weight=100, ensemble_size=40), people
    )
    await hold(session, KindConcept.INSTRUMENT, InstrumentKindRow(name="Long horn", category=InstrumentCategory.WIND, loudness=100), people)
    order, fire, unrest = profile.public_order, profile.fire_risk, profile.unrest
    await keep_crafts_of_life(await at(session, 2))
    assert stat(town, "prosperity") > (prosperity or 0)
    assert profile.public_order > order and profile.fire_risk < fire and profile.unrest < unrest


async def test_the_dyed_rank_a_rare_colour_is_restricted_smuggled_and_torn_down(session: AsyncSession, world: CoreWorld) -> None:
    town, profile = await town_of(session, world, "Dyegate")
    realm = await realm_over(session, world, town)
    colour = ColourTermRow(name="Deepshade", category=ColourFocus.PURPLE, rarity=90, prestige=0)
    await hold(session, KindConcept.COLOUR_TERM, colour, world.people.id)
    profile.unrest = 10
    first = await keep_crafts_of_life(await at(session, 2))
    assert colour.prestige >= 60 and first.restricted == 1
    restriction = await session.scalar(
        select(KindHoldingRow).where(
            KindHoldingRow.holder_node_id == realm.id, KindHoldingRow.kind_id == colour.id, KindHoldingRow.stance == KindStance.FORBIDS
        )
    )
    meaning = await session.scalar(select(ColourMeaningRow).where(ColourMeaningRow.culture_node_id == realm.id))
    assert restriction is not None and meaning is not None and meaning.meaning is ColourMeaning.RANK
    crime, unrest = profile.crime, profile.unrest
    second = await keep_crafts_of_life(await at(session, 3))
    assert second.smuggled == 1 and profile.crime > crime and profile.unrest > unrest
    profile.unrest = 90
    third = await keep_crafts_of_life(await at(session, 4))
    gone = await session.scalar(
        select(KindHoldingRow).where(
            KindHoldingRow.holder_node_id == realm.id, KindHoldingRow.kind_id == colour.id, KindHoldingRow.stance == KindStance.FORBIDS
        )
    )
    assert third.repealed == 1 and gone is None


async def test_a_forbidden_substance_and_fine_dress_under_a_sumptuary_law_breed_crime(session: AsyncSession, world: CoreWorld) -> None:
    town, profile = await town_of(session, world, "Lawmarch")
    realm = await realm_over(session, world, town)
    ctx = await at(session, 2)
    await enact(ctx, realm, LawKind.SUMPTUARY, {"noble_luxury": 60, "merchant_luxury": 20})
    leaf = SubstanceKindRow(name="Dreamleaf", category=SubstanceCategory.HALLUCINOGEN, potency=0, dependence=0, harm=0, rite_weight=0)
    await hold(session, KindConcept.SUBSTANCE, leaf, world.people.id)
    session.add(KindHoldingRow(concept=KindConcept.SUBSTANCE, kind_id=leaf.id, holder_node_id=realm.id, stance=KindStance.FORBIDS, locked=[]))
    robe = GarmentKindRow(name="High robe", category=GarmentCategory.OUTER_LAYER, status_signal=90, prestige=0)
    await hold(session, KindConcept.GARMENT, robe, world.people.id)
    crime = profile.crime
    tally = await keep_crafts_of_life(await at(session, 2))
    assert tally.forbidden_use == 1 and tally.fine_dress == 1 and profile.crime > crime


async def test_dress_tools_and_violent_games_set_the_everyday_mishap_exposure(session: AsyncSession, world: CoreWorld) -> None:
    people = world.people
    ctx = await at(session, 3)
    bare = await exposure_of(ctx, people.id)
    assert not bare.dressed and rate_of(ctx, LifeStage.ADULT, None, 50, bare) == rate_of(ctx, LifeStage.ADULT, None, 50)
    await hold(session, KindConcept.GARMENT, GarmentKindRow(name="Thin wrap", category=GarmentCategory.BODY_WRAP, warmth=10), people.id)
    await hold(session, KindConcept.TOOL, ToolKindRow(name="Loose blade", category=ToolCategory.CUTTING, wear=80), people.id)
    brawl = shaped("Pitfight", GameCategory.COMBAT_SPORT, people, 1)
    await hold(session, KindConcept.GAME, brawl, people.id)
    exposed = await exposure_of(ctx, people.id)
    assert exposed.dressed and exposed.warmth == 10 and exposed.wear == 80 and exposed.violence == brawl.violence
    assert rate_of(ctx, LifeStage.ADULT, None, 50, exposed) > rate_of(ctx, LifeStage.ADULT, None, 50, bare)
    assert MishapKind.SPORT in kinds_for(LifeStage.ADULT, None, True, exposed) and MishapKind.TOOL in kinds_for(LifeStage.ADULT, None, False, exposed)


async def test_a_people_invents_a_game_as_a_kind_and_crowds_ease_unrest(session: AsyncSession, world: CoreWorld) -> None:
    _, profile = await town_of(session, world, "Crowdholm")
    tally = GameTally()
    await keep_games(await at(session, 2, games={"invent_chance": 100}), tally)
    game = await session.scalar(select(GameRow).where(GameRow.origin_node_id == world.people.id))
    holding = await session.scalar(select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.GAME, KindHoldingRow.holder_node_id == world.people.id))
    assert tally.invented == 1 and game is not None and holding is not None and holding.stance is KindStance.MAKES
    spectacle = shaped("Great show", GameCategory.SPECTACLE, world.people, 2)
    session.add(spectacle)
    await session.flush()
    show = made_by(spectacle, world.people.id, 2)
    show.strength = 100
    session.add(show)
    await session.flush()
    unrest = profile.unrest
    await keep_games(await at(session, 3, games={"invent_chance": 0}), tally)
    assert profile.unrest < unrest and tally.played >= 1


async def test_a_household_sells_a_furnishing_for_what_its_people_value_it_at(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    assert await furnishing_worth(ctx, world.people.id) == 0
    chest = FurnishingKindRow(name="Carved chest", category=FurnishingCategory.STORAGE, cost=400)
    await hold(session, KindConcept.FURNISHING, chest, world.people.id)
    assert await furnishing_worth(ctx, world.people.id) == 400


async def test_a_fashionable_garment_wears_thin_when_everyone_wears_it_and_its_hold_loosens(session: AsyncSession, world: CoreWorld) -> None:
    fad = GarmentKindRow(name="Bright sash", category=GarmentCategory.ORNAMENT, fashion=100, novelty=30)
    staple = GarmentKindRow(name="Plain wrap", category=GarmentCategory.BODY_WRAP, fashion=0, novelty=30)
    await hold(session, KindConcept.GARMENT, fad, world.people.id)
    await hold(session, KindConcept.GARMENT, staple, world.people.id)
    holdings = {row.kind_id: row for row in await session.scalars(select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.GARMENT))}
    for row in holdings.values():
        row.strength = 50
    await keep_crafts_of_life(await at(session, 2, fashion={"saturation": 1, "drain": 20, "recovery": 10}))
    assert fad.novelty < 30 and staple.novelty == 30
    assert holdings[fad.id].strength < 50 and holdings[staple.id].strength == 50


async def test_a_rare_fashionable_garment_regains_its_pull_and_comes_back(session: AsyncSession, world: CoreWorld) -> None:
    fad = GarmentKindRow(name="Long veil", category=GarmentCategory.HEAD, fashion=100, novelty=45)
    await hold(session, KindConcept.GARMENT, fad, world.people.id)
    for name in ("Barehold", "Plainmoor", "Lowfield"):
        await settlement(session, name, world, world.regions[0])
    tally = await keep_crafts_of_life(await at(session, 2, fashion={"saturation": 100, "recovery": 20, "drain": 0, "revival_floor": 50}))
    assert fad.novelty > 50 and tally.revived == 1


async def test_heraldry_becomes_the_built_in_emblem_system_and_every_arms_bearer_uses_it(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await town_of(session, world, "Armsford")
    realm = await realm_over(session, world, town)
    other = await realm_over(session, world, await settlement(session, "Farhold", world, world.regions[0]))
    session.add(ArmsRow(holder_entity_id=realm.id, holder_kind=HeraldryHolderKind.POLITY, field=Tincture.RED, since_epoch=1, locked=[]))
    session.add(ArmsRow(holder_entity_id=other.id, holder_kind=HeraldryHolderKind.POLITY, field=Tincture.BLUE, since_epoch=1, locked=["emblem_system_id"]))
    await session.flush()
    tally = await keep_crafts_of_life(await at(session, 2))
    system = await session.scalar(select(EmblemSystemRow).where(EmblemSystemRow.built_in.is_(True)))
    assert system is not None and system.category is EmblemSystem.HERALDRY
    arms = await session.get(ArmsRow, realm.id)
    kept = await session.get(ArmsRow, other.id)
    assert arms is not None and arms.emblem_system_id == system.id and tally.arms_linked == 1
    assert kept is not None and kept.emblem_system_id is None
    used = await session.scalar(select(KindHoldingRow).where(KindHoldingRow.holder_node_id == realm.id, KindHoldingRow.kind_id == system.id))
    assert used is not None and used.concept is KindConcept.EMBLEM_SYSTEM
    assert await session.get(AppliedFixupRow, HERALDRY_FIXUP) is not None
    await session.delete(system)
    await session.flush()
    await keep_crafts_of_life(await at(session, 3))
    assert await session.scalar(select(EmblemSystemRow).where(EmblemSystemRow.built_in.is_(True))) is None
