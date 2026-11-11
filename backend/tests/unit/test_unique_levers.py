import pytest
from pydantic import BaseModel

from aerona.services.player.catalog import ACTIONS, ActionSpec, G, Meta, _sync, free, indexed


class Nothing(BaseModel):
    pass


async def handler(_scope: object, _command: Nothing) -> None:
    return None


def test_every_god_lever_id_is_registered_once() -> None:
    assert len({spec.id for spec in ACTIONS}) == len(ACTIONS)


def test_a_lever_registered_twice_fails_at_import() -> None:
    spec: ActionSpec = _sync(Meta("twice:edit", "Edit twice", G.SOCIETY), handler, Nothing, free, ("F32",))
    with pytest.raises(ValueError, match="registered twice"):
        indexed((spec, spec))
