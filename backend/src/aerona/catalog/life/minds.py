from collections.abc import Mapping

from aerona.core.total import partial, total
from aerona.domain.enums.constructs import InstructionBinding, OrderKind
from aerona.domain.enums.made import IntrusionAim, MadeMindStance
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.minds import MindMaking

CONTRARY = frozenset(
    {
        frozenset({OrderKind.PROTECT, OrderKind.DESTROY}),
        frozenset({OrderKind.GUARD, OrderKind.DESTROY}),
        frozenset({OrderKind.HOLD_STILL, OrderKind.FOLLOW}),
        frozenset({OrderKind.HOLD_STILL, OrderKind.BUILD}),
        frozenset({OrderKind.HOLD_STILL, OrderKind.GATHER}),
        frozenset({OrderKind.HOLD_STILL, OrderKind.REPLICATE}),
        frozenset({OrderKind.FORBID, OrderKind.SERVE}),
        frozenset({OrderKind.MAINTAIN, OrderKind.DESTROY}),
        frozenset({OrderKind.HOLD_STILL, OrderKind.CARRY}),
        frozenset({OrderKind.TEND, OrderKind.DESTROY}),
    }
)


BINDING_HOLD: Mapping[InstructionBinding, int] = total(
    InstructionBinding,
    {
        InstructionBinding.NONE: 0,
        InstructionBinding.ORDER: 20,
        InstructionBinding.OATH: 40,
        InstructionBinding.GEAS: 70,
        InstructionBinding.SEAL: 90,
        InstructionBinding.OWNERSHIP: 30,
        InstructionBinding.LEASE: 20,
        InstructionBinding.SYMBIOSIS: 60,
    },
)


STANCE_BOND = {
    MadeMindStance.ABOMINATION: -2,
    MadeMindStance.TOOL: 0,
    MadeMindStance.KIN: 1,
    MadeMindStance.SACRED: 2,
    MadeMindStance.SILENT: 0,
    MadeMindStance.REGULATED: 0,
}


MAKING_SKILLS = partial(
    MindMaking,
    {
        MindMaking.CRAFT: (SkillKind.ENGINEERING, SkillKind.MECHANICS, SkillKind.SPELLCRAFT, SkillKind.COMPUTING, SkillKind.SMITHING),
        MindMaking.TRAINING: (SkillKind.COMPUTING, SkillKind.TEACHING, SkillKind.SPELLCRAFT),
        MindMaking.COPYING: (SkillKind.COMPUTING, SkillKind.SPELLCRAFT, SkillKind.RITUAL),
        MindMaking.SUMMONING: (SkillKind.SPELLCRAFT, SkillKind.SPIRIT_SPEAKING, SkillKind.RITUAL),
        MindMaking.GROWING: (SkillKind.MEDICINE, SkillKind.SURGERY, SkillKind.SCIENCE),
        MindMaking.TRANSFER: (SkillKind.COMPUTING, SkillKind.SPELLCRAFT, SkillKind.RITUAL),
        MindMaking.AWAKENING: (SkillKind.SPELLCRAFT, SkillKind.RITUAL, SkillKind.COMPUTING),
    },
    without={MindMaking.DIVINE_GRANT},
)

SHIELDED_HOSTS_INTRUSION_AIMS = frozenset({IntrusionAim.DENY, IntrusionAim.SEIZE, IntrusionAim.ALTER})
