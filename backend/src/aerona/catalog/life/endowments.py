from aerona.domain.enums.endowments import EndowmentPurpose

TOWN_EFFECTS: dict[EndowmentPurpose, tuple[str, int]] = {
    EndowmentPurpose.RELIEF: ("unrest", -1),
    EndowmentPurpose.HEALTH: ("sanitation", 1),
    EndowmentPurpose.WORSHIP: ("piety", 1),
    EndowmentPurpose.WORKS: ("prosperity", 1),
    EndowmentPurpose.HOSPITALITY: ("unrest", -1),
}
