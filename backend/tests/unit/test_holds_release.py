from aerona.services.player.catalog import ACTIONS_BY_ID


def test_every_lever_that_can_set_without_holding_can_also_let_a_hold_go() -> None:
    stuck = [
        action_id
        for action_id, spec in ACTIONS_BY_ID.items()
        if (field := spec.input_model.model_fields.get("hold")) is not None
        and field.default is False
        and "release" not in spec.input_model.model_fields
        and f"{action_id.split(':', 1)[0]}:release" not in ACTIONS_BY_ID
    ]
    assert stuck == []
