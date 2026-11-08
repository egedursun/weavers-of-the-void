from enum import StrEnum
from typing import Any

import pytest

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.faith import CultDoctrineRow, SpiritProfileRow
from aerona.domain.enums.faith import FuneralRite, JudgementDoctrine, RebirthPath, SpiritAlignment
from aerona.engine.faith.control import DOCTRINE_SETTERS, SPIRIT_SETTERS

CHOICES = [
    (DOCTRINE_SETTERS, CultDoctrineRow, "judgement", JudgementDoctrine),
    (DOCTRINE_SETTERS, CultDoctrineRow, "rebirth_path", RebirthPath),
    (SPIRIT_SETTERS, SpiritProfileRow, "alignment", SpiritAlignment),
    (SPIRIT_SETTERS, SpiritProfileRow, "rite", FuneralRite),
]


@pytest.mark.parametrize(("setters", "table", "key", "kind"), CHOICES, ids=[item[2] for item in CHOICES])
async def test_every_value_of_a_chosen_field_can_be_set_and_a_stranger_value_is_refused(
    setters: dict[str, Any], table: type, key: str, kind: type[StrEnum]
) -> None:
    row = table()
    for value in kind:
        await setters[key](None, row, value.value)
        assert getattr(row, key) is value
    with pytest.raises(ValidationFailedError):
        await setters[key](None, row, "no such thing")
