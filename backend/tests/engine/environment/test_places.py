from sqlalchemy import select

from aerona.catalog.place_terrain import PLACE_KINDS
from aerona.core.random import SeededRandom
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.warfare import BattleRow, WarRow
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType, MortalRole
from aerona.domain.enums.environment import PlaceCover, ScarKind, TerrainKind, WaterSource
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretKind, SecretOrigin
from aerona.domain.enums.war import BattleOutcome, WarCause, WarStatus
from aerona.domain.models.entity_stats import PlaceStats
from aerona.engine.cosmos.pilgrimage import holy_sites
from aerona.engine.environment.battleground import BattleGround, battle_site, cover_missile_pct, defend_factor
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.place_backfill import KIND_FIXUP, recorded_kind
from aerona.engine.environment.places import KindClues, SacredInputs, drift_toward, holy_place_ids, pilgrims_drawn, sacred_target, typed_kind, write_kind
from aerona.engine.environment.secrets import SecretDraft, find_chance, hide, miner_chance, reveal
from aerona.engine.phases.environment import environment_survey
from aerona.engine.phases.living_stats import reveal_by_mystery
from aerona.engine.phases.places import place_profiles, place_secrets
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.db.factories import seed_world
from tests.engine.environment.factories import mapped_region
from tests.engine.society.factories import Realm, context, make, mortal, settlement, store_map, tuned

RULES = Rules()


async def surveyed(realm: Realm) -> None:
    records = [mapped_region(realm.region.id, neighbours=[realm.far_region.id]), mapped_region(realm.far_region.id, neighbours=[realm.region.id])]
    await store_map(realm.session, realm.world.id, records)


async def place(realm: Realm, name: str, subtype: str | None = None, mystery: int = 10, **extra: object) -> int:
    row = await make(
        realm.session,
        name,
        EntityType.PLACE,
        PlaceStats(danger=10, fertility=50, mystery=mystery),
        world_id=realm.world.id,
        location_id=realm.region.id,
        subtype=subtype,
        **extra,
    )
    return row.id


def test_every_kind_has_a_complete_profile() -> None:
    assert set(PLACE_KINDS) == set(PlaceKind)
    assert all(spec.secrets for spec in PLACE_KINDS.values())


def test_the_recorded_subtype_is_read_once_by_the_fixup() -> None:
    assert recorded_kind("pass") is PlaceKind.PASS
    assert recorded_kind("haunted barrow") is PlaceKind.BURIAL_GROUND
    assert recorded_kind("strange thing") is None


async def test_existing_places_take_their_kind_once_and_new_places_read_typed_signs(realm: Realm) -> None:
    await surveyed(realm)
    old = await place(realm, "Old Pass", "pass")
    corpse = await place(realm, "Corpse", "pass", engine_kind=EngineKind.GOD_CORPSE)
    await environment_survey(context(realm.session))
    assert (await realm.session.get(PlaceProfileRow, old)).kind is PlaceKind.PASS
    assert (await realm.session.get(PlaceProfileRow, corpse)).kind is PlaceKind.PASS
    ground = await realm.session.get(PlaceEnvironmentRow, old)
    assert ground.chokepoint and ground.terrain is TerrainKind.HIGH_PASS
    assert await realm.session.get(AppliedFixupRow, KIND_FIXUP) is not None
    later = await place(realm, "Later Pass", "pass", engine_kind=EngineKind.GOD_CORPSE)
    await environment_survey(context(realm.session))
    assert (await realm.session.get(PlaceProfileRow, later)).kind is PlaceKind.GOD_CORPSE


def test_typed_signs_choose_a_kind_without_reading_prose() -> None:

    clues = KindClues(frozenset({7}), frozenset({8}), frozenset({9}))
    region = RegionEnvironmentRow(dominant_terrain=TerrainKind.MARSH)
    assert typed_kind(EntityRow(id=7, subtype="ruin"), None, region, clues) is PlaceKind.LAIR
    assert typed_kind(EntityRow(id=8), None, region, clues) is PlaceKind.RUIN
    assert typed_kind(EntityRow(id=9), None, region, clues) is PlaceKind.SHRINE_SITE
    assert typed_kind(EntityRow(id=10, subtype="cave"), None, region, clues) is PlaceKind.SWAMP


