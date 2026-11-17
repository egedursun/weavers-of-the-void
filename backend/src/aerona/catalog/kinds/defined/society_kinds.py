from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.society_kinds import (
    OrganisationGovernance,
    OrganisationLegalForm,
    OrganisationMembership,
    OrganisationOwnership,
    OrganisationPurpose,
    ProfessionCategory,
)

ORGANISATION_GOVERNANCE = total(
    OrganisationGovernance,
    {
        OrganisationGovernance.LEADER: Defined(
            "Leader", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "db.tables.society_kinds.OrganisationKindRow")
        ),
        OrganisationGovernance.COUNCIL: Defined("Council", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationGovernance.ASSEMBLY: Defined("Assembly", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationGovernance.HEREDITARY: Defined("Hereditary", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationGovernance.MADE_MIND: Defined("Made mind", checked_by=(), used_by=()),
    },
)

ORGANISATION_LEGAL_FORM = total(
    OrganisationLegalForm,
    {
        OrganisationLegalForm.CHARTERED: Defined("Chartered", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationLegalForm.LICENSED: Defined("Licensed", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationLegalForm.CUSTOMARY: Defined(
            "Customary", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "db.tables.society_kinds.OrganisationKindRow")
        ),
        OrganisationLegalForm.OUTLAWED: Defined(
            "Outlawed", checked_by=("engine.kinds.society.shape_factions",), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)
        ),
        OrganisationLegalForm.SECRET: Defined("Secret", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
    },
)

ORGANISATION_MEMBERSHIP = total(
    OrganisationMembership,
    {
        OrganisationMembership.OPEN: Defined(
            "Open", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "db.tables.society_kinds.OrganisationKindRow")
        ),
        OrganisationMembership.BY_TRADE: Defined("By trade", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationMembership.BY_BIRTH: Defined("By birth", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationMembership.BY_OATH: Defined("By oath", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationMembership.BY_INVITATION: Defined("By invitation", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationMembership.BY_PURCHASE: Defined("By purchase", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationMembership.BY_POWER: Defined("By power", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
    },
)

ORGANISATION_OWNERSHIP = total(
    OrganisationOwnership,
    {
        OrganisationOwnership.MEMBERS: Defined(
            "Members", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "db.tables.society_kinds.OrganisationKindRow")
        ),
        OrganisationOwnership.SHAREHOLDERS: Defined("Shareholders", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationOwnership.FOUNDER: Defined("Founder", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationOwnership.STATE: Defined("State", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationOwnership.FAITH: Defined("Faith", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationOwnership.NONE: Defined("None", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
    },
)

ORGANISATION_PURPOSE = total(
    OrganisationPurpose,
    {
        OrganisationPurpose.TRADE: Defined("Trade", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.CRAFT: Defined("Craft", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.FAITH: Defined("Faith", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.WAR: Defined("War", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.LEARNING: Defined("Learning", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.RULE: Defined("Rule", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.CRIME: Defined("Crime", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.MUTUAL_AID: Defined("Mutual aid", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.LEISURE: Defined("Leisure", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.SECRECY: Defined("Secrecy", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.POLITICS: Defined("Politics", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.EXPLORATION: Defined("Exploration", checked_by=(), used_by=()),
        OrganisationPurpose.MAKING: Defined("Making", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS",)),
        OrganisationPurpose.CARE: Defined("Care", checked_by=(), used_by=()),
    },
)

PROFESSION_CATEGORY = total(
    ProfessionCategory,
    {
        ProfessionCategory.FOOD_PRODUCTION: Defined(
            "Food production", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.CRAFTING: Defined(
            "Crafting", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.TRADE: Defined(
            "Trade", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.TRANSPORT: Defined("Transport", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)),
        ProfessionCategory.CARE: Defined("Care", checked_by=(), used_by=()),
        ProfessionCategory.HEALING: Defined("Healing", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)),
        ProfessionCategory.LEARNING: Defined(
            "Learning", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.FAITH: Defined(
            "Faith", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.RULE_AND_ADMINISTRATION: Defined(
            "Rule and administration", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)
        ),
        ProfessionCategory.LAW: Defined("Law", checked_by=(), used_by=()),
        ProfessionCategory.WAR: Defined(
            "War", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.SECURITY: Defined("Security", checked_by=(), used_by=()),
        ProfessionCategory.ART_AND_ENTERTAINMENT: Defined("Art and entertainment", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)),
        ProfessionCategory.SERVICE: Defined("Service", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS",)),
        ProfessionCategory.BUILDING: Defined(
            "Building", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.EXTRACTION: Defined(
            "Extraction", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_JOBS", "db.kind_concepts.society.BUILT_IN_PROFESSIONS")
        ),
        ProfessionCategory.SCIENCE_AND_ENGINEERING: Defined(
            "Science and engineering", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)
        ),
        ProfessionCategory.INFORMATION: Defined("Information", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)),
        ProfessionCategory.MAKING_MINDS: Defined("Making minds", checked_by=(), used_by=()),
        ProfessionCategory.LIVING_CRAFT: Defined("Living craft", checked_by=(), used_by=()),
        ProfessionCategory.MAGIC: Defined("Magic", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)),
        ProfessionCategory.EXPLORATION: Defined("Exploration", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_PROFESSIONS",)),
    },
)
