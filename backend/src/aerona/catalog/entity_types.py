from collections.abc import Callable
from dataclasses import dataclass

from aerona.catalog.gates import creation_gate_rarity
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.rules.registry import Rules

PERCENT_MIN = 0
PERCENT_MAX = 100

RuleBound = Callable[[Rules], int]


@dataclass(frozen=True)
class StatField:
    key: str
    label: str
    minimum: int | RuleBound = PERCENT_MIN
    maximum: int | RuleBound | None = PERCENT_MAX

    def bounds(self, rules: Rules) -> tuple[int, int | None]:
        low = self.minimum(rules) if callable(self.minimum) else self.minimum
        high = self.maximum(rules) if callable(self.maximum) else self.maximum
        return low, high


@dataclass(frozen=True)
class EntityTypeSpec:
    type: EntityType
    label: str
    plural: str
    noun: str
    creation_tool: str | None
    containers: frozenset[EntityType]
    location_required: bool
    stats: tuple[StatField, ...]
    examples: tuple[str, ...]
    engine_kinds: frozenset[EngineKind] = frozenset()

    @property
    def placeable(self) -> bool:
        return bool(self.containers)

    def stat(self, key: str) -> StatField | None:
        return next((field for field in self.stats if field.key == key), None)


REGION, PLACE, SETTLEMENT = EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT
LAND = frozenset({REGION, PLACE})
INHABITED = frozenset({REGION, PLACE, SETTLEMENT})


def _percent(*pairs: tuple[str, str]) -> tuple[StatField, ...]:
    return tuple(StatField(key, label) for key, label in pairs)


