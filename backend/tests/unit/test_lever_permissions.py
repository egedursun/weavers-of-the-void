import pytest

from aerona.domain.enums.accounts import Permission
from aerona.services.accounts.guard import ensure_lever_allowed
from aerona.services.accounts.lever_holds import LEVER_HOLD_FIELDS
from aerona.services.accounts.lever_permissions import LEVER_PERMISSIONS
from aerona.services.accounts.permissions import lever_permission
from aerona.services.player.catalog import ACTIONS


def test_every_lever_of_the_catalogue_has_its_permission_written_down() -> None:
    levers = {spec.id for spec in ACTIONS}
    assert sorted(levers - set(LEVER_PERMISSIONS)) == []
    assert sorted(set(LEVER_PERMISSIONS) - levers) == []


@pytest.mark.parametrize(
    ("lever", "permission"),
    [
        ("lever:suppress", Permission.LOCK_CANON),
        ("lever:pin", Permission.LOCK_CANON),
        ("canon:set", Permission.LOCK_CANON),
        ("affliction:hold", Permission.LOCK_CANON),
        ("profile:release", Permission.LOCK_CANON),
        ("settings", Permission.CHANGE_RULES),
        ("lever:set", Permission.CHANGE_RULES),
        ("prehistory:run", Permission.START_AGES),
        ("fate:retry", Permission.START_AGES),
        ("eras:run", Permission.START_AGES),
        ("soul:release", Permission.EDIT_WORLD),
        ("oath:release", Permission.EDIT_WORLD),
        ("herd:release", Permission.EDIT_WORLD),
        ("son:image_prompt", Permission.EDIT_WORLD),
        ("market:hold_price", Permission.LOCK_CANON),
        ("shortfall:set", Permission.LOCK_CANON),
        ("household:release", Permission.EDIT_WORLD),
        ("contest:hold", Permission.EDIT_WORLD),
        ("foresight:create", Permission.EDIT_WORLD),
    ],
)
def test_levers_are_classed_by_what_they_do(lever: str, permission: Permission) -> None:
    assert lever_permission(lever) is permission


HOLD_FIELD_NAMES = frozenset({"hold", "release", "lock", "locked", "hold_epochs", "hold_phase"})
FLAG_TYPES = frozenset({"<class 'bool'>", "bool | None", "<class 'int'>", "int | None"})
HOLD_HANDLER_PREFIXES = ("hold", "release", "unhold", "unlock", "lock", "pin", "unpin", "suppress", "unsuppress")
IN_WORLD_HOLDS = frozenset(
    {
        "gathering:hold",
        "household:release",
        "servitor:release",
        "herd:release",
        "divine_creature:release",
        "oath:release",
        "soul:release",
        "dimension:release_law",
        "creed:suppress",
        "rumour:suppress",
        "horror:suppress_cult",
    }
)


def hold_fields_of(model: type) -> tuple[str, ...]:
    fields = getattr(model, "model_fields", {})
    return tuple(
        sorted(
            name
            for name, info in fields.items()
            if name in HOLD_FIELD_NAMES and (str(info.annotation) in FLAG_TYPES or str(info.annotation).startswith("list["))
        )
    )


def test_every_lever_that_can_hold_through_its_payload_declares_it() -> None:
    found = {spec.id: fields for spec in ACTIONS if (fields := hold_fields_of(spec.input_model))}
    assert found == LEVER_HOLD_FIELDS


def test_a_lever_whose_handler_holds_or_releases_is_lock_canon() -> None:
    wrong = []
    for spec in ACTIONS:
        handler = spec.sync or spec.job
        name = getattr(getattr(handler, "__wrapped__", handler), "__name__", "")
        if name.startswith(HOLD_HANDLER_PREFIXES) and spec.id not in IN_WORLD_HOLDS and LEVER_PERMISSIONS[spec.id] is not Permission.LOCK_CANON:
            wrong.append(spec.id)
    assert wrong == []


def test_a_payload_that_holds_needs_lock_canon(monkeypatch: pytest.MonkeyPatch) -> None:
    lever = next(lever for lever, fields in LEVER_HOLD_FIELDS.items() if fields == ("hold", "release") and LEVER_PERMISSIONS[lever] is Permission.EDIT_WORLD)
    asked: list[Permission] = []
    monkeypatch.setattr("aerona.services.accounts.guard.ensure_allowed", asked.append)
    model = next(spec.input_model for spec in ACTIONS if spec.id == lever)
    held = model.model_construct(hold=True, release=[])
    ensure_lever_allowed(lever, held)
    assert asked == [Permission.EDIT_WORLD, Permission.LOCK_CANON]
    asked.clear()
    ensure_lever_allowed(lever, model.model_construct(hold=False, release=[]))
    assert asked == [Permission.EDIT_WORLD]
