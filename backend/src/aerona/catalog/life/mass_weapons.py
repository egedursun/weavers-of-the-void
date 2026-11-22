from aerona.domain.enums.mass_weapons import ProgrammeStage

NEXT = {ProgrammeStage.SOUGHT: ProgrammeStage.BUILDING, ProgrammeStage.BUILDING: ProgrammeStage.READY}

WORK_ON_PROGRAMME_STAGES = frozenset({ProgrammeStage.READY, ProgrammeStage.TESTED})
