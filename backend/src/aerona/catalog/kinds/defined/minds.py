from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.minds import MadeMindsLaw, MadeMindSouls, MindAffect, MindSeat

MADE_MIND_SOULS = total(
    MadeMindSouls,
    {
        MadeMindSouls.NONE: Defined("Never a soul", checked_by=("engine.minds.law.grant_soul", "engine.minds.law.tend_soul"), used_by=()),
        MadeMindSouls.GRANTED: Defined("Only by a god's act", checked_by=(), used_by=("db.tables.minds.MindLawRow", "engine.minds.souls.default_law")),
        MadeMindSouls.EMERGENT: Defined("A soul forms with full will", checked_by=("engine.minds.law.tend_soul",), used_by=()),
        MadeMindSouls.ALWAYS: Defined("Always a soul", checked_by=("engine.minds.law.tend_soul",), used_by=()),
    },
)

MADE_MINDS_LAW = total(
    MadeMindsLaw,
    {
        MadeMindsLaw.NO_WILL: Defined(
            "No will at all", checked_by=("engine.made.genesis.made_minds", "engine.minds.profiles.will_allowed"), used_by=("engine.made.genesis.law_for",)
        ),
        MadeMindsLaw.INSTRUCTED_ONLY: Defined(
            "Instructed only", checked_by=("engine.minds.profiles.will_allowed",), used_by=("engine.minds.profiles.ORIGIN_LAW",)
        ),
        MadeMindsLaw.WILL_MAY_EMERGE: Defined(
            "Will may emerge",
            checked_by=("engine.minds.profiles.law_lets_will_grow",),
            used_by=(
                "db.tables.minds.MindLawRow",
                "engine.made.genesis.law_for",
                "engine.minds.profiles.ORIGIN_LAW",
                "engine.minds.profiles.law_of",
                "engine.minds.souls.default_law",
            ),
        ),
        MadeMindsLaw.WILL_BY_MAKE: Defined("Will as it is made", checked_by=("engine.minds.profiles.law_for",), used_by=()),
    },
)

MIND_AFFECT = total(
    MindAffect,
    {
        MindAffect.NONE: Defined(
            "No feeling",
            checked_by=("engine.body.variants.fearless_share",),
            used_by=(
                "db.tables.minds.MindProfileRow",
                "engine.constructs.making.make_construct",
                "engine.minds.making.apply_outcome",
                "engine.minds.profiles.NO_MIND",
                "engine.minds.profiles.entity_seed",
                "services.player.minds.MindMade",
            ),
        ),
        MindAffect.MODELLED: Defined(
            "Feeling modelled", checked_by=(), used_by=("engine.made.backfill.cores", "engine.made.genesis.made_minds", "tools.mortal.minds.make_mind_tool")
        ),
        MindAffect.FELT: Defined(
            "Feeling felt",
            checked_by=(),
            used_by=("engine.minds.profiles.born", "engine.minds.profiles.entity_seed", "engine.minds.profiles.seed_for", "tools.son.minds.grant_mind"),
        ),
    },
)

