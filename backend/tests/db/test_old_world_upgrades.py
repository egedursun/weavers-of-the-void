import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

VERSIONS = Path(__file__).resolve().parents[2] / "src" / "aerona" / "db" / "alembic" / "versions"
TRADE_AND_WAR = "c52a9d3e6f81_w52_tongues_trade_realms_and_war.py"


def migration(file_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(file_name.removesuffix(".py"), VERSIONS / file_name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def areas(connection: sa.Connection) -> dict[str, str]:
    return {kind: area for kind, area in connection.execute(sa.text("SELECT kind, area FROM law_profiles"))}


def test_laws_of_an_old_world_move_to_their_new_areas_and_back(tmp_path: Path) -> None:
    module = migration(TRADE_AND_WAR)
    law = next(row for row in module.RETYPED if row[0] == "law_profiles")
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            module.op.create_table(
                "law_profiles",
                sa.Column("id", sa.Integer, primary_key=True),
                sa.Column("kind", sa.String(40), nullable=False),
                sa.Column("area", module.enum_of(law[3], law[2]), nullable=False),
            )
            connection.execute(sa.text("INSERT INTO law_profiles (kind, area) VALUES ('slavery', 'property'), ('tithe', 'fiscal'), ('penal_code', 'penal')"))
            module.widen(True, (law,))
            module.move_areas(True)
            module.retype(True, (law,))
            assert areas(connection) == {"slavery": "labour", "tithe": "faith", "penal_code": "penal"}
            module.widen(False, (law,))
            module.move_areas(False)
            module.retype(False, (law,))
            assert areas(connection) == {"slavery": "property", "tithe": "fiscal", "penal_code": "penal"}
    engine.dispose()
