import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from aerona.domain.enums.entity import EntityFlag
from aerona.migration.legacy.vocabulary import Vocabulary

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
OTHER_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x01" * 64


class LegacyFixture:
    def __init__(self, directory: Path, vocabulary: Vocabulary) -> None:
        self.directory = directory
        self.vocabulary = vocabulary
        self.path = directory / vocabulary.database_file
        self.images = directory / vocabulary.image_directory
        directory.mkdir(parents=True, exist_ok=True)
        self.images.mkdir(exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            for table in vocabulary.tables.values():
                columns = ", ".join(f'"{column}"' for column in table.columns.values())
                connection.execute(f'CREATE TABLE "{table.name}" ({columns})')
            connection.commit()

    def enum(self, name: str, english: str) -> str:
        return self.vocabulary.encode(name, english)

    def code(self, kind: str) -> str:
        return self.vocabulary.code(kind)

    def tag(self, prefix: str, value: object) -> str:
        return f"{self.vocabulary.prefix(prefix)}:{value}"

    def flag(self, flag: EntityFlag) -> str:
        return next(legacy for legacy, english in self.vocabulary.tags.flags.items() if english == flag.value)

    def engine_subtype(self, entity_type: str, engine_kind: str) -> str:
        return next(legacy for legacy, english in self.vocabulary.engine_kinds[entity_type].items() if english == engine_kind)

    def blob(self, shape: str, **values: Any) -> str:
        return json.dumps({self.vocabulary.key(shape, key): value for key, value in values.items()}, ensure_ascii=False)

    def stats(self, entity_type: str, **values: int) -> dict[str, int]:
        table = self.vocabulary.entity_stats[entity_type]
        extras = self.vocabulary.entity_extra_stats
        found: dict[str, int] = {}
        for english, value in values.items():
            legacy = next((key for key, name in table.items() if name == english), None) or next(key for key, name in extras.items() if name == english)
            found[legacy] = value
        return found

    def keyed(self, enum_name: str, **values: Any) -> dict[str, Any]:
        return {self.enum(enum_name, key): value for key, value in values.items()}

    def insert(self, table: str, **values: Any) -> None:
        spec = self.vocabulary.table(table)
        encoded = {
            spec.physical(column): json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for column, value in values.items()
        }
        columns = ", ".join(f'"{column}"' for column in encoded)
        marks = ", ".join("?" for _ in encoded)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(f'INSERT INTO "{spec.name}" ({columns}) VALUES ({marks})', tuple(encoded.values()))
            connection.commit()

    def image_file(self, name: str, data: bytes) -> None:
        (self.images / name).write_bytes(data)

    def thumbnail(self, name: str) -> None:
        folder = self.images / self.vocabulary.thumbnail_directory / "160"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(PNG_BYTES)


def rule_key_for(vocabulary: Vocabulary, target: str) -> str:
    return next(legacy for legacy, path in vocabulary.rules.items() if path == target)


def son_stats(fixture: LegacyFixture, value: int) -> dict[str, int]:
    return fixture.keyed("son_stat", **{stat: value for stat in fixture.vocabulary.enums["son_stat"].values()})


def build_world(fixture: LegacyFixture) -> dict[str, int]:
    vocabulary = fixture.vocabulary
    entity, son, creator = fixture.code("entity"), fixture.code("son"), fixture.code("creator")
    threshold = rule_key_for(vocabulary, "balance.apocalypse_threshold")
    fixture.insert(
        "world_state",
        id=1,
        name="Orbis",
        creator_name="Maker",
        seed_idea="Light first",
        cosmology="A quiet sky.",
        naming_rule="Soft names.",
        tone="calm",
        epoch=5,
        year=200,
        creator_essence=120,
        fate_mode=fixture.enum("fate_mode", "auto"),
        rule_overrides={threshold: 500, "UNKNOWN.key": 3},
        creator_mood=fixture.keyed("creator_mood_axis", contentment=60, anger=10, interest=70, loneliness=20),
        creator_passions=fixture.blob("creator_passions", passions=[fixture.enum("creator_passion", "mercy")], automatic=True),
    )
    fixture.insert("stars", id=1, name="Sol", kind=fixture.enum("star_type", "yellow_dwarf"), brightness=70, x=0, y=0, created_epoch=1)
    terrain = fixture.blob("terrain", sea=0.5, mountains=1.0, humidity=0.0)
    climate = fixture.blob("climate", era=fixture.enum("climate_era", "rain"), left=2, since=4)
    fixture.insert(
        "worlds", id=1, name="Orbis", world_type=fixture.enum("world_type", "ordinary"), star_id=1, seed="Orbis", terrain=terrain, climate=climate, danger=20
    )
    fixture.insert("worlds", id=2, name="Umbra", world_type=fixture.enum("world_type", "dead"), star_id=1, seed="Umbra", terrain=terrain, danger=40)
    for son_id, name, rarity in ((1, "Avel", "rare"), (2, "Borun", "common")):
        fixture.insert(
            "sons",
            id=son_id,
            name=name,
            title="the First",
            rarity=fixture.enum("rarity", rarity),
            domain_primary=fixture.enum("domain", "sea"),
            domain_secondary=fixture.enum("domain", "fire"),
            personality=fixture.blob("personality", appearance="tall"),
            stats=son_stats(fixture, 40),
            passions=fixture.keyed("passion", loyalty=50, ambition=50, wrath=20, mercy=30),
            hp=50,
            essence=30,
            status=fixture.enum("son_status", "active"),
            birth_epoch=1,
            current_world=1,
            powers=[{vocabulary.key("power", "name"): "Tide", vocabulary.key("power", "effect"): fixture.enum("power_effect", "essence_spring")}],
            reputation=fixture.blob("reputation", love=40, fear=10, label=fixture.enum("reputation_label", "loved")),
        )
    fixture.insert("son_relations", son_a=1, son_b=2, value=30, note="kin")
    fixture.insert(
        "foreign_gods",
        id=1,
        name="Elder",
        domains=f"{fixture.enum('domain', 'stone')}{vocabulary.texts.domain_separator}{fixture.enum('domain', 'sun')}",
        world_id=2,
        power=60,
        status=fixture.enum("foreign_god_status", "asleep"),
        created_epoch=1,
        powers=[{vocabulary.key("power", "name"): "Ward", vocabulary.key("power", "effect"): fixture.enum("foreign_god_power", "shield")}],
    )
    water = vocabulary.patterns.water.split("|")[0]
    society = {
        vocabulary.key("society", "shares"): fixture.keyed("social_class", farmer=50, artisan=10, merchant=10, priest=10, warrior=10, scribe=10),
        vocabulary.key("society", "stocks"): fixture.keyed("commodity", food=300, ore=20, goods=40),
    }
    signature = vocabulary.json_keys["signature"]
    separators = vocabulary.json_keys["signature_separators"]
    imza = separators["pair"].join(
        f"{signature[key]}{separators['assignment']}{value}"
        for key, value in (("consonants", "lmn"), ("cluster", "ln"), ("ending", "el"), ("length_bias", "1"))
    )
    rows: list[dict[str, Any]] = [
        {"id": 10, "name": "Greatland", "entity_type": "region", "stats": fixture.stats("region", breadth=50), "map_position": [1500, 1000]},
        {"id": 11, "name": "Bluewater", "entity_type": "region", "subtype": water},
        {
            "id": 12,
            "name": "Northfolk",
            "entity_type": "people",
            "location_id": 10,
            "tags": [fixture.tag("tier", 2), fixture.tag("syncretic", 2)],
            "society": society,
        },
        {"id": 13, "name": "Southfolk", "entity_type": "people", "location_id": 10},
        {"id": 14, "name": "Hamlet", "entity_type": "settlement", "location_id": 10},
        {"id": 15, "name": "Hamlet", "entity_type": "place", "location_id": 10},
        {"id": 16, "name": "Ola", "entity_type": "mortal", "location_id": 14, "origin": "mortal", "maker_id": 12, "tags": ["harbor"]},
        {
            "id": 17,
            "name": "Long War",
            "entity_type": "event",
            "subtype": fixture.engine_subtype("event", "war"),
            "tags": [vocabulary.tags.war_ongoing, fixture.tag("side", 12), fixture.tag("side", 13)],
            "stats": {**fixture.stats("event", severity=60), **fixture.stats("event", war_score=2, war_battles=3, war_start=3)},
        },
        {"id": 18, "name": "North Army", "entity_type": "army", "tags": [fixture.tag("side", 12), fixture.tag("war", 17)], "location_id": 10},
        {
            "id": 19,
            "name": "Speech",
            "entity_type": "language",
            "tags": [fixture.tag("signature", imza), fixture.tag("script", fixture.enum("writing_system", "alphabet"))],
        },
        {
            "id": 20,
            "name": "Lore",
            "entity_type": "knowledge",
            "tags": [fixture.tag("branch", fixture.enum("knowledge_branch", "writing")), fixture.flag(EntityFlag.LOST)],
        },
        {"id": 21, "name": "Beast", "entity_type": "species", "tags": [fixture.tag("trait", fixture.enum("creature_trait", "flying")), "mystery:thing"]},
        {"id": 22, "name": "Gone", "entity_type": "mortal", "status": "rejected", "location_id": 14},
    ]
    for row in rows:
        legacy_type = fixture.enum("entity_type", row.pop("entity_type"))
        status = fixture.enum("entity_status", row.pop("status", "canon"))
        origin = fixture.enum("entity_origin", row.pop("origin", "creator"))
        fixture.insert(
            "entities",
            entity_type=legacy_type,
            status=status,
            origin=origin,
            description=f"About {row['name']}.",
            birth_epoch=2,
            world_id=1,
            power_level=2,
            tags=row.pop("tags", []),
            stats=row.pop("stats", {}),
            **row,
        )
    bond_rows = [
        (12, 13, "enemy", None, 1),
        (17, 12, "party_to", next(key for key, value in vocabulary.bond_roles["party_to"].items() if value == "side"), 1),
        (17, 13, "party_to", next(key for key, value in vocabulary.bond_roles["party_to"].items() if value == "side"), 1),
        (13, 12, "pays_tribute", None, 1),
        (12, 16, "holds_captive", "Long War", 1),
        (13, 12, "owes", vocabulary.texts.debt_format.format(amount=40, what="grain", due=7), 1),
        (12, 14, "truce", vocabulary.texts.truce_format.format(reason="calm", until=8), 0),
        (12, 19, "speaks", None, 1),
        (12, 19, "speaks", None, 1),
        (16, 22, "loves", None, 1),
    ]
    for index, (source, target, kind, description, active) in enumerate(bond_rows, start=1):
        fixture.insert(
            "bonds",
            id=index,
            source_kind=entity,
            source_id=source,
            target_kind=entity,
            target_id=target,
            kind=fixture.enum("bond_kind", kind),
            description=description,
            epoch=3,
            active=active,
        )
    fixture.insert(
        "bonds", id=50, source_kind=entity, source_id=12, target_kind=son, target_id=1, kind=fixture.enum("bond_kind", "worships"), epoch=2, active=1
    )
    fixture.insert(
        "bonds", id=51, source_kind=entity, source_id=13, target_kind=creator, target_id=None, kind=fixture.enum("bond_kind", "worships"), epoch=2, active=1
    )
    fixture.insert(
        "bonds", id=52, source_kind=entity, source_id=99, target_kind=entity, target_id=12, kind=fixture.enum("bond_kind", "related"), epoch=2, active=1
    )
    for chronicle_id in range(1, 4):
        fixture.insert(
            "chronicle", id=chronicle_id, epoch=chronicle_id, kind=fixture.enum("chronicle_kind", "world"), text=f"Line {chronicle_id}", entity_ids=[12, 13]
        )
    fixture.insert("chronicle", id=4, epoch=4, kind=fixture.enum("chronicle_kind", "engine_raw"), text="Raw", entity_ids=[17])
    fixture.insert("epochs", epoch=1, name="Dawn", narrative="It began.", year_start=0, year_end=50)
    fixture.insert("threads", id=1, epoch=2, text="A hook", related=[12], status=fixture.enum("thread_status", "open"))
    fixture.insert(
        "lexicon",
        id=1,
        language_id=19,
        word="lumen",
        meaning="light",
        part_of_speech=fixture.enum("part_of_speech", "noun"),
        added_by_kind=son,
        added_by_id=1,
        epoch=2,
    )
    fixture.insert("lexicon", id=2, language_id=19, word="Lumen", meaning="light again", epoch=2)
    fixture.insert("canon_facts", id=1, subject_id=12, predicate=next(iter(vocabulary.canon_predicates)), object_id=10, epoch=2, active=1)
    fixture.insert(
        "messages",
        id=1,
        epoch=3,
        sender_kind=son,
        sender_id=1,
        recipient_kind=creator,
        intent=fixture.enum("message_intent", "prayer"),
        text="Hear me",
        request="a free wish",
    )
    fixture.insert(
        "community_relations",
        entity_a=12,
        entity_b=13,
        value=-40,
        history=[
            {
                vocabulary.key("relation_history", "event"): "war",
                vocabulary.key("relation_history", "epoch"): 3,
                vocabulary.key("relation_history", "delta"): -5,
            }
        ],
    )
    fixture.insert(
        "routes", id=1, world_a=1, world_b=2, method=fixture.enum("travel_method", "ancient_gate"), duration=1, danger=20, known=1, created_epoch=2, active=1
    )
    fixture.insert("achievements", key=fixture.enum("achievement_key", "babel"), epoch=3)
    fixture.insert("images", id=1, target_kind=entity, target_id=12, file_name="a.png", mime="image/png", caption="Northfolk at dawn", cover=1)
    fixture.insert("images", id=2, target_kind=entity, target_id=13, file_name="b.png", mime="image/png", cover=0)
    fixture.insert("images", id=3, target_kind=son, target_id=1, file_name="c.png", mime="image/png", cover=1)
    fixture.image_file("a.png", PNG_BYTES)
    fixture.image_file("b.png", PNG_BYTES)
    fixture.image_file("c.png", OTHER_PNG_BYTES)
    fixture.thumbnail("a.webp")
    return {"entities": len(rows), "bonds": len(bond_rows) + 3, "chronicle": 4}
