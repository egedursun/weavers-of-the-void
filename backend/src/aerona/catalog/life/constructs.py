from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.constructs import CommandToken, ContractStatus
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.structure import ConstructionState

MAKING_SKILLS = (SkillKind.ALCHEMY, SkillKind.ENGINEERING)


TOKEN_CLASS = {CommandToken.ITEM: ItemClass.SEAL, CommandToken.NETWORK_KEY: ItemClass.KEY}


FORMS = ((None, BodyFunction.GRASP), (BodyFunction.SPEECH, None), (BodyFunction.LOCOMOTION, BodyFunction.GRASP))

ASSIGN_HUNTER_CONTRACT_STATUSS = (ContractStatus.POSTED, ContractStatus.TAKEN)
MAKE_CONSTRUCT_COMMAND_TOKENS = (CommandToken.ITEM, CommandToken.WORD, CommandToken.BLOODLINE)
DO_BUILD_CONSTRUCTION_STATES = (ConstructionState.PLANNED, ConstructionState.BUILDING)
DO_MAINTAIN_CONSTRUCTION_STATES = (ConstructionState.COMPLETE, ConstructionState.DAMAGED)
