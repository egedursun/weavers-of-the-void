from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class LinkGraphRules:
    auto_repair: int = rule(1, 0, 1, RuleGroup.LINK_GRAPH, "Dangling ends are repaired automatically at epoch end (1 on, 0 off)")
    fate_auto: int = rule(
        1, 0, 1, RuleGroup.LINK_GRAPH, "At epoch end Fate proposes justified links for weakly linked records and names vague links (1 on, 0 off)"
    )
    weak_degree: int = rule(1, 0, 100, RuleGroup.LINK_GRAPH, "A record with this many links or fewer counts as weakly linked")
    fate_batch: int = rule(12, 1, 200, RuleGroup.LINK_GRAPH, "Fate proposes links for at most this many records per request")
    fate_epoch_cap: int = rule(36, 0, 100000, RuleGroup.LINK_GRAPH, "Maximum weak records Fate examines at epoch end")
    candidates: int = rule(10, 1, 100, RuleGroup.LINK_GRAPH, "Number of candidate neighbours shown to Fate per record")
    proposal_cap: int = rule(3, 1, 20, RuleGroup.LINK_GRAPH, "Fate creates at most this many new links for one record at a time")
    reason_min_chars: int = rule(15, 0, 1000, RuleGroup.LINK_GRAPH, "Minimum length of Fate's link justification (characters); shorter ones are rejected")
    companion_reason_min_chars: int = rule(
        40,
        0,
        1000,
        RuleGroup.LINK_GRAPH,
        'Minimum length of Fate\'s "companion" link justification (characters): companionship must describe something lived together',
    )
    companion_reason_min_words: int = rule(6, 0, 100, RuleGroup.LINK_GRAPH, 'Minimum word count of Fate\'s "companion" link justification')
    revisit_epochs: int = rule(10, 0, 10000, RuleGroup.LINK_GRAPH, "A record Fate examined is re-examined at the earliest after this many epochs")
    related_batch: int = rule(40, 1, 1000, RuleGroup.LINK_GRAPH, 'Fate names at most this many unexplained "related" links per request')
    related_epoch_cap: int = rule(80, 0, 100000, RuleGroup.LINK_GRAPH, 'Maximum unexplained "related" links named at epoch end')
    description_trim_chars: int = rule(300, 50, 10000, RuleGroup.LINK_GRAPH, "Length of a record description shown to Fate (characters)")
    summary_list: int = rule(20, 1, 1000, RuleGroup.LINK_GRAPH, "Number of weakest records and recent repairs listed in the connectivity summary")
    name_min_chars: int = rule(
        4, 1, 100, RuleGroup.LINK_GRAPH, "Minimum length of a name for linking a record whose name appears in text (short names mismatch)"
    )
    event_proposal_cap: int = rule(
        8,
        1,
        100,
        RuleGroup.LINK_GRAPH,
        "Fate creates at most this many links at a time for an event much mentioned in the chronicle (war, disaster participants)",
    )
    priority_share_pct: int = rule(
        50, 0, 100, RuleGroup.LINK_GRAPH, "Share reserved on each Fate pass for events, legends and traditions mentioned in the chronicle but not linked (%)"
    )
    subject_cap: int = rule(5, 0, 100, RuleGroup.LINK_GRAPH, "At most this many subjects named in its description are linked to a legend, tradition or artwork")
    main_cluster_healthy_pct: int = rule(
        95, 0, 100, RuleGroup.LINK_GRAPH, "Connectivity is shown as healthy when the main cluster exceeds this percentage of nodes"
    )
