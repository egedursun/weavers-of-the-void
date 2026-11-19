import sqlalchemy as sa
from alembic import op

revision = "bb0bf64f29b3"
down_revision = "c728db1bc3e7"
branch_labels = None
depends_on = None

BALANCELOOP_OLD = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
    "kind_prestige",
    "kind_substitution",
    "policy_grievance",
    "housework_burden",
)
BALANCELOOP_NEW = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
    "kind_prestige",
    "kind_substitution",
    "policy_grievance",
    "housework_burden",
    "cure_resistance",
    "weather_grievance",
)
BALANCELOOP_RENAMED = ()
RETYPED = (("loop_signals", "loop", "loop", BALANCELOOP_OLD, BALANCELOOP_NEW, BALANCELOOP_RENAMED, False),)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def alter(table: str, column: str, name: str, before: tuple[str, ...], after: tuple[str, ...], *, nullable: bool) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(after, name), existing_nullable=nullable)


def retype(forward: bool) -> None:
    for table, column, name, old, new, renamed, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        wide = tuple(dict.fromkeys((*before, *after)))
        alter(table, column, name, before, wide, nullable=nullable)
        for first, second in renamed:
            source, target = (first, second) if forward else (second, first)
            op.execute(sa.text(f"UPDATE {table} SET {column} = :target WHERE {column} = :source").bindparams(target=target, source=source))
        gone = ", ".join(f"'{value}'" for value in wide if value not in after)
        if gone:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})" if nullable else f"DELETE FROM {table} WHERE {column} IN ({gone})")
        alter(table, column, name, wide, after, nullable=nullable)


def upgrade() -> None:
    retype(True)


def downgrade() -> None:
    retype(False)
