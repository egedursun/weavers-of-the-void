from alembic import context
from sqlalchemy import create_engine

from aerona.db.library.tables import LibraryBase

configuration = context.config
target_metadata = LibraryBase.metadata


def run_offline() -> None:
    context.configure(url=configuration.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    engine = create_engine(configuration.get_main_option("sqlalchemy.url") or "")
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