ENTITY_TYPES: dict[EntityType, EntityTypeSpec] = {
    spec.type: spec
    for spec in (
        EntityTypeSpec(
            REGION,
            "Region",
            "Regions",
            "region",
            "create_region",
            frozenset({REGION}),
            False,
            _percent(("breadth", "Breadth"), ("danger", "Danger"), ("fertility", "Fertility"), ("magic", "Magic density")),
            ("continent", "inland sea", "desert belt", "archipelago", "underworld"),
        ),
        EntityTypeSpec(
            PLACE,
            "Place",
            "Places",
            "place",
            "create_place",
            LAND,
            True,
            _percent(("danger", "Danger"), ("fertility", "Fertility"), ("mystery", "Mystery")),
            ("mountain", "forest", "river", "lake", "cave", "ruin", "island", "swamp", "pass", "well"),
            frozenset({EngineKind.GOD_CORPSE}),
        ),
        EntityTypeSpec(
            EntityType.RESOURCE,
            "Resource",
            "Resources",
            "resource",
            "create_resource",
            LAND,
            True,
            _percent(("abundance", "Abundance"), ("value", "Value"), ("might", "Might")),
            ("ore vein", "magical substance", "healing herb", "sacred spring", "rare crystal", "bone bed"),
            frozenset({EngineKind.COSMIC_TRAVEL_RESOURCE}),
        ),
        EntityTypeSpec(
            SETTLEMENT,
            "Settlement",
            "Settlements",
            "settlement",
            "found_settlement",
            LAND,
            True,
            (
                StatField("population", "Population", lambda rules: rules.limits.population_floor, lambda rules: rules.limits.settlement_population_cap),
                StatField("prosperity", "Prosperity"),
                StatField("defense", "Defense"),
                StatField("piety", "Piety"),
                StatField("wealth", "Wealth"),
            ),
            ("village", "port city", "castle", "monastery", "nomad camp", "capital"),
            frozenset({EngineKind.COLONY}),
        ),
        EntityTypeSpec(
            EntityType.SPECIES,
            "Species",
            "Species",
            "species of creature",
            "create_species",
            LAND,
            False,
            (
                StatField("hp", "HP", 1, lambda rules: rules.limits.hp_cap),
                StatField("strength", "Strength"),
                StatField("agility", "Agility"),
                StatField("intelligence", "Intelligence"),
                StatField("danger", "Danger"),
                StatField("abundance", "Abundance"),
            ),
            ("animal", "plant", "fungus", "monster", "spirit species"),
            frozenset({EngineKind.GOLEM, EngineKind.CHIMERA}),
        ),
        EntityTypeSpec(
            EntityType.PEOPLE,
            "People",
            "Peoples",
            "people",
            "create_people",
            LAND,
            True,
            (
                StatField("population", "Population", lambda rules: rules.limits.people_population_floor, lambda rules: rules.limits.people_population_cap),
                StatField("martiality", "Martiality"),
                StatField("magic", "Magic"),
                StatField("craft", "Craft"),
                StatField("piety", "Piety"),
            ),
            ("race", "tribe", "caste", "mortal lineage"),
        ),
        EntityTypeSpec(
            EntityType.MORTAL,
            "Mortal",
            "Mortals",
            "mortal",
            "create_mortal",
            INHABITED,
            True,
            (
                StatField("hp", "HP", 1, lambda rules: rules.limits.hp_cap),
                StatField("strength", "Strength"),
                StatField("agility", "Agility"),
                StatField("intellect", "Intellect"),
                StatField("charisma", "Charisma"),
                StatField("age", "Age", 0, lambda rules: rules.deep_life.lifespan_cap),
                StatField("lifespan", "Lifespan", 1, lambda rules: rules.deep_life.lifespan_cap),
            ),
            ("hero", "king", "seer", "bandit", "artisan", "saint"),
            frozenset({EngineKind.MIRROR_BIRTH, EngineKind.APPRENTICE}),
        ),
        EntityTypeSpec(
            EntityType.ITEM,
            "Item",
            "Items",
            "item",
            "forge_item",
            INHABITED,
            False,
            _percent(("damage", "Damage"), ("protection", "Protection"), ("might", "Might"), ("curse", "Curse")),
            ("weapon", "armour", "shield", "crown", "mirror", "book", "seal", "instrument", "tool", "holy relic"),
            frozenset({EngineKind.CURRENCY}),
        ),
        EntityTypeSpec(
            EntityType.STRUCTURE,
            "Structure",
            "Structures",
            "work",
            "build_structure",
            INHABITED,
            True,
            _percent(("splendor", "Splendor"), ("durability", "Durability"), ("function", "Function")),
            ("temple", "tower", "bridge", "wall", "monument", "tomb", "observatory", "harbour", "mine", "library"),
            frozenset(
                {
                    EngineKind.TEMPLE,
                    EngineKind.WALL,
                    EngineKind.LIBRARY,
                    EngineKind.SCHOOL,
                    EngineKind.OBSERVATORY,
                    EngineKind.COSMIC_ARCHIVE,
                    EngineKind.WONDER,
                }
            ),
        ),
        EntityTypeSpec(
            EntityType.LANGUAGE,
            "Language",
            "Languages",
            "language",
            "create_language",
            frozenset(),
            False,
            _percent(("spread", "Spread"), ("complexity", "Complexity"), ("sacredness", "Sacredness")),
            ("spoken language", "sacred language", "script", "sign language", "merchant cant", "language of the dead"),
            frozenset({EngineKind.DIALECT, EngineKind.PRIMITIVE_LANGUAGE}),
        ),
        EntityTypeSpec(
            EntityType.LEGEND,
            "Legend",
            "Legends",
            "legend",
            "tell_legend",
            frozenset(),
            False,
            _percent(("spread", "Spread")),
            ("lullaby", "taboo", "proverb", "founding myth", "ghost story"),
            frozenset({EngineKind.ASCENSION_MYTH}),
        ),
        EntityTypeSpec(
            EntityType.TRADITION,
            "Tradition",
            "Traditions",
            "tradition",
            "found_tradition",
            frozenset(),
            False,
            _percent(("spread", "Spread"), ("rigidity", "Rigidity")),
            ("festival", "taboo", "funeral rite", "initiation", "oath ceremony", "seasonal offering"),
        ),
        EntityTypeSpec(
            EntityType.CULT,
            "Cult",
            "Cults",
            "cult",
            "found_cult",
            INHABITED,
            True,
            (
                StatField("followers", "Followers", 1, lambda rules: rules.limits.cult_follower_cap),
                StatField("zeal", "Zeal"),
                StatField("influence", "Influence"),
                StatField("devotion", "Devotion", 0, lambda rules: rules.death.devotion_cap),
            ),
            ("temple order", "secret sect", "priest caste"),
            frozenset({EngineKind.RESURRECTION_ORDER}),
        ),
        EntityTypeSpec(
            EntityType.FACTION,
            "Faction",
            "Factions",
            "faction",
            "found_faction",
            INHABITED,
            True,
            _percent(("strength", "Military strength"), ("wealth", "Wealth"), ("sway", "Sway")),
            ("kingdom", "guild", "knightly order", "pirate league", "dynasty"),
            frozenset(
                {
                    EngineKind.REBELS,
                    EngineKind.MERCHANT_GUILD,
                    EngineKind.PRIESTS_COUNCIL,
                    EngineKind.WARRIOR_BAND,
                    EngineKind.INTERWORLD_FEDERATION,
                    EngineKind.WANDERING_MARKET,
                    EngineKind.VOID_PIRATES,
                }
            ),
        ),
        EntityTypeSpec(
            EntityType.CELESTIAL,
            "Celestial body",
            "Celestial bodies",
            "celestial body",
            "hang_celestial",
            frozenset(),
            False,
            _percent(("brightness", "Brightness"), ("influence", "Influence")),
            ("star", "constellation", "moon", "comet", "wandering light", "wound in the sky"),
            frozenset({EngineKind.COMET}),
        ),
        EntityTypeSpec(
            EntityType.ARTWORK,
            "Artwork",
            "Artworks",
            "artwork",
            "create_artwork",
            INHABITED,
            False,
            _percent(("renown", "Renown"), ("influence", "Influence")),
            ("folk song", "epic", "statue", "fresco", "play", "book", "dance", "lament", "weaving"),
        ),
        EntityTypeSpec(
            EntityType.LAW,
            "Law",
            "Laws",
            "law",
            "decree_law",
            INHABITED,
            False,
            _percent(("rigidity", "Rigidity"), ("justice", "Justice")),
            ("penal code", "inheritance rule", "trade law", "worship ban", "blood-feud custom"),
        ),
        EntityTypeSpec(
            EntityType.SPIRIT,
            "Spirit",
            "Spirits",
            "spirit",
            "summon_spirit",
            INHABITED,
            False,
            _percent(("strength", "Strength"), ("unrest", "Unrest")),
            ("ghost", "ancestor spirit", "haunt", "guardian spirit", "lost soul"),
            frozenset({EngineKind.DESCENDED_SOUL, EngineKind.GOD_SHADE}),
        ),
        EntityTypeSpec(
            EntityType.KNOWLEDGE,
            "Knowledge",
            "Knowledge",
            "knowledge",
            "inspire_knowledge",
            frozenset(),
            False,
            (StatField("level", "Level", 1, lambda rules: rules.mortal_tools.knowledge_level_cap), StatField("spread", "Spread")),
            ("agriculture", "metallurgy", "seafaring", "writing", "architecture", "medicine", "school of magic", "art of war", "astronomy"),
        ),
        EntityTypeSpec(
            EntityType.PROPHECY,
            "Prophecy",
            "Prophecies",
            "prophecy",
            "utter_prophecy",
            frozenset(),
            False,
            _percent(("certainty", "Certainty")),
            ("prophecy", "doom sign", "cursed word"),
            frozenset({EngineKind.ECLIPSE_PROPHECY}),
        ),
        EntityTypeSpec(
            EntityType.EVENT,
            "Event",
            "Events",
            "event",
            "start_event",
            INHABITED,
            False,
            _percent(("severity", "Severity")),
            ("war", "plague", "flood", "famine", "migration", "uprising", "catastrophe"),
            frozenset(
                {
                    EngineKind.WAR,
                    EngineKind.BATTLE,
                    EngineKind.SIEGE,
                    EngineKind.MAGIC_STORM,
                    EngineKind.EARTHQUAKE,
                    EngineKind.FLOOD,
                    EngineKind.PLAGUE,
                    EngineKind.DROUGHT,
                    EngineKind.STORM,
                    EngineKind.FAMINE,
                    EngineKind.UPRISING,
                    EngineKind.MIGRATION,
                }
            ),
        ),
        EntityTypeSpec(
            EntityType.VESSEL,
            "Vessel",
            "Vessels",
            "vessel",
            "create_vessel",
            INHABITED,
            False,
            (
                StatField("speed", "Speed"),
                StatField("range", "Range"),
                StatField("crew", "Crew", 0, None),
                StatField("armor", "Armour"),
                StatField("strangeness", "Strangeness"),
            ),
            ("light-sailer", "bone-hulled ship", "generation ship", "ancient gate", "cosmic mount", "divine bridge"),
            frozenset({EngineKind.GHOST_SHIP}),
        ),
        EntityTypeSpec(
            EntityType.OUTER_BEING,
            "Outer Being",
            "Outer Beings",
            "outer being",
            None,
            LAND,
            False,
            _percent(("size", "Size"), ("interest", "Interest"), ("influence", "Influence")),
            ("something from outside the cosmos", "the unnamed thing"),
        ),
        EntityTypeSpec(
            EntityType.ARMY,
            "Army",
            "Armies",
            "army",
            None,
            INHABITED,
            False,
            (
                StatField("size", "Soldiers", lambda rules: rules.campaigns.army_min_soldiers, lambda rules: rules.limits.army_soldier_cap),
                StatField("morale", "Morale"),
                StatField("equipment", "Equipment"),
                StatField("experience", "Experience"),
            ),
            ("army", "legion", "raider band", "holy guard", "fleet"),
            frozenset({EngineKind.PEOPLES_ARMY, EngineKind.HOLY_GUARD, EngineKind.MERCENARY_ARMY}),
        ),
        EntityTypeSpec(
            EntityType.TRADE_ROUTE,
            "Trade route",
            "Trade routes",
            "trade route",
            None,
            LAND,
            False,
            (
                StatField("capacity", "Capacity", lambda rules: 0, lambda rules: rules.trade_routes.capacity_cap),
                StatField("danger", "Danger"),
                StatField("renown", "Renown"),
                StatField("culture", "Carried culture"),
            ),
            ("trade road", "caravan way", "sea lane", "river route", "sky lane"),
        ),
        EntityTypeSpec(
            EntityType.DISEASE,
            "Disease",
            "Diseases",
            "disease",
            None,
            LAND,
            False,
            (
                StatField("virulence", "Virulence"),
                StatField("lethality", "Lethality"),
                StatField("infected", "Infected", lambda rules: 0, lambda rules: rules.limits.people_population_cap),
                StatField("dead", "Dead", lambda rules: 0, lambda rules: rules.limits.people_population_cap),
            ),
            ("plague", "wasting fever", "river flux", "rot of the lungs", "spirit sickness", "void blight"),
        ),
        EntityTypeSpec(
            EntityType.POLITY,
            "Polity",
            "Polities",
            "realm",
            None,
            frozenset(),
            False,
            (
                StatField("legitimacy", "Legitimacy"),
                StatField("stability", "Stability"),
                StatField("subjects", "Subjects", lambda rules: 0, lambda rules: rules.limits.people_population_cap),
                StatField("territory", "Lands held", lambda rules: 0, lambda rules: 100000),
            ),
            ("kingdom", "chiefdom", "republic", "empire", "theocracy", "merchant league"),
        ),
        EntityTypeSpec(
            EntityType.HOUSE,
            "House",
            "Houses",
            "house",
            None,
            frozenset(),
            False,
            (
                StatField("prestige", "Prestige"),
                StatField("members", "Living members", lambda rules: 0, lambda rules: 100000),
                StatField("wealth", "Wealth"),
            ),
            ("royal house", "noble line", "clan", "merchant dynasty", "priestly lineage"),
        ),
        EntityTypeSpec(
            EntityType.TREATY,
            "Treaty",
            "Treaties",
            "treaty",
            None,
            frozenset(),
            False,
            (
                StatField("parties", "Parties", lambda rules: 0, lambda rules: 1000),
                StatField("trust", "Trust"),
            ),
            ("peace", "alliance", "vassal oath", "marriage pact", "trade pact"),
        ),
        EntityTypeSpec(
            EntityType.IDEOLOGY,
            "Ideology",
            "Ideologies",
            "ideology",
            None,
            frozenset(),
            False,
            (
                StatField("adherents", "Adherents", lambda rules: 0, lambda rules: 100000),
                StatField("appeal", "Appeal"),
            ),
            ("egalitarian creed", "doctrine of divine right", "school of reason", "mercantile creed", "godless creed"),
        ),
        EntityTypeSpec(
            EntityType.RITE,
            "Rite",
            "Rites",
            "rite",
            None,
            frozenset(),
            False,
            (
                StatField("power", "Power", lambda rules: 1, lambda rules: 10),
                StatField("castings", "Castings", lambda rules: 0, lambda rules: 100000),
            ),
            ("calling of flame", "rain summoning", "warding of the walls", "raising of the fallen", "reading of omens"),
        ),
        EntityTypeSpec(
            EntityType.NATURAL_LAW,
            "Natural law",
            "Natural laws",
            "natural law",
            "decree_natural_law",
            frozenset(),
            False,
            (),
            ("return of the dead", "price of magic", "order of the seasons"),
        ),
    )
}

