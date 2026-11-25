from aerona.services.divine_will.language import player_language, strays_from, sure_language


def test_a_clear_message_names_its_language() -> None:
    assert sure_language("D\u00fcnyan\u0131n en kalabal\u0131k yerle\u015fiminin refah\u0131n\u0131 on puan art\u0131r.") == "Turkish"
    assert sure_language("Make a plan to found three villages on the northern coast.") == "English"


def test_a_short_unsure_message_takes_the_language_of_the_remembered_exchanges() -> None:
    earlier = [
        "Bu d\u00fcnyadaki b\u00fct\u00fcn sava\u015flar\u0131 eksiksiz listele.",
        "Ostra'n\u0131n o\u011fullar\u0131 kimler, hangisi en g\u00fc\u00e7l\u00fc?",
    ]
    assert sure_language("Hesk'i kutsa") == ""
    assert sure_language("First answer.") == ""
    assert player_language("Hesk'i kutsa", earlier) == "Turkish"


def test_an_unknowable_message_names_no_language() -> None:
    assert player_language("42", []) == ""


def test_one_paragraph_in_another_language_makes_the_answer_stray() -> None:
    turkish = "Kural bulundu ve \u015fu an varsay\u0131lan de\u011ferinde duruyor, d\u00fcnya genelinde ge\u00e7erli."
    mixed = "Plan one now has three steps and nothing has run yet.\n\n" + turkish
    assert strays_from(mixed, "Turkish")
    assert not strays_from(turkish, "Turkish")
