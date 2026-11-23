from aerona.engine.interconnect.compliance import CATALOGUE
from aerona.services.player.catalog import ACTIONS_BY_ID

GENERIC_KIND_LEVERS = frozenset(
    {"authored_kind:create", "authored_kind:edit", "authored_kind:hold", "authored_kind:spread", "authored_kind:retire", "authored_kind:delete"}
)
SHARED_LEVERS = frozenset({"record_row:create", "record_row:edit", "record_row:delete", "profile:set", "profile:release", "lever:pin", *GENERIC_KIND_LEVERS})


def section_of(item: str) -> str:
    return item.split("/", maxsplit=1)[0]


def test_every_lever_of_a_reference_pass_is_filed_under_its_section() -> None:
    misfiled = [
        f"{row.section}: {lever} is filed under {', '.join(ACTIONS_BY_ID[lever].rows) or 'nothing'}"
        for row in CATALOGUE
        if "/RP" in row.section
        for lever in row.levers
        if lever not in SHARED_LEVERS and not any(item == row.section or section_of(item) == section_of(row.section) for item in ACTIONS_BY_ID[lever].rows)
    ]
    assert misfiled == []
