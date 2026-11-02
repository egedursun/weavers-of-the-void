from aerona.tools.son.memory import clean_plan


def test_plan_drops_tool_names_and_record_numbers() -> None:
    assert clean_plan("Use write_plan then raise the Kael (#12) against #4 Orrin.") == "Use then raise the Kael against Orrin."
