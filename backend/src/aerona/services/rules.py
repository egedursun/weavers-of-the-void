from collections.abc import Sequence

from sqlalchemy import delete, select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.session import Database
from aerona.db.tables.rule_override import RuleOverrideRow
from aerona.rules.model import RuleDescriptor
from aerona.rules.registry import Rules
from aerona.rules.snapshot import apply_overrides, catalog, coerce, constraint_violations, is_default, with_value

RuleChange = tuple[str, str, float | None]


class RulesService:
    def __init__(self, database: Database) -> None:
        self._database = database
        self._defaults = Rules()
        self._current = self._defaults

    @property
    def current(self) -> Rules:
        return self._current

    async def load(self) -> None:
        async with self._database.read() as session:
            rows = await session.scalars(select(RuleOverrideRow))
            overrides = {(row.namespace, row.key): row.value for row in rows}
        self._current = apply_overrides(self._defaults, overrides)

    def catalog(self) -> list[RuleDescriptor]:
        return catalog(self._current)

    async def set_value(self, namespace: str, key: str, value: float) -> RuleDescriptor:
        coerced = coerce(self._defaults, namespace, key, value)
        violations = constraint_violations(with_value(self._current, namespace, key, coerced))
        if violations:
            raise ValidationFailedError(" ".join(violations))
        async with self._database.write() as session:
            if is_default(self._defaults, namespace, key, coerced):
                await session.execute(delete(RuleOverrideRow).where(RuleOverrideRow.namespace == namespace, RuleOverrideRow.key == key))
            else:
                await session.merge(RuleOverrideRow(namespace=namespace, key=key, value=float(coerced)))
        await self.load()
        return self._find(namespace, key)

    async def reset_value(self, namespace: str, key: str) -> RuleDescriptor:
        async with self._database.write() as session:
            await session.execute(delete(RuleOverrideRow).where(RuleOverrideRow.namespace == namespace, RuleOverrideRow.key == key))
        await self.load()
        return self._find(namespace, key)

    async def apply_batch(self, changes: Sequence[RuleChange], *, reset_all: bool = False) -> None:
        async with self._database.read() as session:
            rows = list(await session.scalars(select(RuleOverrideRow)))
        overrides: dict[tuple[str, str], float] = {} if reset_all else {(row.namespace, row.key): row.value for row in rows}
        for namespace, key, value in changes:
            self._find(namespace, key)
            coerced = None if value is None else coerce(self._defaults, namespace, key, value)
            if coerced is None or is_default(self._defaults, namespace, key, coerced):
                overrides.pop((namespace, key), None)
            else:
                overrides[(namespace, key)] = float(coerced)
        violations = constraint_violations(apply_overrides(self._defaults, overrides))
        if violations:
            raise ValidationFailedError(" ".join(violations))
        async with self._database.write() as session:
            await session.execute(delete(RuleOverrideRow))
            session.add_all(RuleOverrideRow(namespace=namespace, key=key, value=value) for (namespace, key), value in overrides.items())
        await self.load()

    async def reset_all(self) -> None:
        async with self._database.write() as session:
            await session.execute(delete(RuleOverrideRow))
        await self.load()

    def _find(self, namespace: str, key: str) -> RuleDescriptor:
        found = next((item for item in self.catalog() if item.namespace == namespace and item.key == key), None)
        if found is None:
            raise NotFoundError(f"Unknown rule {namespace}.{key}.")
        return found
