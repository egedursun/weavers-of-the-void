from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.governance import CliqueAim, MergerKind, VoteBasis

CLIQUE_AIM = total(
    CliqueAim,
    {
        CliqueAim.STRATEGY: Defined(
            "Strategy",
            checked_by=(
                "engine.governance.cliques.lost_heart",
                "engine.governance.heads.head_defies",
                "engine.governance.heads.strategy_vote",
                "tools.mortal.governance.cast_org_vote",
            ),
            used_by=(
                "db.tables.governance.OrgCliqueRow",
                "engine.governance.cliques.bid_from_clique",
                "engine.governance.cliques.form_clique",
                "tools.mortal.governance.cast_org_vote",
            ),
        ),
        CliqueAim.HEAD: Defined(
            "Head",
            checked_by=("engine.governance.cliques.form_clique", "engine.governance.cliques.lost_heart", "engine.governance.heads.clique_choice"),
            used_by=("engine.governance.cliques.form_clique", "tools.mortal.governance.seek_headship"),
        ),
        CliqueAim.SPLIT: Defined("Split", checked_by=("engine.governance.cliques.tend_cliques",), used_by=("engine.governance.cliques.lost_heart",)),
        CliqueAim.MERGER: Defined("Merger", checked_by=("engine.governance.cliques.tend_cliques",), used_by=()),
    },
)

MERGER_KIND = total(
    MergerKind,
    {
        MergerKind.MERGER: Defined(
            "Merger",
            checked_by=(),
            used_by=("db.tables.governance.OrgMergerRow", "engine.governance.cliques.bid_from_clique", "engine.governance.mergers.FRIENDLY"),
        ),
        MergerKind.FRIENDLY_ACQUISITION: Defined(
            "Friendly acquisition",
            checked_by=(),
            used_by=("engine.governance.mergers.FRIENDLY", "engine.governance.mergers.answer_resistance", "engine.governance.strategy.follow_strategy"),
        ),
        MergerKind.HOSTILE_TAKEOVER: Defined(
            "Hostile takeover",
            checked_by=("engine.governance.mergers.answer_bid", "engine.governance.mergers.asking_price"),
            used_by=("engine.governance.strategy.follow_strategy",),
        ),
        MergerKind.BUYOUT: Defined("Buyout", checked_by=(), used_by=("engine.governance.mergers.FRIENDLY",)),
        MergerKind.ABSORPTION_BY_POLITY: Defined(
            "Absorption by polity", checked_by=("tools.mortal.governance.bid_for_org",), used_by=("engine.governance.mergers.FRIENDLY",)
        ),
    },
)

VOTE_BASIS = total(
    VoteBasis,
    {
        VoteBasis.ONE_MEMBER_ONE_VOTE: Defined(
            "One member one vote", checked_by=(), used_by=("catalog.governance.ORG_FORMS", "db.tables.governance.OrgGovernanceRow")
        ),
        VoteBasis.BY_SHARE: Defined(
            "By share",
            checked_by=("engine.governance.seats.member_weights",),
            used_by=("catalog.governance.ORG_FORMS", "engine.governance.seats.seed_governance"),
        ),
        VoteBasis.BY_RANK: Defined(
            "By rank", checked_by=("engine.governance.seats.member_weights",), used_by=("catalog.governance.CULT_FORM", "catalog.governance.ORG_FORMS")
        ),
        VoteBasis.BY_SENIORITY: Defined("By seniority", checked_by=("engine.governance.seats.member_weights",), used_by=("catalog.governance.ORG_FORMS",)),
    },
)
