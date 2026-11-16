from dataclasses import dataclass

from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import CouncilMotion, SonPunishment, VotingRule


@dataclass(frozen=True)
class Motion:
    motion: CouncilMotion
    target_node_id: int | None = None
    world_id: int | None = None
    school: MagicSchool | None = None
    punishment: SonPunishment | None = None
    voting_rule: VotingRule | None = None