CREATION_BASE_COST_RULES: dict[EntityType, RuleBound] = {
    EntityType.REGION: lambda rules: rules.creation_base_cost.region,
    EntityType.PLACE: lambda rules: rules.creation_base_cost.place,
    EntityType.RESOURCE: lambda rules: rules.creation_base_cost.resource,
    EntityType.SETTLEMENT: lambda rules: rules.creation_base_cost.settlement,
    EntityType.SPECIES: lambda rules: rules.creation_base_cost.species,
    EntityType.PEOPLE: lambda rules: rules.creation_base_cost.people,
    EntityType.MORTAL: lambda rules: rules.creation_base_cost.mortal,
    EntityType.ITEM: lambda rules: rules.creation_base_cost.item,
    EntityType.STRUCTURE: lambda rules: rules.creation_base_cost.structure,
    EntityType.LANGUAGE: lambda rules: rules.creation_base_cost.language,
    EntityType.LEGEND: lambda rules: rules.creation_base_cost.legend,
    EntityType.TRADITION: lambda rules: rules.creation_base_cost.tradition,
    EntityType.CULT: lambda rules: rules.creation_base_cost.cult,
    EntityType.FACTION: lambda rules: rules.creation_base_cost.faction,
    EntityType.CELESTIAL: lambda rules: rules.creation_base_cost.celestial,
    EntityType.ARTWORK: lambda rules: rules.creation_base_cost.artwork,
    EntityType.LAW: lambda rules: rules.creation_base_cost.law,
    EntityType.SPIRIT: lambda rules: rules.creation_base_cost.spirit,
    EntityType.KNOWLEDGE: lambda rules: rules.creation_base_cost.knowledge,
    EntityType.PROPHECY: lambda rules: rules.creation_base_cost.prophecy,
    EntityType.EVENT: lambda rules: rules.creation_base_cost.event,
    EntityType.VESSEL: lambda rules: rules.creation_base_cost.vessel,
    EntityType.OUTER_BEING: lambda rules: rules.creation_base_cost.outer_being,
    EntityType.ARMY: lambda rules: rules.creation_base_cost.army,
    EntityType.NATURAL_LAW: lambda rules: rules.creation_base_cost.natural_law,
    EntityType.TRADE_ROUTE: lambda rules: rules.creation_base_cost.trade_route,
    EntityType.DISEASE: lambda rules: rules.creation_base_cost.disease,
    EntityType.POLITY: lambda rules: rules.creation_base_cost.polity,
    EntityType.HOUSE: lambda rules: rules.creation_base_cost.house,
    EntityType.TREATY: lambda rules: rules.creation_base_cost.treaty,
    EntityType.IDEOLOGY: lambda rules: rules.creation_base_cost.ideology,
    EntityType.RITE: lambda rules: rules.creation_base_cost.rite,
}