def test_sacredness_tends_toward_kind_temples_relics_and_nexus() -> None:
    table = RULES.places
    plain = sacred_target(RULES, PlaceKind.VALLEY, SacredInputs(0, 0, False, False))
    holy = sacred_target(RULES, PlaceKind.SHRINE_SITE, SacredInputs(1, 1, True, True))
    assert plain == table.sacred_profane_base
    assert holy == min(100, table.sacred_holy_base + table.sacred_per_temple + table.sacred_per_relic + table.sacred_pilgrimage_site + table.sacred_nexus)
    assert drift_toward(10, 40, 5) == 15 and drift_toward(40, 10, 5) == 35 and drift_toward(12, 14, 5) == 14
    assert pilgrims_drawn(RULES, table.pilgrimage_threshold - 1, 10000) == 0
    assert pilgrims_drawn(RULES, 100, 10000) == round(10000 * table.pilgrim_share_permille / 1000)


async def test_sacred_places_draw_pilgrims_and_hold_their_sacredness(realm: Realm) -> None:
    await surveyed(realm)
    shrine = await place(realm, "Shrine")
    await environment_survey(context(realm.session))
    profile = await write_kind(realm.session, RULES, shrine, PlaceKind.SHRINE_SITE)
    profile.sacredness = 90
    town = await settlement(realm, "Pilgrim Town", population=8000, location_id=shrine)
    piety = stat(town, "piety") or 0
    await place_profiles(context(realm.session))
    assert profile.sacredness == 90 - RULES.places.sacred_drift
    assert profile.pilgrims > 0
    assert (stat(town, "piety") or 0) > piety
    profile.locked = ["sacredness"]
    profile.sacredness = 90
    await place_profiles(context(realm.session))
    assert profile.sacredness == 90


async def test_many_battles_turn_a_valley_into_a_battlefield(realm: Realm) -> None:
    await surveyed(realm)
    valley = await place(realm, "Red Vale")
    await environment_survey(context(realm.session))
    await write_kind(realm.session, RULES, valley, PlaceKind.VALLEY)
    first = await settlement(realm, "A")
    second = await settlement(realm, "B")
    war = WarRow(event_entity_id=first.id, world_id=realm.world.id, started_epoch=1, status=WarStatus.ONGOING, cause=WarCause.HOSTILITY)
    realm.session.add(war)
    await realm.session.flush()
    for index in range(RULES.places.battlefield_battles):
        realm.session.add(
            BattleRow(
                war_id=war.id,
                epoch=1,
                sequence=index,
                place_entity_id=valley,
                winner_entity_id=first.id,
                loser_entity_id=second.id,
                outcome=BattleOutcome.FIELD_VICTORY,
                gap=1.0,
            )
        )
    await realm.session.flush()
    await place_profiles(context(realm.session))
    assert (await realm.session.get(PlaceProfileRow, valley)).kind is PlaceKind.BATTLEFIELD


async def test_secrets_are_seeded_once_by_mystery(realm: Realm) -> None:
    await surveyed(realm)
    cave = await place(realm, "Deep Cave", mystery=100)
    await environment_survey(context(realm.session))
    await write_kind(realm.session, RULES, cave, PlaceKind.CAVE)
    rules = tuned(places={"secret_chance_pct": 100})
    await place_profiles(context(realm.session, rules))
    secrets = list(await realm.session.scalars(select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id == cave)))
    assert len(secrets) == 1 and secrets[0].kind in PLACE_KINDS[PlaceKind.CAVE].secrets
    await place_profiles(context(realm.session, rules))
    assert len(list(await realm.session.scalars(select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id == cave)))) == 1


