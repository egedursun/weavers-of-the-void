import sqlalchemy as sa
from alembic import op

revision = "c4e8a2f6b913"
down_revision = "d733ac5e0320"
branch_labels = None
depends_on = None

BONDS = sa.table("bonds", sa.column("id"), sa.column("source_node_id"), sa.column("target_node_id"), sa.column("kind"), sa.column("role"))
ENTITIES = sa.table("entities", sa.column("id"), sa.column("entity_type"), sa.column("birth_epoch"))
FOLK = ENTITIES.alias("folk")
TOWN = ENTITIES.alias("town")
RULE = BONDS.alias("rule")
HOME = BONDS.alias("home")
HOMED = sa.select(HOME.c.id).where(HOME.c.source_node_id == FOLK.c.id, HOME.c.role == "homeland", HOME.c.kind.in_(["rules", "lives_in"]))
FIRST_TOWNS = (
    sa.select(RULE.c.id)
    .join(FOLK, FOLK.c.id == RULE.c.source_node_id)
    .join(TOWN, TOWN.c.id == RULE.c.target_node_id)
    .where(
        FOLK.c.entity_type == "people",
        TOWN.c.entity_type == "settlement",
        RULE.c.kind == "rules",
        RULE.c.role.is_(None),
        TOWN.c.birth_epoch == FOLK.c.birth_epoch,
        ~sa.exists(HOMED),
    )
)
HOMELESS_FIRST_TOWNS = sa.update(BONDS).where(BONDS.c.id.in_(FIRST_TOWNS)).values(role="homeland")


def upgrade() -> None:
    op.get_bind().execute(HOMELESS_FIRST_TOWNS)


def downgrade() -> None:
    pass
