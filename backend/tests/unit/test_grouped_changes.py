from aerona.services.books.records import ToldChange, grouped_changes

TAIL = " by the engine in economy"
HEAD = "count of community cohorts of Ilsaren"
MADE = "created an event casualties record of Sobreth"


def shifted(when: str, before: str, after: str, tail: str = TAIL) -> ToldChange:
    return ToldChange(when, HEAD, tail, (before, after))


def test_a_change_told_alone_reads_as_before() -> None:
    told = shifted("epoch 2, year 100", "3", "5")
    assert grouped_changes([told]) == [told.text()] == [f"epoch 2, year 100: {HEAD}: 3 → 5{TAIL}"]


def test_the_same_record_made_many_times_is_told_once_with_every_moment() -> None:
    made = [ToldChange("epoch 4, year 180", MADE, TAIL)] * 3 + [ToldChange("epoch 5, year 220", MADE, TAIL)]
    assert grouped_changes(made) == [f"{MADE}{TAIL}: epoch 4, year 180 (3 times); epoch 5, year 220"]


def test_a_value_changed_again_and_again_reads_as_one_chain_and_breaks_where_it_jumps() -> None:
    series = [shifted("epoch 2, year 100", "3", "5"), shifted("epoch 3, year 150", "5", "4"), shifted("epoch 4, year 200", "9", "8")]
    assert grouped_changes(series) == [f"{HEAD}{TAIL}: 3 → 5 (epoch 2, year 100) → 4 (epoch 3, year 150); 9 → 8 (epoch 4, year 200)"]


def test_changes_with_other_reasons_stay_apart_and_keep_their_order() -> None:
    first = shifted("epoch 2, year 100", "3", "5", f"{TAIL} because famine -2")
    second = shifted("epoch 3, year 150", "5", "4")
    rewritten = ToldChange("epoch 3, year 160", HEAD, TAIL, rewrote="rewrote its list")
    third = shifted("epoch 4, year 200", "4", "6")
    lines = grouped_changes([first, second, rewritten, third])
    assert lines == [first.text(), f"{HEAD}{TAIL}: 5 → 4 (epoch 3, year 150); rewrote its list (epoch 3, year 160); 4 → 6 (epoch 4, year 200)"]


def test_every_moment_and_value_survives_the_grouping() -> None:
    changes = [shifted(f"epoch {epoch}, year {epoch * 50}", str(epoch), str(epoch + (epoch % 3))) for epoch in range(1, 30)]
    text = " ".join(grouped_changes(changes))
    for told in changes:
        assert told.when in text
        assert told.shift is not None and all(value in text for value in told.shift)


def test_a_packed_change_comes_back_whole() -> None:
    for told in (shifted("epoch 1", "a\x1fb", "c"), ToldChange("epoch 1", MADE, TAIL), ToldChange("epoch 2", HEAD, TAIL, rewrote="rewrote name")):
        back = ToldChange.unpacked(told.packed())
        assert back.text() == told.text().replace("\x1f", " ")