def test_finding_and_digging_chances_follow_skill_mystery_strength_and_mining() -> None:
    table = RULES.places
    weak = find_chance(RULES, skill=0, mystery=0, strength=100, called=False)
    strong = find_chance(RULES, skill=100, mystery=100, strength=0, called=True)
    assert weak == 0.0
    assert strong == table.discover_cap_pct
    assert miner_chance(RULES, table.miner_mined_min - 1, 0) == 0.0
    assert miner_chance(RULES, 100, 0) == table.miner_pct


async def test_an_explorer_finds_a_buried_relic(realm: Realm) -> None:
    await surveyed(realm)
    ruin = await place(realm, "Old Ruin", mystery=100)
    await environment_survey(context(realm.session))
    await write_kind(realm.session, RULES, ruin, PlaceKind.RUIN)
    seeker = await mortal(realm, "Seeker", role=MortalRole.EXPLORER)
    ctx = context(realm.session, tuned(places={"discover_base_pct": 100, "discover_cap_pct": 100}))
    secret = hide(ctx, ruin, SecretDraft(SecretKind.BURIED_RELIC, 0), SecretOrigin.PLAYER)
    await realm.session.flush()
    await place_secrets(ctx)
    assert secret.revealed_epoch == ctx.epoch and secret.revealed_by is DiscoveryMode.EXPLORER and secret.revealed_by_entity_id == seeker.id
    assert secret.result_entity_id is not None


async def test_deep_mining_breaks_a_sealed_spirit_free(realm: Realm) -> None:
    await surveyed(realm)
    mine = await place(realm, "Old Mine")
    await environment_survey(context(realm.session))
    await write_kind(realm.session, RULES, mine, PlaceKind.MINE_SITE)
    region = await realm.session.get(RegionEnvironmentRow, realm.region.id)
    region.mined = 100
    await settlement(realm, "Miners")
    ctx = context(realm.session, tuned(places={"miner_pct": 100}))
    secret = hide(ctx, mine, SecretDraft(SecretKind.SEALED_SPIRIT, 0), SecretOrigin.LAND)
    await realm.session.flush()
    await place_secrets(ctx)
    assert secret.revealed_by is DiscoveryMode.MINER and not secret.sealed and secret.released_epoch == ctx.epoch
    assert region.scars.get(ScarKind.HAUNTED.value, 0) > 0


async def test_a_held_secret_stays_hidden(realm: Realm) -> None:
    await surveyed(realm)
    ruin = await place(realm, "Kept Ruin", mystery=100)
    await environment_survey(context(realm.session))
    await mortal(realm, "Seeker", role=MortalRole.EXPLORER)
    ctx = context(realm.session, tuned(places={"discover_base_pct": 100, "discover_cap_pct": 100}))
    secret = hide(ctx, ruin, SecretDraft(SecretKind.BURIED_RELIC, 0), SecretOrigin.PLAYER)
    secret.held = True
    await realm.session.flush()
    await place_secrets(ctx)
    assert secret.revealed_epoch is None


async def test_a_solved_mystery_reveals_a_lost_rite(realm: Realm) -> None:

    await surveyed(realm)
    grove = await place(realm, "Whisper Grove", mystery=80)
    await environment_survey(context(realm.session))
    seeker = await settlement(realm, "Seekers", location_id=grove)
    ctx = context(realm.session)
    secret = hide(ctx, grove, SecretDraft(SecretKind.LOST_RITE, 10, school=MagicSchool.LIFE), SecretOrigin.LAND)
    await realm.session.flush()
    assert await reveal_by_mystery(ctx, await realm.session.get(type(seeker), grove), seeker)
    assert secret.revealed_by is DiscoveryMode.MYSTERY and secret.result_entity_id is not None


