from aerona.catalog.gatherings import HOST_ROLES, INCIDENT_ROLES, TITLE_ROLES
from aerona.domain.enums.gathering import CollectionKind, CollectionRole, GatheringKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.history.collections import title_text

HOST, MOURNED, GUEST = 1, 2, 3
NAMES = {HOST: "Ordrin Keelwright", MOURNED: "Riron", GUEST: "Alsol"}


def test_a_funeral_is_named_for_the_one_mourned_never_for_its_host() -> None:
    members = {HOST: CollectionRole.HOST, MOURNED: CollectionRole.VICTIM, GUEST: CollectionRole.GUEST}
    assert title_text(CollectionKind.FUNERAL, members, [], NAMES) == "Funeral of Riron"


def test_a_wedding_names_both_who_wed_and_its_host_weds_too() -> None:
    members = {HOST: HOST_ROLES[GatheringKind.WEDDING], GUEST: CollectionRole.LEADER}
    assert title_text(CollectionKind.WEDDING, members, [], NAMES) == "Wedding of Ordrin Keelwright and Alsol"


def test_two_names_joined_in_a_title_always_share_one_standing() -> None:
    for kind in CollectionKind:
        for first in CollectionRole:
            for second in CollectionRole:
                if first is second:
                    continue
                title = title_text(kind, {HOST: first, MOURNED: second}, [], NAMES)
                if " and " in title:
                    assert any(first in roles and second in roles for roles in TITLE_ROLES[kind]), (kind, first, second, title)


def test_a_history_with_no_named_member_is_named_for_its_place() -> None:
    assert title_text(CollectionKind.RIOT, {GUEST: CollectionRole.WITNESS}, [MOURNED], NAMES) == "Riot at Riron"


def test_a_founding_is_named_for_what_was_founded_not_for_whom() -> None:
    members = {HOST: INCIDENT_ROLES[IncidentRole.SUBJECT], MOURNED: INCIDENT_ROLES[IncidentRole.PRODUCT]}
    assert title_text(CollectionKind.FOUNDING, members, [], NAMES) == "Founding of Riron"