def entity_type_spec(entity_type: EntityType) -> EntityTypeSpec:
    return ENTITY_TYPES[entity_type]


def engine_kind_owner(kind: EngineKind) -> EntityType | None:
    return next((spec.type for spec in ENTITY_TYPES.values() if kind in spec.engine_kinds), None)


def can_contain(container: EntityType, contained: EntityType) -> bool:
    return container in ENTITY_TYPES[contained].containers


@dataclass(frozen=True)
class CreationCostEntry:
    entity_type: EntityType
    base_cost: int
    minimum_rarity: Rarity


@dataclass(frozen=True)
class CreationCostTable:
    entries: dict[EntityType, CreationCostEntry]
    cost_per_power_level: int
    in_domain_pct: int
    out_of_domain_pct: int
    creativity_discount_pct: int
    cheap_power_cost_pct: int

    def cost(self, entity_type: EntityType, power_level: int, in_domain: bool, creativity: int, cheap_power: bool = False) -> int:
        percent = PERCENT_MAX
        base = self.entries[entity_type].base_cost + self.cost_per_power_level * power_level
        domain_multiplier = (self.in_domain_pct if in_domain else self.out_of_domain_pct) / percent
        creativity_multiplier = 1 - (creativity / percent) * (self.creativity_discount_pct / percent)
        power_multiplier = self.cheap_power_cost_pct / percent if cheap_power else 1
        return max(1, round(base * domain_multiplier * creativity_multiplier * power_multiplier))


def build_creation_cost_table(rules: Rules) -> CreationCostTable:
    core = rules.core_rules
    entries = {
        entity_type: CreationCostEntry(entity_type, read(rules), creation_gate_rarity(rules, entity_type))
        for entity_type, read in CREATION_BASE_COST_RULES.items()
    }
    return CreationCostTable(
        entries=entries,
        cost_per_power_level=core.cost_per_power_level,
        in_domain_pct=core.cost_in_domain_pct,
        out_of_domain_pct=core.cost_out_of_domain_pct,
        creativity_discount_pct=core.creativity_discount_pct,
        cheap_power_cost_pct=core.cheap_power_cost_pct,
    )
