from typing import Any

from aerona.catalog.rarities import entity_power_band, entity_rarity
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.rarity import RARITY_ORDER
from aerona.domain.models.entity_stats import BeastStats, MortalStats
from aerona.rules.registry import Rules
from tests.api.conftest import ApiWorld, seeded

TOP_POWER_LEVEL = 40


async def add_characters(api: ApiWorld) -> dict[str, int]:
    core = seeded(api).core
    made: dict[str, int] = {}
    async with api.services.database.write() as session:
        entities = EntityRepository(session)
        for name, entity_type, stats, power, status in (
            ("Ilvane Ostrey", EntityType.MORTAL, MortalStats(hp=40, strength=55, agility=30), 1, EntityStatus.CANON),
            ("Corran Vey", EntityType.MORTAL, MortalStats(hp=90, strength=80, agility=70), 12, EntityStatus.CANON),
            ("The Pale Grazer", EntityType.BEAST, BeastStats(hp=200, danger=70, strength=90), 6, EntityStatus.DEAD),
        ):
            row = await entities.create(
                EntityDraft(
                    name=name,
                    entity_type=entity_type,
                    description=f"{name} walks the first region.",
                    stats=stats,
                    power_level=power,
                    origin=EntityOrigin.SON,
                    birth_epoch=1,
                    world_id=core.world.id,
                    location_id=core.regions[0].id,
                    creator_son_id=core.son.id,
                    split_title=False,
                )
            )
            row.status = status
            if status is EntityStatus.DEAD:
                row.end_epoch = 1
            made[name] = row.id
    return made


async def cards(api: ApiWorld, **params: Any) -> dict[str, Any]:
    response = await api.http.get("/api/cards", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_every_character_has_a_card_with_the_gods_leading(api: ApiWorld) -> None:
    made = await add_characters(api)
    core = seeded(api).core
    deck = await cards(api, limit=200)
    items = deck["items"]
    assert items[0]["node_kind"] == "creator"
    assert items[0]["headline"][0]["key"] == "essence"
    son = next(item for item in items if item["node_id"] == core.son.id)
    assert son["rarity"] == core.son.rarity.value
    assert (son["level"], son["xp"]) == (core.son.level, core.son.xp)
    assert [line["key"] for line in son["headline"]] == ["might", "hp"]
    assert {line["key"] for line in son["stats"]} >= {"strength", "wisdom", "hp", "essence", "existence"}
    mortal = next(item for item in items if item["node_id"] == made["Corran Vey"])
    assert mortal["entity_type"] == "mortal"
    assert mortal["power_level"] == 12
    assert [line["key"] for line in mortal["headline"]] == ["hp", "strength"]
    beast = next(item for item in items if item["node_id"] == made["The Pale Grazer"])
    assert beast["fallen"] is True
    assert beast["ended_epoch"] == 1
    kinds = [item["node_kind"] for item in items]
    assert kinds.index("entity") > max(index for index, kind in enumerate(kinds) if kind != "entity")
    assert core.people.id not in {item["node_id"] for item in items}
    totals = {(row["node_kind"], row["entity_type"]): row["total"] for row in deck["decks"]}
    assert totals[("entity", "mortal")] >= 2
    assert totals[("son", None)] >= 1


async def test_cards_filter_by_deck_rarity_world_state_and_name(api: ApiWorld) -> None:
    made = await add_characters(api)
    mythic = entity_rarity(Rules(), 12).value
    found = await cards(api, entity_type="mortal", rarity=mythic)
    assert [item["node_id"] for item in found["items"]] == [made["Corran Vey"]]
    tiers = {row["rarity"]: row["total"] for row in found["rarities"]}
    assert list(tiers) == [rarity.value for rarity in RARITY_ORDER]
    assert tiers[mythic] == 1
    assert tiers[entity_rarity(Rules(), 1).value] >= 1
    sons = await cards(api, node_kind="son")
    assert sons["items"] and {item["node_kind"] for item in sons["items"]} == {"son"}
    living = await cards(api, entity_type="beast", fallen="false")
    assert made["The Pale Grazer"] not in {item["node_id"] for item in living["items"]}
    named = await cards(api, q="ostrey")
    assert [item["node_id"] for item in named["items"]] == [made["Ilvane Ostrey"]]
    elsewhere = await cards(api, world_id=999999)
    assert elsewhere["total"] == 0
    assert (await api.http.get("/api/cards", params={"limit": 0})).status_code == 400


async def test_card_pages_run_across_gods_and_mortals_without_gaps(api: ApiWorld) -> None:
    await add_characters(api)
    whole = await cards(api, limit=200, order="name")
    ids = [item["node_id"] for item in whole["items"]]
    paged: list[int] = []
    for offset in range(0, whole["total"], 2):
        paged += [item["node_id"] for item in (await cards(api, offset=offset, limit=2, order="name"))["items"]]
    assert paged == ids
    assert len(set(ids)) == len(ids) == whole["total"]


def test_power_bands_hold_exactly_the_levels_of_their_rarity() -> None:
    rules = Rules()
    for rarity in RARITY_ORDER:
        low, high = entity_power_band(rules, rarity)
        top = TOP_POWER_LEVEL if high is None else high
        levels = {level for level in range(1, TOP_POWER_LEVEL + 1) if entity_rarity(rules, level) is rarity}
        assert levels == set(range(low, top + 1))
