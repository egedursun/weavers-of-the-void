from aerona.db.tables.creator_bonds import CovenantRow, CreatorChosenRow, CreatorDepictionRow, CreatorStandingRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow, SyncretismRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind

DIVINE_POWER_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="divine_power_grammar",
        spec_item="S47.5",
        title="Divine powers built from a verb, an object, a scope, a mode, a cost, a cooldown, a strength and the domains they draw on",
        subsystem=S.GODS,
        phases=("divine_wounds",),
        surface=Surface(drawer="section-divine-powers"),
        backfill="divine_wounds: every old preset gift of a son or a foreign god becomes a row of the grammar on the first epoch, keeping its own effect",
        templates=("divine.power_incident",),
        tables=(DivinePowerRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("wield_power",),
        targets=("son", "foreign_god", "mortal", "people", "settlement"),
        couplings=(
            Coupling(S.GODS, "a power's strength grows with the domains its holder holds", E.MODIFIER, "divine_grammar.effect_pct"),
            Coupling(S.SOCIAL, "triggered powers act when the faithful are threatened or hungry", E.TRIGGER, "divine_grammar.trigger_at"),
            Coupling(S.ECONOMY, "powers over goods make or take stock", E.FLOW, "divine_grammar.goods_per_point"),
        ),
    ),
)
CREATOR_BOND_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="creator_bonds",
        spec_item="S47.5",
        title="How each people holds the Creator, how it pictures it, its covenants and heresies, the Creator's chosen and its absence",
        subsystem=S.GODS,
        phases=("creator_attention",),
        surface=Surface(drawer="section-creator-bonds"),
        backfill="creator_attention: every people is given a view and an image of the Creator on the first epoch, read from its values and tongue",
        templates=("creator.covenant_sealed", "creator.covenant_broken"),
        tables=(CreatorStandingRow.__tablename__, CovenantRow.__tablename__, CreatorChosenRow.__tablename__, CreatorDepictionRow.__tablename__),
        exposure=Exposure.NONE,
        tools=(),
        targets=("people", "mortal", "settlement", "world"),
        couplings=(
            Coupling(S.FAITH, "peoples that worship the Creator feed its essence", E.FLOW, "creator_bonds.worship_essence"),
            Coupling(S.COSMOS, "love and awe that outweigh dread slow the doom clock", E.MODIFIER, "creator_bonds.doom_relief"),
            Coupling(S.SOCIAL, "the chosen draw the envy of those around them", E.TRIGGER, "creator_bonds.chosen_renown"),
        ),
    ),
)
PANTHEON_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="pantheon_life",
        spec_item="S47.5",
        title="How the gods of a world stand together, the ties between them, gods held as one, forgotten gods and rival gods of one domain",
        subsystem=S.GODS,
        phases=("god_relations",),
        surface=Surface(drawer="section-pantheon"),
        backfill="god_relations: every world with gods is given a pantheon and its ties on the first epoch",
        templates=("divine.syncretism", "divine.god_forgotten", "divine.god_returned"),
        tables=(PantheonStructureRow.__tablename__, PantheonTieRow.__tablename__, SyncretismRow.__tablename__),
        exposure=Exposure.NONE,
        tools=(),
        targets=("world", "foreign_god", "son", "people"),
        couplings=(
            Coupling(S.FAITH, "gods held as one pass faith from the lesser to the dominant", E.FLOW, "pantheon_life.blend_faith"),
            Coupling(S.FAITH, "a people whose god fails to deliver turns to a rival of the same domain", E.TRIGGER, "pantheon_life.switch_pct"),
            Coupling(S.GODS, "ties within a pantheon pull each god's stance", E.MODIFIER, "pantheon_life.tie_pull"),
        ),
    ),
)
