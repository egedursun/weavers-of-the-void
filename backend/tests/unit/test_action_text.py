from aerona.catalog.policy import serfdom
from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH
from aerona.core.action_text import ELLIPSIS, readable_summary
from aerona.domain.enums.society import SocialClass
from aerona.migration.legacy.ledger_history import _summary
from aerona.prompts.filters import signed


def test_a_plain_summary_stays_as_it_is() -> None:
    assert readable_summary(None) is None
    assert readable_summary("") == ""
    assert readable_summary("raised a temple") == "raised a temple"


def test_tool_arguments_read_as_prose_and_are_cut_at_the_limit() -> None:
    prose = readable_summary('{"name": "Brookhold", "population": 1200}')
    assert prose is not None and "Brookhold" in prose and "{" not in prose
    cut = readable_summary('{"name": "Brookhold", "description": "' + "long " * 80 + '"}', limit=40)
    assert cut is not None and len(cut) == 40 and cut.endswith(ELLIPSIS)


def test_truncated_arguments_are_still_read() -> None:
    prose = readable_summary('{"name": "Brookh')
    assert prose is not None and "Brookh" in prose and prose.endswith(ELLIPSIS)
    listed = readable_summary('{"tenets": ["mercy", "order"')
    assert listed is not None and "mercy" in listed
    assert readable_summary("{not json at all") == "{not json at all"


def test_signed_numbers_and_serfdom_shifts() -> None:
    assert (signed(3), signed(0), signed(-2)) == ("+3", "0", "-2")
    assert serfdom({"allowed": True})[SocialClass.SERF_OR_SLAVE] < 0 < serfdom({})[SocialClass.SERF_OR_SLAVE]


def test_old_ledger_summaries_are_squeezed_read_and_cut_to_the_ledger_limit() -> None:
    assert _summary(None) is None and _summary("") is None
    assert _summary("raised   a\n temple") == "raised a temple"
    long = _summary("x " * LEDGER_SUMMARY_MAX_LENGTH)
    assert long is not None and len(long) == LEDGER_SUMMARY_MAX_LENGTH and long.endswith(ELLIPSIS)