async def test_a_found_seam_becomes_a_resource_and_a_mineral_layer(realm: Realm) -> None:

    await surveyed(realm)
    cliff = await place(realm, "Iron Cliff")
    await environment_survey(context(realm.session))
    region = await realm.session.get(RegionEnvironmentRow, realm.region.id)
    ctx = context(realm.session)
    secret = hide(ctx, cliff, SecretDraft(SecretKind.HIDDEN_RESOURCE, 70, material=MaterialKind.IRON), SecretOrigin.LAND)
    await realm.session.flush()
    resource = await reveal(ctx, secret, DiscoveryMode.PLAYER, None, region)
    assert resource is not None and resource.entity_type is EntityType.RESOURCE
    assert region.mineral_layers[MaterialKind.IRON.value] >= 70


async def test_chokepoints_draw_battles_and_cover_shelters_defenders(realm: Realm) -> None:
    await surveyed(realm)
    gorge = await place(realm, "Gorge")
    await environment_survey(context(realm.session))
    await write_kind(realm.session, RULES, gorge, PlaceKind.PASS)
    book = await EnvironmentBook.load(realm.session, RULES, 3)
    always = tuned(places={"chokepoint_battle_pct": 100})
    site = battle_site(always, book, realm.region.id, SeededRandom.for_epoch(1, 1, "site"))
    assert site is not None and site.entity_id == gorge
    assert battle_site(tuned(places={"chokepoint_battle_pct": 0}), book, realm.region.id, SeededRandom.for_epoch(1, 1, "site")) is None
    open_ground = PlaceEnvironmentRow(cover=PlaceCover.OPEN, height_advantage=0, chokepoint=False)
    forest = PlaceEnvironmentRow(cover=PlaceCover.HEAVY, height_advantage=0, chokepoint=False)
    assert defend_factor(RULES, BattleGround(place=forest)) > defend_factor(RULES, BattleGround(place=open_ground))
    assert cover_missile_pct(RULES, PlaceCover.HEAVY) < cover_missile_pct(RULES, PlaceCover.LIGHT) < cover_missile_pct(RULES, None)


async def test_holy_sites_count_nexus_and_sacred_places_of_the_world_only(realm: Realm) -> None:
    await surveyed(realm)
    nexus = await place(realm, "Nexus")
    sacred = await place(realm, "Sacred Spring")
    await environment_survey(context(realm.session))
    ground = await realm.session.get(PlaceEnvironmentRow, nexus)
    ground.nexus = True
    (await realm.session.get(PlaceProfileRow, sacred)).sacredness = 95
    other_world: WorldRow = await seed_world(realm.session, name="Elsewhere", star_name="Elsewhere Sun")
    stranger = await make(realm.session, "Far Nexus", EntityType.PLACE, PlaceStats(), world_id=other_world.id)
    realm.session.add(PlaceProfileRow(entity_id=stranger.id, kind=PlaceKind.NEXUS, sacredness=100, pilgrims=0, secrets_seeded=True, locked=[]))
    realm.session.add(
        PlaceEnvironmentRow(entity_id=stranger.id, cover=PlaceCover.OPEN, water_source=WaterSource.NONE, height_advantage=0, soil_fertility=50, nexus=True)
    )
    await realm.session.flush()
    ids = await holy_place_ids(realm.session, RULES, realm.world.id)
    assert ids == [sacred, nexus]
    assert [site.id for site in await holy_sites(realm.session, realm.world.id, None, RULES)] == [sacred, nexus]
    await add_flag(realm.session, stranger.id, EntityFlag.PILGRIMAGE_SITE, 1)
    assert stranger.id not in [site.id for site in await holy_sites(realm.session, realm.world.id, None, RULES)]


async def test_a_son_can_hold_a_place_kind_against_battles(realm: Realm) -> None:
    await surveyed(realm)
    valley = await place(realm, "Held Vale")
    await environment_survey(context(realm.session))
    profile = await write_kind(realm.session, RULES, valley, PlaceKind.VALLEY)
    profile.locked = ["kind"]
    await place_profiles(context(realm.session, tuned(places={"battlefield_battles": 1})))
    assert profile.kind is PlaceKind.VALLEY
