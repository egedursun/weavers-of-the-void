from aerona.engine.interconnect.registry import Mechanic, Subsystem

Behaviour = tuple[str, str, str, tuple[str, ...], str, tuple[str, ...], tuple[str, ...], Subsystem, str | None, str]

BODY_GAP_MECHANICS: tuple[Mechanic, ...] = ()
MIND_GAP_MECHANICS: tuple[Mechanic, ...] = ()
LIFE_MECHANICS: tuple[Mechanic, ...] = ()
STANDING_MECHANICS: tuple[Mechanic, ...] = ()
MORTAL_MECHANICS = (*BODY_GAP_MECHANICS, *MIND_GAP_MECHANICS, *LIFE_MECHANICS, *STANDING_MECHANICS)
BEHAVIOURS: tuple[Behaviour, ...] = ()
