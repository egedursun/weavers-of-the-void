from dataclasses import dataclass

from aerona.media.store import MediaStore
from aerona.services.container import Services
from aerona.services.divine_will.index import LoreIndex
from aerona.services.divine_will.library import DivineWillLibrary, library_for
from aerona.services.divine_will_reads import ActionDesk, LoreReads, WillReadServices
from aerona.services.rule_changes import RuleDesk, rule_desk


@dataclass(frozen=True)
class WillHost:
    services: Services
    reads: WillReadServices
    library: DivineWillLibrary

    @property
    def lore_reads(self) -> LoreReads:
        return self.reads.lore_reads

    @property
    def action_desk(self) -> ActionDesk:
        return self.reads.action_desk

    @property
    def lore_index(self) -> LoreIndex:
        return self.services.application.lore_index

    @property
    def attachment_store(self) -> MediaStore:
        return self.services.application.media

    @property
    def rule_desk(self) -> RuleDesk:
        return rule_desk(self.services)


def will_host(services: Services) -> WillHost:
    return WillHost(services=services, reads=WillReadServices(), library=library_for(services, services.application.lore_index))
