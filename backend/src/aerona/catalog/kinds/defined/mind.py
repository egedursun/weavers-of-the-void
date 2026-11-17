from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.mind import OpinionComponent, TraitEffect

OPINION_COMPONENT = total(
    OpinionComponent,
    {
        OpinionComponent.TRUST: Defined(
            "Trust", checked_by=("catalog.mind.MEMORIES",), used_by=("engine.mind.opinion.components_of", "engine.mortal.acts.update_loyalty")
        ),
        OpinionComponent.FEAR: Defined(
            "Fear", checked_by=("catalog.mind.MEMORIES",), used_by=("engine.mind.opinion.NEGATIVE_COMPONENTS", "engine.mortal.acts.update_loyalty")
        ),
        OpinionComponent.RESPECT: Defined("Respect", checked_by=("catalog.mind.MEMORIES",), used_by=("engine.mortal.acts.update_loyalty",)),
        OpinionComponent.AFFECTION: Defined(
            "Affection", checked_by=("catalog.mind.MEMORIES",), used_by=("engine.mortal.acts.update_loyalty", "engine.mortal.course.swear_kinship")
        ),
        OpinionComponent.GRIEVANCE: Defined(
            "Grievance",
            checked_by=("catalog.mind.MEMORIES",),
            used_by=("engine.mind.opinion.NEGATIVE_COMPONENTS", "engine.mortal.acts.plot", "engine.mortal.acts.update_loyalty"),
        ),
    },
)

TRAIT_EFFECT = total(
    TraitEffect,
    {
        TraitEffect.WAR_APPETITE: Defined("War appetite", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.war_drive",)),
        TraitEffect.BETRAYAL: Defined("Betrayal", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.betrayal_drive",)),
        TraitEffect.CRUELTY: Defined("Cruelty", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.cruelty_drive",)),
        TraitEffect.TRUST: Defined("Trust", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.opinion.compose",)),
        TraitEffect.MEMORY_DECAY: Defined(
            "Memory decay", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.memories.default_decay", "engine.phases.mind.vengeance")
        ),
        TraitEffect.ZEAL: Defined("Zeal", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.zeal_drive",)),
        TraitEffect.AGENT_WEIGHT: Defined("Agent weight", checked_by=("catalog.mind.TRAITS",), used_by=("agents.mortal.candidates",)),
        TraitEffect.LEARNING: Defined("Learning", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.skills.practise",)),
        TraitEffect.DRIFT: Defined("Drift", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.values.drift_person",)),
        TraitEffect.EXPLORATION: Defined("Exploration", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.expedition_drive",)),
        TraitEffect.FERTILITY: Defined("Fertility", checked_by=("catalog.mind.TRAITS",), used_by=("engine.phases.births.couple_chance",)),
        TraitEffect.JUSTICE: Defined("Justice", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.unrest",)),
        TraitEffect.DECEIT: Defined("Deceit", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.deceit_drive", "tools.mortal.war.sabotage")),
        TraitEffect.GREED: Defined("Greed", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.drives.greed_drive",)),
        TraitEffect.COURAGE: Defined(
            "Courage", checked_by=("catalog.mind.TRAITS",), used_by=("engine.military.clash.willpower_of", "engine.military.duels.fighter")
        ),
        TraitEffect.CHARM: Defined("Charm", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mind.opinion.compose",)),
        TraitEffect.SOCIABILITY: Defined("Sociability", checked_by=("catalog.mind.TRAITS",), used_by=("engine.relations.interactions.lands",)),
        TraitEffect.RESILIENCE: Defined("Resilience", checked_by=("catalog.mind.TRAITS",), used_by=("engine.mortal.standing.add_stress",)),
    },
)
