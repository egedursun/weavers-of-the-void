from aerona.catalog.vehicles import FRAMES, UNWHEELED, frame_layout
from aerona.domain.enums.vehicles import Propulsion, VehicleFrame, VehicleSection

ROWED = frozenset({Propulsion.OARS, Propulsion.SAIL_AND_OAR, Propulsion.CREW, Propulsion.CURRENT})


def sections(frame: VehicleFrame) -> set[VehicleSection]:
    return {part.section for part in frame_layout(frame)}


def test_a_boat_is_driven_by_what_drives_it() -> None:
    assert VehicleSection.ENGINE in sections(VehicleFrame.MOTORBOAT)
    assert VehicleSection.SAILS in sections(VehicleFrame.SAILBOAT)
    assert VehicleSection.OARS in sections(VehicleFrame.ROWBOAT)
    assert VehicleSection.OARS not in sections(VehicleFrame.RIVER_BARGE)


def test_no_frame_carries_oars_or_wheels_it_does_not_have() -> None:
    for frame, spec in FRAMES.items():
        laid = frame_layout(frame)
        names = {part.section for part in laid}
        assert VehicleSection.OARS not in names or spec.propulsion in ROWED, frame
        assert frame not in UNWHEELED or VehicleSection.WHEELS not in names, frame
        assert all(neighbour in names for part in laid for neighbour in part.neighbours), frame
