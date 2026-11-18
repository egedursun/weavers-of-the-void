from alembic import op

revision = "c4e8a2d6f1b3"
down_revision = "7527af03f013"
branch_labels = None
depends_on = None


RENAMED_KINDS = (
    ("horror.route_stitched", "horror.route_reopened"),
    ("travel.route_stitched", "travel.route_reopened"),
    ("tools.son.stitch", "tools.son.seal_leak"),
    ("fate.thread_advanced", "fate.story_advanced"),
    ("fate.thread_closed", "fate.story_closed"),
    ("player.canon.thread_advanced", "player.canon.story_advanced"),
    ("player.canon.thread_closed", "player.canon.story_closed"),
    ("player.canon.thread_opened", "player.canon.story_opened"),
    ("magic.eternal_storm", "magic.lasting_storm"),
    ("institutions.place_swallowed", "institutions.place_absorbed"),
)
KIND_COLUMNS = (("incidents", "kind"), ("chronicle", "template_key"))


def rename(pairs: tuple[tuple[str, str], ...]) -> None:
    for table, column in KIND_COLUMNS:
        for former, current in pairs:
            op.execute(f"UPDATE {table} SET {column} = '{current}' WHERE {column} = '{former}'")


def upgrade() -> None:
    rename(RENAMED_KINDS)


def downgrade() -> None:
    rename(tuple((current, former) for former, current in RENAMED_KINDS))