MIND_SEAT = total(
    MindSeat,
    {
        MindSeat.BODY: Defined(
            "In one body",
            checked_by=(
                "engine.body.afflictions.transfer_cure",
                "engine.collective.accounts.official_medium",
                "engine.divine.council_order.regulate",
                "engine.divine.council_order.regulation_motion",
                "engine.environment.secrets.sleeping_mind",
                "engine.made.kinds.watch_minds",
                "engine.mind.wider_needs.by_activity_and_make",
                "engine.minds.continuity.carry_soul",
                "engine.minds.crimes.copying_crime",
                "engine.minds.phase.awaken",
                "engine.minds.profiles.profile_from",
                "engine.sites.rooms.furnish",
                "engine.tongues.modality.made_people",
            ),
            used_by=(
                "agents.context.minds_lines.PLAIN_SEATS",
                "api.schemas.cosmography.CosmicBeingRecord",
                "catalog.cosmography.BEING_MODEL",
                "catalog.cosmography.EMBODIED",
                "engine.constructs.making.make_construct",
                "engine.made.backfill.substrates",
                "engine.made.realms.escapes",
                "engine.minds.profiles.born",
                "engine.minds.profiles.entity_seed",
                "engine.powers.phase.end_span",
                "services.player.minds.MindMade",
                "services.player.minds.MindPlace",
                "services.player.minds.StateRestore",
                "tools.mortal.minds.seat_for",
                "tools.son.minds.grant_mind",
            ),
        ),
        MindSeat.BODIES: Defined(
            "Across many bodies",
            checked_by=("engine.powers.phase.gestalts",),
            used_by=(
                "catalog.cosmography.BEING_MODEL",
                "catalog.cosmography.EMBODIED",
                "engine.made.replicators.wake_swarm",
                "engine.minds.profiles.MADE_SEATS",
                "engine.powers.phase.gestalts",
                "engine.powers.phase.hive_minds",
            ),
        ),
        MindSeat.OBJECT: Defined(
            "In an object",
            checked_by=(),
            used_by=(
                "engine.made.realms.UNHOUSED_SEATS",
                "engine.minds.profiles.MADE_SEATS",
                "engine.minds.seat_loss.SEATED_ELSEWHERE",
                "engine.powers.use.MADE_SEATS",
                "tools.mortal.minds.SEATS",
                "tools.mortal.minds.make_mind_tool",
            ),
        ),
        MindSeat.STRUCTURE: Defined(
            "In a structure",
            checked_by=(),
            used_by=(
                "catalog.cosmography.BEING_MODEL",
                "engine.made.backfill.cores",
                "engine.made.genesis.made_minds",
                "engine.made.realms.UNHOUSED_SEATS",
                "engine.minds.profiles.MADE_SEATS",
                "engine.minds.seat_loss.SEATED_ELSEWHERE",
                "engine.powers.use.MADE_SEATS",
                "tools.mortal.minds.SEATS",
            ),
        ),
        MindSeat.NETWORK: Defined(
            "In a network",
            checked_by=(),
            used_by=(
                "engine.made.realms.UNHOUSED_SEATS",
                "engine.minds.profiles.MADE_SEATS",
                "engine.minds.seat_loss.SEATED_ELSEWHERE",
                "engine.powers.use.MADE_SEATS",
                "tools.mortal.minds.SEATS",
            ),
        ),
        MindSeat.MEDIUM: Defined(
            "In a medium",
            checked_by=(),
            used_by=(
                "catalog.cosmography.BEING_MODEL",
                "engine.minds.profiles.MADE_SEATS",
                "engine.minds.seat_loss.SEATED_ELSEWHERE",
                "engine.powers.use.MADE_SEATS",
            ),
        ),
        MindSeat.PLACE: Defined(
            "In a place",
            checked_by=("engine.minds.profiles.profile_from",),
            used_by=(
                "catalog.cosmography.BEING_MODEL",
                "engine.minds.profiles.MADE_SEATS",
                "engine.minds.profiles.seed_for",
                "tools.mortal.minds.SEATS",
                "tools.son.minds.grant_mind",
            ),
        ),
        MindSeat.HOST: Defined(
            "In a host", checked_by=("engine.powers.phase.end_span",), used_by=("engine.minds.seat_loss.SEATED_ELSEWHERE", "engine.powers.effects.possess")
        ),
        MindSeat.REALM: Defined(
            "In a made realm",
            checked_by=(
                "api.routers.minds.node_made_world",
                "engine.made.realms.admit_by_entry",
                "engine.made.realms.minds_inside",
                "engine.minds.seat_loss.seat_lost",
            ),
            used_by=(
                "catalog.cosmography.BEING_MODEL",
                "engine.made.realms.admit_by_entry",
                "engine.made.realms.enter_realm",
                "engine.made.realms.withdraw",
                "engine.minds.profiles.MADE_SEATS",
                "engine.minds.seat_loss.SEATED_ELSEWHERE",
            ),
        ),
        MindSeat.NONE: Defined(
            "No mind",
            checked_by=(
                "engine.made.backfill.cores",
                "engine.made.genesis.made_minds",
                "engine.minds.phase.awaken",
                "services.integrity.minds_links.drop_empty_profiles",
                "tools.son.minds.soul_target",
                "tools.son.minds.still_mind",
            ),
            used_by=(
                "agents.context.minds_lines.PLAIN_SEATS",
                "catalog.cosmography.BEING_MODEL",
                "db.tables.minds.MindProfileRow",
                "engine.minds.continuity.RUNNING_SEATS",
                "engine.minds.profiles.NO_MIND",
                "engine.minds.profiles.entity_seed",
                "engine.minds.seat_loss.lose_seat",
                "services.integrity.minds_links.mend_minds_links",
            ),
        ),
        MindSeat.DIVINE: Defined(
            "Divine", checked_by=("engine.minds.phase.awaken", "engine.minds.profiles.profile_from"), used_by=("engine.minds.profiles.seed_for",)
        ),
    },
)
