from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
WAYS = "section-ways-of-life"
HOLDERS = ("people", "settlement", "polity", "cult", "faction", "mortal", "son", "foreign_god", "creator", "world", "star")
KIND_LEVERS = (
    "authored_kind:create",
    "authored_kind:edit",
    "authored_kind:hold",
    "authored_kind:spread",
    "authored_kind:retire",
    "authored_kind:delete",
    "record_row:edit",
    "record_row:delete",
)

KIND_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="ways_of_life",
        spec_item="S48.12",
        title="Peoples make their own kinds of things as they awaken and grow; kinds spread by contact and trade, fade and retire when unheld",
        subsystem=S.CULTURE,
        phases=("ways_of_life",),
        surface=Surface(drawer=WAYS, layer="map-layer-cuisines"),
        backfill="kinds.legacy_holdings: towns hold the goods they store, the dishes they cook and the ranks of their folk; factions their organisation",
        templates=("awakening.people",),
        tables=(KindHoldingRow.__tablename__, GoodKindRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("invent_kind", "adopt_kind", "forbid_kind", "shape_kind"),
        levers=KIND_LEVERS,
        targets=HOLDERS,
        couplings=(
            Coupling(
                S.ECONOMY, "kinds of things move markets, diets, health and gatherings through their typed properties", E.MODIFIER, "kinds.prestige_spread_pct"
            ),
            Coupling(S.CULTURE, "contact and trade carry kinds between peoples, faster the more prestige a kind lends", E.FLOW, "kinds.spread_pct"),
        ),
    ),
    Mechanic(
        key="kind_derivation",
        spec_item="S48.13",
        title="A kind tied to a dear good gives way to a substitute made from a cheaper one, and two kinds held side by side fuse into a new kind",
        subsystem=S.CULTURE,
        phases=("ways_of_life",),
        surface=Surface(drawer=WAYS),
        backfill="ways_of_life: derived kinds arise only from living epochs",
        templates=("kinds.substituted", "kinds.fused"),
        exposure=Exposure.CONTEXT,
        levers=KIND_LEVERS,
        targets=HOLDERS,
        couplings=(
            Coupling(S.ECONOMY, "a good that stays dear makes its kinds give way to substitutes", E.TRIGGER, "kinds.scarcity_index"),
            Coupling(S.CULTURE, "kinds of one category held strongly side by side fuse into a new kind", E.FLOW, "kinds.fusion_pct"),
        ),
    ),
)
