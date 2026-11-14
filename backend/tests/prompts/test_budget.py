from aerona.prompts.budget import BudgetSection, budget, sectioned_budget
from aerona.prompts.filters import count_word, cut_at_word, degree, fair_shares, mood_level, offered, ordinal, share_of

TRIM = 20


def test_budget_keeps_short_text() -> None:
    assert budget("short", 100, "hint", TRIM) == "short"


def test_budget_keeps_whole_lines_and_appends_a_hint() -> None:
    text = "\n".join(["line one", "line two", "line three"])
    result = budget(text, 18, "look with search_entities", TRIM)
    assert result.startswith("line one\nline two")
    assert result.endswith("(+1 more line; look with search_entities)")


def test_budget_cuts_the_first_line_when_nothing_fits() -> None:
    result = budget("x" * 50, 10, "hint", TRIM)
    assert result.startswith("x" * 9 + "…")


def test_budget_partially_keeps_a_long_line_when_there_is_room() -> None:
    text = "a\n" + "b" * 200
    result = budget(text, 60, "hint", TRIM)
    assert "b" * 20 in result
    assert "…" in result


def test_sectioned_budget_drops_empty_sections_and_fits() -> None:
    sections = [BudgetSection("HEADER", 6, "h"), BudgetSection("", 10, "e"), BudgetSection("\n".join(["z" * 40] * 20), 10, "see more")]
    result = sectioned_budget(sections, 200, TRIM)
    assert result.startswith("HEADER\n")
    assert "see more" in result
    assert len(result) < 260


def test_sectioned_budget_returns_everything_when_it_fits() -> None:
    sections = [BudgetSection("a", 1, "h"), BudgetSection("b", 1, "h")]
    assert sectioned_budget(sections, 100, TRIM) == "a\nb"
    assert sectioned_budget([], 100, TRIM) == ""


def test_filters() -> None:
    assert mood_level(0) == "almost none"
    assert mood_level(100) == "about to overflow"
    assert degree(85, "dark") == "very dark"
    assert degree(5, "dark") == "hardly dark at all"
    assert share_of(15, 70) == 10
    assert share_of(1, 1) == 1
    assert ordinal(1) == "1st"
    assert ordinal(12) == "12th"
    assert ordinal(23) == "23rd"
    assert count_word(2) == "two"
    assert count_word(40) == "40"
    assert cut_at_word("salt and bone", 9) == "salt and…"
    assert fair_shares([10, 1000, 50], 300) == [10, 240, 50]
    assert offered(["curse"], [("curse", "c"), ("challenge", "x")]) == ["c"]
    assert offered(None, [("curse", "c")]) == ["c"]
