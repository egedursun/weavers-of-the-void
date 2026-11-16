from dataclasses import dataclass

from aerona.domain.enums.action import ActionKind, ActionPolarity
from aerona.domain.enums.creator import CreatorPassion

A = ActionKind
P = CreatorPassion


@dataclass(frozen=True)
class PassionSpec:
    passion: CreatorPassion
    label: str
    hint: str


CREATOR_PASSIONS: dict[CreatorPassion, PassionSpec] = {
    spec.passion: spec
    for spec in (
        PassionSpec(P.ORDER, "Order", "laws, borders, things falling into place"),
        PassionSpec(P.CHAOS, "Chaos", "destruction, disasters, unexpected transformations"),
        PassionSpec(P.BEAUTY, "Beauty", "art, works, songs, crafted things"),
        PassionSpec(P.KNOWLEDGE, "Knowledge", "taught knowledge, writing, discovery"),
        PassionSpec(P.WAR, "War", "conflict, heroism, conquest"),
        PassionSpec(P.MERCY, "Mercy", "miracles, healing, forgiven crimes"),
        PassionSpec(P.CREATION, "Creation", "new worlds, stars, new peoples"),
        PassionSpec(P.SILENCE, "Silence", "an untouched world, children left to themselves"),
    )
}

ACTION_PASSIONS: dict[ActionKind, frozenset[CreatorPassion]] = {
    A.CREATE_WORLD: frozenset({P.CREATION}),
    A.BIRTH_WORLD: frozenset({P.CREATION}),
    A.IGNITE_STAR: frozenset({P.CREATION}),
    A.HANG_STAR: frozenset({P.CREATION}),
    A.REKINDLE_STAR: frozenset({P.CREATION}),
    A.REVELATION: frozenset({P.CREATION}),
    A.SUMMON_SON: frozenset({P.CREATION}),
    A.AWAKEN_PEOPLES: frozenset({P.CREATION}),
    A.DISASTER: frozenset({P.CHAOS}),
    A.CURSE: frozenset({P.CHAOS}),
    A.LINEAGE_CURSE: frozenset({P.CHAOS}),
    A.WRATH: frozenset({P.CHAOS}),
    A.WORLD_WRATH: frozenset({P.CHAOS}),
    A.EXTINGUISH_STAR: frozenset({P.CHAOS}),
    A.SEVER_ROUTE: frozenset({P.CHAOS}),
    A.SKY_EVENT: frozenset({P.CHAOS}),
    A.DESTROY: frozenset({P.CHAOS}),
    A.MIRACLE: frozenset({P.MERCY}),
    A.ANSWER_PRAYER: frozenset({P.MERCY}),
    A.FORGIVE: frozenset({P.MERCY}),
    A.PARDON: frozenset({P.MERCY}),
    A.RESURRECT_SON: frozenset({P.MERCY}),
    A.RESURRECT_MORTAL: frozenset({P.MERCY}),
    A.BLESS_HP: frozenset({P.MERCY}),
    A.TEACH_KNOWLEDGE: frozenset({P.KNOWLEDGE}),
    A.CHOOSE_PROPHET: frozenset({P.KNOWLEDGE}),
    A.SEAL_GATE: frozenset({P.ORDER}),
    A.REPAIR_ROUTE: frozenset({P.ORDER}),
    A.CLEANSE_LEAK: frozenset({P.ORDER}),
    A.COMMAND: frozenset({P.ORDER}),
    A.ABSOLUTE_COMMAND: frozenset({P.ORDER}),
    A.EXILE_ENTITY: frozenset({P.ORDER}),
    A.SUPPRESS_REBELLION: frozenset({P.ORDER, P.WAR}),
    A.INCITE_WAR: frozenset({P.WAR}),
    A.DECLARE_WAR: frozenset({P.WAR}),
    A.LAY_SIEGE: frozenset({P.WAR}),
    A.RAISE_ARMY: frozenset({P.WAR}),
    A.DESIGN_UNIT: frozenset({P.WAR}),
    A.OFFER_PEACE: frozenset({P.ORDER}),
    A.KILL_FOREIGN_GOD: frozenset({P.WAR}),
    A.FOREIGN_GOD_WAR: frozenset({P.WAR}),
    A.EDIT_RECORD: frozenset({P.BEAUTY}),
    A.MANIFESTATION: frozenset({P.BEAUTY}),
}

ACTION_POLARITY: dict[ActionKind, ActionPolarity] = {
    **{
        kind: ActionPolarity.BENEVOLENT
        for kind in (
            A.BLESS_ESSENCE,
            A.BLESS_HP,
            A.BLESS_STAT,
            A.BLESS_EXISTENCE,
            A.FORGIVE,
            A.ANSWER_PRAYER,
            A.RESURRECT_SON,
            A.ADD_STAR,
            A.ASCEND,
            A.GRANT_POWER,
        )
    },
    **{
        kind: ActionPolarity.STERN
        for kind in (A.LIGHTNING, A.CHAIN, A.EXILE_SON, A.SUPPRESS_REBELLION, A.CURSE, A.DRAIN_ESSENCE, A.DEVOUR, A.DEMOTE, A.KILL_SON, A.ABSOLUTE_COMMAND)
    },
}


def polarity_of(action: ActionKind) -> ActionPolarity:
    return ACTION_POLARITY.get(action, ActionPolarity.NEUTRAL)
