from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactValue, PlaceRule, ProcessClock, ProcessGroup

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "player.history",
        ProcessGroup.GODS,
        "{account}",
        roles=tuple(RoleSpec(role, required=False, many=True) for role in IncidentRole if role is not IncidentRole.PLACE),
        facts=(FactSpec("account", FactValue.NAME),),
        place=PlaceRule.WHEN_KNOWN,
        clock=ProcessClock.INSTANT,
        chronicle_kind=ChronicleKind.CREATOR_HAND,
        open_facts=True,
    ),
    IncidentKindSpec(
        "legacy.line",
        ProcessGroup.PEOPLES,
        "{account}",
        roles=(RoleSpec(IncidentRole.SUBJECT, required=False, many=True),),
        facts=(FactSpec("account", FactValue.NAME), FactSpec("legacy_key", FactValue.NAME)),
        place=PlaceRule.WHEN_KNOWN,
        clock=ProcessClock.INSTANT,
        legacy=True,
    ),
    IncidentKindSpec(
        "legacy.fold",
        ProcessGroup.PEOPLES,
        "{account}",
        roles=(RoleSpec(IncidentRole.SUBJECT, required=False, many=True),),
        facts=(FactSpec("account", FactValue.NAME), FactSpec("legacy_key", FactValue.NAME)),
        place=PlaceRule.NONE,
        clock=ProcessClock.INSTANT,
        legacy=True,
    ),
)
