from collections.abc import Callable

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.model import RuleDescriptor
from aerona.services.container import Services
from aerona.services.rules import RulesService


class RuleDesk:
    def __init__(self, rules: RulesService, database: Database, bus: EventBus, discovering: Callable[[], bool]) -> None:
        self.rules = rules
        self.database = database
        self.bus = bus
        self.discovering = discovering

    def find(self, namespace: str, key: str) -> RuleDescriptor | None:
        return next((item for item in self.rules.catalog() if item.namespace == namespace and item.key == key), None)

    async def change(self, namespace: str, key: str, value: float | None) -> RuleDescriptor:
        descriptor = await (self.rules.reset_value(namespace, key) if value is None else self.rules.set_value(namespace, key, value))
        await self.settle({"namespace": namespace, "key": key})
        return descriptor

    async def settle(self, payload: dict[str, str]) -> None:
        if not self.discovering():
            async with self.database.write() as session:
                repository = CosmosRepository(session)
                if await repository.get() is not None:
                    await repository.store_rules(self.rules.current)
        self.bus.publish(EventKind.RULES_CHANGED, payload)


def rule_desk(services: Services) -> RuleDesk:
    return RuleDesk(services.rules, services.database, services.bus, lambda: services.application.discovery.active)
