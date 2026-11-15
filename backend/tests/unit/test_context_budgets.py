from aerona.rules.registry import Rules
from aerona.services.integrity.context_budgets import budget_floors


def test_every_whole_prompt_holds_the_sum_of_its_sections_so_nothing_fitting_is_cut_by_the_whole() -> None:
    rules = Rules()
    context, fate, mortal = rules.context, rules.fate, rules.mortal_tools
    son_sections = (
        context.son_geography_chars,
        context.son_map_chars,
        context.son_cosmos_chars,
        context.son_language_chars,
        context.son_unlocated_chars,
        context.son_chronicle_chars,
    )
    memory = (
        context.memory_creations_chars,
        context.memory_recollections_chars,
        context.memory_about_chars,
        context.memory_folk_beliefs_chars,
        context.memory_messages_chars,
    )
    fate_sections = (
        context.fate_geography_chars,
        context.fate_map_chars,
        context.fate_cosmos_chars,
        context.fate_language_chars,
        context.fate_unlocated_chars,
        context.fate_chronicle_chars,
    )
    judgment = (
        context.fate_summary_chars,
        fate.budget_new_creations_chars,
        fate.budget_old_prophecies_chars,
        fate.budget_epoch_events_chars,
        fate.budget_engine_notes_chars,
        fate.budget_engine_born_chars,
        fate.budget_world_records_chars,
    )
    mortal_sections = (
        mortal.ctx_self_chars,
        mortal.ctx_character_chars,
        mortal.ctx_nearby_chars,
        mortal.ctx_knowledge_chars,
        mortal.ctx_mentions_chars,
        mortal.ctx_languages_chars,
        mortal.ctx_events_chars,
    )
    assert sum(son_sections) <= context.son_summary_chars
    assert sum(memory) <= context.son_memory_chars
    assert context.son_summary_chars + context.son_memory_chars + rules.summoning.opportunities_chars <= context.son_prompt_chars
    assert sum(fate_sections) <= context.fate_summary_chars
    assert sum(judgment) <= fate.budget_judgment_prompt_chars
    assert sum(mortal_sections) <= context.mortal_context_chars
    assert fate.budget_chronicler_engine_chars + fate.budget_name_type_chars + fate.budget_previous_judgments_chars + rules.chronicle_audit.budget_chars <= (
        fate.budget_chronicler_prompt_chars
    )


def test_the_prompt_budgets_leave_the_gods_and_mortals_room_for_a_grown_world() -> None:
    rules = Rules()
    assert rules.context.son_prompt_chars >= 200_000 and rules.context.son_summary_chars >= 100_000
    assert rules.context.mortal_context_chars >= 100_000 and rules.fate.budget_judgment_prompt_chars >= 400_000
    assert rules.model.agent_timeout >= 900 and rules.model.structured_timeout >= 600
    floors = budget_floors()
    assert floors[("context", "son_prompt_chars")] == rules.context.son_prompt_chars and ("model", "agent_timeout") in floors
