from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.gathering import CollectionKind, Milestone

COLLECTION_KIND = total(
    CollectionKind,
    {
        CollectionKind.WAR: Defined(
            "War",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE", "engine.polity.standing.recovery"),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.BATTLE: Defined(
            "Battle",
            checked_by=("catalog.gatherings.NEST_PARENTS", "catalog.norms.GATHERING_SITUATIONS"),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.EPIC_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.SIEGE: Defined(
            "Siege",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE", "catalog.gatherings.NEST_PARENTS", "catalog.norms.GATHERING_SITUATIONS"),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.incident_kinds.g04_body.KINDS",
                "engine.collective.accounts.EPIC_KINDS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.DUEL: Defined(
            "Duel",
            checked_by=("catalog.gatherings.NEST_PARENTS", "catalog.norms.GATHERING_SITUATIONS"),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.incident_kinds.g01_single_combat.KINDS",
                "catalog.incident_kinds.g08_diplomacy.KINDS",
                "engine.collective.accounts.EPIC_KINDS",
                "engine.collective.storylets.duel_between",
            ),
        ),
        CollectionKind.ABDUCTION: Defined(
            "Abduction", checked_by=(), used_by=("catalog.incident_kinds.g01_single_combat.KINDS", "engine.history.collections.SCHEME_COLLECTIONS")
        ),
        CollectionKind.BEAST_ATTACK: Defined(
            "Beast attack",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=("catalog.gatherings.KEY_COLLECTIONS", "catalog.incident_kinds.g01_single_combat.KINDS"),
        ),
        CollectionKind.RAID: Defined("Raid", checked_by=("catalog.gatherings.NEST_PARENTS",), used_by=("catalog.gatherings.KEY_COLLECTIONS",)),
        CollectionKind.PERSECUTION: Defined(
            "Persecution",
            checked_by=("catalog.gatherings.NEST_PARENTS",),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.incident_kinds.g01_single_combat.KINDS",
                "catalog.incident_kinds.g01_single_combat.accused_kind",
                "engine.collective.accounts.FAITH_KINDS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.GRIEF_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.PURGE: Defined(
            "Purge",
            checked_by=("catalog.gatherings.NEST_PARENTS",),
            used_by=(
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.GRIEF_KINDS",
                "engine.collective.accounts.RECORDED",
                "engine.history.collections.from_purges",
            ),
        ),
        CollectionKind.INSURRECTION: Defined(
            "Insurrection",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=(
                "catalog.collective.ACT_COLLECTION",
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.COUP: Defined(
            "Coup",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "catalog.incident_kinds.g07_law.KINDS",
                "engine.collective.accounts.RECORDED",
                "engine.history.collections.SCHEME_COLLECTIONS",
            ),
        ),
        CollectionKind.SUCCESSION_CRISIS: Defined(
            "Succession crisis",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "catalog.incident_kinds.g07_law.KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.OCCUPATION: Defined(
            "Occupation",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE", "catalog.gatherings.NEST_PARENTS"),
            used_by=("engine.collective.accounts.GRIEF_KINDS", "engine.collective.accounts.RECORDED", "engine.history.collections.from_occupations"),
        ),
        CollectionKind.JOURNEY: Defined("Journey", checked_by=("catalog.collective.COLLECTION_FORMATIVE",), used_by=("catalog.gatherings.KEY_COLLECTIONS",)),
        CollectionKind.PILGRIMAGE: Defined(
            "Pilgrimage",
            checked_by=("catalog.gatherings.NEST_PARENTS", "catalog.norms.GATHERING_SITUATIONS"),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.KEY_COLLECTIONS", "engine.collective.accounts.FAITH_KINDS"),
        ),
        CollectionKind.COMPETITION: Defined("Competition", checked_by=(), used_by=("catalog.gatherings.GATHERING_COLLECTIONS",)),
        CollectionKind.PERFORMANCE: Defined(
            "Performance",
            checked_by=("catalog.gatherings.NEST_PARENTS",),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "engine.collective.accounts.STAGED_KINDS"),
        ),
        CollectionKind.PROCESSION: Defined(
            "Procession",
            checked_by=("catalog.norms.GATHERING_SITUATIONS",),
            used_by=("catalog.collective.ACT_COLLECTION", "catalog.gatherings.GATHERING_COLLECTIONS"),
        ),
        CollectionKind.CEREMONY: Defined(
            "Ceremony",
            checked_by=("catalog.norms.GATHERING_SITUATIONS",),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.NEST_PARENTS", "engine.collective.accounts.STAGED_KINDS"),
        ),
        CollectionKind.WEDDING: Defined(
            "Wedding",
            checked_by=("catalog.norms.GATHERING_SITUATIONS", "engine.collective.storylets.cast_wedding_challenge"),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.KEY_COLLECTIONS", "catalog.gatherings.NEST_PARENTS"),
        ),
        CollectionKind.FUNERAL: Defined(
            "Funeral",
            checked_by=("catalog.gatherings.NEST_PARENTS", "catalog.norms.GATHERING_SITUATIONS"),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.KEY_COLLECTIONS", "catalog.incident_kinds.g04_body.KINDS"),
        ),
        CollectionKind.CORONATION: Defined(
            "Accession",
            checked_by=("catalog.gatherings.NEST_PARENTS", "catalog.norms.GATHERING_SITUATIONS"),
            used_by=(
                "catalog.gatherings.GATHERING_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.PRIDE_KINDS",
                "engine.collective.accounts.RECORDED",
                "engine.collective.accounts.STAGED_KINDS",
            ),
        ),
        CollectionKind.FEAST: Defined(
            "Feast",
            checked_by=("catalog.norms.GATHERING_SITUATIONS",),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.NEST_PARENTS", "engine.collective.accounts.STAGED_KINDS"),
        ),
        CollectionKind.TOURNAMENT: Defined(
            "Tournament",
            checked_by=("catalog.gatherings.NEST_PARENTS",),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.NEST_PARENTS", "engine.collective.accounts.STAGED_KINDS"),
        ),
        CollectionKind.HUNT: Defined(
            "Hunt",
            checked_by=("catalog.gatherings.NEST_PARENTS",),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.incident_kinds.g01_single_combat.KINDS"),
        ),
        CollectionKind.COUNCIL: Defined("Council", checked_by=("catalog.norms.GATHERING_SITUATIONS",), used_by=("catalog.gatherings.GATHERING_COLLECTIONS",)),
        CollectionKind.SUMMIT: Defined(
            "Summit",
            checked_by=("catalog.norms.GATHERING_SITUATIONS",),
            used_by=("catalog.gatherings.GATHERING_COLLECTIONS", "catalog.gatherings.KEY_COLLECTIONS", "catalog.incident_kinds.g07_law.KINDS"),
        ),
        CollectionKind.PLAGUE: Defined(
            "Plague",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "catalog.incident_kinds.g04_body.KINDS",
                "catalog.incident_kinds.g04_body.disease_origin",
                "engine.collective.accounts.GRIEF_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.FAMINE: Defined(
            "Famine",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.GRIEF_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.MIGRATION: Defined(
            "Migration",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE", "catalog.gatherings.NEST_PARENTS"),
            used_by=("catalog.gatherings.KEY_COLLECTIONS", "engine.collective.accounts.RECORDED"),
        ),
        CollectionKind.FOUNDING: Defined(
            "Founding",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE", "engine.collective.accounts.found_myth"),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "catalog.incident_kinds.g04_body.KINDS",
                "catalog.incident_kinds.g07_law.KINDS",
                "engine.collective.accounts.GREAT_KINDS",
                "engine.collective.accounts.PRIDE_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.THEFT: Defined("Theft", checked_by=(), used_by=("catalog.gatherings.KEY_COLLECTIONS", "engine.history.collections.SCHEME_COLLECTIONS")),
        CollectionKind.INVESTIGATION: Defined(
            "Investigation",
            checked_by=(),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "catalog.incident_kinds.g07_law.KINDS",
                "engine.collective.accounts.SWORN_KINDS",
            ),
        ),
        CollectionKind.TRIAL: Defined(
            "Trial",
            checked_by=("catalog.gatherings.NEST_PARENTS",),
            used_by=(
                "catalog.gatherings.GATHERING_COLLECTIONS",
                "catalog.gatherings.KEY_PREFIX_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "catalog.incident_kinds.g01_single_combat.sentence_kind",
                "catalog.incident_kinds.g07_law.KINDS",
                "engine.collective.accounts.SWORN_KINDS",
            ),
        ),
        CollectionKind.CONVERSION_WAVE: Defined(
            "Wave of conversion",
            checked_by=(),
            used_by=(
                "catalog.collective.ACT_COLLECTION",
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.FAITH_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.SCHISM: Defined(
            "Schism",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=(
                "catalog.gatherings.KEY_COLLECTIONS",
                "catalog.gatherings.NEST_PARENTS",
                "engine.collective.accounts.FAITH_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.EXCAVATION: Defined(
            "Excavation",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE", "engine.collective.accounts.excavated"),
            used_by=("catalog.gatherings.KEY_PREFIX_COLLECTIONS", "engine.sites.digs.begin"),
        ),
        CollectionKind.HEROQUEST: Defined(
            "Heroquest",
            checked_by=(),
            used_by=(
                "catalog.incident_kinds.g01_single_combat.KINDS",
                "catalog.incident_kinds.g01_single_combat.quest_end",
                "catalog.incident_kinds.g01_single_combat.quest_kind",
                "engine.collective.accounts.EPIC_KINDS",
                "engine.collective.accounts.FAITH_KINDS",
                "engine.collective.accounts.RECORDED",
                "engine.mythic.heroquests.begin_quest",
            ),
        ),
        CollectionKind.RIOT: Defined(
            "Riot",
            checked_by=(),
            used_by=(
                "catalog.collective.ACT_COLLECTION",
                "catalog.incident_kinds.g04_body.KINDS",
                "engine.collective.accounts.GRIEF_KINDS",
                "engine.collective.accounts.RECORDED",
            ),
        ),
        CollectionKind.PANIC: Defined("Panic", checked_by=(), used_by=("catalog.collective.ACT_COLLECTION", "engine.collective.accounts.RECORDED")),
        CollectionKind.MOVEMENT: Defined(
            "Movement",
            checked_by=("catalog.collective.COLLECTION_FORMATIVE",),
            used_by=("catalog.collective.ACT_COLLECTION", "engine.collective.accounts.FAITH_KINDS", "engine.collective.accounts.RECORDED"),
        ),
        CollectionKind.STORYLET: Defined("Storylet", checked_by=(), used_by=("catalog.incident_kinds.g11_social.KINDS", "engine.collective.storylets.begin")),
    },
)

MILESTONE = total(
    Milestone,
    {
        Milestone.BIRTH: Defined("A birth", checked_by=(), used_by=("engine.gatherings.occasions.milestones",)),
        Milestone.COMING_OF_AGE: Defined(
            "Coming of age", checked_by=(), used_by=("engine.customs.age_sets.hold_promotion", "engine.gatherings.occasions.milestones")
        ),
        Milestone.ANNIVERSARY: Defined("An anniversary", checked_by=(), used_by=("engine.gatherings.occasions.milestones",)),
    },
)
