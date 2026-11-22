from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.constructs import MindWill, OrderCondition

MIND_WILL = total(
    MindWill,
    {
        MindWill.NONE: Defined(
            "No will",
            checked_by=(
                "engine.minds.crimes.erasure_crime",
                "engine.minds.phase.awaken",
                "engine.minds.phase.lose_will",
                "engine.minds.profiles.profile_from",
                "engine.minds.profiles.will_allowed",
                "services.integrity.minds_links.drop_empty_profiles",
                "tools.son.minds.awaken_mind",
            ),
            used_by=(
                "db.tables.minds.MindProfileRow",
                "engine.made.genesis.made_minds",
                "engine.minds.making.apply_outcome",
                "engine.minds.profiles.NO_MIND",
                "engine.minds.profiles.WILL_ORDER",
            ),
        ),
        MindWill.INSTRUCTED: Defined(
            "Follows orders",
            checked_by=("engine.minds.phase.grow_will", "engine.minds.phase.lose_will"),
            used_by=(
                "api.routers.pursuits.construct_view",
                "engine.constructs.making.make_construct",
                "engine.constructs.orders.WILL_LADDER",
                "engine.made.backfill.cores",
                "engine.made.genesis.made_minds",
                "engine.minds.profiles.WILL_ORDER",
                "engine.minds.profiles.entity_seed",
                "engine.minds.profiles.will_allowed",
                "engine.minds.sentences.forced_edit",
                "services.player.minds.MindMade",
                "tools.mortal.minds.MakeMindInput",
            ),
        ),
        MindWill.EMERGENT: Defined(
            "A will stirs",
            checked_by=("engine.minds.phase.grow_will",),
            used_by=(
                "engine.constructs.orders.WILL_LADDER",
                "engine.made.replicators.wake_swarm",
                "engine.minds.phase.awaken",
                "engine.minds.phase.grow_will",
                "engine.minds.profiles.WILL_ORDER",
                "engine.minds.profiles.entity_seed",
            ),
        ),
        MindWill.FULL: Defined(
            "A will of its own",
            checked_by=(
                "engine.minds.law.tend_soul",
                "engine.minds.law.tend_status",
                "engine.minds.phase.depart",
                "engine.minds.phase.exceed",
                "engine.minds.phase.minds",
            ),
            used_by=(
                "agents.context.minds_lines.WILLED",
                "engine.constructs.orders.FREE_WILLS",
                "engine.constructs.orders.WILL_LADDER",
                "engine.minds.crimes.WILLED",
                "engine.minds.phase.grow_will",
                "engine.minds.profiles.WILL_ORDER",
                "engine.minds.profiles.born",
                "engine.minds.profiles.entity_seed",
                "engine.minds.profiles.seed_for",
                "engine.powers.phase.gestalts",
                "engine.powers.phase.hive_minds",
                "tools.son.minds.AwakenMindInput",
                "tools.son.minds.grant_mind",
            ),
        ),
        MindWill.EXCEEDING: Defined(
            "Beyond every order",
            checked_by=(
                "engine.constructs.orders.grow_will",
                "engine.constructs.orders.keep_constructs",
                "engine.constructs.orders.pull_switch",
                "engine.made.replicators.stop_runaway",
                "engine.minds.law.tend_soul",
                "engine.minds.law.tend_status",
                "engine.minds.phase.depart",
                "engine.minds.phase.minds",
            ),
            used_by=(
                "agents.context.minds_lines.WILLED",
                "engine.constructs.orders.FREE_WILLS",
                "engine.constructs.orders.WILL_LADDER",
                "engine.minds.crimes.WILLED",
                "engine.minds.phase.exceed",
                "engine.minds.profiles.WILL_ORDER",
            ),
        ),
    },
)

ORDER_CONDITION = total(
    OrderCondition,
    {
        OrderCondition.ALWAYS: Defined(
            "Always",
            checked_by=("engine.constructs.orders.holds",),
            used_by=(
                "db.tables.constructs.InstructionOrderRow",
                "engine.constructs.making.make_construct",
                "services.player.constructs.OrderDraft",
                "tools.mortal.arts.command_construct",
                "tools.son.arts.order_construct",
            ),
        ),
        OrderCondition.WHILE_MAKER_LIVES: Defined(
            "While its maker lives", checked_by=("engine.constructs.orders.holds", "engine.constructs.orders.lapses"), used_by=()
        ),
        OrderCondition.UNTIL_DATE: Defined(
            "Until an epoch",
            checked_by=("engine.constructs.control.give_order", "engine.constructs.orders.holds", "engine.constructs.orders.lapses"),
            used_by=(),
        ),
        OrderCondition.WHEN_ATTACKED: Defined("When attacked", checked_by=("engine.constructs.orders.holds",), used_by=()),
        OrderCondition.WHEN_TOKEN_SHOWN: Defined("When the token is shown", checked_by=("engine.constructs.orders.holds",), used_by=()),
    },
)
