from aerona.domain.enums.node import NodeKind
from aerona.domain.models.base import ValueObject


class NodeRef(ValueObject):
    kind: NodeKind
    id: int

    @property
    def key(self) -> str:
        return f"{self.kind.value}:{self.id}"
