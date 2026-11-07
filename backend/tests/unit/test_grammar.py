from aerona.catalog.god_lines import Line
from aerona.core.grammar import an, fill
from aerona.prompts.environment import environment


def test_an_picks_the_article_by_sound() -> None:
    assert [an(word) for word in ("empire", "oak", "umbra", "kingdom")] == ["an empire", "an oak", "an umbra", "a kingdom"]
    assert [an(number) for number in (8, 9, 11, 18, 110, 18000)] == ["an 8", "a 9", "an 11", "an 18", "a 110", "an 18000"]
    assert an("island", capital=True) == "An island"


def test_templates_fill_articles_by_their_words() -> None:
    assert fill("{x:an} and {y:An}", x="ash", y="bell") == "an ash and A bell"
    assert Line("probe", "{me} issued {kind:an} mandate.").render(me="Ilsa", kind="export ban") == "Ilsa issued an export ban mandate."
    assert environment().from_string("{{ kind | an }}; {{ kind | an(capital=True) }}").render(kind="empire") == "an empire; An empire"
